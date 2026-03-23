#!/usr/bin/env python3
"""
Bulletproof evolution: high-mutation runs for cross-seed consistency.

20 mutations/gen x 100 gen = 2000 mutations per seed.  Tests ALL inter-module
edges (not just a subset) and saves the full evolved brain weights for
verification.

This is a thin CLI wrapper around ``compile.evolve.run_evolution`` which
implements the (1+1) ES loop.  The wrapper handles BrainEngine selection
(LIF vs Izhikevich) and CLI arguments.

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch

from compile.constants import GAIN
from compile.data import load_connectome, load_module_labels, build_edge_synapse_index
from compile.fitness import (
    fitness_navigation, fitness_escape, fitness_turning,
    fitness_arousal, fitness_circles, fitness_rhythm,
)
from compile.evolve import run_evolution
from compile.simulate import IzhikevichBrainEngine, evaluate_brain
from compile.stats import bootstrap_ci, improvement_with_ci

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fitness registry (array-based functions used by evaluate_brain/run_evolution)
# ---------------------------------------------------------------------------

FITNESS_FUNCTIONS = {
    "navigation": ("sugar", fitness_navigation),
    "escape":     ("lc4",   fitness_escape),
    "turning":    ("jo",    fitness_turning),
    "arousal":    ("sugar", fitness_arousal),
    "circles":    ("sugar", fitness_circles),
    "rhythm":     ("sugar", fitness_rhythm),
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_bulletproof(
    fitness_name: str,
    seed: int,
    model: str = "lif",
    gain: float = GAIN,
    n_generations: int = 100,
    n_mutations: int = 20,
    n_steps: int = 1000,
    output_dir: str = "results",
):
    """Run a single-seed evolution experiment."""
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    # Load edge index
    df_conn, _, _ = load_connectome()
    labels = load_module_labels()
    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    logger.info("Inter-module edges: %d", len(inter_module_edges))

    # Build brain engine
    if model == "lif":
        from brain_body_bridge import BrainEngine
        brain = BrainEngine(device="cpu")
        brain._syn_vals.mul_(gain)

        # Wrap LIF brain so compile.evolve can use evaluate_brain on it.
        # LIF BrainEngine has the same interface as IzhikevichBrainEngine,
        # so run_evolution works with either.
    else:
        brain = IzhikevichBrainEngine(device="cpu")

    # Run evolution via shared library
    result = run_evolution(
        brain=brain,
        fitness_name=fitness_name,
        fitness_fn=fitness_fn,
        stimulus=stimulus,
        edge_syn_idx=edge_syn_idx,
        inter_module_edges=inter_module_edges,
        seed=seed,
        n_generations=n_generations,
        n_mutations=n_mutations,
        n_steps=n_steps,
        output_dir=output_dir,
    )

    # Summary
    baseline = result["baseline"]
    final = result["final_fitness"]
    accepted = result["accepted"]
    total_mut = result["total_mutations"]
    edges_tested = result["edges_tested"]

    logger.info(
        "Done! %s s%d: %.2f -> %.2f (%+.1f%%)",
        fitness_name, seed, baseline, final,
        (final - baseline) / max(abs(baseline), 0.001) * 100,
    )
    logger.info(
        "Accepted: %d/%d (%.1f%%)  Edges tested: %d/%d (%.0f%%)",
        accepted, total_mut, 100 * accepted / total_mut,
        edges_tested, len(inter_module_edges),
        100 * edges_tested / len(inter_module_edges),
    )

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Bulletproof evolution: high-mutation cross-seed runs")
    parser.add_argument("--fitness", required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument("--seed", type=int, default=42, help="Single seed (use --seeds for multiple)")
    parser.add_argument("--seeds", type=int, nargs="+", default=None,
                        help="Multiple seeds for cross-seed statistics (overrides --seed)")
    parser.add_argument("--generations", type=int, default=100)
    parser.add_argument("--mutations", type=int, default=20)
    parser.add_argument("--n-steps", type=int, default=1000, help="Simulation steps per evaluation")
    parser.add_argument("--model", choices=["lif", "izh"], default="lif",
                        help="Neuron model: lif (BrainEngine) or izh (Izhikevich)")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    args = parser.parse_args()

    # Support multiple seeds for statistical analysis
    seeds = [args.seed] if args.seeds is None else args.seeds
    results = []
    for s in seeds:
        r = run_bulletproof(
            fitness_name=args.fitness,
            seed=s,
            model=args.model,
            n_generations=args.generations,
            n_mutations=args.mutations,
            n_steps=args.n_steps,
            output_dir=args.output_dir,
        )
        results.append(r)

    # Statistical summary across seeds
    if len(results) > 1:
        baseline = results[0]["baseline"]
        seed_fitnesses = np.array([r["final_fitness"] for r in results])
        logger.info("=" * 60)
        logger.info("CROSS-SEED STATISTICAL SUMMARY (%d seeds)", len(results))
        logger.info("=" * 60)

        point, ci_lo, ci_hi = bootstrap_ci(seed_fitnesses)
        logger.info(
            "Final fitness: %.2f [95%% CI: %.2f, %.2f]",
            point, ci_lo, ci_hi,
        )

        imp = improvement_with_ci(baseline, seed_fitnesses)
        logger.info(
            "Improvement over baseline (%.2f): %.1f%% [95%% CI: %.1f%%, %.1f%%]",
            baseline, imp["improvement_pct"], imp["ci_lower_pct"], imp["ci_upper_pct"],
        )
        logger.info(
            "Absolute: %.2f -> %.2f [95%% CI: %.2f, %.2f]",
            baseline, imp["mean_evolved"], imp["ci_lower"], imp["ci_upper"],
        )
