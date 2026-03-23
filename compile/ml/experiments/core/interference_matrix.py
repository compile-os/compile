#!/usr/bin/env python3
"""
Interference matrix: the processor's spec sheet.

5 compiled brains x 5 fitness functions = 25 evaluations.  Each cell answers:
compiling behavior X changed behavior Y by how much?

  Diagonal = direct improvement (expected).
  Off-diagonal positive = synergy (compiling X helps Y).
  Off-diagonal negative = interference (compiling X breaks Y).

Runs on the gene-guided subcircuit (hemilineage-selected neurons + I/O).
Evolution is hemilineage-pair level (not module-level).

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS, DN_NAMES, STIM_SUGAR, STIM_LC4, STIM_JO,
    SIGNATURE_HEMIS, NEURON_TYPES, GAIN,
    DT, W_SCALE, POISSON_WEIGHT, POISSON_RATE,
)
from compile.data import load_connectome, load_annotations, build_annotation_maps
from compile.fitness import f_nav, f_esc, f_turn, f_arousal, f_circles
from compile.simulate import run_simulation
from compile.stats import bootstrap_ci, improvement_with_ci

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Behavior registry
# ---------------------------------------------------------------------------

BEHAVIORS = {
    "navigation": ("sugar", f_nav),
    "escape":     ("lc4",   f_esc),
    "turning":    ("jo",    f_turn),
    "arousal":    ("sugar", f_arousal),
    "circles":    ("sugar", f_circles),
}

STIM = {
    "sugar": STIM_SUGAR,
    "lc4": STIM_LC4,
    "jo": STIM_JO,
}


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(
    n_gen: int = 15,
    n_mut: int = 10,
    seed: int = 42,
    n_seeds: int = 3,
    output_dir: str = "results",
):
    """Run the full interference matrix experiment."""
    logger.info("=" * 60)
    logger.info("INTERFERENCE MATRIX")
    logger.info("The processor's spec sheet")
    logger.info("=" * 60)

    # Load data
    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    maps = build_annotation_maps(ann)
    rid_to_hemi = maps["rid_to_hemi"]
    rid_to_class = maps["rid_to_class"]
    rid_to_nt = maps["rid_to_nt"]
    neuron_ids = df_comp.index.astype(str).tolist()

    # Build gene-guided circuit
    essential_io = set(DN_NEURONS.values())
    for s in STIM.values():
        essential_io.update(s)

    gene_neurons = []
    for idx, nid in enumerate(neuron_ids):
        if rid_to_hemi.get(nid, "unknown") in SIGNATURE_HEMIS or idx in essential_io:
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

    # Build hemilineage-pair edge index for evolution
    hemi_of = {}
    for idx in gene_neurons:
        hemi_of[old_to_new[idx]] = rid_to_hemi.get(neuron_ids[idx], "unknown")

    edge_syn_idx = defaultdict(list)
    for i in range(n_syn):
        edge = (hemi_of.get(pre_sub[i], "?"), hemi_of.get(post_sub[i], "?"))
        edge_syn_idx[edge].append(i)
    inter_edges = [(k, v) for k, v in edge_syn_idx.items() if k[0] != k[1]]

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
    stim_new = {
        name: [old_to_new[i] for i in idxs if i in old_to_new]
        for name, idxs in STIM.items()
    }

    def _run_sim(syn_vals_local, stim_indices, n_steps=500):
        """Run simulation on subcircuit."""
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
    # Phase 1: Compile each behavior independently
    # ================================================================
    logger.info("=" * 60)
    logger.info("PHASE 1: Compile each behavior (%d gen x %d mut)", n_gen, n_mut)
    logger.info("=" * 60)

    syn_base = torch.tensor(vals_sub, dtype=torch.float32)
    compiled_weights = {}  # bname -> list of (weights, fitness) per seed
    seeds = list(range(seed, seed + n_seeds))

    for bname, (stim_name, fit_fn) in BEHAVIORS.items():
        seed_results = []
        for s in seeds:
            np.random.seed(s)
            torch.manual_seed(s)
            best = syn_base.clone()
            stim_idx = stim_new.get(stim_name, [])
            dn = _run_sim(best, stim_idx)
            current = fit_fn(dn)

            for gen in range(n_gen):
                for mi in range(n_mut):
                    edge_key, syns = inter_edges[np.random.randint(len(inter_edges))]
                    old = best[syns].clone()
                    scale = np.random.uniform(0.5, 4.0)
                    test = best.clone()
                    test[syns] = old * scale
                    dn = _run_sim(test, stim_idx)
                    fit = fit_fn(dn)
                    if fit > current:
                        current = fit
                        best[syns] = old * scale

            seed_results.append((best, current))
            logger.info("  %12s seed %d: compiled fitness = %.0f", bname, s, current)

        fitnesses = np.array([f for _, f in seed_results])
        pt, lo, hi = bootstrap_ci(fitnesses)
        logger.info(
            "  %12s: mean fitness = %.0f [95%% CI: %.0f, %.0f] (%d seeds)",
            bname, pt, lo, hi, n_seeds,
        )
        compiled_weights[bname] = seed_results

    # ================================================================
    # Phase 2: Cross-evaluate -- the interference matrix
    # ================================================================
    logger.info("=" * 60)
    logger.info("PHASE 2: Interference Matrix (5x5)")
    logger.info("=" * 60)

    # Baselines
    baselines = {}
    for bname, (stim_name, fit_fn) in BEHAVIORS.items():
        stim_idx = stim_new.get(stim_name, [])
        dn = _run_sim(syn_base, stim_idx)
        baselines[bname] = fit_fn(dn)

    # Build matrix with bootstrap CIs across seeds
    matrix = {}
    bnames = list(BEHAVIORS.keys())

    header = f"{'Compiled ->':>14}"
    for b in bnames:
        header += f" {b[:6]:>12}"
    header += f" {'baseline':>8}"
    logger.info(header)

    for compiled_for in bnames:
        seed_weights_list = compiled_weights[compiled_for]
        line = f"{'Test v ' + compiled_for[:6]:>14}"
        for tested_on in bnames:
            stim_name, fit_fn = BEHAVIORS[tested_on]
            stim_idx = stim_new.get(stim_name, [])
            bl = baselines[tested_on]

            # Evaluate each seed's compiled weights on this behavior
            seed_scores = []
            for weights, _ in seed_weights_list:
                dn = _run_sim(weights, stim_idx)
                score = fit_fn(dn)
                seed_scores.append(score)

            seed_scores = np.array(seed_scores)
            seed_deltas = (seed_scores - bl) / max(abs(bl), 1) * 100
            mean_score = float(np.mean(seed_scores))
            mean_delta = float(np.mean(seed_deltas))
            pt, lo, hi = bootstrap_ci(seed_deltas)

            matrix[(compiled_for, tested_on)] = {
                "score_mean": mean_score,
                "score_seeds": seed_scores.tolist(),
                "baseline": bl,
                "delta_pct": mean_delta,
                "delta_pct_ci": [float(pt), float(lo), float(hi)],
            }
            line += f" {mean_delta:>+5.0f}%({lo:>+.0f},{hi:>+.0f})"
        line += f" {baselines[compiled_for]:>8.0f}"
        logger.info(line)

    # ================================================================
    # Analysis
    # ================================================================
    logger.info("=" * 60)
    logger.info("ANALYSIS")
    logger.info("=" * 60)

    logger.info("Direct improvements (diagonal):")
    for b in bnames:
        cell = matrix[(b, b)]
        d = cell["delta_pct"]
        ci = cell["delta_pct_ci"]
        logger.info("  %12s: %+.0f%% [95%% CI: %+.0f%%, %+.0f%%]", b, d, ci[1], ci[2])

    logger.info("Synergies (off-diagonal > +10%%):")
    for cf in bnames:
        for to in bnames:
            if cf != to:
                cell = matrix[(cf, to)]
                d = cell["delta_pct"]
                ci = cell["delta_pct_ci"]
                if d > 10:
                    logger.info("  Compiling %s -> %s: %+.0f%% [CI: %+.0f%%, %+.0f%%]", cf, to, d, ci[1], ci[2])

    logger.info("Interference (off-diagonal < -10%%):")
    for cf in bnames:
        for to in bnames:
            if cf != to:
                cell = matrix[(cf, to)]
                d = cell["delta_pct"]
                ci = cell["delta_pct_ci"]
                if d < -10:
                    logger.info("  Compiling %s -> %s: %+.0f%% [CI: %+.0f%%, %+.0f%%]", cf, to, d, ci[1], ci[2])

    logger.info("Compatibility matrix (can be co-compiled):")
    for i, b1 in enumerate(bnames):
        for j, b2 in enumerate(bnames):
            if i < j:
                d12 = matrix[(b1, b2)]["delta_pct"]
                d21 = matrix[(b2, b1)]["delta_pct"]
                ci12 = matrix[(b1, b2)]["delta_pct_ci"]
                ci21 = matrix[(b2, b1)]["delta_pct_ci"]
                # Conservative: use CI upper bound to check if interference is reliable
                compatible = ci12[1] > -10 and ci21[1] > -10
                status = "COMPATIBLE" if compatible else "CONFLICT"
                logger.info(
                    "  %12s + %-12s: %s (cross-effects: %+.0f%% [%+.0f,%+.0f], %+.0f%% [%+.0f,%+.0f])",
                    b1, b2, status, d12, ci12[1], ci12[2], d21, ci21[1], ci21[2],
                )

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "baselines": baselines,
        "matrix": {f"{cf}->{to}": v for (cf, to), v in matrix.items()},
        "behaviors": bnames,
        "n_seeds": n_seeds,
    }
    out_path = outdir / "interference_matrix.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Saved to %s", out_path)

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Interference matrix: behavior cross-evaluation")
    parser.add_argument("--generations", type=int, default=15, help="Evolution generations per behavior")
    parser.add_argument("--mutations", type=int, default=10, help="Mutations per generation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-seeds", type=int, default=3, help="Number of seeds per behavior for bootstrap CIs")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    run_experiment(
        n_gen=args.generations,
        n_mut=args.mutations,
        seed=args.seed,
        n_seeds=args.n_seeds,
        output_dir=args.output_dir,
    )
