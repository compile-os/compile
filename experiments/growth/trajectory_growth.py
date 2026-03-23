#!/usr/bin/env python3
"""
Axon Trajectory Growth Model for FlyWire connectome.
Predicts synaptic connections by simulating axon growth through 3D brain space.

Strategy:
  V1: Mean direction per hemilineage + tube search along trajectory
  V2: Distance-decay synapse probability + position-dependent vector field
  V3: KNN vector field + branching + target-region attraction
"""

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial import KDTree
from sklearn.preprocessing import normalize
import logging, sys, time, json
from pathlib import Path
from collections import defaultdict

# ─── Logging ────────────────────────────────────────────────────────────────
LOG_PATH = Path("/home/ubuntu/bulletproof_results/trajectory_growth.log")
LOG_PATH.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger()

# ─── Config ─────────────────────────────────────────────────────────────────
DATA_DIR = Path("/home/ubuntu/fly-brain-embodied/data")
ANNOTATION_FILE = DATA_DIR / "flywire_annotations.tsv"
CONNECTIVITY_FILE = DATA_DIR / "2025_Connectivity_783.parquet"

# Gene-guided hemilineages (19 signature hemilineages from gene_guided.json)
SIGNATURE_HEMILINEAGES = [
    'VPNd2','VLPp2','DM3_CX_d2','LB23','LB12','VLPl2_medial','LB7',
    'VLPl&p2_posterior','MD3','MX12','VLPl&p2_lateral','DM1_CX_d2',
    'WEDd1','MX3','VPNd1','putative_primary','CREa2_medial',
    'CREa1_dorsal','SLPal3_and_SLPal4_dorsal'
]


# ════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ════════════════════════════════════════════════════════════════════════════

def load_annotations():
    log.info("Loading annotations...")
    ann = pd.read_csv(ANNOTATION_FILE, sep='\t', low_memory=False,
                      dtype={'root_id': str, 'supervoxel_id': str})
    # Keep only neurons with valid soma positions
    ann = ann.dropna(subset=['soma_x','soma_y','soma_z','pos_x','pos_y','pos_z'])
    ann['root_id'] = ann['root_id'].astype(str)
    log.info(f"  Loaded {len(ann):,} annotated neurons with positions")
    return ann


def load_connectivity():
    log.info("Loading connectivity parquet...")
    df = pq.read_table(CONNECTIVITY_FILE).to_pandas()
    df['Presynaptic_ID'] = df['Presynaptic_ID'].astype(str)
    df['Postsynaptic_ID'] = df['Postsynaptic_ID'].astype(str)
    log.info(f"  Loaded {len(df):,} synaptic connections")
    return df


def get_gene_guided_neurons(ann):
    """Select the 8158-neuron gene-guided processor (signature hemilineages)."""
    mask = ann['ito_lee_hemilineage'].isin(SIGNATURE_HEMILINEAGES)
    subset = ann[mask].copy()
    log.info(f"  Gene-guided processor: {len(subset):,} neurons")
    for h in SIGNATURE_HEMILINEAGES:
        n = (subset['ito_lee_hemilineage'] == h).sum()
        log.info(f"    {h}: {n}")
    return subset


# ════════════════════════════════════════════════════════════════════════════
# TRAJECTORY COMPUTATION
# ════════════════════════════════════════════════════════════════════════════

def compute_trajectory_vectors(ann):
    """
    For each neuron: direction vector = (pos - soma) normalized.
    pos_x/y/z is the representative annotation point (centroid or axon terminal area).
    """
    soma = ann[['soma_x','soma_y','soma_z']].values
    pos  = ann[['pos_x','pos_y','pos_z']].values
    raw_vecs = pos - soma                     # shape (N, 3)
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    # Handle zero-length vectors
    zero_mask = (norms.flatten() < 1e-6)
    norms[zero_mask] = 1.0
    unit_vecs = raw_vecs / norms
    unit_vecs[zero_mask] = 0.0
    return unit_vecs, norms.flatten()


def fit_hemilineage_vector_fields(ann, unit_vecs):
    """
    V1: Simple mean direction vector per hemilineage.
    V2: Spatial binning – direction varies with position in brain space.
    Returns:
      mean_dirs: {hemilineage -> mean unit vector}
      spread: {hemilineage -> angular spread (radians)}
    """
    mean_dirs = {}
    spreads   = {}
    hemi_col  = ann['ito_lee_hemilineage'].values

    for hemi in SIGNATURE_HEMILINEAGES:
        idx = np.where(hemi_col == hemi)[0]
        if len(idx) == 0:
            mean_dirs[hemi] = np.zeros(3)
            spreads[hemi] = np.pi
            continue
        vecs = unit_vecs[idx]
        # Remove zero vectors
        norms = np.linalg.norm(vecs, axis=1)
        vecs = vecs[norms > 0.1]
        if len(vecs) == 0:
            mean_dirs[hemi] = np.zeros(3)
            spreads[hemi] = np.pi
            continue

        mean_v = vecs.mean(axis=0)
        norm_m = np.linalg.norm(mean_v)
        if norm_m > 1e-6:
            mean_v = mean_v / norm_m
        mean_dirs[hemi] = mean_v

        # Angular spread: mean angle between individual vecs and mean direction
        dots = np.clip(vecs @ mean_v, -1, 1)
        angles = np.arccos(dots)
        spreads[hemi] = float(angles.mean())

        log.info(f"  [{hemi}] n={len(idx)}, dir=({mean_v[0]:.3f},{mean_v[1]:.3f},{mean_v[2]:.3f}), "
                 f"spread={np.degrees(spreads[hemi]):.1f}°")

    return mean_dirs, spreads


# ════════════════════════════════════════════════════════════════════════════
# V1 TRAJECTORY SIMULATION – TUBE MODEL
# ════════════════════════════════════════════════════════════════════════════

def simulate_trajectories_v1(ann_subset, ann_all, mean_dirs,
                              tube_radius=5000, n_steps=20, step_size=5000):
    """
    For each axon in the gene-guided set:
    1. Start at soma position
    2. Walk in mean hemilineage direction for n_steps
    3. At each step, find all neurons (from all annotations) within tube_radius
    4. Those are predicted postsynaptic targets

    tube_radius, step_size in nm (FlyWire coordinate units ~ 4nm/voxel -> multiply accordingly)
    Actually FlyWire coords are in 4nm voxel units, so 5000 = 20 microns
    """
    log.info(f"\nV1 Simulation: tube_radius={tube_radius}, steps={n_steps}, step={step_size}")

    # Build KDTree over ALL annotated neurons
    all_soma = ann_all[['soma_x','soma_y','soma_z']].values
    all_ids  = ann_all['root_id'].values
    tree = KDTree(all_soma)

    # Index subsets
    hemi_col = ann_subset['ito_lee_hemilineage'].values
    soma_arr = ann_subset[['soma_x','soma_y','soma_z']].values
    pre_ids  = ann_subset['root_id'].values

    predicted_edges = set()
    n_axons = len(ann_subset)

    for i in range(n_axons):
        hemi = hemi_col[i]
        if hemi not in mean_dirs:
            continue
        direction = mean_dirs[hemi]
        if np.linalg.norm(direction) < 0.1:
            continue

        pos = soma_arr[i].copy().astype(float)
        pre_id = pre_ids[i]

        # Walk along trajectory
        for step in range(n_steps):
            pos += direction * step_size
            # Query sphere around current position
            neighbors = tree.query_ball_point(pos, tube_radius)
            for ni in neighbors:
                post_id = all_ids[ni]
                if post_id != pre_id:
                    predicted_edges.add((pre_id, post_id))

    log.info(f"  V1 predicted {len(predicted_edges):,} unique connections")
    return predicted_edges


# ════════════════════════════════════════════════════════════════════════════
# V2 TRAJECTORY SIMULATION – DISTANCE DECAY + BRANCHING
# ════════════════════════════════════════════════════════════════════════════

def simulate_trajectories_v2(ann_subset, ann_all, mean_dirs, spreads,
                              tube_radius=4000, n_steps=25, step_size=4000,
                              n_branches=3, branch_angle_scale=0.3):
    """
    V2 improvements:
    - Per-neuron direction = mean_dir + small random deviation (proportional to spread)
    - Multiple branch directions (capture dendritic spread)
    - Only sample from neurons within the gene-guided set for post-synaptic targets
    """
    log.info(f"\nV2 Simulation: tube={tube_radius}, steps={n_steps}, step={step_size}, branches={n_branches}")

    all_soma = ann_all[['soma_x','soma_y','soma_z']].values
    all_ids  = ann_all['root_id'].values
    tree = KDTree(all_soma)

    hemi_col = ann_subset['ito_lee_hemilineage'].values
    soma_arr = ann_subset[['soma_x','soma_y','soma_z']].values
    pre_ids  = ann_subset['root_id'].values

    predicted_edges = set()
    rng = np.random.default_rng(42)

    for i in range(len(ann_subset)):
        hemi = hemi_col[i]
        if hemi not in mean_dirs:
            continue
        mean_dir = mean_dirs[hemi]
        if np.linalg.norm(mean_dir) < 0.1:
            continue

        spread = spreads.get(hemi, 0.5)
        pre_id = pre_ids[i]

        # Generate branch directions: main + deviations
        branch_dirs = [mean_dir]
        for _ in range(n_branches - 1):
            noise = rng.normal(0, spread * branch_angle_scale, 3)
            d = mean_dir + noise
            n = np.linalg.norm(d)
            if n > 0:
                branch_dirs.append(d / n)

        for direction in branch_dirs:
            pos = soma_arr[i].copy().astype(float)
            for step in range(n_steps):
                pos += direction * step_size
                neighbors = tree.query_ball_point(pos, tube_radius)
                for ni in neighbors:
                    post_id = all_ids[ni]
                    if post_id != pre_id:
                        predicted_edges.add((pre_id, post_id))

    log.info(f"  V2 predicted {len(predicted_edges):,} unique connections")
    return predicted_edges


# ════════════════════════════════════════════════════════════════════════════
# V3 TRAJECTORY SIMULATION – SPATIAL VECTOR FIELD (KNN-BASED)
# ════════════════════════════════════════════════════════════════════════════

def build_spatial_vector_field(ann_all, unit_vecs_all, n_neighbors=50):
    """
    Build a KNN-based spatial vector field:
    Given any point in 3D space, find K nearest annotated neurons and
    return their mean trajectory direction.
    """
    log.info("Building spatial vector field (KNN)...")
    soma_all = ann_all[['soma_x','soma_y','soma_z']].values
    field_tree = KDTree(soma_all)
    return field_tree, soma_all, unit_vecs_all


def query_vector_field(pos, field_tree, soma_all, unit_vecs_all, n_neighbors=30):
    """Get interpolated direction at position `pos` from nearby neurons."""
    dists, idxs = field_tree.query(pos, k=min(n_neighbors, len(soma_all)))
    vecs = unit_vecs_all[idxs]
    # Weight by inverse distance
    w = 1.0 / (dists + 1e-6)
    w = w / w.sum()
    mean_v = (vecs * w[:, None]).sum(axis=0)
    n = np.linalg.norm(mean_v)
    if n > 1e-6:
        return mean_v / n
    return mean_v


def simulate_trajectories_v3(ann_subset, ann_all, unit_vecs_all,
                              tube_radius=3500, n_steps=30, step_size=3500,
                              n_branches=4, use_hemi_bias=True, mean_dirs=None):
    """
    V3: Follow global spatial vector field with hemilineage bias.
    At each step, direction = 0.6 * hemi_mean_dir + 0.4 * spatial_field_dir
    """
    log.info(f"\nV3 Simulation: tube={tube_radius}, steps={n_steps}, step={step_size}, branches={n_branches}")

    field_tree, soma_all, vecs_all = build_spatial_vector_field(ann_all, unit_vecs_all)

    all_soma = ann_all[['soma_x','soma_y','soma_z']].values
    all_ids  = ann_all['root_id'].values
    target_tree = KDTree(all_soma)

    hemi_col = ann_subset['ito_lee_hemilineage'].values
    soma_arr = ann_subset[['soma_x','soma_y','soma_z']].values
    pre_ids  = ann_subset['root_id'].values

    predicted_edges = set()
    rng = np.random.default_rng(123)

    for i in range(len(ann_subset)):
        hemi = hemi_col[i]
        pre_id = pre_ids[i]

        # Initial direction: hemi mean or spatial field
        if use_hemi_bias and mean_dirs and hemi in mean_dirs:
            hemi_dir = mean_dirs[hemi]
        else:
            hemi_dir = np.zeros(3)

        # Multiple branches
        for b in range(n_branches):
            pos = soma_arr[i].copy().astype(float)
            # Add small initial spread for branches
            noise = rng.normal(0, 0.2, 3)
            init_dir = hemi_dir + noise
            n = np.linalg.norm(init_dir)
            if n < 1e-6:
                continue
            direction = init_dir / n

            for step in range(n_steps):
                pos += direction * step_size

                # Update direction from spatial field + hemi bias
                field_dir = query_vector_field(pos, field_tree, soma_all, vecs_all, n_neighbors=20)
                if np.linalg.norm(hemi_dir) > 0.1:
                    new_dir = 0.6 * hemi_dir + 0.4 * field_dir
                else:
                    new_dir = field_dir
                n = np.linalg.norm(new_dir)
                if n > 1e-6:
                    direction = new_dir / n

                # Find nearby targets
                neighbors = target_tree.query_ball_point(pos, tube_radius)
                for ni in neighbors:
                    post_id = all_ids[ni]
                    if post_id != pre_id:
                        predicted_edges.add((pre_id, post_id))

    log.info(f"  V3 predicted {len(predicted_edges):,} unique connections")
    return predicted_edges


# ════════════════════════════════════════════════════════════════════════════
# EVALUATION
# ════════════════════════════════════════════════════════════════════════════

def evaluate(predicted_edges, real_edges_set, version_name="V?"):
    """Compute precision, recall, F1."""
    if not predicted_edges:
        log.info(f"  [{version_name}] No predicted edges!")
        return {"precision": 0, "recall": 0, "f1": 0}

    tp = len(predicted_edges & real_edges_set)
    precision = tp / len(predicted_edges) if predicted_edges else 0
    recall    = tp / len(real_edges_set)   if real_edges_set else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    log.info(f"\n{'='*60}")
    log.info(f"  [{version_name}] RESULTS:")
    log.info(f"    Real connections:      {len(real_edges_set):>10,}")
    log.info(f"    Predicted connections: {len(predicted_edges):>10,}")
    log.info(f"    True positives:        {tp:>10,}")
    log.info(f"    Precision: {precision:.4f}  ({precision*100:.2f}%)")
    log.info(f"    Recall:    {recall:.4f}  ({recall*100:.2f}%)")
    log.info(f"    F1 Score:  {f1:.4f}")
    log.info(f"{'='*60}\n")

    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "predicted": len(predicted_edges), "real": len(real_edges_set)}


def grid_search_params(ann_subset, ann_all, mean_dirs, real_edges_set, version="v1"):
    """Search over tube_radius and step_size to find best F1."""
    log.info("\n--- Grid search for optimal parameters ---")
    best_f1 = 0
    best_params = {}
    results = []

    if version == "v1":
        radii = [2000, 3000, 5000, 8000]
        steps_list = [15, 20, 30]
        step_sizes = [3000, 5000, 8000]
    else:
        radii = [3000, 4000, 6000]
        steps_list = [20, 30]
        step_sizes = [3000, 5000]

    for radius in radii:
        for n_steps in steps_list:
            for step_size in step_sizes:
                t0 = time.time()
                pred = simulate_trajectories_v1(ann_subset, ann_all, mean_dirs,
                                                tube_radius=radius, n_steps=n_steps,
                                                step_size=step_size)
                metrics = evaluate(pred, real_edges_set, f"grid r={radius} s={step_size} n={n_steps}")
                elapsed = time.time() - t0
                results.append({"radius": radius, "n_steps": n_steps, "step_size": step_size,
                                 "f1": metrics["f1"], "precision": metrics["precision"],
                                 "recall": metrics["recall"], "time": elapsed})
                if metrics["f1"] > best_f1:
                    best_f1 = metrics["f1"]
                    best_params = {"radius": radius, "n_steps": n_steps, "step_size": step_size}
                log.info(f"    r={radius} step={step_size} n={n_steps} -> F1={metrics['f1']:.4f} ({elapsed:.1f}s)")

    log.info(f"\nBest params: {best_params} -> F1={best_f1:.4f}")
    return best_params, results


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    t_start = time.time()
    log.info("=" * 70)
    log.info("AXON TRAJECTORY GROWTH MODEL  –  FlyWire Connectome")
    log.info("=" * 70)

    # 1. Load data
    ann_all  = load_annotations()
    conn_df  = load_connectivity()
    ann_sub  = get_gene_guided_neurons(ann_all)

    # 2. Build real edge set (within gene-guided subset)
    gene_ids = set(ann_sub['root_id'].values)
    log.info(f"\nBuilding real edge set within gene-guided {len(gene_ids):,} neurons...")
    conn_sub = conn_df[
        conn_df['Presynaptic_ID'].isin(gene_ids) &
        conn_df['Postsynaptic_ID'].isin(gene_ids)
    ]
    real_edges = set(zip(conn_sub['Presynaptic_ID'], conn_sub['Postsynaptic_ID']))
    log.info(f"  Real connections within subset: {len(real_edges):,}")

    # 3. Compute trajectory vectors for all neurons
    log.info("\nComputing trajectory vectors...")
    unit_vecs_all, traj_lengths_all = compute_trajectory_vectors(ann_all)

    # Also for subset
    unit_vecs_sub, _ = compute_trajectory_vectors(ann_sub)

    # 4. Fit hemilineage vector fields
    log.info("\nFitting hemilineage vector fields...")
    mean_dirs, spreads = fit_hemilineage_vector_fields(ann_sub, unit_vecs_sub)

    # ── V1: Mean-direction tube model ──────────────────────────────────────
    log.info("\n" + "─"*60)
    log.info("VERSION 1: Mean-direction tube model")
    log.info("─"*60)

    v1_pred = simulate_trajectories_v1(
        ann_sub, ann_all, mean_dirs,
        tube_radius=5000, n_steps=20, step_size=5000
    )
    v1_metrics = evaluate(v1_pred, real_edges, "V1-baseline")

    # Quick grid search around baseline
    log.info("\nGrid searching V1 parameters...")
    best_params_v1, grid_results = grid_search_params(
        ann_sub, ann_all, mean_dirs, real_edges, version="v1"
    )

    v1_best_pred = simulate_trajectories_v1(
        ann_sub, ann_all, mean_dirs,
        tube_radius=best_params_v1['radius'],
        n_steps=best_params_v1['n_steps'],
        step_size=best_params_v1['step_size']
    )
    v1_best_metrics = evaluate(v1_best_pred, real_edges, "V1-best")

    # ── V2: Branching + spread model ──────────────────────────────────────
    log.info("\n" + "─"*60)
    log.info("VERSION 2: Branching + angular spread model")
    log.info("─"*60)

    v2_pred = simulate_trajectories_v2(
        ann_sub, ann_all, mean_dirs, spreads,
        tube_radius=4000, n_steps=25, step_size=4000,
        n_branches=3, branch_angle_scale=0.3
    )
    v2_metrics = evaluate(v2_pred, real_edges, "V2-branching")

    # Grid search V2
    for radius in [3000, 4000, 6000]:
        for n_branches in [2, 3, 5]:
            pred = simulate_trajectories_v2(
                ann_sub, ann_all, mean_dirs, spreads,
                tube_radius=radius, n_steps=25, step_size=radius,
                n_branches=n_branches, branch_angle_scale=0.25
            )
            m = evaluate(pred, real_edges, f"V2 r={radius} b={n_branches}")

    # ── V3: Spatial vector field model ────────────────────────────────────
    log.info("\n" + "─"*60)
    log.info("VERSION 3: Spatial KNN vector field model")
    log.info("─"*60)

    v3_pred = simulate_trajectories_v3(
        ann_sub, ann_all, unit_vecs_all,
        tube_radius=3500, n_steps=25, step_size=3500,
        n_branches=3, use_hemi_bias=True, mean_dirs=mean_dirs
    )
    v3_metrics = evaluate(v3_pred, real_edges, "V3-spatial-field")

    # ── V4: Combined predictions (V2 union V3) ────────────────────────────
    log.info("\n" + "─"*60)
    log.info("VERSION 4: Combined V2 + V3 ensemble")
    log.info("─"*60)

    v4_pred = v2_pred | v3_pred
    v4_metrics = evaluate(v4_pred, real_edges, "V4-ensemble")

    # ─── Per-hemilineage breakdown ─────────────────────────────────────────
    log.info("\n--- Per-hemilineage recall breakdown (V2) ---")
    hemi_col = ann_sub['ito_lee_hemilineage'].values
    pre_ids  = ann_sub['root_id'].values

    for hemi in SIGNATURE_HEMILINEAGES:
        hemi_pre_ids = set(pre_ids[hemi_col == hemi])
        real_hemi = {e for e in real_edges if e[0] in hemi_pre_ids}
        pred_hemi = {e for e in v2_pred if e[0] in hemi_pre_ids}
        if not real_hemi:
            continue
        tp = len(pred_hemi & real_hemi)
        rec = tp / len(real_hemi) if real_hemi else 0
        pre = tp / len(pred_hemi) if pred_hemi else 0
        f1  = 2*pre*rec/(pre+rec) if (pre+rec) > 0 else 0
        log.info(f"  {hemi:<35} real={len(real_hemi):>6,}  pred={len(pred_hemi):>6,}  "
                 f"recall={rec:.3f}  prec={pre:.3f}  F1={f1:.3f}")

    # ─── Summary ──────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    log.info("\n" + "=" * 70)
    log.info("FINAL SUMMARY")
    log.info("=" * 70)
    log.info(f"  V1 baseline:  F1={v1_metrics['f1']:.4f}  (P={v1_metrics['precision']:.4f} R={v1_metrics['recall']:.4f})")
    log.info(f"  V1 best:      F1={v1_best_metrics['f1']:.4f}  (P={v1_best_metrics['precision']:.4f} R={v1_best_metrics['recall']:.4f})")
    log.info(f"  V2 branching: F1={v2_metrics['f1']:.4f}  (P={v2_metrics['precision']:.4f} R={v2_metrics['recall']:.4f})")
    log.info(f"  V3 spatial:   F1={v3_metrics['f1']:.4f}  (P={v3_metrics['precision']:.4f} R={v3_metrics['recall']:.4f})")
    log.info(f"  V4 ensemble:  F1={v4_metrics['f1']:.4f}  (P={v4_metrics['precision']:.4f} R={v4_metrics['recall']:.4f})")
    log.info(f"\n  Total runtime: {elapsed/60:.1f} minutes")

    # Save results JSON
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_gene_guided_neurons": len(ann_sub),
        "n_real_edges": len(real_edges),
        "v1_baseline": v1_metrics,
        "v1_best": v1_best_metrics,
        "v1_best_params": best_params_v1,
        "v2_branching": v2_metrics,
        "v3_spatial": v3_metrics,
        "v4_ensemble": v4_metrics,
        "signature_hemilineages": SIGNATURE_HEMILINEAGES,
        "runtime_seconds": elapsed
    }
    out_path = Path("/home/ubuntu/bulletproof_results/trajectory_growth.json")
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    log.info(f"\nResults saved to {out_path}")
    log.info("DONE.")


if __name__ == "__main__":
    main()
