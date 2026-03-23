#!/usr/bin/env python3
"""
Izhikevich conflict resolution experiment.

Evolves specifically for conflict resolution during stimulus switching:
fitness = escape_activation(500-550) - nav_activation(500-550).

Goal: find edges that suppress navigation quickly or activate escape fast
after the stimulus switch from sugar to LC4.
"""

import json
import logging
import time
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
    STIM_LC4_EXTENDED,
    STIM_SUGAR,
    W_SCALE,
)
from compile.data import (
    build_annotation_maps,
    build_edge_synapse_index,
    load_annotations,
    load_connectome,
    load_module_labels,
)
from compile.simulate import assign_neuron_types, build_weight_matrix, izh_step

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

STIM = {"sugar": STIM_SUGAR, "lc4": STIM_LC4_EXTENDED}
PHASE1_STEPS = 500
CONFLICT_START = PHASE1_STEPS
CONFLICT_END = PHASE1_STEPS + 50
EVAL_STEPS = CONFLICT_END


def run_conflict_only(syn_vals_override, *, pre, post, num_neurons, neuron_params, dn_names, dn_idx):
    """Run simulation through end of conflict window (550 steps)."""
    a_t = torch.tensor(neuron_params["a"])
    b_t = torch.tensor(neuron_params["b"])
    c_t = torch.tensor(neuron_params["c"])
    d_t = torch.tensor(neuron_params["d"])

    W = build_weight_matrix(pre, post, syn_vals_override, num_neurons)

    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)
    rates = torch.zeros(1, num_neurons)

    for idx in STIM["sugar"]:
        if 0 <= idx < num_neurons:
            rates[0, idx] = POISSON_RATE

    dn_timeseries = []
    for step in range(EVAL_STEPS):
        if step == PHASE1_STEPS:
            rates.zero_()
            for idx in STIM["lc4"]:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE
        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)

        spk = spikes.squeeze(0)
        dn_timeseries.append([int(spk[dn_idx[j]].item()) for j in range(len(dn_names))])

    return np.array(dn_timeseries)


def fitness_conflict_resolution(dn_ts, nav_dn_idx, esc_dn_idx):
    """Primary fitness: escape - nav during conflict window, penalize nav collapse."""
    conflict_esc = float(dn_ts[CONFLICT_START:CONFLICT_END, esc_dn_idx].sum())
    conflict_nav = float(dn_ts[CONFLICT_START:CONFLICT_END, nav_dn_idx].sum())
    phase1_nav = float(dn_ts[0:PHASE1_STEPS, nav_dn_idx].sum())
    resolution = conflict_esc - conflict_nav
    nav_penalty = max(0, 500.0 - phase1_nav) * 0.1
    return {
        "fitness": resolution - nav_penalty,
        "resolution": resolution,
        "conflict_esc": conflict_esc,
        "conflict_nav": conflict_nav,
        "phase1_nav": phase1_nav,
    }


def main():
    logger.info("=" * 60)
    logger.info("IZHIKEVICH CONFLICT RESOLUTION")
    logger.info("=" * 60)

    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    labels = load_module_labels()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    neuron_params = assign_neuron_types(num_neurons, neuron_ids, maps["rid_to_nt"], maps["rid_to_class"])

    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    _syn_vals = torch.tensor(vals * GAIN, dtype=torch.float32)

    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = list(inter_module_edges)

    dn_names = DN_NAMES
    dn_idx_list = [DN_NEURONS[n] for n in dn_names]
    nav_dn_idx = [i for i, n in enumerate(dn_names) if "P9" in n or "MN9" in n]
    esc_dn_idx = [i for i, n in enumerate(dn_names) if "GF" in n or "MDN" in n]

    sim_kwargs = dict(pre=pre, post=post, num_neurons=num_neurons,
                      neuron_params=neuron_params, dn_names=dn_names, dn_idx=dn_idx_list)

    # Baseline
    t0 = time.time()
    dn_ts_bl = run_conflict_only(_syn_vals, **sim_kwargs)
    bl = fitness_conflict_resolution(dn_ts_bl, nav_dn_idx, esc_dn_idx)
    logger.info("Baseline: resolution=%.1f fitness=%.1f (%.1fs)", bl["resolution"], bl["fitness"], time.time() - t0)

    # Evolution
    N_GEN, N_MUT = 30, 12
    np.random.seed(123)
    torch.manual_seed(123)
    current_fitness = bl["fitness"]
    best_syn_vals = _syn_vals.clone()
    all_mutations = []
    accepted = 0
    t_start = time.time()

    for gen in range(N_GEN):
        ga = 0
        for mi in range(N_MUT):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syns = edge_syn_idx[edge]
            old = best_syn_vals[syns].clone()
            scale = np.random.choice([np.random.uniform(0.1, 0.9), np.random.uniform(1.1, 5.0)])
            test_vals = best_syn_vals.clone()
            test_vals[syns] = old * scale

            dn_ts = run_conflict_only(test_vals, **sim_kwargs)
            result = fitness_conflict_resolution(dn_ts, nav_dn_idx, esc_dn_idx)
            acc = result["fitness"] > current_fitness

            all_mutations.append({
                "gen": gen, "mi": mi, "edge": [int(edge[0]), int(edge[1])],
                "scale": float(scale), "fitness": float(result["fitness"]),
                "delta": float(result["fitness"] - current_fitness), "accepted": acc,
            })

            if acc:
                current_fitness = result["fitness"]
                best_syn_vals[syns] = old * scale
                ga += 1
                accepted += 1

        if gen % 5 == 4 or gen == N_GEN - 1:
            logger.info("Gen %d: fit=%.1f acc=%d/%d total=%d", gen, current_fitness, ga, N_MUT, accepted)

    dn_ts_final = run_conflict_only(best_syn_vals, **sim_kwargs)
    final = fitness_conflict_resolution(dn_ts_final, nav_dn_idx, esc_dn_idx)
    logger.info("Final: resolution=%.1f fitness=%.1f", final["resolution"], final["fitness"])

    unique_edges = sorted(set(tuple(m["edge"]) for m in all_mutations if m["accepted"]))
    logger.info("Unique evolvable edges: %d", len(unique_edges))

    outdir = Path("results/conflict_resolution")
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "izh_conflict_resolution.json", "w") as f:
        json.dump({"baseline": bl, "final": final, "accepted_edges": unique_edges,
                    "total_accepted": accepted}, f, indent=2)
    logger.info("Saved. Total time: %.0fs", time.time() - t_start)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
