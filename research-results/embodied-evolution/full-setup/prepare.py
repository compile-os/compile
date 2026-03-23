"""
Compile Autoresearch - Data preparation and evaluation utilities.
Adapted from Karpathy's autoresearch for neural foundation model research.

This file contains FIXED constants and evaluation - DO NOT MODIFY.
The agent only modifies train.py.

Usage:
    python prepare.py              # download MOABB datasets
    python prepare.py --dataset bnci2014001  # specific dataset
"""

import os
import sys
import numpy as np
import torch
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# Constants (FIXED - do not modify)
# ---------------------------------------------------------------------------

TIME_BUDGET = 300        # 5 minutes training time budget
SAMPLE_RATE = 128        # Resample all data to this rate
WINDOW_SIZE = 4.0        # Window size in seconds
NUM_CLASSES = 4          # Motor imagery: left hand, right hand, feet, tongue
EVAL_TRIALS = 100        # Number of trials for evaluation

# Cache directory
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "compile-autoresearch")
DATA_DIR = os.path.join(CACHE_DIR, "data")

# ---------------------------------------------------------------------------
# Dataset loading (MOABB)
# ---------------------------------------------------------------------------

def download_moabb_data(dataset_name: str = "bnci2014001"):
    """Download MOABB dataset. Returns path to cached data."""
    os.makedirs(DATA_DIR, exist_ok=True)
    cache_file = os.path.join(DATA_DIR, f"{dataset_name}.pt")

    if os.path.exists(cache_file):
        print(f"Data: loading cached {dataset_name} from {cache_file}")
        return torch.load(cache_file)

    print(f"Data: downloading {dataset_name} via MOABB...")

    try:
        from moabb.datasets import BNCI2014001, BNCI2014002, BNCI2014004
        from moabb.paradigms import MotorImagery
    except ImportError:
        print("ERROR: MOABB not installed. Run: pip install moabb")
        sys.exit(1)

    # Select dataset
    datasets = {
        "bnci2014001": BNCI2014001,
        "bnci2014002": BNCI2014002,
        "bnci2014004": BNCI2014004,
    }

    if dataset_name not in datasets:
        print(f"ERROR: Unknown dataset {dataset_name}. Available: {list(datasets.keys())}")
        sys.exit(1)

    dataset = datasets[dataset_name]()
    paradigm = MotorImagery(
        n_classes=NUM_CLASSES,
        fmin=4, fmax=40,  # Filter to relevant frequency bands
        resample=SAMPLE_RATE,
        tmin=0, tmax=WINDOW_SIZE
    )

    # Get data for all subjects
    X, labels, meta = paradigm.get_data(dataset=dataset)

    # Convert to tensors organized by subject
    subjects = np.unique(meta['subject'])
    data = {}

    for subj in subjects:
        mask = meta['subject'] == subj
        X_subj = torch.tensor(X[mask], dtype=torch.float32)
        y_subj = torch.tensor(labels[mask], dtype=torch.long)

        # Normalize per-channel
        mean = X_subj.mean(dim=(0, 2), keepdim=True)
        std = X_subj.std(dim=(0, 2), keepdim=True) + 1e-6
        X_subj = (X_subj - mean) / std

        data[subj] = {'X': X_subj, 'y': y_subj}

    # Save to cache
    torch.save(data, cache_file)
    print(f"Data: saved to {cache_file}")
    print(f"Data: {len(subjects)} subjects, {X.shape[1]} channels, {X.shape[2]} timepoints")

    return data


@dataclass
class SubjectData:
    """Container for a single subject's data."""
    X: torch.Tensor  # (n_trials, n_channels, n_timepoints)
    y: torch.Tensor  # (n_trials,)
    subject_id: str


def load_data(dataset_name: str = "bnci2014001") -> List[SubjectData]:
    """Load dataset and return list of SubjectData objects."""
    data = download_moabb_data(dataset_name)
    subjects = []
    for subj_id, subj_data in data.items():
        subjects.append(SubjectData(
            X=subj_data['X'],
            y=subj_data['y'],
            subject_id=str(subj_id)
        ))
    return subjects


# ---------------------------------------------------------------------------
# Data utilities (imported by train.py)
# ---------------------------------------------------------------------------

class CrossSubjectDataLoader:
    """
    Leave-one-subject-out data loader for cross-subject evaluation.
    This is the core of the thesis: train on N-1 subjects, test on 1.
    """

    def __init__(self, subjects: List[SubjectData], test_subject_idx: int,
                 batch_size: int = 32, device: str = "cuda"):
        self.device = device
        self.batch_size = batch_size

        # Split: all subjects except test_subject_idx for training
        self.train_subjects = [s for i, s in enumerate(subjects) if i != test_subject_idx]
        self.test_subject = subjects[test_subject_idx]

        # Concatenate all training data
        self.train_X = torch.cat([s.X for s in self.train_subjects], dim=0)
        self.train_y = torch.cat([s.y for s in self.train_subjects], dim=0)

        # Test data (held-out subject)
        self.test_X = self.test_subject.X
        self.test_y = self.test_subject.y

        self.n_train = len(self.train_X)
        self.n_test = len(self.test_X)

        # Metadata
        self.n_channels = self.train_X.shape[1]
        self.n_timepoints = self.train_X.shape[2]

    def train_batches(self):
        """Infinite iterator over training batches."""
        epoch = 0
        while True:
            perm = torch.randperm(self.n_train)
            for i in range(0, self.n_train, self.batch_size):
                idx = perm[i:i + self.batch_size]
                X = self.train_X[idx].to(self.device)
                y = self.train_y[idx].to(self.device)
                yield X, y, epoch
            epoch += 1

    def test_batches(self):
        """Single pass over test data."""
        for i in range(0, self.n_test, self.batch_size):
            X = self.test_X[i:i + self.batch_size].to(self.device)
            y = self.test_y[i:i + self.batch_size].to(self.device)
            yield X, y


def make_cross_subject_loader(dataset_name: str, test_subject_idx: int,
                               batch_size: int = 32, device: str = "cuda"):
    """Create a cross-subject data loader."""
    subjects = load_data(dataset_name)
    return CrossSubjectDataLoader(subjects, test_subject_idx, batch_size, device)


def get_num_subjects(dataset_name: str = "bnci2014001") -> int:
    """Get number of subjects in dataset."""
    subjects = load_data(dataset_name)
    return len(subjects)


# ---------------------------------------------------------------------------
# Evaluation (FIXED - this is the ground truth metric)
# ---------------------------------------------------------------------------

@torch.no_grad()
def evaluate_cross_subject_accuracy(model, loader: CrossSubjectDataLoader) -> float:
    """
    Zero-shot cross-subject accuracy.

    This is THE metric for the thesis: can we decode a new subject
    with ZERO calibration data?

    Returns accuracy as a float between 0 and 1.
    """
    model.eval()
    correct = 0
    total = 0

    for X, y in loader.test_batches():
        logits = model(X)
        preds = logits.argmax(dim=-1)
        correct += (preds == y).sum().item()
        total += len(y)

    model.train()
    return correct / total if total > 0 else 0.0


@torch.no_grad()
def evaluate_all_subjects(model, dataset_name: str = "bnci2014001",
                          batch_size: int = 32, device: str = "cuda") -> Dict[str, float]:
    """
    Leave-one-out evaluation across all subjects.
    Returns dict with per-subject accuracy and mean accuracy.
    """
    subjects = load_data(dataset_name)
    n_subjects = len(subjects)

    accuracies = []
    for i in range(n_subjects):
        loader = CrossSubjectDataLoader(subjects, i, batch_size, device)
        acc = evaluate_cross_subject_accuracy(model, loader)
        accuracies.append(acc)

    return {
        'per_subject': accuracies,
        'mean_accuracy': np.mean(accuracies),
        'std_accuracy': np.std(accuracies),
        'min_accuracy': np.min(accuracies),
        'max_accuracy': np.max(accuracies),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare data for Compile autoresearch")
    parser.add_argument("--dataset", type=str, default="bnci2014001",
                        help="MOABB dataset name")
    args = parser.parse_args()

    print(f"Cache directory: {CACHE_DIR}")
    print()

    # Download data
    subjects = load_data(args.dataset)
    print(f"\nLoaded {len(subjects)} subjects")
    for s in subjects[:3]:
        print(f"  Subject {s.subject_id}: X={s.X.shape}, y={s.y.shape}")
    if len(subjects) > 3:
        print(f"  ... and {len(subjects) - 3} more")

    print("\nDone! Ready to train with: uv run train.py")
