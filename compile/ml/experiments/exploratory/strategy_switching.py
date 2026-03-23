#!/usr/bin/env python3
"""
Compile strategy switching experiment.

Can evolution find wiring that enables the brain to CHANGE behavior
mid-simulation?  Two-phase fitness: sugar (navigate) then JO (turn).
Fitness = min(phase1_nav, phase2_turn) forces competence at BOTH phases.

Uses BrainEngine (LIF) if available, otherwise IzhikevichBrainEngine.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PHASE1_STEPS = 500
PHASE2_STEPS = 500


def _get_brain_engine():
    try:
        from brain_body_bridge import BrainEngine
        return BrainEngine(device="cpu")
    except ImportError:
        from compile.simulate import IzhikevichBrainEngine
        return IzhikevichBrainEngine(device="cpu")


def evaluate_switching(brain, n_steps_per_phase=500):
    """Two-phase evaluation: sugar then JO."""
    dn_names = list(brain.dn_indices.keys())
    dn_idx = [brain.dn_indices[n] for n in dn_names]

    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus("sugar")

    phase1_spikes = np.zeros(len(dn_names))
    for _ in range(n_steps_per_phase):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            phase1_spikes[j] += spk[idx].item()

    brain.set_stimulus("jo")
    phase2_spikes = np.zeros(len(dn_names))
    for _ in range(n_steps_per_phase):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            phase2_spikes[j] += spk[idx].item()

    return {"dn_names": dn_names, "phase1": phase1_spikes, "phase2": phase2_spikes}


def fitness_switching(data):
    """Phase 1: nav; Phase 2: turn; fitness = min(nav, turn)."""
    names = data["dn_names"]
    p9_idx = [i for i, n in enumerate(names) if "P9" in n or "MN9" in n]
    nav_score = float(sum(data["phase1"][i] for i in p9_idx))

    da01_l = names.index("DNa01_left") if "DNa01_left" in names else -1
    da01_r = names.index("DNa01_right") if "DNa01_right" in names else -1
    da02_l = names.index("DNa02_left") if "DNa02_left" in names else -1
    da02_r = names.index("DNa02_right") if "DNa02_right" in names else -1
    left = data["phase2"][da01_l] + (data["phase2"][da02_l] if da02_l >= 0 else 0)
    right = data["phase2"][da01_r] + (data["phase2"][da02_r] if da02_r >= 0 else 0)
    turn_score = float(abs(left - right) + (left + right) * 0.1)

    return {"fitness": min(nav_score, turn_score), "nav_score": nav_score, "turn_score": turn_score}


def run_evolution(seed, brain, edge_syn_idx, inter_module_edges, n_generations=25, n_mutations=10):
    """Run (1+1) ES for strategy switching."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    brain._syn_vals.mul_(GAIN)

    data = evaluate_switching(brain)
    bl = fitness_switching(data)
    current_fitness = bl["fitness"]
    logger.info("Seed %d baseline: nav=%.2f turn=%.2f fit=%.2f", seed, bl["nav_score"], bl["turn_score"], bl["fitness"])

    all_mutations = []
    accepted = 0
    t0 = time.time()

    for gen in range(n_generations):
        ga = 0
        for mi in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syns = edge_syn_idx[edge]
            old = brain._syn_vals[syns].clone()
            scale = np.random.uniform(0.2, 5.0)
            brain._syn_vals[syns] = old * scale

            data = evaluate_switching(brain)
            result = fitness_switching(data)
            acc = result["fitness"] > current_fitness

            all_mutations.append({
                "seed": int(seed), "gen": gen, "mi": mi,
                "edge": [int(edge[0]), int(edge[1])],
                "scale": float(scale), "fitness": float(result["fitness"]),
                "delta": float(result["fitness"] - current_fitness), "accepted": acc,
                "nav_score": result["nav_score"], "turn_score": result["turn_score"],
            })

            if acc:
                current_fitness = result["fitness"]
                ga += 1
                accepted += 1
            else:
                brain._syn_vals[syns] = old

        if gen % 5 == 4 or gen == n_generations - 1:
            logger.info("Gen %d: fit=%.2f acc=%d/%d total=%d",
                        gen, current_fitness, ga, n_mutations, accepted)

    return {"seed": seed, "baseline": bl, "final_fitness": current_fitness,
            "total_accepted": accepted, "mutations": all_mutations}


def main():
    parser = argparse.ArgumentParser(description="Strategy switching evolution")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42])
    parser.add_argument("--generations", type=int, default=25)
    parser.add_argument("--mutations", type=int, default=10)
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("STRATEGY SWITCHING EVOLUTION")
    logger.info("=" * 60)

    labels = load_module_labels()
    df_conn = load_connectome()[0]
    edge_syn_idx, inter_module_edges_set = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = list(inter_module_edges_set)

    all_results = []
    for seed in args.seeds:
        brain = _get_brain_engine()
        result = run_evolution(seed, brain, edge_syn_idx, inter_module_edges,
                               args.generations, args.mutations)
        all_results.append(result)

    # Analysis
    all_acc_edges = set()
    for r in all_results:
        edges = set(tuple(m["edge"]) for m in r["mutations"] if m["accepted"])
        all_acc_edges.update(edges)
    logger.info("Total unique evolvable edges: %d", len(all_acc_edges))

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "strategy_switching.json", "w") as f:
        json.dump({
            "experiment": "strategy_switching",
            "results": all_results,
            "all_evolvable_edges": sorted(all_acc_edges),
        }, f, indent=2)
    logger.info("Saved to %s", outdir / "strategy_switching.json")
    logger.info("DONE.")


if __name__ == "__main__":
    main()
