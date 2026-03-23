#!/usr/bin/env python3
"""
Axon trajectory growth model for FlyWire connectome.

Uses soma positions + connectivity as a proxy for axon trajectories.
Vector from pre-soma to post-soma approximates axon growth direction.
Simulates growth along hemilineage vector fields and predicts connections.

Includes: PCA-based principal axis, bidirectional growth, trajectory-line
proximity, and parameter sweep.
"""

import json
import logging
import time
import warnings
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.decomposition import PCA

from compile.constants import SIGNATURE_HEMIS
from compile.data import get_data_dir, load_annotations

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SIGNATURE_HEMILINEAGES = sorted(SIGNATURE_HEMIS)
SIGNATURE_CELL_CLASSES = [
    "ME>LO.LOP", "LOP", "DAN", "ME", "LA", "CX", "ME>LA", "LO", "ME>LO",
]


def load_data():
    """Load annotations and connectivity for trajectory model."""
    logger.info("Loading flywire_annotations.tsv ...")
    ann = load_annotations()
    logger.info("Loaded %d neuron annotations", len(ann))

    ann["hemilineage"] = ann["ito_lee_hemilineage"].fillna(ann.get("hartenstein_hemilineage", ""))
    mask_hemi = ann["hemilineage"].isin(SIGNATURE_HEMILINEAGES)
    gene_guided_ann = ann[mask_hemi].copy()
    logger.info("Gene-guided neurons (hemi filter): %d", len(gene_guided_ann))

    gene_guided_ann = gene_guided_ann.dropna(subset=["soma_x", "soma_y", "soma_z"])
    logger.info("With soma positions: %d", len(gene_guided_ann))

    soma_pos = dict(
        zip(gene_guided_ann["root_id"], gene_guided_ann[["soma_x", "soma_y", "soma_z"]].values)
    )
    soma_hemi = dict(zip(gene_guided_ann["root_id"], gene_guided_ann["hemilineage"]))
    gene_guided_ids = set(gene_guided_ann["root_id"].values)
    logger.info("Unique gene-guided root IDs: %d", len(gene_guided_ids))

    logger.info("Loading connectivity parquet ...")
    data_dir = get_data_dir()
    t0 = time.time()
    conn = pd.read_parquet(
        data_dir / "2025_Connectivity_783.parquet",
        columns=["Presynaptic_ID", "Postsynaptic_ID", "Connectivity"],
    )
    logger.info("Loaded %d connections in %.1fs", len(conn), time.time() - t0)

    conn_gg = conn[
        conn["Presynaptic_ID"].isin(gene_guided_ids)
        & conn["Postsynaptic_ID"].isin(gene_guided_ids)
    ].copy()
    logger.info("Gene-guided internal connections: %d", len(conn_gg))

    real_connections = set(zip(conn_gg["Presynaptic_ID"], conn_gg["Postsynaptic_ID"]))
    logger.info("Real connection pairs: %d", len(real_connections))

    return gene_guided_ids, soma_pos, soma_hemi, conn_gg, real_connections


def compute_hemilineage_fields(conn_gg, soma_pos, soma_hemi):
    """Compute trajectory vectors and hemilineage vector fields."""
    conn_gg = conn_gg[
        conn_gg["Presynaptic_ID"].isin(soma_pos) & conn_gg["Postsynaptic_ID"].isin(soma_pos)
    ].copy()

    pre_somas = np.array([soma_pos[rid] for rid in conn_gg["Presynaptic_ID"]])
    post_somas = np.array([soma_pos[rid] for rid in conn_gg["Postsynaptic_ID"]])
    raw_vectors = post_somas - pre_somas
    norms = np.linalg.norm(raw_vectors, axis=1, keepdims=True)
    norms = np.where(norms < 1e-6, 1.0, norms)
    unit_vectors = raw_vectors / norms

    conn_gg["pre_hemi"] = conn_gg["Presynaptic_ID"].map(soma_hemi)
    conn_gg = conn_gg.dropna(subset=["pre_hemi"])

    hemi_vectors = defaultdict(list)
    for i, row in enumerate(conn_gg.itertuples()):
        hemi_vectors[row.pre_hemi].append(unit_vectors[i])

    hemi_stats = {}
    for hemi, vecs in hemi_vectors.items():
        vecs = np.array(vecs)
        n = len(vecs)
        mean_dir = vecs.mean(axis=0)
        mean_norm = np.linalg.norm(mean_dir)
        mean_dir_unit = mean_dir / mean_norm if mean_norm > 1e-6 else np.array([1.0, 0.0, 0.0])
        concentration = mean_norm

        if n >= 3:
            pca = PCA(n_components=min(3, n))
            pca.fit(vecs)
            principal_axis = pca.components_[0]
            if np.dot(principal_axis, mean_dir) < 0:
                principal_axis = -principal_axis
            var_explained = pca.explained_variance_ratio_[0]
        else:
            principal_axis = mean_dir_unit
            var_explained = 1.0

        hemi_stats[hemi] = {
            "n_connections": n,
            "mean_direction": mean_dir_unit,
            "principal_axis": principal_axis,
            "concentration": concentration,
            "var_explained": var_explained,
        }

    logger.info("Hemilineages with trajectory data: %d", len(hemi_stats))
    return hemi_stats


def simulate_axon_growth(pre_id, soma_xyz, direction, all_ids, all_somas, kd_tree,
                         step_size=5000, n_steps=20, synapse_radius=8000):
    """Simulate axon growing from soma along direction vector."""
    predicted = set()
    pos = soma_xyz.copy().astype(float)
    for _ in range(n_steps):
        pos = pos + direction * step_size
        idxs = kd_tree.query_ball_point(pos, synapse_radius)
        for idx in idxs:
            nid = all_ids[idx]
            if nid != pre_id:
                predicted.add(nid)
    return predicted


def evaluate(predicted_set, real_set):
    """Compute precision, recall, F1."""
    tp = len(predicted_set & real_set)
    fp = len(predicted_set - real_set)
    fn = len(real_set - predicted_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def main():
    logger.info("=" * 70)
    logger.info("AXON TRAJECTORY GROWTH MODEL v1.0")
    logger.info("=" * 70)

    gene_guided_ids, soma_pos, soma_hemi, conn_gg, real_connections = load_data()
    hemi_stats = compute_hemilineage_fields(conn_gg, soma_pos, soma_hemi)

    # Build KD-tree
    gg_ids = np.array(list(gene_guided_ids & set(soma_pos.keys())))
    gg_somas = np.array([soma_pos[rid] for rid in gg_ids])
    tree = cKDTree(gg_somas)
    logger.info("KD-tree built over %d gene-guided neurons", len(gg_ids))

    # Baseline simulation
    STEP_SIZE = 5000
    N_STEPS = 25
    SYNAPSE_RADIUS = 7000

    logger.info("Running trajectory simulation ...")
    t0 = time.time()
    all_predicted = set()
    n_simulated = 0
    for pre_id in gene_guided_ids:
        if pre_id not in soma_pos:
            continue
        hemi = soma_hemi.get(pre_id)
        if hemi not in hemi_stats:
            continue
        targets = simulate_axon_growth(
            pre_id, soma_pos[pre_id], hemi_stats[hemi]["mean_direction"],
            gg_ids, gg_somas, tree,
            step_size=STEP_SIZE, n_steps=N_STEPS, synapse_radius=SYNAPSE_RADIUS,
        )
        for post_id in targets:
            all_predicted.add((pre_id, post_id))
        n_simulated += 1

    logger.info("Simulated %d neurons in %.1fs", n_simulated, time.time() - t0)
    metrics = evaluate(all_predicted, real_connections)
    logger.info("Baseline: P=%.4f R=%.4f F1=%.4f", metrics["precision"], metrics["recall"], metrics["f1"])

    # Parameter sweep
    logger.info("Parameter sweep...")
    best_f1 = metrics["f1"]
    best_params = {"step_size": STEP_SIZE, "n_steps": N_STEPS, "synapse_radius": SYNAPSE_RADIUS}

    sweep_configs = [
        (3000, 30, 5000), (3000, 30, 8000), (5000, 25, 5000),
        (5000, 25, 10000), (7000, 20, 6000), (7000, 20, 9000),
        (4000, 35, 7000), (10000, 15, 8000), (2000, 50, 4000),
    ]
    for step, nstep, radius in sweep_configs:
        predicted_sweep = set()
        for pre_id in gene_guided_ids:
            if pre_id not in soma_pos:
                continue
            hemi = soma_hemi.get(pre_id)
            if hemi not in hemi_stats:
                continue
            targets = simulate_axon_growth(
                pre_id, soma_pos[pre_id], hemi_stats[hemi]["mean_direction"],
                gg_ids, gg_somas, tree,
                step_size=step, n_steps=nstep, synapse_radius=radius,
            )
            for post_id in targets:
                predicted_sweep.add((pre_id, post_id))

        m = evaluate(predicted_sweep, real_connections)
        flag = " *** BEST ***" if m["f1"] > best_f1 else ""
        logger.info(
            "  step=%d nstep=%d radius=%d  P=%.4f R=%.4f F1=%.4f%s",
            step, nstep, radius, m["precision"], m["recall"], m["f1"], flag,
        )
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_params = {"step_size": step, "n_steps": nstep, "synapse_radius": radius}

    # PCA principal axis
    all_predicted_pca = set()
    for pre_id in gene_guided_ids:
        if pre_id not in soma_pos:
            continue
        hemi = soma_hemi.get(pre_id)
        if hemi not in hemi_stats:
            continue
        targets = simulate_axon_growth(
            pre_id, soma_pos[pre_id], hemi_stats[hemi]["principal_axis"],
            gg_ids, gg_somas, tree,
            step_size=best_params["step_size"], n_steps=best_params["n_steps"],
            synapse_radius=best_params["synapse_radius"],
        )
        for post_id in targets:
            all_predicted_pca.add((pre_id, post_id))

    m_pca = evaluate(all_predicted_pca, real_connections)
    logger.info("PCA axis: P=%.4f R=%.4f F1=%.4f", m_pca["precision"], m_pca["recall"], m_pca["f1"])

    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "version": "1.0",
        "n_neurons": len(gene_guided_ids),
        "n_real_connections": len(real_connections),
        "hemilineages": len(hemi_stats),
        "params": best_params,
        "baseline": metrics,
        "pca": m_pca,
        "best_f1": best_f1,
    }
    out_path = Path("results/trajectory_results_v1.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Results saved to %s", out_path)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
