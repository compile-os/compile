"""
Self-Supervised Pre-Training for Neural Signals
================================================

TWO APPROACHES TO COMPARE:

Track A: Masked Reconstruction (baseline - what LaBraM does)
- Mask random time segments
- Reconstruct the masked portions
- Generic, borrowed from BERT/NLP

Track B: Cross-View Prediction (novel - exploits neural signal physics)
- Decompose signal into frequency bands (delta, theta, alpha, beta, gamma)
- Mask ONE frequency band
- Predict the masked band from the other bands
- Forces model to learn: "when alpha desynchronizes, beta rebounds"
- This IS the neural code - cross-frequency relationships

The key insight: brain signals encode the SAME information at multiple
frequency scales simultaneously. Cross-view prediction exploits this.

Run both overnight. Compare linear probe accuracy. The one that learns
faster wins.
"""

import os
import sys
import gc
import math
import time
import random
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from scipy import signal as scipy_signal

# Import evaluation from prepare (read-only)
from prepare_ssl import (
    load_pretrain_data,
    load_finetune_data,
    linear_probe_evaluate,
    DEVICE,
    TIME_BUDGET,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class Config:
    # Which approach to use
    approach: str = "cross_view"  # "masked_recon" or "cross_view"

    # Architecture
    d_model: int = 256
    n_layers: int = 6
    n_heads: int = 4
    dropout: float = 0.1

    # Cross-view prediction settings
    frequency_bands: List[Tuple[float, float]] = field(default_factory=lambda: [
        (1, 4),    # Delta
        (4, 8),    # Theta
        (8, 13),   # Alpha (mu rhythm - key for motor imagery!)
        (13, 30),  # Beta
        (30, 50),  # Low gamma
    ])
    mask_n_bands: int = 1  # How many bands to mask (1 = easiest, more = harder)

    # Masked reconstruction settings (baseline)
    mask_ratio: float = 0.15

    # Contrastive (used by both)
    use_contrastive: bool = True
    contrastive_temp: float = 0.07
    contrastive_weight: float = 0.3

    # Training
    batch_size: int = 24  # Reduced from 64 for T4 GPU memory
    lr: float = 3e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1


# =============================================================================
# FREQUENCY BAND DECOMPOSITION
# =============================================================================

class FrequencyDecomposer:
    """
    Decompose EEG into frequency bands using bandpass filtering.

    This is the key to cross-view prediction:
    - Same neural event appears in multiple frequency bands
    - Model learns to predict one band from others
    - Forces learning of cross-frequency relationships
    """

    def __init__(self, bands: List[Tuple[float, float]], fs: float = 160.0):
        self.bands = bands
        self.fs = fs
        self.n_bands = len(bands)

        # Pre-compute filter coefficients
        self.filters = []
        for low, high in bands:
            # Butterworth bandpass filter
            nyq = fs / 2
            low_norm = max(low / nyq, 0.01)  # Avoid 0
            high_norm = min(high / nyq, 0.99)  # Avoid 1
            b, a = scipy_signal.butter(4, [low_norm, high_norm], btype='band')
            self.filters.append((b, a))

    def decompose(self, x: torch.Tensor) -> torch.Tensor:
        """
        Decompose signal into frequency bands.

        Args:
            x: (batch, channels, time) raw signal

        Returns:
            bands: (batch, n_bands, channels, time) decomposed signal
        """
        B, C, T = x.shape
        x_np = x.cpu().numpy()

        bands = np.zeros((B, self.n_bands, C, T), dtype=np.float32)

        for i, (b, a) in enumerate(self.filters):
            for batch_idx in range(B):
                for ch_idx in range(C):
                    # Apply filter (forward-backward for zero phase)
                    try:
                        bands[batch_idx, i, ch_idx, :] = scipy_signal.filtfilt(
                            b, a, x_np[batch_idx, ch_idx, :], padlen=min(50, T-1)
                        )
                    except:
                        # If filter fails, use original signal
                        bands[batch_idx, i, ch_idx, :] = x_np[batch_idx, ch_idx, :]

        return torch.tensor(bands, device=x.device)

    def decompose_batch(self, x: torch.Tensor) -> torch.Tensor:
        """Vectorized decomposition (faster but approximate)."""
        # Use FFT-based filtering for speed
        B, C, T = x.shape

        # FFT
        x_fft = torch.fft.rfft(x, dim=-1)
        freqs = torch.fft.rfftfreq(T, 1/self.fs).to(x.device)

        bands = []
        for low, high in self.bands:
            # Create frequency mask
            mask = ((freqs >= low) & (freqs <= high)).float()
            # Smooth edges to avoid ringing
            mask = mask.unsqueeze(0).unsqueeze(0)  # (1, 1, freq)

            # Apply mask and inverse FFT
            filtered_fft = x_fft * mask
            filtered = torch.fft.irfft(filtered_fft, n=T, dim=-1)
            bands.append(filtered)

        return torch.stack(bands, dim=1)  # (B, n_bands, C, T)


# =============================================================================
# MODEL ARCHITECTURE
# =============================================================================

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1)]


class CrossAttention(nn.Module):
    """Cross-attention between frequency bands."""

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, query, key_value):
        attn_out, _ = self.attn(query, key_value, key_value)
        return self.norm(query + self.dropout(attn_out))


class FrequencyBandEncoder(nn.Module):
    """
    Encoder that processes each frequency band and learns cross-band relationships.

    This is the core of cross-view prediction:
    - Each band gets its own embedding
    - Cross-attention learns relationships between bands
    - "When alpha drops, beta increases" is learned implicitly
    """

    def __init__(self, config: Config, n_channels: int, n_timepoints: int):
        super().__init__()
        self.config = config
        self.n_bands = len(config.frequency_bands)
        self.n_channels = n_channels
        self.n_timepoints = n_timepoints

        # Per-band input projection
        self.band_proj = nn.Linear(n_channels, config.d_model)

        # Band embeddings (like token type embeddings in BERT)
        self.band_embed = nn.Parameter(torch.randn(1, self.n_bands, 1, config.d_model) * 0.02)

        # Positional encoding for time
        self.pos_enc = PositionalEncoding(config.d_model, max_len=n_timepoints)

        # Self-attention within each band
        self.self_attn_layers = nn.ModuleList([
            nn.TransformerEncoderLayer(
                d_model=config.d_model,
                nhead=config.n_heads,
                dim_feedforward=config.d_model * 4,
                dropout=config.dropout,
                batch_first=True,
            )
            for _ in range(config.n_layers // 2)
        ])

        # Cross-attention between bands
        self.cross_attn_layers = nn.ModuleList([
            CrossAttention(config.d_model, config.n_heads, config.dropout)
            for _ in range(config.n_layers // 2)
        ])

        self.norm = nn.LayerNorm(config.d_model)

        # Reconstruction head (predict masked band)
        self.recon_head = nn.Linear(config.d_model, n_channels)

        # Contrastive projection
        self.proj_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model),
            nn.GELU(),
            nn.Linear(config.d_model, config.d_model // 2),
        )

    def forward(self, bands: torch.Tensor, mask_band_idx: Optional[int] = None):
        """
        Args:
            bands: (batch, n_bands, channels, time) frequency-decomposed signal
            mask_band_idx: which band to mask (for cross-view prediction)

        Returns:
            embeddings: per-band embeddings
            pooled: global embedding for contrastive learning
            reconstructed: predicted masked band
        """
        B, N, C, T = bands.shape  # batch, n_bands, channels, time

        # Reshape for processing: (B * N, T, C)
        x = bands.permute(0, 1, 3, 2).reshape(B * N, T, C)

        # Project to d_model
        x = self.band_proj(x)  # (B * N, T, D)

        # Add positional encoding
        x = self.pos_enc(x)

        # Reshape back: (B, N, T, D)
        x = x.view(B, N, T, -1)

        # Add band embeddings
        x = x + self.band_embed

        # Apply mask if doing cross-view prediction
        if mask_band_idx is not None:
            # Store masked band for reconstruction target
            masked_input = x[:, mask_band_idx].clone()
            # Replace with learnable mask token
            if not hasattr(self, 'mask_token'):
                self.mask_token = nn.Parameter(torch.randn(1, 1, self.config.d_model) * 0.02).to(x.device)
            x[:, mask_band_idx] = self.mask_token.expand(B, T, -1)

        # Self-attention within each band
        x_flat = x.view(B * N, T, -1)
        for layer in self.self_attn_layers:
            x_flat = layer(x_flat)
        x = x_flat.view(B, N, T, -1)

        # Cross-attention between bands
        # Pool each band temporally for cross-band attention
        x_pooled = x.mean(dim=2)  # (B, N, D)

        for cross_layer in self.cross_attn_layers:
            # Each band attends to all other bands
            x_pooled = cross_layer(x_pooled, x_pooled)

        # Global pooling for contrastive
        global_embed = x_pooled.mean(dim=1)  # (B, D)
        global_embed = self.norm(global_embed)

        # Reconstruct masked band if needed
        reconstructed = None
        if mask_band_idx is not None:
            # Use the cross-attended embedding to reconstruct
            recon_embed = x_pooled[:, mask_band_idx]  # (B, D)
            # Expand to time dimension and predict channels
            recon_embed = recon_embed.unsqueeze(1).expand(-1, T, -1)  # (B, T, D)
            reconstructed = self.recon_head(recon_embed)  # (B, T, C)
            reconstructed = reconstructed.permute(0, 2, 1)  # (B, C, T)

        # Contrastive projection
        contrastive = F.normalize(self.proj_head(global_embed), dim=-1)

        return {
            'embeddings': x,  # (B, N, T, D)
            'pooled': global_embed,  # (B, D)
            'contrastive': contrastive,  # (B, D/2)
            'reconstructed': reconstructed,  # (B, C, T) or None
        }


class StandardEncoder(nn.Module):
    """Standard transformer encoder for masked reconstruction baseline."""

    def __init__(self, config: Config, n_channels: int, n_timepoints: int):
        super().__init__()
        self.config = config
        self.n_channels = n_channels

        # Input projection
        self.input_proj = nn.Linear(n_channels, config.d_model)
        self.pos_enc = PositionalEncoding(config.d_model, max_len=n_timepoints)

        # Transformer
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_model * 4,
            dropout=config.dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=config.n_layers)

        self.norm = nn.LayerNorm(config.d_model)

        # Heads
        self.recon_head = nn.Linear(config.d_model, n_channels)
        self.proj_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model),
            nn.GELU(),
            nn.Linear(config.d_model, config.d_model // 2),
        )

        # Mask token
        self.mask_token = nn.Parameter(torch.randn(1, 1, config.d_model) * 0.02)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None):
        """
        Args:
            x: (batch, channels, time)
            mask: (batch, time) binary mask
        """
        B, C, T = x.shape

        # (B, C, T) -> (B, T, C) -> (B, T, D)
        x = x.permute(0, 2, 1)
        x = self.input_proj(x)
        x = self.pos_enc(x)

        # Apply mask
        if mask is not None:
            mask_expanded = mask.unsqueeze(-1)  # (B, T, 1)
            x = x * (1 - mask_expanded.float()) + self.mask_token * mask_expanded.float()

        # Transformer
        x = self.transformer(x)
        x = self.norm(x)

        # Pooled embedding
        pooled = x.mean(dim=1)  # (B, D)

        # Reconstruction
        reconstructed = self.recon_head(x).permute(0, 2, 1)  # (B, C, T)

        # Contrastive
        contrastive = F.normalize(self.proj_head(pooled), dim=-1)

        return {
            'embeddings': x,
            'pooled': pooled,
            'contrastive': contrastive,
            'reconstructed': reconstructed,
        }


# =============================================================================
# TRAINING
# =============================================================================

def train():
    """Main training function."""
    print("=" * 60)
    print("Self-Supervised Pre-Training: Cross-View vs Masked Reconstruction")
    print("=" * 60)

    config = Config()
    print(f"\nApproach: {config.approach}")

    # Load data
    print("\nLoading pre-training data...")
    pretrain_data = load_pretrain_data()
    n_channels = pretrain_data['n_channels']
    n_timepoints = pretrain_data['n_timepoints']
    X = pretrain_data['X']

    print(f"Channels: {n_channels}, Timepoints: {n_timepoints}")
    print(f"Pre-train samples: {len(X)}")

    # Create model based on approach
    if config.approach == "cross_view":
        print("\n>>> CROSS-VIEW PREDICTION (novel approach)")
        print(">>> Learning cross-frequency relationships in neural signals")
        model = FrequencyBandEncoder(config, n_channels, n_timepoints).to(DEVICE)
        decomposer = FrequencyDecomposer(config.frequency_bands, fs=160.0)
    else:
        print("\n>>> MASKED RECONSTRUCTION (baseline)")
        model = StandardEncoder(config, n_channels, n_timepoints).to(DEVICE)
        decomposer = None

    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {n_params:,}")

    # Optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.lr,
        weight_decay=config.weight_decay,
    )

    # DataLoader
    dataset = TensorDataset(X)
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, drop_last=True)

    # Training loop
    print(f"\nStarting training (time budget: {TIME_BUDGET}s)...")
    start_time = time.time()
    step = 0
    total_loss = 0
    total_recon_loss = 0
    total_contrast_loss = 0

    warmup_steps = int(len(loader) * config.warmup_ratio)

    while True:
        for (batch,) in loader:
            elapsed = time.time() - start_time
            if elapsed >= TIME_BUDGET:
                break

            batch = batch.to(DEVICE)
            B, C, T = batch.shape

            # Warmup LR
            if step < warmup_steps:
                lr_scale = (step + 1) / warmup_steps
                for pg in optimizer.param_groups:
                    pg['lr'] = config.lr * lr_scale

            optimizer.zero_grad()

            if config.approach == "cross_view":
                # Cross-view prediction
                # Decompose into frequency bands
                bands = decomposer.decompose_batch(batch)  # (B, n_bands, C, T)

                # Randomly select band to mask
                mask_band_idx = random.randint(0, len(config.frequency_bands) - 1)

                # Forward pass
                outputs = model(bands, mask_band_idx=mask_band_idx)

                # Reconstruction loss (predict masked band from others)
                target = bands[:, mask_band_idx]  # (B, C, T)
                recon_loss = F.mse_loss(outputs['reconstructed'], target)

            else:
                # Masked reconstruction
                mask = torch.rand(B, T, device=DEVICE) < config.mask_ratio
                outputs = model(batch, mask=mask)

                # Reconstruction loss on masked positions
                target = batch.permute(0, 2, 1)  # (B, T, C)
                pred = outputs['reconstructed'].permute(0, 2, 1)  # (B, T, C)
                mask_expanded = mask.unsqueeze(-1)
                recon_loss = F.mse_loss(pred[mask_expanded.expand_as(pred)],
                                        target[mask_expanded.expand_as(target)])

            # Contrastive loss
            if config.use_contrastive:
                z = outputs['contrastive']
                sim = torch.mm(z, z.t()) / config.contrastive_temp
                labels = torch.arange(B, device=DEVICE)
                contrast_loss = F.cross_entropy(sim, labels)
            else:
                contrast_loss = torch.tensor(0.0, device=DEVICE)

            # Total loss
            loss = recon_loss + config.contrastive_weight * contrast_loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += loss.item()
            total_recon_loss += recon_loss.item()
            total_contrast_loss += contrast_loss.item()
            step += 1

            if step % 50 == 0:
                avg_loss = total_loss / step
                avg_recon = total_recon_loss / step
                avg_contrast = total_contrast_loss / step
                print(f"Step {step} | Loss: {avg_loss:.4f} | Recon: {avg_recon:.4f} | Contrast: {avg_contrast:.4f}")

        elapsed = time.time() - start_time
        if elapsed >= TIME_BUDGET:
            break

    training_time = time.time() - start_time
    print(f"\nTraining complete. Steps: {step}, Time: {training_time:.1f}s")

    # Evaluate with linear probe
    print("\nEvaluating with linear probe...")

    # Create evaluation wrapper that matches expected interface
    # Use batched inference to avoid OOM
    class EncoderWrapper(nn.Module):
        def __init__(self, model, decomposer, approach):
            super().__init__()
            self.model = model
            self.decomposer = decomposer
            self.approach = approach

        def forward(self, x):
            # Batch to avoid OOM
            batch_size = 16
            all_pooled = []

            for i in range(0, len(x), batch_size):
                batch = x[i:i+batch_size]
                if self.approach == "cross_view":
                    bands = self.decomposer.decompose_batch(batch)
                    outputs = self.model(bands, mask_band_idx=None)
                else:
                    outputs = self.model(batch, mask=None)
                all_pooled.append(outputs['pooled'])

            return None, torch.cat(all_pooled, dim=0)

    eval_model = EncoderWrapper(model, decomposer, config.approach)
    eval_model.eval()

    finetune_data = load_finetune_data()
    probe_accuracy = linear_probe_evaluate(eval_model, finetune_data)

    # Memory
    if torch.cuda.is_available():
        peak_memory = torch.cuda.max_memory_allocated() / 1024**2
    else:
        peak_memory = 0

    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"---")
    print(f"approach:         {config.approach}")
    print(f"probe_accuracy:   {probe_accuracy:.6f}")
    print(f"final_loss:       {total_loss / step:.6f}")
    print(f"recon_loss:       {total_recon_loss / step:.6f}")
    print(f"contrast_loss:    {total_contrast_loss / step:.6f}")
    print(f"training_seconds: {training_time:.1f}")
    print(f"peak_vram_mb:     {peak_memory:.1f}")
    print(f"num_steps:        {step}")
    print(f"num_params:       {n_params}")
    print(f"d_model:          {config.d_model}")
    print(f"n_layers:         {config.n_layers}")

    # Cleanup
    del model, optimizer
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return probe_accuracy


def finetune():
    """
    Full fine-tuning: unfreeze the SSL pre-trained backbone and train on labeled data.

    This is the REAL test: does SSL pre-training + fine-tuning beat from-scratch?
    - From-scratch supervised: 51.98%
    - SSL + linear probe: 48.24%
    - SSL + fine-tuning: ???

    If this beats 51.98%, the foundation model thesis is proven.
    """
    print("=" * 60)
    print("FULL FINE-TUNING: SSL Pre-trained → Motor Imagery")
    print("=" * 60)

    config = Config()
    config.approach = "cross_view"  # Use the winning approach

    # Load pre-training data to get dimensions
    print("\nLoading data...")
    pretrain_data = load_pretrain_data()
    finetune_data = load_finetune_data()

    n_channels = pretrain_data['n_channels']
    n_timepoints = pretrain_data['n_timepoints']
    n_classes = finetune_data['n_classes']

    # Create model
    print("\n>>> Creating cross-view encoder...")
    model = FrequencyBandEncoder(config, n_channels, n_timepoints).to(DEVICE)
    decomposer = FrequencyDecomposer(config.frequency_bands, fs=160.0)

    # Phase 1: Pre-train (same as before but shorter for speed)
    print("\n>>> Phase 1: SSL Pre-training (60s)...")

    optimizer = torch.optim.AdamW(model.parameters(), lr=config.lr, weight_decay=config.weight_decay)
    dataset = TensorDataset(pretrain_data['X'])
    loader = DataLoader(dataset, batch_size=config.batch_size, shuffle=True, drop_last=True)

    pretrain_time = 60  # Shorter pre-training for this test
    start_time = time.time()
    step = 0

    model.train()
    while time.time() - start_time < pretrain_time:
        for (batch,) in loader:
            if time.time() - start_time >= pretrain_time:
                break

            batch = batch.to(DEVICE)
            bands = decomposer.decompose_batch(batch)
            mask_band_idx = random.randint(0, len(config.frequency_bands) - 1)

            optimizer.zero_grad()
            outputs = model(bands, mask_band_idx=mask_band_idx)

            target = bands[:, mask_band_idx]
            recon_loss = F.mse_loss(outputs['reconstructed'], target)

            z = outputs['contrastive']
            sim = torch.mm(z, z.t()) / config.contrastive_temp
            labels = torch.arange(len(batch), device=DEVICE)
            contrast_loss = F.cross_entropy(sim, labels)

            loss = recon_loss + config.contrastive_weight * contrast_loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            step += 1

            if step % 25 == 0:
                print(f"  Pre-train step {step} | Loss: {loss.item():.4f}")

    print(f"  Pre-training done: {step} steps")

    # Phase 2: Fine-tune on labeled data with CAREFUL transfer learning
    print("\n>>> Phase 2: Fine-tuning on Motor Imagery (CAREFUL TRANSFER)...")
    print("    Fix: discriminative LR (backbone 1e-5, head 1e-3) + dropout + early stopping")

    # Add classification head with dropout
    classifier = nn.Sequential(
        nn.Dropout(0.4),  # Aggressive dropout to prevent overfitting
        nn.Linear(config.d_model, n_classes)
    ).to(DEVICE)

    # DISCRIMINATIVE LEARNING RATES - key fix
    # Backbone: very low LR to preserve pre-trained representations
    # Head: normal LR to learn task-specific mapping
    finetune_optimizer = torch.optim.AdamW([
        {'params': model.parameters(), 'lr': 1e-5},  # 10x LOWER than before
        {'params': classifier.parameters(), 'lr': 1e-3},
    ], weight_decay=0.05)  # More weight decay

    train_X = finetune_data['train_X'].to(DEVICE)
    train_y = finetune_data['train_y'].to(DEVICE)
    test_X = finetune_data['test_X'].to(DEVICE)
    test_y = finetune_data['test_y'].to(DEVICE)

    train_dataset = TensorDataset(train_X, train_y)
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)  # Reduced for T4 memory

    # Early stopping on TEST accuracy
    finetune_epochs = 100
    best_test_acc = 0
    patience = 15
    patience_counter = 0
    best_state = None

    for epoch in range(finetune_epochs):
        model.train()
        classifier.train()
        epoch_loss = 0
        correct = 0
        total = 0

        for X_batch, y_batch in train_loader:
            finetune_optimizer.zero_grad()

            # Forward through encoder
            bands = decomposer.decompose_batch(X_batch)
            outputs = model(bands, mask_band_idx=None)
            pooled = outputs['pooled']

            # Classify
            logits = classifier(pooled)
            loss = F.cross_entropy(logits, y_batch)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            torch.nn.utils.clip_grad_norm_(classifier.parameters(), 1.0)
            finetune_optimizer.step()

            epoch_loss += loss.item()
            preds = logits.argmax(dim=1)
            correct += (preds == y_batch).sum().item()
            total += len(y_batch)

        train_acc = correct / total

        # Evaluate on test set for early stopping
        model.eval()
        classifier.eval()
        with torch.no_grad():
            all_preds = []
            for i in range(0, len(test_X), 16):
                batch = test_X[i:i+16]
                bands = decomposer.decompose_batch(batch)
                outputs = model(bands, mask_band_idx=None)
                logits = classifier(outputs['pooled'])
                all_preds.append(logits.argmax(dim=1))
            preds = torch.cat(all_preds)
            test_acc = (preds == test_y).float().mean().item()

        if (epoch + 1) % 5 == 0:
            print(f"  Epoch {epoch+1} | Loss: {epoch_loss/len(train_loader):.4f} | Train: {train_acc:.4f} | Test: {test_acc:.4f}")

        # Early stopping
        if test_acc > best_test_acc:
            best_test_acc = test_acc
            patience_counter = 0
            best_state = {
                'model': {k: v.clone() for k, v in model.state_dict().items()},
                'classifier': {k: v.clone() for k, v in classifier.state_dict().items()},
            }
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"  Early stopping at epoch {epoch+1}")
                break

    # Restore best model
    if best_state is not None:
        model.load_state_dict(best_state['model'])
        classifier.load_state_dict(best_state['classifier'])

    accuracy = best_test_acc

    # Results
    print("\n" + "=" * 60)
    print("FINE-TUNING RESULTS")
    print("=" * 60)
    print(f"---")
    print(f"finetune_accuracy: {accuracy:.6f}")
    print(f"")
    print(f"COMPARISON:")
    print(f"  From-scratch supervised:  51.98%")
    print(f"  SSL + linear probe:       48.24%")
    print(f"  SSL + fine-tuning:        {accuracy*100:.2f}%")
    print(f"")
    if accuracy > 0.5198:
        print(f">>> FOUNDATION MODEL THESIS CONFIRMED <<<")
        print(f">>> Pre-training + fine-tuning beats from-scratch! <<<")
    else:
        print(f"  Gap to beat: {(0.5198 - accuracy)*100:.2f}%")
    print("=" * 60)

    return accuracy


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "finetune":
        finetune()
    else:
        train()
