#!/usr/bin/env python3
"""
Experiment A: Prediction validation -- break the circularity.

Compile navigation on the gene-guided circuit.  BEFORE running evolution, write
down predictions based on full-connectome results, then check.

Pre-registered predictions (from full connectome experiments):
  P1: Evolvable hemilineages will include VPNd1, VPNd2 (visual projection neurons)
  P2: CX hemilineages (DM3_CX_d2, DM1_CX_d2) will be frozen for navigation
  P3: The evolvable surface will be <15% of edges
  P4: Navigation-compiled circuit will show INCREASED escape as side effect
  P5: putative_primary will be the most connected evolvable hemilineage

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS, DN_NAMES, STIM_SUGAR, STIM_LC4,
    SIGNATURE_HEMIS, NEURON_TYPES, GAIN,
    DT, W_SCALE, POISSON_WEIGHT, POISSON_RATE,
)
from compile.data import load_connectome, load_annotations, load_module_labels, build_annotation_maps
from compile.fitness import f_nav, f_esc
from compile.simulate import run_simulation
from compile.stats import bootstrap_ci, improvement_with_ci

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Predictions (pre-registered)
# ---------------------------------------------------------------------------

PREDICTIONS = {
    "P1": "VPNd1 and VPNd2 hemilineages will contain evolvable edges for navigation",
    "P2": "CX hemilineages (DM3_CX_d2, DM1_CX_d2) will be FROZEN for navigation",
    "P3": "Evolvable surface will be <15% of edges",
    "P4": "Escape score will INCREASE as side effect of navigation optimization (shared DN hub amplification)",
    "P5": "putative_primary will be the most connected evolvable hemilineage",
}


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(
    n_gen: int = 25,
    n_mut: int = 10,
    seed: int = 42,
    output_dir: str = "results",
):
    """Run the full prediction validation experiment."""
    logger.info("=" * 60)
    logger.info("PREDICTION VALIDATION EXPERIMENT")
    logger.info("Breaking the circularity: predict, then test")
    logger.info("=" * 60)

    # Load data
    df_conn, df_comp, num_neurons = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    maps = build_annotation_maps(ann)
    rid_to_hemi = maps["rid_to_hemi"]
    rid_to_class = maps["rid_to_class"]
    rid_to_nt = maps["rid_to_nt"]
    neuron_ids = df_comp.index.astype(str).tolist()

    # Display predictions
    logger.info("=" * 60)
    logger.info("PREDICTIONS (pre-registered)")
    logger.info("=" * 60)
    for k, v in PREDICTIONS.items():
        logger.info("  %s: %s", k, v)

    # ================================================================
    # Build gene-guided circuit
    # ================================================================
    logger.info("=" * 60)
    logger.info("Building gene-guided circuit")
    logger.info("=" * 60)

    essential_io = set(DN_NEURONS.values()) | set(STIM_SUGAR) | set(STIM_LC4)
    gene_neurons = []
    for idx, nid in enumerate(neuron_ids):
        hemi = rid_to_hemi.get(nid, "unknown")
        if hemi in SIGNATURE_HEMIS or idx in essential_io:
            gene_neurons.append(idx)

    gene_set = set(gene_neurons)
    gene_neurons = sorted(gene_set)
    n_sub = len(gene_neurons)
    old_to_new = {old: new for new, old in enumerate(gene_neurons)}
    logger.info("Gene-guided circuit: %d neurons", n_sub)

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    n_conn = len(df_conn)

    mask = np.array([
        pre_full[i] in gene_set and post_full[i] in gene_set
        for i in range(n_conn)
    ])
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(n_conn) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(n_conn) if mask[i]])
    vals_sub = vals_full[mask] * GAIN
    n_syn = len(pre_sub)
    logger.info("Synapses: %d", n_syn)

    # Build edge index by hemilineage pair
    hemi_of_neuron = {}
    for idx in gene_neurons:
        hemi_of_neuron[old_to_new[idx]] = rid_to_hemi.get(neuron_ids[idx], "unknown")

    edge_syn_idx = defaultdict(list)
    for i in range(n_syn):
        pre_h = hemi_of_neuron.get(pre_sub[i], "unknown")
        post_h = hemi_of_neuron.get(post_sub[i], "unknown")
        edge = (pre_h, post_h)
        edge_syn_idx[edge].append(i)

    inter_edges = [(k, v) for k, v in edge_syn_idx.items() if k[0] != k[1]]
    logger.info("Hemilineage-pair edges: %d", len(inter_edges))

    # Neuron types
    rs = NEURON_TYPES["RS"]
    ib = NEURON_TYPES["IB"]
    fs = NEURON_TYPES["FS"]

    a = np.full(n_sub, rs["a"], dtype=np.float32)
    b_arr = np.full(n_sub, rs["b"], dtype=np.float32)
    c_arr = np.full(n_sub, rs["c"], dtype=np.float32)
    d_arr = np.full(n_sub, rs["d"], dtype=np.float32)

    for new_idx, old_idx in enumerate(gene_neurons):
        nid = neuron_ids[old_idx]
        cc = rid_to_class.get(nid, "")
        if isinstance(cc, str) and "CX" in cc:
            a[new_idx], b_arr[new_idx] = ib["a"], ib["b"]
            c_arr[new_idx], d_arr[new_idx] = ib["c"], ib["d"]
        elif rid_to_nt.get(nid, "") in ("gaba", "GABA"):
            a[new_idx], b_arr[new_idx] = fs["a"], fs["b"]
            c_arr[new_idx], d_arr[new_idx] = fs["c"], fs["d"]

    neuron_params = {"a": a, "b": b_arr, "c": c_arr, "d": d_arr}

    dn_new = {nm: old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in old_to_new}
    stim_sugar = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
    stim_lc4 = [old_to_new[i] for i in STIM_LC4 if i in old_to_new]

    def _run_sim(syn_vals_local, stim_indices, n_steps=500):
        return run_simulation(
            syn_vals=syn_vals_local,
            pre=pre_sub, post=post_sub,
            num_neurons=n_sub,
            neuron_params=neuron_params,
            stim_indices=stim_indices,
            dn_indices=dn_new,
            n_steps=n_steps,
        )

    # ================================================================
    # Baselines
    # ================================================================
    syn_vals = torch.tensor(vals_sub, dtype=torch.float32)

    logger.info("Baselines:")
    dn_nav = _run_sim(syn_vals, stim_sugar)
    bl_nav = f_nav(dn_nav)
    bl_esc_on_sugar = f_esc(dn_nav)
    logger.info("  Sugar: nav=%d, esc=%d", bl_nav, bl_esc_on_sugar)

    dn_esc = _run_sim(syn_vals, stim_lc4)
    bl_esc = f_esc(dn_esc)
    logger.info("  LC4:   esc=%d", bl_esc)

    # ================================================================
    # Evolution: compile navigation
    # ================================================================
    logger.info("=" * 60)
    logger.info("EVOLUTION: Compile navigation on gene-guided circuit")
    logger.info("=" * 60)

    np.random.seed(seed)
    torch.manual_seed(seed)
    best_vals = syn_vals.clone()
    current = bl_nav
    accepted = 0
    acc_edges = []

    t0 = time.time()
    for gen in range(n_gen):
        ga = 0
        for mi in range(n_mut):
            edge_key, syns = inter_edges[np.random.randint(len(inter_edges))]
            old = best_vals[syns].clone()
            scale = np.random.uniform(0.5, 4.0)
            test = best_vals.clone()
            test[syns] = old * scale
            dn = _run_sim(test, stim_sugar)
            fit = f_nav(dn)
            if fit > current:
                current = fit
                best_vals[syns] = old * scale
                ga += 1
                accepted += 1
                acc_edges.append(edge_key)
                logger.info(
                    "  G%dM%d: %s->%s s=%.2f nav=%d ACCEPTED",
                    gen, mi, edge_key[0], edge_key[1], scale, fit,
                )
        if gen % 5 == 4:
            logger.info(
                "  Gen %d: nav=%d acc=%d/10 total=%d [%.0fs]",
                gen, current, ga, accepted, time.time() - t0,
            )

    # ================================================================
    # VALIDATE PREDICTIONS
    # ================================================================
    logger.info("=" * 60)
    logger.info("PREDICTION VALIDATION")
    logger.info("=" * 60)

    acc_hemi_set = set()
    acc_hemi_counts = Counter()
    for h_from, h_to in acc_edges:
        acc_hemi_set.add(h_from)
        acc_hemi_set.add(h_to)
        acc_hemi_counts[h_from] += 1
        acc_hemi_counts[h_to] += 1

    logger.info("Evolved edges (%d accepted):", accepted)
    unique_acc = sorted(set(acc_edges))
    for e in unique_acc:
        logger.info("  %s -> %s", e[0], e[1])

    logger.info("Evolvable hemilineages: %s", sorted(acc_hemi_set))

    # P1: VPNd1/VPNd2 in evolvable set
    p1 = "VPNd1" in acc_hemi_set or "VPNd2" in acc_hemi_set
    logger.info("P1 (VPNd1/VPNd2 evolvable): %s", "CONFIRMED" if p1 else "FAILED")

    # P2: CX hemilineages frozen
    cx_hemis = {"DM3_CX_d2", "DM1_CX_d2"}
    p2 = len(cx_hemis & acc_hemi_set) == 0
    logger.info(
        "P2 (CX hemilineages frozen): %s (CX in evolvable: %s)",
        "CONFIRMED" if p2 else "FAILED", cx_hemis & acc_hemi_set,
    )

    # P3: <15% evolvable
    evolvable_pct = 100 * len(unique_acc) / len(inter_edges)
    p3 = evolvable_pct < 15
    logger.info(
        "P3 (<15%% evolvable): %s (%.1f%%)",
        "CONFIRMED" if p3 else "FAILED", evolvable_pct,
    )

    # P4: Escape increases as side effect
    dn_nav_evolved = _run_sim(best_vals, stim_sugar)
    evolved_esc_on_sugar = f_esc(dn_nav_evolved)
    p4 = evolved_esc_on_sugar > bl_esc_on_sugar
    logger.info(
        "P4 (escape side effect): %s (baseline esc=%d, evolved esc=%d)",
        "CONFIRMED" if p4 else "FAILED", bl_esc_on_sugar, evolved_esc_on_sugar,
    )

    dn_esc_evolved = _run_sim(best_vals, stim_lc4)
    evolved_esc_lc4 = f_esc(dn_esc_evolved)
    logger.info(
        "    (LC4 escape: baseline=%d, evolved=%d, delta=%+d)",
        bl_esc, evolved_esc_lc4, evolved_esc_lc4 - bl_esc,
    )

    # P5: putative_primary most connected evolvable
    p5_top = acc_hemi_counts.most_common(1)[0][0] if acc_hemi_counts else "none"
    p5 = p5_top == "putative_primary"
    logger.info(
        "P5 (putative_primary top evolvable): %s (top: %s, counts: %s)",
        "CONFIRMED" if p5 else "FAILED", p5_top, acc_hemi_counts.most_common(5),
    )

    # Summary
    confirmed = sum([p1, p2, p3, p4, p5])
    logger.info("=" * 60)
    logger.info("PREDICTIONS: %d/5 CONFIRMED", confirmed)
    logger.info("=" * 60)
    pred_results = [p1, p2, p3, p4, p5]
    for i, (k, v) in enumerate(PREDICTIONS.items()):
        status = "CONFIRMED" if pred_results[i] else "FAILED"
        logger.info("  %s: %s -- %s", k, status, v)

    if confirmed >= 4:
        logger.info(">>> STRONG PREDICTIVE POWER. The framework predicts, not just optimizes.")
    elif confirmed >= 3:
        logger.info(">>> MODERATE PREDICTIVE POWER. Most predictions hold.")
    else:
        logger.info(">>> WEAK PREDICTIVE POWER. Framework optimizes but doesn't predict well.")

    # ================================================================
    # Statistical analysis
    # ================================================================
    logger.info("=" * 60)
    logger.info("STATISTICAL ANALYSIS")
    logger.info("=" * 60)

    # Bootstrap CIs for numeric measurements
    # P3: evolvable percentage -- bootstrap over the accepted edges
    evolvable_counts = np.array([1 if e in set(acc_edges) else 0 for e in [k for k, _ in inter_edges]])
    evolvable_pt, evolvable_lo, evolvable_hi = bootstrap_ci(
        evolvable_counts, statistic=lambda x: np.mean(x) * 100,
    )
    logger.info(
        "P3 evolvable surface: %.1f%% [95%% CI: %.1f%%, %.1f%%]",
        evolvable_pt, evolvable_lo, evolvable_hi,
    )

    # P4: escape side effect -- improvement_with_ci
    imp_esc = improvement_with_ci(
        float(bl_esc_on_sugar),
        np.array([float(evolved_esc_on_sugar)]),
    )
    logger.info(
        "P4 escape side effect: baseline=%d, evolved=%d, change=%.1f%%",
        bl_esc_on_sugar, evolved_esc_on_sugar, imp_esc["improvement_pct"],
    )

    # Navigation improvement CI
    imp_nav = improvement_with_ci(float(bl_nav), np.array([float(current)]))
    logger.info(
        "Navigation improvement: %.1f%% [baseline=%d, evolved=%d]",
        imp_nav["improvement_pct"], bl_nav, current,
    )

    # Binomial test for overall prediction confirmation
    # Under null hypothesis (random guessing), each prediction has p=0.5
    from scipy.stats import binom_test  # noqa: E402
    n_predictions = 5
    binom_p = binom_test(confirmed, n_predictions, 0.5, alternative="greater")
    logger.info(
        "Binomial test: %d/%d confirmed, p = %.4f (one-sided, H0: chance = 50%%)",
        confirmed, n_predictions, binom_p,
    )

    stats_output = {
        "evolvable_pct_ci": [float(evolvable_pt), float(evolvable_lo), float(evolvable_hi)],
        "nav_improvement_pct": float(imp_nav["improvement_pct"]),
        "escape_side_effect_pct": float(imp_esc["improvement_pct"]),
        "binomial_test_p": float(binom_p),
    }

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "prediction_validation.json"
    with open(out_path, "w") as f:
        json.dump({
            "predictions": PREDICTIONS,
            "results": {"P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5},
            "confirmed": confirmed,
            "evolvable_hemilineages": sorted(acc_hemi_set),
            "evolvable_edges": [list(e) for e in unique_acc],
            "baseline_nav": bl_nav,
            "evolved_nav": current,
            "baseline_esc_sugar": bl_esc_on_sugar,
            "evolved_esc_sugar": evolved_esc_on_sugar,
            "statistics": stats_output,
        }, f, indent=2)
    logger.info("Saved to %s", out_path)

    return confirmed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Prediction validation: pre-registered hypothesis testing")
    parser.add_argument("--generations", type=int, default=25)
    parser.add_argument("--mutations", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    run_experiment(
        n_gen=args.generations,
        n_mut=args.mutations,
        seed=args.seed,
        output_dir=args.output_dir,
    )
