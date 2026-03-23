#!/usr/bin/env python3
"""
Curvature retest: Does curvature predict Izhikevich-evolvability?

Computes Ollivier-Ricci curvature on the module graph and tests
correlation with Izhikevich-based evolvability, controlling for the
synapse count confound that collapsed the LIF result.
"""

import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy import stats

from compile.data import build_annotation_maps, load_annotations, load_connectome, load_module_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ollivier_ricci_curvature(G, src, tgt, alpha=0.5):
    """Compute Ollivier-Ricci curvature for edge (src, tgt)."""
    from scipy.optimize import linear_sum_assignment

    src_neighbors = list(G.successors(src))
    tgt_neighbors = list(G.successors(tgt))
    if not src_neighbors or not tgt_neighbors:
        return 0.0

    src_nodes = [src] + src_neighbors
    src_probs = [alpha] + [(1 - alpha) / len(src_neighbors)] * len(src_neighbors)
    tgt_nodes = [tgt] + tgt_neighbors
    tgt_probs = [alpha] + [(1 - alpha) / len(tgt_neighbors)] * len(tgt_neighbors)

    cost_matrix = np.zeros((len(src_nodes), len(tgt_nodes)))
    for i, s in enumerate(src_nodes):
        for j, t in enumerate(tgt_nodes):
            if s == t:
                cost_matrix[i, j] = 0
            else:
                try:
                    cost_matrix[i, j] = nx.shortest_path_length(G, s, t)
                except nx.NetworkXNoPath:
                    cost_matrix[i, j] = G.number_of_nodes()

    src_probs = np.array(src_probs)
    tgt_probs = np.array(tgt_probs)
    src_counts = (src_probs * 100).astype(int)
    tgt_counts = (tgt_probs * 100).astype(int)
    src_counts[-1] += 100 - src_counts.sum()
    tgt_counts[-1] += 100 - tgt_counts.sum()

    n_src = int(src_counts.sum())
    n_tgt = int(tgt_counts.sum())
    scaled_cost = np.zeros((n_src, n_tgt))

    row = 0
    for i, sc in enumerate(src_counts):
        for _ in range(sc):
            col = 0
            for j, tc in enumerate(tgt_counts):
                for _ in range(tc):
                    scaled_cost[row, col] = cost_matrix[i, j]
                    col += 1
            row += 1

    row_ind, col_ind = linear_sum_assignment(scaled_cost[:row, :col])
    W1 = scaled_cost[row_ind, col_ind].sum() / min(row, col)

    try:
        d = nx.shortest_path_length(G, src, tgt)
    except nx.NetworkXNoPath:
        d = G.number_of_nodes()

    return 1.0 - W1 / d if d > 0 else 0.0


def main():
    logger.info("=" * 60)
    logger.info("CURVATURE RETEST")
    logger.info("=" * 60)

    labels = load_module_labels()
    df = load_connectome()[0]
    pre_mods = labels[df["Presynaptic_Index"].values].astype(int)
    post_mods = labels[df["Postsynaptic_Index"].values].astype(int)

    edge_syn_count = defaultdict(int)
    for i in range(len(df)):
        edge_syn_count[(int(pre_mods[i]), int(post_mods[i]))] += 1

    G = nx.DiGraph()
    n_modules = int(labels.max()) + 1
    for mod in range(n_modules):
        G.add_node(mod)
    for (src, tgt), count in edge_syn_count.items():
        if src != tgt:
            G.add_edge(src, tgt, weight=count)

    inter_module_edges = [(s, t) for (s, t) in edge_syn_count if s != t]
    logger.info("Module graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())

    # Compute curvature
    logger.info("Computing Ollivier-Ricci curvature...")
    curvatures = {}
    for i, (src, tgt) in enumerate(inter_module_edges):
        curvatures[(src, tgt)] = ollivier_ricci_curvature(G, src, tgt)
        if (i + 1) % 500 == 0:
            logger.info("  [%d/%d]", i + 1, len(inter_module_edges))

    logger.info("Curvature: mean=%.4f std=%.4f", np.mean(list(curvatures.values())), np.std(list(curvatures.values())))

    # Load evolvability data
    izh_evolvable = set()
    output_dir = os.environ.get("COMPILE_OUTPUT_DIR", "results")
    for candidate in [os.path.join(output_dir, "izh_strategy_switching.json"),
                       "results/izh_strategy_switching.json"]:
        if os.path.exists(candidate):
            with open(candidate) as f:
                data = json.load(f)
            izh_evolvable = set(tuple(e) for e in data.get("accepted_edges", []))
            logger.info("Izh evolvable edges: %d", len(izh_evolvable))
            break

    # Correlation analysis
    edges = list(curvatures.keys())
    curv_vals = np.array([curvatures[e] for e in edges])
    syn_counts = np.array([edge_syn_count[e] for e in edges])
    log_syn = np.log1p(syn_counts)
    izh_evol = np.array([1 if e in izh_evolvable else 0 for e in edges])

    p_raw = p_partial = None
    if izh_evol.sum() > 0:
        evol_curv = curv_vals[izh_evol == 1]
        non_evol_curv = curv_vals[izh_evol == 0]
        _, p_raw = stats.mannwhitneyu(evol_curv, non_evol_curv, alternative="two-sided")
        r_pb, p_pb = stats.pointbiserialr(izh_evol, curv_vals)
        logger.info("Raw: evolvable mean=%.4f, non-evolvable mean=%.4f, p=%.6e",
                     evol_curv.mean(), non_evol_curv.mean(), p_raw)

    if izh_evol.sum() > 1:
        slope, intercept = np.polyfit(log_syn, curv_vals, 1)
        curv_residual = curv_vals - (slope * log_syn + intercept)
        r_partial, p_partial = stats.pointbiserialr(izh_evol, curv_residual)
        logger.info("Partial (controlling synapse count): r=%.4f p=%.6e", r_partial, p_partial)
        if p_partial < 0.05:
            logger.info(">>> SIGNIFICANT! Curvature predicts Izh-evolvability after confound control")
        else:
            logger.info(">>> Not significant after confound control")

    outdir = Path(output_dir) / "curvature_retest"
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "curvature_retest.json", "w") as f:
        json.dump({
            "izh_evolvable": sorted([list(e) for e in izh_evolvable]),
            "raw_p": float(p_raw) if p_raw is not None else None,
            "partial_p": float(p_partial) if p_partial is not None else None,
        }, f, indent=2)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
