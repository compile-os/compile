"""
Self-Supervised Pre-Training - Data & Evaluation (READ-ONLY)
============================================================

DO NOT MODIFY THIS FILE. It contains:
1. Data loading for pre-training (unlabeled) and fine-tuning (labeled)
2. Linear probe evaluation (the metric)
3. Constants (time budget, device, etc.)

The autoresearch agent only modifies train_ssl.py.
"""

import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from pathlib import Path
import numpy as np

# =============================================================================
# CONSTANTS - DO NOT MODIFY
# =============================================================================

TIME_BUDGET = 120  # 2 minutes for quick experiments

# Device selection
if torch.cuda.is_available():
    DEVICE = torch.device('cuda')
elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    DEVICE = torch.device('mps')
else:
    DEVICE = torch.device('cpu')

CACHE_DIR = Path.home() / ".cache" / "compile-autoresearch"

# =============================================================================
# DATA LOADING
# =============================================================================

def load_pretrain_data() -> dict:
    """
    Load unlabeled data for self-supervised pre-training.

    Currently uses PhysioNet MI (will expand to TUH + others).
    Returns data WITHOUT labels - just raw signals.
    """
    cache_file = CACHE_DIR / "physionet_mi_v2.pt"

    if not cache_file.exists():
        print("Pre-training data not found. Downloading PhysioNet MI...")
        _download_physionet()

    data = torch.load(cache_file, weights_only=False)
    metadata = data['_metadata']

    # Combine all subjects' data (no labels needed)
    all_X = []
    for key, value in data.items():
        if isinstance(key, int):  # Subject ID
            all_X.append(value['X'])

    X = torch.cat(all_X, dim=0)

    # Normalize globally
    X = (X - X.mean()) / (X.std() + 1e-6)

    print(f"Loaded {len(X)} samples for pre-training")
    print(f"Shape: {X.shape} (samples, channels, time)")

    return {
        'X': X,
        'n_channels': X.shape[1],
        'n_timepoints': X.shape[2],
    }


def load_finetune_data() -> dict:
    """
    Load labeled data for linear probe evaluation.

    Uses a held-out portion of PhysioNet MI with labels.
    This is for evaluation only - not training the encoder.
    """
    cache_file = CACHE_DIR / "physionet_mi_v2.pt"

    if not cache_file.exists():
        raise FileNotFoundError(f"Data not found at {cache_file}. Run prepare first.")

    data = torch.load(cache_file, weights_only=False)
    metadata = data['_metadata']

    # Use last 10 subjects for evaluation
    subjects = sorted([k for k in data.keys() if isinstance(k, int)])
    eval_subjects = subjects[-10:]
    train_subjects = subjects[:-10]

    # Training data for linear probe (from non-eval subjects)
    train_X, train_y = [], []
    for s in train_subjects[:20]:  # Use subset for speed
        train_X.append(data[s]['X'])
        train_y.append(data[s]['y'])

    train_X = torch.cat(train_X, dim=0)
    train_y = torch.cat(train_y, dim=0)

    # Test data (held-out subjects)
    test_X, test_y = [], []
    for s in eval_subjects:
        test_X.append(data[s]['X'])
        test_y.append(data[s]['y'])

    test_X = torch.cat(test_X, dim=0)
    test_y = torch.cat(test_y, dim=0)

    # Normalize
    mean, std = train_X.mean(), train_X.std() + 1e-6
    train_X = (train_X - mean) / std
    test_X = (test_X - mean) / std

    return {
        'train_X': train_X,
        'train_y': train_y,
        'test_X': test_X,
        'test_y': test_y,
        'n_classes': metadata['n_classes'],
    }


def _download_physionet():
    """Download PhysioNet MI dataset via MOABB."""
    print("Downloading PhysioNet Motor Imagery dataset...")

    from moabb.datasets import PhysionetMI
    from moabb.paradigms import MotorImagery

    dataset = PhysionetMI()
    paradigm = MotorImagery(n_classes=4, fmin=8, fmax=32, tmin=0, tmax=3)

    subjects = dataset.subject_list[:109]

    # First pass: collect all labels
    print("Pass 1: Collecting labels...")
    all_labels = set()
    subject_raw = {}

    for i, subj in enumerate(subjects):
        try:
            X, y, _ = paradigm.get_data(dataset, subjects=[subj])
            all_labels.update(np.unique(y))
            subject_raw[subj] = {'X': X, 'y': y}
            if (i + 1) % 20 == 0:
                print(f"  Scanned {i + 1}/{len(subjects)}")
        except Exception as e:
            print(f"  Warning: Failed subject {subj}: {e}")

    # Global label map
    global_labels = sorted(list(all_labels))
    label_map = {label: idx for idx, label in enumerate(global_labels)}
    print(f"Labels: {global_labels}")

    # Second pass: process data
    print("Pass 2: Processing...")
    data = {}
    min_samples = None

    for i, (subj, raw) in enumerate(subject_raw.items()):
        X, y = raw['X'], raw['y']

        if min_samples is None:
            min_samples = X.shape[2]
        else:
            min_samples = min(min_samples, X.shape[2])

        X_tensor = torch.tensor(X, dtype=torch.float32)
        mean = X_tensor.mean(dim=(0, 2), keepdim=True)
        std = X_tensor.std(dim=(0, 2), keepdim=True) + 1e-6
        X_tensor = (X_tensor - mean) / std

        y_encoded = torch.tensor([label_map[label] for label in y], dtype=torch.long)
        data[subj] = {'X': X_tensor, 'y': y_encoded}

        if (i + 1) % 20 == 0:
            print(f"  Processed {i + 1}/{len(subject_raw)}")

    # Crop to min length
    for subj in data:
        data[subj]['X'] = data[subj]['X'][:, :, :min_samples]

    data['_metadata'] = {
        'global_labels': global_labels,
        'global_label_map': label_map,
        'n_classes': len(global_labels),
        'n_timepoints': min_samples,
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(data, CACHE_DIR / "physionet_mi_v2.pt")
    print(f"Saved to {CACHE_DIR / 'physionet_mi_v2.pt'}")


# =============================================================================
# LINEAR PROBE EVALUATION - DO NOT MODIFY
# =============================================================================

def linear_probe_evaluate(encoder: nn.Module, data: dict, epochs: int = 50) -> float:
    """
    Evaluate encoder quality using linear probe.

    Freezes the encoder, trains a linear classifier on top,
    and returns zero-shot cross-subject accuracy.

    This is the metric autoresearch optimizes.
    """
    encoder.eval()

    train_X = data['train_X'].to(DEVICE)
    train_y = data['train_y'].to(DEVICE)
    test_X = data['test_X'].to(DEVICE)
    test_y = data['test_y'].to(DEVICE)
    n_classes = data['n_classes']

    # Get embeddings (frozen encoder)
    with torch.no_grad():
        _, train_embed = encoder(train_X)  # (N, D)
        _, test_embed = encoder(test_X)

    d_model = train_embed.shape[1]

    # Linear classifier
    classifier = nn.Linear(d_model, n_classes).to(DEVICE)
    optimizer = torch.optim.Adam(classifier.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    # Train classifier
    dataset = TensorDataset(train_embed, train_y)
    loader = DataLoader(dataset, batch_size=64, shuffle=True)

    for epoch in range(epochs):
        classifier.train()
        for X_batch, y_batch in loader:
            optimizer.zero_grad()
            logits = classifier(X_batch)
            loss = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()

    # Evaluate on test set
    classifier.eval()
    with torch.no_grad():
        logits = classifier(test_embed)
        preds = logits.argmax(dim=1)
        accuracy = (preds == test_y).float().mean().item()

    return accuracy


# =============================================================================
# MAIN - Run to prepare data
# =============================================================================

if __name__ == "__main__":
    print("Preparing data for self-supervised pre-training...")

    if not (CACHE_DIR / "physionet_mi_v2.pt").exists():
        _download_physionet()
    else:
        print("Data already exists.")

    # Test loading
    pretrain = load_pretrain_data()
    finetune = load_finetune_data()

    print(f"\nPre-train: {pretrain['X'].shape}")
    print(f"Fine-tune train: {finetune['train_X'].shape}")
    print(f"Fine-tune test: {finetune['test_X'].shape}")
    print(f"Classes: {finetune['n_classes']}")
    print(f"\nDevice: {DEVICE}")
    print("Ready for self-supervised pre-training!")
