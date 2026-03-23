#!/usr/bin/env python3
"""
End-to-end behavioral test of the growth program.

Generate a synthetic circuit from scratch using ONLY implementable
developmental rules (distance + NT compatibility + flow).  No FlyWire
connectivity used in construction.  Then test: does it produce behavior?
Does evolution improve it faster than random?

Three outcomes:
  1. Grown circuit produces behavior at baseline -> growth program works alone
  2. Grown circuit + evolution > random + evolution -> useful scaffold
  3. Grown circuit = random -> implementable rules insufficient
"""

import json
import logging
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS,
    DN_NAMES,
    DT,
    GAIN,
    POISSON_RATE,
    POISSON_WEIGHT,
    SIGNATURE_HEMIS,
    STIM_LC4,
    STIM_JO,
    STIM_SUGAR,
    W_SCALE,
)
from compile.data import (
    build_annotation_maps,
    load_annotations,
    load_connectome,
)
from compile.fitness import f_arousal, f_circles, f_esc, f_nav, f_rhythm, f_turn
from compile.simulate import assign_neuron_types, run_simulation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

STIM = {"sugar": STIM_SUGAR, "lc4": STIM_LC4, "jo": STIM_JO}
BEHAVIORS = {
    "navigation": ("sugar", f_nav),
    "escape": ("lc4", f_esc),
    "turning": ("jo", f_turn),
    "arousal": ("sugar", f_arousal),
    "circles": ("sugar", f_circles),
    "rhythm": ("sugar", f_rhythm),
}

# Flow compatibility (implementable growth rule)
FLOW_COMPAT = {
    ("intrinsic", "intrinsic"): 1.0,
    ("sensory", "intrinsic"): 0.8,
    ("intrinsic", "descending"): 0.7,
    ("sensory", "descending"): 0.3,
    ("ascending", "intrinsic"): 0.6,
}

# Simple NT compatibility for growth
NT_COMPAT_GROWTH = {
    ("acetylcholine", "acetylcholine"): 1.0,
    ("acetylcholine", "gaba"): 0.5,
    ("gaba", "acetylcholine"): 0.8,
    ("gaba", "gaba"): 0.3,
    ("glutamate", "acetylcholine"): 0.7,
    ("glutamate", "gaba"): 0.4,
    ("dopamine", "acetylcholine"): 0.6,
    ("serotonin", "acetylcholine"): 0.5,
}


def growth_connection_prob(i, j, positions, nt_types, flow_types):
    """Probability of connection from neuron i to j using ONLY implementable rules."""
    dist = np.linalg.norm(positions[i] - positions[j])
    dist_score = np.exp(-dist / 15000) if dist > 0 else 1.0
    nt_score = NT_COMPAT_GROWTH.get((nt_types[i], nt_types[j]), 0.1)
    flow_score = FLOW_COMPAT.get((flow_types[i], flow_types[j]), 0.2)
    return 0.25 * dist_score + 0.25 * nt_score + 1.0 * flow_score


def generate_circuit(n_neurons, connection_density, positions, nt_types, flow_types,
                     use_growth_rules=True, seed=42):
    """Generate a synthetic circuit using growth rules or random."""
    rng = np.random.RandomState(seed)
    n_target = int(n_neurons * n_neurons * connection_density)

    pre_list, post_list, val_list = [], [], []
    if use_growth_rules:
        logger.info("  Computing growth probabilities for %d neurons...", n_neurons)
        n_candidates = min(n_target * 20, n_neurons * 1000)
        candidates_i = rng.randint(0, n_neurons, n_candidates)
        candidates_j = rng.randint(0, n_neurons, n_candidates)
        scores = np.zeros(n_candidates)
        for k in range(n_candidates):
            if candidates_i[k] != candidates_j[k]:
                scores[k] = growth_connection_prob(
                    candidates_i[k], candidates_j[k], positions, nt_types, flow_types,
                )
        top_idx = np.argsort(scores)[-n_target:]
        for k in top_idx:
            if scores[k] > 0:
                pre_list.append(candidates_i[k])
                post_list.append(candidates_j[k])
                val_list.append(float(scores[k]))
    else:
        logger.info("  Generating %d random connections...", n_target)
        for _ in range(n_target):
            i = rng.randint(0, n_neurons)
            j = rng.randint(0, n_neurons)
            if i != j:
                pre_list.append(i)
                post_list.append(j)
                val_list.append(rng.uniform(0.1, 2.0))

    seen = set()
    pre_f, post_f, val_f = [], [], []
    for p, q, v in zip(pre_list, post_list, val_list):
        if (p, q) not in seen:
            seen.add((p, q))
            pre_f.append(p)
            post_f.append(q)
            val_f.append(v)
    return np.array(pre_f), np.array(post_f), np.array(val_f)


def run_sim(pre_arr, post_arr, val_arr, stim_indices, n_sub, neuron_params, dn_new, n_steps=500):
    """Run Izhikevich simulation on given circuit."""
    syn_vals = torch.tensor(val_arr * GAIN, dtype=torch.float32)
    return run_simulation(
        syn_vals, pre_arr, post_arr, n_sub, neuron_params,
        stim_indices, dn_new, n_steps=n_steps,
    )


def evolve_circuit(pre, post, vals, stim_idx, fit_fn, n_sub, neuron_params, dn_new,
                   n_gen=15, n_mut=10, seed=42):
    """Run evolution on a circuit. Returns fitness trajectory."""
    rng = np.random.RandomState(seed)
    best_vals = vals.copy()
    dn = run_sim(pre, post, best_vals, stim_idx, n_sub, neuron_params, dn_new)
    current = fit_fn(dn)
    trajectory = [current]
    accepted = 0

    for gen in range(n_gen):
        for mi in range(n_mut):
            n_mutate = max(1, len(vals) // 100)
            mut_idx = rng.choice(len(vals), n_mutate, replace=False)
            old = best_vals[mut_idx].copy()
            scale = rng.uniform(0.5, 4.0)
            test_vals = best_vals.copy()
            test_vals[mut_idx] = old * scale
            dn = run_sim(pre, post, test_vals, stim_idx, n_sub, neuron_params, dn_new)
            fit = fit_fn(dn)
            if fit > current:
                current = fit
                best_vals[mut_idx] = old * scale
                accepted += 1
        trajectory.append(current)

    return trajectory, accepted


def main():
    logger.info("=" * 60)
    logger.info("GROWTH PROGRAM BEHAVIORAL TEST")
    logger.info("=" * 60)

    df_comp = load_connectome()[1]  # only need df_comp here initially
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()
    num_neurons_full = len(df_comp)
    maps = build_annotation_maps(ann)

    rid_to_flow = dict(zip(ann["root_id"].astype(str), ann["flow"].fillna("unknown")))
    rid_to_sx = dict(zip(ann["root_id"].astype(str), ann["soma_x"]))
    rid_to_sy = dict(zip(ann["root_id"].astype(str), ann["soma_y"]))
    rid_to_sz = dict(zip(ann["root_id"].astype(str), ann["soma_z"]))

    # Select gene-guided neurons
    essential_io = set(DN_NEURONS.values())
    for s in STIM.values():
        essential_io.update(s)

    gene_neurons = []
    for idx, nid in enumerate(neuron_ids):
        if maps["rid_to_hemi"].get(nid, "unknown") in SIGNATURE_HEMIS or idx in essential_io:
            gene_neurons.append(idx)
    gene_neurons = sorted(set(gene_neurons))
    n_sub = len(gene_neurons)
    old_to_new = {old: new for new, old in enumerate(gene_neurons)}
    logger.info("Gene-guided neurons: %d", n_sub)

    # Get positions and features
    positions = np.zeros((n_sub, 3))
    nt_types = []
    flow_types = []
    for i, idx in enumerate(gene_neurons):
        nid = neuron_ids[idx]
        try:
            sx = float(rid_to_sx.get(nid, 0) or 0)
            sy = float(rid_to_sy.get(nid, 0) or 0)
            sz = float(rid_to_sz.get(nid, 0) or 0)
            positions[i] = [sx, sy, sz]
        except (ValueError, TypeError):
            pass
        nt_types.append(str(maps["rid_to_nt"].get(nid, "unknown")))
        flow_types.append(str(rid_to_flow.get(nid, "unknown")))

    # Neuron types
    neuron_params = assign_neuron_types(
        n_sub,
        [neuron_ids[gene_neurons[i]] for i in range(n_sub)],
        maps["rid_to_nt"],
        maps["rid_to_class"],
    )

    dn_new = {nm: old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in old_to_new}
    stim_new = {name: [old_to_new[i] for i in idxs if i in old_to_new] for name, idxs in STIM.items()}

    # Load real FlyWire circuit for comparison
    df_conn = load_connectome()[0]
    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    gene_set = set(gene_neurons)
    mask = np.array([pre_full[i] in gene_set and post_full[i] in gene_set for i in range(len(df_conn))])
    real_pre = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
    real_post = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
    real_vals = vals_full[mask]
    real_density = len(real_pre) / (n_sub * n_sub)
    logger.info("Real circuit: %d synapses (density=%.6f)", len(real_pre), real_density)

    # Generate circuits
    logger.info("Generating circuits...")
    t0 = time.time()
    grown_pre, grown_post, grown_vals = generate_circuit(
        n_sub, real_density, positions, nt_types, flow_types, use_growth_rules=True, seed=42,
    )
    logger.info("Grown circuit: %d synapses (%.1fs)", len(grown_pre), time.time() - t0)

    t0 = time.time()
    rand_pre, rand_post, rand_vals = generate_circuit(
        n_sub, real_density, positions, nt_types, flow_types, use_growth_rules=False, seed=42,
    )
    logger.info("Random circuit: %d synapses (%.1fs)", len(rand_pre), time.time() - t0)

    # Phase 1: Baseline behavioral test
    logger.info("PHASE 1: Baseline behavior (no evolution)")
    circuits = {
        "real": (real_pre, real_post, real_vals),
        "grown": (grown_pre, grown_post, grown_vals),
        "random": (rand_pre, rand_post, rand_vals),
    }

    baselines = {}
    for cname, (pre, post, vals) in circuits.items():
        baselines[cname] = {}
        for bname, (stim_name, fit_fn) in BEHAVIORS.items():
            stim_idx = stim_new.get(stim_name, [])
            dn = run_sim(pre, post, vals, stim_idx, n_sub, neuron_params, dn_new)
            score = fit_fn(dn)
            baselines[cname][bname] = score
        logger.info(
            "  %s: nav=%.0f esc=%.0f turn=%.0f arousal=%.0f circles=%.0f rhythm=%.1f",
            cname, baselines[cname]["navigation"], baselines[cname]["escape"],
            baselines[cname]["turning"], baselines[cname]["arousal"],
            baselines[cname]["circles"], baselines[cname]["rhythm"],
        )

    # Phase 2: Evolution comparison
    logger.info("PHASE 2: Evolution (navigation fitness, 15 gen x 10 mut)")
    for cname in ["grown", "random", "real"]:
        pre, post, vals = circuits[cname]
        stim_idx = stim_new.get("sugar", [])
        t0 = time.time()
        traj, acc = evolve_circuit(
            pre, post, vals, stim_idx, f_nav, n_sub, neuron_params, dn_new,
        )
        elapsed = time.time() - t0
        logger.info(
            "  %s: %.0f -> %.0f (%d accepted, %.0fs)",
            cname, traj[0], traj[-1], acc, elapsed,
        )

    # Summary
    grown_active = sum(1 for b in baselines["grown"].values() if b > 0)
    random_active = sum(1 for b in baselines["random"].values() if b > 0)
    real_active = sum(1 for b in baselines["real"].values() if b > 0)

    logger.info("Active behaviors: real=%d/6, grown=%d/6, random=%d/6",
                real_active, grown_active, random_active)

    if grown_active > random_active:
        logger.info(">>> GROWTH PROGRAM PRODUCES MORE BEHAVIOR THAN RANDOM")
    elif grown_active == random_active and any(
        baselines["grown"][b] > baselines["random"][b] * 1.1 for b in BEHAVIORS
    ):
        logger.info(">>> GROWTH PROGRAM PRODUCES STRONGER BEHAVIOR THAN RANDOM")
    else:
        logger.info(">>> GROWTH PROGRAM NOT BETTER THAN RANDOM AT BASELINE")

    # Save
    outdir = Path("results/growth_behavioral_test")
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "growth_behavioral_test.json", "w") as f:
        json.dump({
            "baselines": baselines,
            "grown_active": grown_active, "random_active": random_active, "real_active": real_active,
            "n_neurons": n_sub,
            "grown_synapses": len(grown_pre), "random_synapses": len(rand_pre),
            "real_synapses": len(real_pre),
        }, f, indent=2)
    logger.info("Saved to %s", outdir / "growth_behavioral_test.json")
    logger.info("DONE.")


if __name__ == "__main__":
    main()
