#!/usr/bin/env python3
"""
Izhikevich attention experiment -- third cognitive capability.

Selective attention via spatial cue.  Split 21 sugar neurons into LEFT
(first 11) and RIGHT (last 10).  Protocol: cue left -> delay -> choice
(both sides).  Fitness = left_DN - right_DN during choice phase.

Tests whether evolution can find wiring that enables spatially-cued
attention, and whether the recruited modules overlap with those used
for working memory and conflict resolution (shared cognitive backbone).
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Stimulus split
SUGAR_LEFT = STIM_SUGAR[:11]
SUGAR_RIGHT = STIM_SUGAR[11:]

# Left/right DN pairs for attention scoring
LEFT_DN_NAMES = ["P9_left", "MN9_left"]
RIGHT_DN_NAMES = ["P9_right", "MN9_right"]

# Protocol timing
CUE_START, CUE_END = 0, 50
DELAY_END = 250
CHOICE_END = 550
TOTAL_STEPS = CHOICE_END


def run_attention(syn_vals_override, *, pre, post, num_neurons, neuron_params,
                  dn_names, dn_idx, cx_neurons, left_dn_cols, right_dn_cols):
    """Run attention simulation. Returns DN timeseries and CX timeseries."""
    a_t = torch.tensor(neuron_params["a"])
    b_t = torch.tensor(neuron_params["b"])
    c_t = torch.tensor(neuron_params["c"])
    d_t = torch.tensor(neuron_params["d"])

    W = build_weight_matrix(pre, post, syn_vals_override, num_neurons)

    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)
    rates = torch.zeros(1, num_neurons)

    dn_timeseries = []
    cx_timeseries = []

    for step in range(TOTAL_STEPS):
        rates.zero_()
        if step < CUE_END:
            for idx in SUGAR_LEFT:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE
        elif step >= DELAY_END:
            for idx in SUGAR_LEFT + SUGAR_RIGHT:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE

        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)

        spk = spikes.squeeze(0)
        dn_vec = [int(spk[dn_idx[j]].item()) for j in range(len(dn_names))]
        cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
        dn_timeseries.append(dn_vec)
        cx_timeseries.append(cx_spk)

    return np.array(dn_timeseries), np.array(cx_timeseries)


def fitness_attention(dn_ts, left_dn_cols, right_dn_cols):
    """Fitness = left - right DN spikes during choice phase."""
    choice = dn_ts[DELAY_END:CHOICE_END]
    left_spikes = float(choice[:, left_dn_cols].sum())
    right_spikes = float(choice[:, right_dn_cols].sum())
    score = left_spikes - right_spikes
    return {
        "fitness": score,
        "left_spikes": left_spikes,
        "right_spikes": right_spikes,
        "laterality": score / max(left_spikes + right_spikes, 1.0),
    }


def main():
    logger.info("=" * 60)
    logger.info("IZHIKEVICH ATTENTION -- Third Cognitive Capability")
    logger.info("=" * 60)

    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    labels = load_module_labels()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    neuron_params = assign_neuron_types(num_neurons, neuron_ids, maps["rid_to_nt"], maps["rid_to_class"])

    cx_neurons = [idx for idx, nid in enumerate(neuron_ids)
                  if isinstance(maps["rid_to_class"].get(nid, ""), str) and "CX" in maps["rid_to_class"].get(nid, "")]
    logger.info("CX (IB) neurons: %d", len(cx_neurons))

    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    _syn_vals = torch.tensor(vals * GAIN, dtype=torch.float32)

    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = list(inter_module_edges)

    dn_names = DN_NAMES
    dn_idx = [DN_NEURONS[n] for n in dn_names]
    left_dn_cols = [dn_names.index(n) for n in LEFT_DN_NAMES]
    right_dn_cols = [dn_names.index(n) for n in RIGHT_DN_NAMES]

    sim_kwargs = dict(
        pre=pre, post=post, num_neurons=num_neurons, neuron_params=neuron_params,
        dn_names=dn_names, dn_idx=dn_idx, cx_neurons=cx_neurons,
        left_dn_cols=left_dn_cols, right_dn_cols=right_dn_cols,
    )

    # Baseline
    t0 = time.time()
    dn_ts_bl, cx_ts_bl = run_attention(_syn_vals, **sim_kwargs)
    bl = fitness_attention(dn_ts_bl, left_dn_cols, right_dn_cols)
    logger.info("Baseline: lat=%+.3f fitness=%.1f (%.1fs)", bl["laterality"], bl["fitness"], time.time() - t0)

    # Evolution
    logger.info("EVOLUTION: Selective Attention (25 gen x 10 mut)")
    N_GEN, N_MUT = 25, 10
    np.random.seed(42)
    torch.manual_seed(42)

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
            scale = np.random.uniform(0.5, 4.0)
            test_vals = best_syn_vals.clone()
            test_vals[syns] = old * scale

            dn_ts_t, _ = run_attention(test_vals, **sim_kwargs)
            result = fitness_attention(dn_ts_t, left_dn_cols, right_dn_cols)
            new_fitness = result["fitness"]
            acc = new_fitness > current_fitness

            all_mutations.append({
                "gen": gen, "mi": mi, "edge": [int(edge[0]), int(edge[1])],
                "scale": float(scale), "fitness": float(new_fitness),
                "delta": float(new_fitness - current_fitness), "accepted": acc,
            })

            if acc:
                current_fitness = new_fitness
                best_syn_vals[syns] = old * scale
                ga += 1
                accepted += 1

        if gen % 5 == 4 or gen == N_GEN - 1:
            logger.info("Gen %d: fit=%+.1f acc=%d/%d total=%d", gen, current_fitness, ga, N_MUT, accepted)

    # Final analysis
    dn_ts_ev, cx_ts_ev = run_attention(best_syn_vals, **sim_kwargs)
    final = fitness_attention(dn_ts_ev, left_dn_cols, right_dn_cols)
    logger.info("Evolved: lat=%+.3f fitness=%.1f", final["laterality"], final["fitness"])

    acc_edges = sorted(set(tuple(m["edge"]) for m in all_mutations if m["accepted"]))
    attn_modules = sorted(set(m for e in acc_edges for m in e))
    logger.info("Modules recruited: %s", attn_modules)

    # Save
    outdir = Path("results/attention")
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "izhikevich_attention",
        "baseline": bl, "final": final,
        "accepted_edges": acc_edges,
        "attention_modules": attn_modules,
        "total_accepted": accepted,
        "total_mutations": len(all_mutations),
    }
    with open(outdir / "attention.json", "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Saved to %s", outdir / "attention.json")
    logger.info("DONE. Total time: %.0fs", time.time() - t_start)


if __name__ == "__main__":
    main()
