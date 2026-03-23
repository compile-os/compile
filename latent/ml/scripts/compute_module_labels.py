#!/usr/bin/env python3
"""
Compute module labels for the FlyWire v783 connectome via MiniBatchKMeans.

This script clusters the ~130k neurons of the FlyWire v783 connectome into
50 modules and saves the result as ``module_labels_v2.npy``.

Algorithm
---------
MiniBatchKMeans (sklearn) with n_clusters=50, random_state=42, batch_size=10000.

Why MiniBatchKMeans instead of spectral clustering?
    Spectral clustering requires computing eigenvectors of a ~130k x 130k
    Laplacian, which is prohibitively expensive in both memory (~130 GB for
    the dense Laplacian) and time.  MiniBatchKMeans on a compact 4-feature
    representation runs in seconds on a laptop and produces well-balanced
    modules suitable for the downstream gauge-theory analysis (Forman
    curvature, holonomy, evolution fitness landscape).

Features (per neuron)
---------------------
1. **Normalized neuron index** — ``np.arange(n) / n``.
   FlyWire indices encode rough spatial position, so this acts as a cheap
   proxy for anatomical location.
2. **Log in-degree (normalized)** — ``log1p(in_deg) / log1p(max(in_deg))``.
3. **Log out-degree (normalized)** — ``log1p(out_deg) / log1p(max(out_deg))``.
4. **Balance ratio** — ``(in_deg - out_deg) / (total_deg + 1)``.
   Captures whether a neuron is primarily a receiver or sender.

Parameters
----------
N_MODULES   = 50
random_state = 42
batch_size   = 10000

Data source
-----------
FlyWire v783 connectivity parquet, loaded via ``compile.data.load_connectome()``.
Only the ``Presynaptic_Index`` and ``Postsynaptic_Index`` columns are used
(degree is computed from unweighted edge counts).

Usage
-----
    python scripts/compute_module_labels.py                 # save to data/module_labels_v2.npy
    python scripts/compute_module_labels.py --output /tmp/labels.npy
    python scripts/compute_module_labels.py --verify         # recompute and compare to existing file

Provenance
----------
Algorithm originally implemented in ``experiments/legacy/gauge_theory_v2.py``.
Extracted here for reproducibility.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.cluster import MiniBatchKMeans

from compile.data import load_connectome

# ── Constants ────────────────────────────────────────────────────────────────
N_MODULES = 50
RANDOM_STATE = 42
BATCH_SIZE = 10000


def compute_module_labels() -> tuple[np.ndarray, int]:
    """Compute module labels from the FlyWire v783 connectome.

    Returns
    -------
    module_labels : np.ndarray of shape (n_neurons,), dtype int32
        Cluster assignment for each neuron (0..49).
    n_neurons : int
        Total number of neurons.
    """
    # 1. Load connectome
    print("[1] Loading FlyWire v783 connectome...")
    df_conn, _df_comp, num_neurons = load_connectome()

    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values

    n_neurons = num_neurons
    print(f"    Neurons: {n_neurons:,}")
    print(f"    Synapses: {len(pre):,}")

    # 2. Compute in-degree and out-degree (unweighted edge counts)
    print("[2] Computing neuron features...")
    adj = sparse.csr_matrix(
        (np.ones(len(pre), dtype=np.float32), (pre, post)),
        shape=(n_neurons, n_neurons),
    )
    in_degree = np.array(adj.sum(axis=0)).flatten()
    out_degree = np.array(adj.sum(axis=1)).flatten()
    total_degree = in_degree + out_degree

    # 3. Build 4-feature matrix
    neuron_features = np.column_stack([
        np.arange(n_neurons) / n_neurons,                        # normalized index
        np.log1p(in_degree) / np.log1p(in_degree.max()),         # log in-degree
        np.log1p(out_degree) / np.log1p(out_degree.max()),       # log out-degree
        (in_degree - out_degree) / (total_degree + 1),           # balance ratio
    ])

    # 4. Cluster
    print(f"[3] Running MiniBatchKMeans (n_clusters={N_MODULES}, "
          f"random_state={RANDOM_STATE}, batch_size={BATCH_SIZE})...")
    kmeans = MiniBatchKMeans(
        n_clusters=N_MODULES,
        random_state=RANDOM_STATE,
        batch_size=BATCH_SIZE,
    )
    module_labels = kmeans.fit_predict(neuron_features).astype(np.int32)

    return module_labels, n_neurons


def print_summary(module_labels: np.ndarray, df_conn=None) -> None:
    """Print summary statistics about the clustering."""
    sizes = Counter(module_labels)
    size_vals = list(sizes.values())
    print(f"\n── Summary ({'─' * 50})")
    print(f"  Modules:        {len(sizes)}")
    print(f"  Module sizes:   min={min(size_vals)}, max={max(size_vals)}, "
          f"mean={np.mean(size_vals):.0f}, std={np.std(size_vals):.0f}")

    if df_conn is not None:
        pre = df_conn["Presynaptic_Index"].values
        post = df_conn["Postsynaptic_Index"].values
        intra = np.sum(module_labels[pre] == module_labels[post])
        inter = len(pre) - intra
        print(f"  Intra-module edges: {int(intra):,}")
        print(f"  Inter-module edges: {int(inter):,}")
        print(f"  Inter/total ratio:  {inter / len(pre):.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute module_labels_v2.npy from the FlyWire v783 connectome."
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("data/module_labels_v2.npy"),
        help="Output path (default: data/module_labels_v2.npy)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Recompute and verify against existing file at --output path.",
    )
    args = parser.parse_args()

    module_labels, n_neurons = compute_module_labels()

    # Load connectome again for edge statistics (cheap — already cached)
    df_conn, _, _ = load_connectome()
    print_summary(module_labels, df_conn)

    if args.verify:
        if not args.output.exists():
            print(f"\n[!] Cannot verify: {args.output} does not exist.", file=sys.stderr)
            sys.exit(1)
        existing = np.load(args.output)
        if np.array_equal(module_labels, existing):
            print(f"\n[OK] Recomputed labels match {args.output} exactly.")
        else:
            n_diff = np.sum(module_labels != existing)
            print(f"\n[MISMATCH] {n_diff:,} / {n_neurons:,} labels differ "
                  f"({100 * n_diff / n_neurons:.2f}%).", file=sys.stderr)
            sys.exit(1)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.output, module_labels)
        print(f"\n[4] Saved {args.output}  (shape={module_labels.shape}, "
              f"dtype={module_labels.dtype})")


if __name__ == "__main__":
    main()
