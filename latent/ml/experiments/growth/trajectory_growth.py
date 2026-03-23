#!/usr/bin/env python3
"""
Axon trajectory growth model for FlyWire connectome.

Predicts synaptic connections by simulating axon growth through 3D brain
space.  Three model versions with increasing sophistication:
  V1: Mean direction per hemilineage + tube search along trajectory
  V2: Distance-decay synapse probability + position-dependent vector field
  V3: KNN vector field + branching + target-region attraction
"""

import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import KDTree

from compile.constants import SIGNATURE_HEMIS
from compile.data import get_data_dir, load_annotations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SIGNATURE_HEMILINEAGES = sorted(SIGNATURE_HEMIS)


def _load_annotations_with_positions():
    """Load annotations and filter to neurons with valid positions."""
    logger.info("Loading annotations...")
    ann = load_annotations()
    ann = ann.dropna(subset=["soma_x", "soma_y", "soma_z", "pos_x", "pos_y", "pos_z"])
    ann["root_id"] = ann["root_id"].astype(str)
    logger.info("Loaded %d annotated neurons with positions", len(ann))
    return ann


def _load_connectivity():
    """Load connectivity parquet."""
    logger.info("Loading connectivity parquet...")
    data_dir = get_data_dir()
    import pyarrow.parquet as pq

    df = pq.read_table(data_dir / "2025_Connectivity_783.parquet").to_pandas()
    df["Presynaptic_ID"] = df["Presynaptic_ID"].astype(str)
    df["Postsynaptic_ID"] = df["Postsynaptic_ID"].astype(str)
    logger.info("Loaded %d synaptic connections", len(df))
    return df


def get_gene_guided_neurons(ann):
    """Select the gene-guided processor (signature hemilineages)."""
    mask = ann["ito_lee_hemilineage"].isin(SIGNATURE_HEMILINEAGES)
    subset = ann[mask].copy()
    logger.info("Gene-guided processor: %d neurons", len(subset))
    return subset


def compute_trajectory_vectors(ann):
    """For each neuron: direction vector = (pos - soma) normalized."""
    soma = ann[["soma_x", "soma_y", "soma_z"]].values
    pos = ann[["pos_x", "pos_y", "pos_z"]].values
    raw_vecs = pos - soma
    norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
    zero_mask = norms.flatten() < 1e-6
    norms[zero_mask] = 1.0
    unit_vecs = raw_vecs / norms
    unit_vecs[zero_mask] = 0.0
    return unit_vecs, norms.flatten()


def fit_hemilineage_vector_fields(ann, unit_vecs):
    """Compute mean direction and angular spread per hemilineage."""
    mean_dirs = {}
    spreads = {}
    hemi_col = ann["ito_lee_hemilineage"].values

    for hemi in SIGNATURE_HEMILINEAGES:
        idx = np.where(hemi_col == hemi)[0]
        if len(idx) == 0:
            mean_dirs[hemi] = np.zeros(3)
            spreads[hemi] = np.pi
            continue
        vecs = unit_vecs[idx]
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

        dots = np.clip(vecs @ mean_v, -1, 1)
        angles = np.arccos(dots)
        spreads[hemi] = float(angles.mean())
        logger.info(
            "  [%s] n=%d, dir=(%.3f,%.3f,%.3f), spread=%.1f deg",
            hemi, len(idx), mean_v[0], mean_v[1], mean_v[2], np.degrees(spreads[hemi]),
        )

    return mean_dirs, spreads


def simulate_trajectories_v1(ann_subset, ann_all, mean_dirs,
                              tube_radius=5000, n_steps=20, step_size=5000):
    """V1: Walk in mean hemilineage direction, capture neurons in tube."""
    logger.info("V1 Simulation: tube_radius=%d, steps=%d, step=%d", tube_radius, n_steps, step_size)
    all_soma = ann_all[["soma_x", "soma_y", "soma_z"]].values
    all_ids = ann_all["root_id"].values
    tree = KDTree(all_soma)

    hemi_col = ann_subset["ito_lee_hemilineage"].values
    soma_arr = ann_subset[["soma_x", "soma_y", "soma_z"]].values
    pre_ids = ann_subset["root_id"].values
    predicted_edges = set()

    for i in range(len(ann_subset)):
        hemi = hemi_col[i]
        if hemi not in mean_dirs:
            continue
        direction = mean_dirs[hemi]
        if np.linalg.norm(direction) < 0.1:
            continue
        pos = soma_arr[i].copy().astype(float)
        pre_id = pre_ids[i]
        for step in range(n_steps):
            pos += direction * step_size
            neighbors = tree.query_ball_point(pos, tube_radius)
            for ni in neighbors:
                post_id = all_ids[ni]
                if post_id != pre_id:
                    predicted_edges.add((pre_id, post_id))

    logger.info("  V1 predicted %d unique connections", len(predicted_edges))
    return predicted_edges


def simulate_trajectories_v2(ann_subset, ann_all, mean_dirs, spreads,
                              tube_radius=4000, n_steps=25, step_size=4000,
                              n_branches=3, branch_angle_scale=0.3):
    """V2: Per-neuron direction with random deviation + multiple branches."""
    logger.info("V2 Simulation: tube=%d, steps=%d, step=%d, branches=%d",
                tube_radius, n_steps, step_size, n_branches)
    all_soma = ann_all[["soma_x", "soma_y", "soma_z"]].values
    all_ids = ann_all["root_id"].values
    tree = KDTree(all_soma)

    hemi_col = ann_subset["ito_lee_hemilineage"].values
    soma_arr = ann_subset[["soma_x", "soma_y", "soma_z"]].values
    pre_ids = ann_subset["root_id"].values
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

    logger.info("  V2 predicted %d unique connections", len(predicted_edges))
    return predicted_edges


def build_spatial_vector_field(ann_all, unit_vecs_all):
    """Build a KNN-based spatial vector field."""
    logger.info("Building spatial vector field (KNN)...")
    soma_all = ann_all[["soma_x", "soma_y", "soma_z"]].values
    field_tree = KDTree(soma_all)
    return field_tree, soma_all, unit_vecs_all


def query_vector_field(pos, field_tree, soma_all, unit_vecs_all, n_neighbors=30):
    """Get interpolated direction at position from nearby neurons."""
    dists, idxs = field_tree.query(pos, k=min(n_neighbors, len(soma_all)))
    vecs = unit_vecs_all[idxs]
    w = 1.0 / (dists + 1e-6)
    w = w / w.sum()
    mean_v = (vecs * w[:, None]).sum(axis=0)
    n = np.linalg.norm(mean_v)
    return mean_v / n if n > 1e-6 else mean_v


def simulate_trajectories_v3(ann_subset, ann_all, unit_vecs_all,
                              tube_radius=3500, n_steps=30, step_size=3500,
                              n_branches=4, use_hemi_bias=True, mean_dirs=None):
    """V3: Follow global spatial vector field with hemilineage bias."""
    logger.info("V3 Simulation: tube=%d, steps=%d, step=%d, branches=%d",
                tube_radius, n_steps, step_size, n_branches)
    field_tree, soma_all, vecs_all = build_spatial_vector_field(ann_all, unit_vecs_all)

    all_soma = ann_all[["soma_x", "soma_y", "soma_z"]].values
    all_ids = ann_all["root_id"].values
    target_tree = KDTree(all_soma)

    hemi_col = ann_subset["ito_lee_hemilineage"].values
    soma_arr = ann_subset[["soma_x", "soma_y", "soma_z"]].values
    pre_ids = ann_subset["root_id"].values
    predicted_edges = set()
    rng = np.random.default_rng(123)

    for i in range(len(ann_subset)):
        hemi = hemi_col[i]
        pre_id = pre_ids[i]
        hemi_dir = mean_dirs.get(hemi, np.zeros(3)) if use_hemi_bias and mean_dirs else np.zeros(3)

        for b in range(n_branches):
            pos = soma_arr[i].copy().astype(float)
            noise = rng.normal(0, 0.2, 3)
            init_dir = hemi_dir + noise
            n = np.linalg.norm(init_dir)
            if n < 1e-6:
                continue
            direction = init_dir / n

            for step in range(n_steps):
                pos += direction * step_size
                field_dir = query_vector_field(pos, field_tree, soma_all, vecs_all, n_neighbors=20)
                if np.linalg.norm(hemi_dir) > 0.1:
                    new_dir = 0.6 * hemi_dir + 0.4 * field_dir
                else:
                    new_dir = field_dir
                n = np.linalg.norm(new_dir)
                if n > 1e-6:
                    direction = new_dir / n

                neighbors = target_tree.query_ball_point(pos, tube_radius)
                for ni in neighbors:
                    post_id = all_ids[ni]
                    if post_id != pre_id:
                        predicted_edges.add((pre_id, post_id))

    logger.info("  V3 predicted %d unique connections", len(predicted_edges))
    return predicted_edges


def evaluate(predicted_edges, real_edges_set, version_name="V?"):
    """Compute precision, recall, F1."""
    if not predicted_edges:
        logger.info("  [%s] No predicted edges!", version_name)
        return {"precision": 0, "recall": 0, "f1": 0}

    tp = len(predicted_edges & real_edges_set)
    precision = tp / len(predicted_edges) if predicted_edges else 0
    recall = tp / len(real_edges_set) if real_edges_set else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    logger.info("[%s] RESULTS:", version_name)
    logger.info("  Real: %d  Predicted: %d  TP: %d", len(real_edges_set), len(predicted_edges), tp)
    logger.info("  Precision: %.4f  Recall: %.4f  F1: %.4f", precision, recall, f1)

    return {"precision": precision, "recall": recall, "f1": f1,
            "tp": tp, "predicted": len(predicted_edges), "real": len(real_edges_set)}


def main():
    t_start = time.time()
    logger.info("=" * 70)
    logger.info("AXON TRAJECTORY GROWTH MODEL -- FlyWire Connectome")
    logger.info("=" * 70)

    ann_all = _load_annotations_with_positions()
    conn_df = _load_connectivity()
    ann_sub = get_gene_guided_neurons(ann_all)

    gene_ids = set(ann_sub["root_id"].values)
    logger.info("Building real edge set within %d gene-guided neurons...", len(gene_ids))
    conn_sub = conn_df[
        conn_df["Presynaptic_ID"].isin(gene_ids) & conn_df["Postsynaptic_ID"].isin(gene_ids)
    ]
    real_edges = set(zip(conn_sub["Presynaptic_ID"], conn_sub["Postsynaptic_ID"]))
    logger.info("Real connections within subset: %d", len(real_edges))

    logger.info("Computing trajectory vectors...")
    unit_vecs_all, _ = compute_trajectory_vectors(ann_all)
    unit_vecs_sub, _ = compute_trajectory_vectors(ann_sub)

    logger.info("Fitting hemilineage vector fields...")
    mean_dirs, spreads = fit_hemilineage_vector_fields(ann_sub, unit_vecs_sub)

    # V1
    v1_pred = simulate_trajectories_v1(ann_sub, ann_all, mean_dirs)
    v1_metrics = evaluate(v1_pred, real_edges, "V1-baseline")

    # V2
    v2_pred = simulate_trajectories_v2(ann_sub, ann_all, mean_dirs, spreads)
    v2_metrics = evaluate(v2_pred, real_edges, "V2-branching")

    # V3
    v3_pred = simulate_trajectories_v3(
        ann_sub, ann_all, unit_vecs_all,
        use_hemi_bias=True, mean_dirs=mean_dirs,
    )
    v3_metrics = evaluate(v3_pred, real_edges, "V3-spatial-field")

    # V4: ensemble
    v4_pred = v2_pred | v3_pred
    v4_metrics = evaluate(v4_pred, real_edges, "V4-ensemble")

    elapsed = time.time() - t_start
    logger.info("FINAL SUMMARY")
    logger.info("  V1: F1=%.4f  V2: F1=%.4f  V3: F1=%.4f  V4: F1=%.4f",
                v1_metrics["f1"], v2_metrics["f1"], v3_metrics["f1"], v4_metrics["f1"])
    logger.info("  Total runtime: %.1f minutes", elapsed / 60)

    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_gene_guided_neurons": len(ann_sub),
        "n_real_edges": len(real_edges),
        "v1_baseline": v1_metrics,
        "v2_branching": v2_metrics,
        "v3_spatial": v3_metrics,
        "v4_ensemble": v4_metrics,
        "runtime_seconds": elapsed,
    }
    out_path = Path("results/trajectory_growth.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info("Results saved to %s", out_path)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
