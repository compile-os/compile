#!/usr/bin/env python3
"""
Developmental growth simulation for 8,158-neuron gene-guided processor.

Simulates axon growth with progressive rule additions, measuring what
percentage of real FlyWire connections each rule set produces.

Rules:
  0: Baseline -- random connections weighted by distance
  1: + Hemilineage-pair connection probabilities from real data
  2: + Neurotransmitter compatibility
  3: + Sharpened spatial proximity weighting
  4: + Target density (axons prefer denser regions)
  5: + Synapse count matching (calibrate to real pair counts)
"""

import json
import logging
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from compile.constants import NT_COMPATIBILITY, NT_COMPATIBILITY_DEFAULT

warnings.filterwarnings("ignore")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

np.random.seed(42)

# Output paths (configurable via environment or defaults)
RESULTS_FILE = "results/growth_simulation_results.json"
COMPILER_FILE = "results/developmental_compiler.json"


def load_data(compiler_path=COMPILER_FILE):
    """Load all data for the growth simulation."""
    logger.info("=" * 70)
    logger.info("DEVELOPMENTAL GROWTH SIMULATION -- FlyWire 8,158-Neuron Processor")
    logger.info("=" * 70)

    # Load compiler program
    with open(compiler_path) as f:
        compiler = json.load(f)

    cell_types = compiler["growth_program"]["cell_types"]
    conn_rules = compiler["growth_program"]["connections"]
    target_synapses = compiler["target_synapses"]

    hemilineage_list = [ct["hemilineage"] for ct in cell_types]
    hl_count_map = {ct["hemilineage"]: ct["count"] for ct in cell_types}
    hl_nt_map = {ct["hemilineage"]: ct["neurotransmitter"] for ct in cell_types}

    logger.info(
        "Compiler: %d hemilineages, %d connection rules",
        len(cell_types), len(conn_rules),
    )
    logger.info("Target synapses from compiler: %d", target_synapses)

    # Load annotations
    logger.info("Loading FlyWire annotations...")
    from compile.data import load_annotations as _load_ann

    t0 = time.time()
    ann = _load_ann()
    logger.info("Loaded %d neurons in %.1fs", len(ann), time.time() - t0)

    ann["_hl"] = ann["ito_lee_hemilineage"].fillna("putative_primary")
    ann.loc[ann["_hl"] == "", "_hl"] = "putative_primary"
    ann.loc[~ann["_hl"].isin(hemilineage_list), "_hl"] = "putative_primary"

    mask = ann["_hl"].isin(hemilineage_list)
    pool = ann[mask].copy()
    logger.info("Neurons in target hemilineages: %d", len(pool))

    if "soma_x" in pool.columns and pool["soma_x"].notna().mean() > 0.5:
        xyz_cols = ["soma_x", "soma_y", "soma_z"]
    else:
        xyz_cols = ["pos_x", "pos_y", "pos_z"]
    logger.info("Using coordinate columns: %s", xyz_cols)

    pool = pool.dropna(subset=xyz_cols)
    logger.info("Neurons with valid coordinates: %d", len(pool))

    sampled_frames = []
    for hl in hemilineage_list:
        target_n = hl_count_map[hl]
        subset = pool[pool["_hl"] == hl]
        if len(subset) == 0:
            logger.warning("No neurons found for hemilineage: %s", hl)
            continue
        if len(subset) > target_n:
            subset = subset.sample(n=target_n, random_state=42)
        sampled_frames.append(subset)

    neurons = pd.concat(sampled_frames, ignore_index=True)
    n = len(neurons)
    logger.info("Final neuron set: %d neurons", n)

    coords = neurons[xyz_cols].values.astype(np.float32)
    root_ids = neurons["root_id"].values
    hl_labels = neurons["_hl"].values
    nt_labels = np.array([hl_nt_map.get(hl, "acetylcholine") for hl in hl_labels])

    id_to_idx = {int(rid): i for i, rid in enumerate(root_ids)}

    # Load connectivity
    logger.info("Loading connectivity data...")
    from compile.data import get_data_dir

    data_dir = get_data_dir()
    t0 = time.time()
    conn_df = pd.read_parquet(data_dir / "2025_Connectivity_783.parquet")
    logger.info("Full connectome: %d synaptic contacts in %.1fs", len(conn_df), time.time() - t0)

    our_ids = set(id_to_idx.keys())
    mask_pre = conn_df["Presynaptic_ID"].isin(our_ids)
    mask_post = conn_df["Postsynaptic_ID"].isin(our_ids)
    real_conn = conn_df[mask_pre & mask_post].copy()
    logger.info("Synaptic contacts within our %d-neuron set: %d", n, len(real_conn))

    pre_arr = real_conn["Presynaptic_ID"].map(id_to_idx).values
    post_arr = real_conn["Postsynaptic_ID"].map(id_to_idx).values
    valid = ~np.isnan(pre_arr.astype(float)) & ~np.isnan(post_arr.astype(float))
    pre_arr = pre_arr[valid].astype(np.int32)
    post_arr = post_arr[valid].astype(np.int32)

    real_encoded = pre_arr.astype(np.int64) * n + post_arr.astype(np.int64)
    real_pairs = set(real_encoded.tolist())
    logger.info("Unique real (pre, post) neuron pairs: %d", len(real_pairs))

    pair_weights = {}
    conn_vals = real_conn["Connectivity"].values[valid]
    for p, q, syn in zip(pre_arr, post_arr, conn_vals):
        key = int(p) * n + int(q)
        pair_weights[key] = pair_weights.get(key, 0) + int(syn)

    hl_pair_prob = {}
    for rule in conn_rules:
        key = (rule["from"], rule["to"])
        hl_pair_prob[key] = rule["connection_probability"]

    unique_hls = sorted(set(hl_labels))
    hl_to_int = {hl: i for i, hl in enumerate(unique_hls)}
    hl_int = np.array([hl_to_int[hl] for hl in hl_labels], dtype=np.int16)

    n_hl = len(unique_hls)
    hl_prob_matrix = np.full((n_hl, n_hl), 0.001, dtype=np.float32)
    for (hl_from, hl_to), prob in hl_pair_prob.items():
        if hl_from in hl_to_int and hl_to in hl_to_int:
            i, j = hl_to_int[hl_from], hl_to_int[hl_to]
            hl_prob_matrix[i, j] = max(prob, 0.001)

    unique_nts = sorted(set(nt_labels))
    nt_to_int = {nt: i for i, nt in enumerate(unique_nts)}
    nt_int = np.array([nt_to_int[nt] for nt in nt_labels], dtype=np.int8)

    n_nt = len(unique_nts)
    nt_compat_matrix = np.full((n_nt, n_nt), NT_COMPATIBILITY_DEFAULT, dtype=np.float32)
    for (nt_from, nt_to), val in NT_COMPATIBILITY.items():
        if nt_from in nt_to_int and nt_to in nt_to_int:
            i, j = nt_to_int[nt_from], nt_to_int[nt_to]
            nt_compat_matrix[i, j] = val

    logger.info("Data loading complete.")
    logger.info(
        "Neurons: %d | Real pairs: %d | Hemilineages: %d | NTs: %d",
        n, len(real_pairs), n_hl, n_nt,
    )

    return dict(
        n=n, coords=coords, root_ids=root_ids, hl_labels=hl_labels,
        nt_labels=nt_labels, hl_int=hl_int, nt_int=nt_int,
        hl_prob_matrix=hl_prob_matrix, nt_compat_matrix=nt_compat_matrix,
        real_pairs=real_pairs, pair_weights=pair_weights,
        unique_hls=unique_hls, unique_nts=unique_nts,
        target_synapses=target_synapses,
    )


def build_neighbor_graph(coords, k=300):
    """Build k-nearest-neighbor graph for axon growth routing."""
    logger.info("Building KD-tree neighbor graph (k=%d)...", k)
    t0 = time.time()
    tree = cKDTree(coords)
    dists, idxs = tree.query(coords, k=k + 1)
    dists = dists[:, 1:].astype(np.float32)
    idxs = idxs[:, 1:].astype(np.int32)
    logger.info("Done in %.1fs | median NN dist: %.1f", time.time() - t0, np.median(dists[:, 0]))

    sigma = np.median(dists[:, :20], axis=1).astype(np.float32)
    sigma[sigma < 1.0] = 1.0

    r_density = float(np.median(sigma) * 2.0)
    logger.info("Density radius: %.1f nm", r_density)
    density = np.array(
        [len(tree.query_ball_point(coords[i], r_density)) for i in range(len(coords))],
        dtype=np.float32,
    )
    density /= density.max()

    return dists, idxs, sigma, density


def simulate(data, dists, idxs, sigma, density, rule_level, k=300):
    """Grow axons and measure connectivity match at given rule level."""
    n = data["n"]
    hl_int = data["hl_int"]
    nt_int = data["nt_int"]
    hl_pm = data["hl_prob_matrix"]
    nt_cm = data["nt_compat_matrix"]
    real_pairs = data["real_pairs"]
    n_real = len(real_pairs)

    rule_names = {
        0: "Distance-only baseline",
        1: "+ Hemilineage-pair probabilities",
        2: "+ Neurotransmitter compatibility",
        3: "+ Sharpened spatial decay",
        4: "+ Target density weighting",
        5: "+ Synapse-count calibration",
    }

    logger.info("=" * 60)
    logger.info("RULE LEVEL %d: %s", rule_level, rule_names.get(rule_level, ""))
    logger.info("=" * 60)

    t0 = time.time()
    avg_out_degree = n_real / n

    simulated_encoded = []
    for i in range(n):
        nbr_idx = idxs[i]
        nbr_dist = dists[i]
        sig_i = sigma[i]

        w = np.exp(-nbr_dist / sig_i)

        if rule_level >= 1:
            w = w * hl_pm[hl_int[i], hl_int[nbr_idx]]
        if rule_level >= 2:
            w = w * nt_cm[nt_int[i], nt_int[nbr_idx]]
        if rule_level >= 3:
            w = w * np.exp(-nbr_dist / sig_i)
        if rule_level >= 4:
            w = w * (1.0 + density[nbr_idx])

        w_sum = w.sum()
        if w_sum <= 0:
            continue
        w /= w_sum

        n_out = max(1, int(round(np.random.poisson(avg_out_degree))))
        n_out = min(n_out, k)
        chosen = np.random.choice(k, size=n_out, replace=False, p=w)
        targets = nbr_idx[chosen]
        for t in targets:
            simulated_encoded.append(i * n + int(t))

    sim_set = set(simulated_encoded)

    if rule_level >= 5 and len(sim_set) > n_real:
        sim_set = set(list(sim_set)[:n_real])

    matched = sim_set & real_pairs
    n_sim = len(sim_set)
    n_matched = len(matched)

    recall = n_matched / n_real if n_real > 0 else 0.0
    precision = n_matched / n_sim if n_sim > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    elapsed = time.time() - t0
    logger.info("  Simulated pairs : %10d", n_sim)
    logger.info("  Real pairs      : %10d", n_real)
    logger.info("  Matched pairs   : %10d", n_matched)
    logger.info("  Recall          : %8.2f%%", recall * 100)
    logger.info("  Precision       : %8.2f%%", precision * 100)
    logger.info("  F1 Score        : %8.2f%%", f1 * 100)
    logger.info("  Time            : %.1fs", elapsed)

    return {
        "rule_level": rule_level,
        "rule_name": rule_names.get(rule_level, ""),
        "n_simulated": n_sim,
        "n_real": n_real,
        "n_matched": n_matched,
        "recall_pct": round(recall * 100, 4),
        "precision_pct": round(precision * 100, 4),
        "f1_pct": round(f1 * 100, 4),
        "elapsed_s": round(elapsed, 1),
    }


def main():
    data = load_data()

    K = 300
    dists, idxs, sigma, density = build_neighbor_graph(data["coords"], k=K)

    all_results = []
    for level in range(6):
        result = simulate(data, dists, idxs, sigma, density, rule_level=level, k=K)
        all_results.append(result)

    # Summary table
    logger.info("=" * 70)
    logger.info("SUMMARY -- Progressive Rule Addition")
    logger.info("=" * 70)
    logger.info(
        "%-6s %-42s %8s %10s %8s", "Level", "Rule", "Recall", "Precision", "F1",
    )
    for r in all_results:
        logger.info(
            "  %-4d %-42s %7.2f%%  %8.2f%%  %7.2f%%",
            r["rule_level"], r["rule_name"],
            r["recall_pct"], r["precision_pct"], r["f1_pct"],
        )

    # Save results
    out_path = Path(RESULTS_FILE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "developmental_growth_simulation",
        "n_neurons": data["n"],
        "n_real_pairs": len(data["real_pairs"]),
        "k_neighbors": K,
        "results": all_results,
    }
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Results saved to: %s", out_path)

    best = max(all_results, key=lambda r: r["recall_pct"])
    logger.info("Best rule level: %d -- %s", best["rule_level"], best["rule_name"])
    logger.info("Best recall: %.2f%% of real FlyWire connections produced", best["recall_pct"])


if __name__ == "__main__":
    main()
