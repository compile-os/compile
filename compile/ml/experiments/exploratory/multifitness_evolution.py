#!/usr/bin/env python3
"""
Multi-fitness convergent evolution.

Run evolution with spike-based fitness functions to map the brain's
complete API surface.  Uses BrainEngine (LIF) if available, otherwise
falls back to IzhikevichBrainEngine from compile.simulate.

Usage: python3 multifitness_evolution.py --fitness navigation --seed 42
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import torch

from compile.constants import GAIN
from compile.data import build_edge_synapse_index, load_connectome, load_module_labels
from compile.fitness import f_arousal, f_esc, f_nav, f_turn

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _fitness_efficiency(dn_spikes):
    p9 = sum(dn_spikes.get(n, 0) for n in ["P9_left", "P9_right", "P9_oDN1_left", "P9_oDN1_right"])
    total = sum(dn_spikes.values()) + 1
    return p9 / total


def _fitness_inhibition(dn_spikes):
    return -sum(dn_spikes.values())


FITNESS_FUNCTIONS = {
    "navigation": ("sugar", f_nav),
    "escape": ("lc4", f_esc),
    "turning": ("jo", f_turn),
    "arousal": ("sugar", f_arousal),
    "efficiency": ("sugar", _fitness_efficiency),
    "inhibition": ("bitter", _fitness_inhibition),
}


def _get_brain_engine(device="cpu"):
    """Try BrainEngine (LIF), fall back to IzhikevichBrainEngine."""
    try:
        from brain_body_bridge import BrainEngine
        brain = BrainEngine(device=device)
        logger.info("Using LIF BrainEngine")
        return brain
    except ImportError:
        from compile.simulate import IzhikevichBrainEngine
        brain = IzhikevichBrainEngine(device=device)
        logger.info("Using IzhikevichBrainEngine (BrainEngine not available)")
        return brain


def evaluate_brain(brain, stimulus, n_steps=300):
    """Run brain and return DN spike counts."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    dn_spikes = {name: 0 for name in brain.dn_indices}
    for _ in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for name, idx in brain.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
    return dn_spikes


def run_evolution(fitness_name, seed, gain=8.0, n_generations=50, n_mutations=5,
                  n_steps=300, output_dir="results/multifitness"):
    """Run evolution for one fitness function and seed."""
    np.random.seed(seed)
    torch.manual_seed(seed)

    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    brain = _get_brain_engine(device="cpu")
    brain._syn_vals.mul_(gain)

    labels = load_module_labels()
    df_conn = load_connectome()[0]
    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = list(inter_module_edges)
    logger.info("Inter-module edges: %d", len(inter_module_edges))

    dn_spikes = evaluate_brain(brain, stimulus, n_steps)
    baseline_fitness = fitness_fn(dn_spikes)
    current_fitness = baseline_fitness
    logger.info("Baseline (%s): %.4f", fitness_name, baseline_fitness)

    all_mutations = []
    accepted_count = 0

    for gen in range(n_generations):
        gen_accepted = 0
        for mut_i in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syn_indices = edge_syn_idx[edge]
            old_vals = brain._syn_vals[syn_indices].clone()
            scale = np.random.uniform(0.3, 3.0)
            brain._syn_vals[syn_indices] = old_vals * scale

            dn_new = evaluate_brain(brain, stimulus, n_steps)
            new_fitness = fitness_fn(dn_new)
            accepted = new_fitness > current_fitness

            all_mutations.append({
                "seed": int(seed), "generation": gen, "mutation_index": mut_i,
                "pre_module": int(edge[0]), "post_module": int(edge[1]),
                "scale": float(scale), "fitness_before": float(current_fitness),
                "fitness_after": float(new_fitness), "delta": float(new_fitness - current_fitness),
                "accepted": accepted,
            })

            if accepted:
                current_fitness = new_fitness
                gen_accepted += 1
                accepted_count += 1
            else:
                brain._syn_vals[syn_indices] = old_vals

        if gen % 10 == 9 or gen == n_generations - 1:
            logger.info("Gen %d: fitness=%.4f accepted=%d/%d", gen, current_fitness, gen_accepted, n_mutations)

    outfile = f"{output_dir}/{fitness_name}_seed{seed}_final.json"
    with open(outfile, "w") as f:
        json.dump({
            "fitness_name": fitness_name, "seed": seed, "gain": gain,
            "baseline_fitness": baseline_fitness, "final_fitness": current_fitness,
            "total_accepted": accepted_count, "mutations": all_mutations,
        }, f, indent=2)
    logger.info("Saved to %s. Improvement: %.2f%%",
                outfile, 100 * (current_fitness - baseline_fitness) / max(abs(baseline_fitness), 0.001))
    return current_fitness


def main():
    parser = argparse.ArgumentParser(description="Multi-fitness evolution")
    parser.add_argument("--fitness", required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--gain", type=float, default=8.0)
    parser.add_argument("--generations", type=int, default=50)
    parser.add_argument("--mutations", type=int, default=5)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"))
    args = parser.parse_args()

    run_evolution(args.fitness, args.seed, args.gain,
                  args.generations, args.mutations, args.steps, args.output)


if __name__ == "__main__":
    main()
