"""
Compile Autoresearch - Neural Foundation Model Training
Adapted from Karpathy's autoresearch for BCI/neural signals.

THIS IS THE FILE THE AGENT MODIFIES.
Everything is fair game: architecture, optimizer, hyperparameters, etc.

The goal: achieve the lowest cross-subject zero-shot error rate.
Train on N-1 subjects, test on held-out subject with ZERO calibration.

Usage: uv run train.py
"""

import os
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

import gc
import math
import time
from dataclasses import dataclass, asdict

import torch
import torch.nn as nn
import torch.nn.functional as F

from prepare import (
    TIME_BUDGET, SAMPLE_RATE, WINDOW_SIZE, NUM_CLASSES,
    make_cross_subject_loader, get_num_subjects,
    evaluate_cross_subject_accuracy
)

# ---------------------------------------------------------------------------
# Neural Foundation Model
# ---------------------------------------------------------------------------

@dataclass
class CompileConfig:
    n_channels: int = 22          # EEG channels (BNCI2014001 has 22)
    n_timepoints: int = 512       # 4 seconds * 128 Hz
    n_classes: int = 4            # Motor imagery classes
    d_model: int = 256            # Model dimension
    n_heads: int = 8              # Attention heads
    n_layers: int = 4             # Transformer layers
    d_ff: int = 512               # Feedforward dimension
    dropout: float = 0.1          # Dropout rate
    use_spatial_attention: bool = True
    use_temporal_attention: bool = True


def norm(x):
    return F.layer_norm(x, (x.size(-1),))


class SpatialAttention(nn.Module):
    """Attention over EEG channels."""

    def __init__(self, config: CompileConfig):
        super().__init__()
        self.n_heads = config.n_heads
        self.d_model = config.d_model
        self.head_dim = config.d_model // config.n_heads

        self.q = nn.Linear(config.d_model, config.d_model, bias=False)
        self.k = nn.Linear(config.d_model, config.d_model, bias=False)
        self.v = nn.Linear(config.d_model, config.d_model, bias=False)
        self.proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        # x: (B, C, T, D) -> attend over C (channels)
        B, C, T, D = x.shape
        x_flat = x.transpose(1, 2).reshape(B * T, C, D)

        q = self.q(x_flat).view(B * T, C, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k(x_flat).view(B * T, C, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v(x_flat).view(B * T, C, self.n_heads, self.head_dim).transpose(1, 2)

        attn = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = (attn @ v).transpose(1, 2).reshape(B * T, C, D)
        out = self.proj(out)
        out = out.view(B, T, C, D).transpose(1, 2)
        return out


class TemporalAttention(nn.Module):
    """Attention over time steps."""

    def __init__(self, config: CompileConfig):
        super().__init__()
        self.n_heads = config.n_heads
        self.d_model = config.d_model
        self.head_dim = config.d_model // config.n_heads

        self.q = nn.Linear(config.d_model, config.d_model, bias=False)
        self.k = nn.Linear(config.d_model, config.d_model, bias=False)
        self.v = nn.Linear(config.d_model, config.d_model, bias=False)
        self.proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        # x: (B, C, T, D) -> attend over T (time)
        B, C, T, D = x.shape
        x_flat = x.reshape(B * C, T, D)

        q = self.q(x_flat).view(B * C, T, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k(x_flat).view(B * C, T, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v(x_flat).view(B * C, T, self.n_heads, self.head_dim).transpose(1, 2)

        attn = (q @ k.transpose(-2, -1)) * (self.head_dim ** -0.5)
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)

        out = (attn @ v).transpose(1, 2).reshape(B * C, T, D)
        out = self.proj(out)
        out = out.view(B, C, T, D)
        return out


class FeedForward(nn.Module):
    def __init__(self, config: CompileConfig):
        super().__init__()
        self.fc1 = nn.Linear(config.d_model, config.d_ff, bias=False)
        self.fc2 = nn.Linear(config.d_ff, config.d_model, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        x = self.fc1(x)
        x = F.gelu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


class TransformerBlock(nn.Module):
    def __init__(self, config: CompileConfig):
        super().__init__()
        self.config = config

        if config.use_spatial_attention:
            self.spatial_attn = SpatialAttention(config)
            self.spatial_norm = nn.LayerNorm(config.d_model)

        if config.use_temporal_attention:
            self.temporal_attn = TemporalAttention(config)
            self.temporal_norm = nn.LayerNorm(config.d_model)

        self.ff = FeedForward(config)
        self.ff_norm = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x):
        # x: (B, C, T, D)
        if self.config.use_spatial_attention:
            x = x + self.dropout(self.spatial_attn(self.spatial_norm(x)))

        if self.config.use_temporal_attention:
            x = x + self.dropout(self.temporal_attn(self.temporal_norm(x)))

        x = x + self.dropout(self.ff(self.ff_norm(x)))
        return x


class CompileModel(nn.Module):
    """
    Compile Neural Foundation Model.

    Input: (B, n_channels, n_timepoints)
    Output: (B, n_classes) logits for classification

    The embedding layer projects each (channel, time) position to d_model.
    Then we apply spatial-temporal transformer blocks.
    Finally, we pool and classify.
    """

    def __init__(self, config: CompileConfig):
        super().__init__()
        self.config = config

        # Input projection: each channel's time series -> d_model
        self.input_proj = nn.Linear(1, config.d_model)

        # Learnable positional embeddings
        self.channel_embed = nn.Parameter(torch.randn(1, config.n_channels, 1, config.d_model) * 0.02)
        self.time_embed = nn.Parameter(torch.randn(1, 1, config.n_timepoints, config.d_model) * 0.02)

        # Transformer blocks
        self.blocks = nn.ModuleList([
            TransformerBlock(config) for _ in range(config.n_layers)
        ])

        self.norm = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)

        # Classification head
        self.classifier = nn.Linear(config.d_model, config.n_classes)

        # Initialize
        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(self, x):
        # x: (B, C, T)
        B, C, T = x.shape

        # Reshape and project: (B, C, T) -> (B, C, T, 1) -> (B, C, T, D)
        x = x.unsqueeze(-1)
        x = self.input_proj(x)

        # Add positional embeddings
        x = x + self.channel_embed[:, :C, :, :]
        x = x + self.time_embed[:, :, :T, :]

        # Transformer blocks
        for block in self.blocks:
            x = block(x)

        # Global average pooling: (B, C, T, D) -> (B, D)
        x = x.mean(dim=(1, 2))

        # Normalize and classify
        x = self.norm(x)
        x = self.dropout(x)
        logits = self.classifier(x)

        return logits


# ---------------------------------------------------------------------------
# Hyperparameters (EDIT THESE - this is what the agent tunes)
# ---------------------------------------------------------------------------

# Model architecture
D_MODEL = 256           # Model dimension
N_HEADS = 8             # Attention heads
N_LAYERS = 4            # Transformer layers
D_FF = 512              # Feedforward dimension
DROPOUT = 0.1           # Dropout rate
USE_SPATIAL = True      # Use spatial (channel) attention
USE_TEMPORAL = True     # Use temporal attention

# Optimization
LEARNING_RATE = 1e-3    # Learning rate
WEIGHT_DECAY = 0.01     # Weight decay
BATCH_SIZE = 32         # Batch size
WARMUP_RATIO = 0.1      # Warmup fraction
ADAM_BETAS = (0.9, 0.999)

# Dataset
DATASET = "bnci2014001"  # MOABB dataset
TEST_SUBJECT_IDX = 0     # Which subject to hold out for evaluation

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

t_start = time.time()
torch.manual_seed(42)
torch.cuda.manual_seed(42)

# Device setup
if torch.cuda.is_available():
    device = torch.device("cuda")
    torch.set_float32_matmul_precision("high")
    print(f"Using CUDA: {torch.cuda.get_device_name()}")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
    print("Using MPS (Apple Silicon)")
else:
    device = torch.device("cpu")
    print("Using CPU (warning: will be slow)")

# Load data
print(f"Loading dataset: {DATASET}")
loader = make_cross_subject_loader(DATASET, TEST_SUBJECT_IDX, BATCH_SIZE, str(device))
n_subjects = get_num_subjects(DATASET)

print(f"Train subjects: {n_subjects - 1}, Test subject: {TEST_SUBJECT_IDX}")
print(f"Train samples: {loader.n_train}, Test samples: {loader.n_test}")
print(f"Channels: {loader.n_channels}, Timepoints: {loader.n_timepoints}")

# Build model
config = CompileConfig(
    n_channels=loader.n_channels,
    n_timepoints=loader.n_timepoints,
    n_classes=NUM_CLASSES,
    d_model=D_MODEL,
    n_heads=N_HEADS,
    n_layers=N_LAYERS,
    d_ff=D_FF,
    dropout=DROPOUT,
    use_spatial_attention=USE_SPATIAL,
    use_temporal_attention=USE_TEMPORAL,
)
print(f"Model config: {asdict(config)}")

model = CompileModel(config).to(device)
num_params = sum(p.numel() for p in model.parameters())
print(f"Parameters: {num_params:,}")

# Optimizer
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    betas=ADAM_BETAS,
    weight_decay=WEIGHT_DECAY
)

# Compile model (if supported)
if hasattr(torch, 'compile') and device.type == 'cuda':
    model = torch.compile(model, dynamic=False)

# LR schedule
def get_lr_multiplier(progress):
    if progress < WARMUP_RATIO:
        return progress / WARMUP_RATIO if WARMUP_RATIO > 0 else 1.0
    else:
        # Cosine decay
        decay_progress = (progress - WARMUP_RATIO) / (1.0 - WARMUP_RATIO)
        return 0.5 * (1 + math.cos(math.pi * decay_progress))

# Data iterator
train_iter = loader.train_batches()
X, y, epoch = next(train_iter)

print(f"Time budget: {TIME_BUDGET}s")

# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

t_start_training = time.time()
total_training_time = 0
step = 0
smooth_loss = 0
best_acc = 0

while True:
    t0 = time.time()

    # Forward pass
    model.train()
    logits = model(X)
    loss = F.cross_entropy(logits, y)

    # Backward pass
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    # Get next batch
    X, y, epoch = next(train_iter)

    t1 = time.time()
    dt = t1 - t0

    # Don't count first few steps (compilation overhead)
    if step > 5:
        total_training_time += dt

    # Progress and LR schedule
    progress = min(total_training_time / TIME_BUDGET, 1.0)
    lrm = get_lr_multiplier(progress)
    for group in optimizer.param_groups:
        group['lr'] = LEARNING_RATE * lrm

    # Logging
    loss_f = loss.item()

    # Fast fail
    if math.isnan(loss_f) or loss_f > 100:
        print("FAIL: Loss exploded")
        exit(1)

    ema_beta = 0.9
    smooth_loss = ema_beta * smooth_loss + (1 - ema_beta) * loss_f
    debiased_loss = smooth_loss / (1 - ema_beta ** (step + 1))

    pct_done = 100 * progress
    remaining = max(0, TIME_BUDGET - total_training_time)

    # Print every 10 steps
    if step % 10 == 0:
        print(f"\rstep {step:05d} ({pct_done:.1f}%) | loss: {debiased_loss:.4f} | lrm: {lrm:.3f} | dt: {dt*1000:.0f}ms | epoch: {epoch} | remaining: {remaining:.0f}s    ", end="", flush=True)

    # GC management
    if step == 0:
        gc.collect()
        gc.freeze()
        gc.disable()
    elif (step + 1) % 1000 == 0:
        gc.collect()

    step += 1

    # Time's up
    if step > 5 and total_training_time >= TIME_BUDGET:
        break

print()

# ---------------------------------------------------------------------------
# Final evaluation
# ---------------------------------------------------------------------------

model.eval()
test_acc = evaluate_cross_subject_accuracy(model, loader)
train_acc = 0.0

# Quick train accuracy check
correct = 0
total = 0
with torch.no_grad():
    for i, (X_t, y_t, _) in enumerate(loader.train_batches()):
        if i >= 10:
            break
        logits = model(X_t)
        preds = logits.argmax(dim=-1)
        correct += (preds == y_t).sum().item()
        total += len(y_t)
train_acc = correct / total if total > 0 else 0

# Final summary
t_end = time.time()
if torch.cuda.is_available():
    peak_vram_mb = torch.cuda.max_memory_allocated() / 1024 / 1024
else:
    peak_vram_mb = 0

print("---")
print(f"test_accuracy:    {test_acc:.6f}")
print(f"train_accuracy:   {train_acc:.6f}")
print(f"training_seconds: {total_training_time:.1f}")
print(f"total_seconds:    {t_end - t_start:.1f}")
print(f"peak_vram_mb:     {peak_vram_mb:.1f}")
print(f"num_steps:        {step}")
print(f"num_params:       {num_params}")
print(f"test_subject:     {TEST_SUBJECT_IDX}")
print(f"final_loss:       {debiased_loss:.4f}")
