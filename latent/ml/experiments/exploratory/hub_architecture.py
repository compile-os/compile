#!/usr/bin/env python3
"""
Hub architecture optimality experiments.

Tests whether hub-and-spoke is necessary, location-specific, or a bottleneck
in the FlyWire connectome by running evolution on surgically modified brains.

Three experiments:
  1. FLAT (no-hub): Suppress all hubs to ≤2x average connectivity
  2. SWAP: Demote modules 4,19 → promote modules 12,37
  3. MORE: Add 4 extra hubs (modules 8,12,25,37) alongside existing 4,19

Each experiment runs evolution for multiple behaviors (navigation, escape,
turning) with 5 seeds for cross-seed statistics, then compares to a
biological (unmodified) baseline run with the same parameters.

Usage:
    # Run a single experiment + behavior
    python hub_architecture.py --experiment flat --fitness navigation --seeds 0 1 2 3 4

    # Run biological baseline for comparison
    python hub_architecture.py --experiment baseline --fitness navigation --seeds 0 1 2 3 4

    # Analyze results from a completed run
    python hub_architecture.py --analyze results/hub_architecture/

Designed to run on C5 AWS instances with autoresearch. Each instance runs
one experiment for all behaviors (or a subset). Total runtime: ~6-12 hours
per instance depending on generations.
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
from compile.data import (
    build_edge_synapse_index,
    load_connectome,
    load_module_labels,
)
from compile.evolve import run_evolution
from compile.fitness import (
    fitness_escape,
    fitness_navigation,
    fitness_turning,
)
from compile.hub_surgery import (
    add_hubs,
    flatten_hubs,
    identify_hubs,
    swap_hubs,
)
from compile.simulate import IzhikevichBrainEngine
from compile.stats import bootstrap_ci

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

FITNESS_FUNCTIONS = {
    "navigation": ("sugar", fitness_navigation),
    "escape": ("lc4", fitness_escape),
    "turning": ("jo", fitness_turning),
}

# Hub module IDs from prior analysis (edge 19→4 is the key finding)
BIOLOGICAL_HUBS = [4, 19]

# Alternative hub candidates — chosen to be non-hub modules with moderate
# connectivity (not the weakest, not already hubs). Modules 12 and 37
# appear in the conflict_mods set but are not primary hubs.
ALTERNATIVE_HUBS = [12, 37]

# Additional hubs for the "more hubs" experiment — 4 modules spread
# across the conflict_mods set that are not already hubs.
EXTRA_HUBS = [8, 12, 25, 37]

# Evolution parameters
DEFAULT_GENERATIONS = 100
DEFAULT_MUTATIONS = 20
DEFAULT_STEPS = 1000
DEFAULT_SEEDS = [0, 1, 2, 3, 4]


# ── Experiment runners ────────────────────────────────────────────────────

def run_experiment(
    experiment: str,
    fitness_name: str,
    seeds: list[int],
    n_generations: int = DEFAULT_GENERATIONS,
    n_mutations: int = DEFAULT_MUTATIONS,
    n_steps: int = DEFAULT_STEPS,
    output_dir: str = "results/hub_architecture",
    max_ratio: float = 2.0,
) -> dict:
    """
    Run a hub architecture experiment.

    Args:
        experiment: one of 'baseline', 'flat', 'swap', 'more'
        fitness_name: 'navigation', 'escape', or 'turning'
        seeds: list of random seeds
        n_generations: evolution generations
        n_mutations: mutations per generation
        n_steps: simulation steps per evaluation
        output_dir: base output directory
        max_ratio: for flat experiment, max connectivity ratio

    Returns:
        dict with all results and surgery report
    """
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]
    exp_dir = Path(output_dir) / experiment / fitness_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Load connectome structure (shared across seeds)
    df_conn, _, _ = load_connectome()
    labels = load_module_labels()
    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    logger.info("Inter-module edges: %d", len(inter_module_edges))

    all_results = []
    surgery_report = None

    for seed in seeds:
        logger.info("=" * 60)
        logger.info(
            "EXPERIMENT=%s FITNESS=%s SEED=%d",
            experiment, fitness_name, seed,
        )
        logger.info("=" * 60)

        # Fresh brain for each seed
        brain = IzhikevichBrainEngine(device="cpu")

        # Apply surgery BEFORE evolution
        if experiment == "flat":
            surgery_report = flatten_hubs(
                brain._syn_vals, edge_syn_idx, inter_module_edges,
                max_ratio=max_ratio,
            )
        elif experiment == "swap":
            surgery_report = swap_hubs(
                brain._syn_vals, edge_syn_idx, inter_module_edges,
                old_hubs=BIOLOGICAL_HUBS,
                new_hubs=ALTERNATIVE_HUBS,
            )
        elif experiment == "more":
            surgery_report = add_hubs(
                brain._syn_vals, edge_syn_idx, inter_module_edges,
                existing_hubs=BIOLOGICAL_HUBS,
                new_hubs=EXTRA_HUBS,
            )
        elif experiment == "baseline":
            surgery_report = {"operation": "none (biological baseline)"}
        else:
            raise ValueError(f"Unknown experiment: {experiment}")

        # Rebuild weight matrix after surgery
        if experiment != "baseline":
            brain._rebuild_weight_matrix()

        # Identify hubs AFTER surgery (for verification)
        post_hubs, post_strengths = identify_hubs(
            brain._syn_vals, edge_syn_idx, inter_module_edges, top_n=6,
        )

        # Run evolution
        t0 = time.time()
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
            output_dir=str(exp_dir),
        )
        elapsed = time.time() - t0

        result["experiment"] = experiment
        result["elapsed_seconds"] = elapsed
        result["surgery_report"] = surgery_report
        result["post_surgery_top6_hubs"] = post_hubs
        result["post_surgery_strengths"] = {
            str(k): float(v) for k, v in
            sorted(post_strengths.items(), key=lambda x: x[1], reverse=True)[:10]
        }

        all_results.append(result)

        logger.info(
            "Seed %d done in %.0fs: %.2f -> %.2f (%+.1f%%)",
            seed, elapsed, result["baseline"], result["final_fitness"],
            result["improvement_pct"],
        )

    # Cross-seed summary
    summary = _compute_summary(experiment, fitness_name, all_results)

    # Save everything
    output = {
        "experiment": experiment,
        "fitness_name": fitness_name,
        "seeds": seeds,
        "params": {
            "n_generations": n_generations,
            "n_mutations": n_mutations,
            "n_steps": n_steps,
            "max_ratio": max_ratio if experiment == "flat" else None,
        },
        "surgery_report": surgery_report,
        "summary": summary,
        "per_seed": [
            {k: v for k, v in r.items() if k != "mutations"}
            for r in all_results
        ],
    }

    outpath = exp_dir / "experiment_results.json"
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info("Saved results to %s", outpath)

    return output


def _compute_summary(experiment: str, fitness_name: str, results: list[dict]) -> dict:
    """Compute cross-seed statistical summary."""
    baselines = np.array([r["baseline"] for r in results])
    finals = np.array([r["final_fitness"] for r in results])
    improvements = finals - baselines
    improvement_pcts = np.array([r["improvement_pct"] for r in results])
    accepted = np.array([r["accepted"] for r in results])

    summary = {
        "n_seeds": len(results),
        "baseline_mean": float(baselines.mean()),
        "baseline_std": float(baselines.std()),
        "final_mean": float(finals.mean()),
        "final_std": float(finals.std()),
        "improvement_mean": float(improvements.mean()),
        "improvement_std": float(improvements.std()),
        "improvement_pct_mean": float(improvement_pcts.mean()),
        "improvement_pct_std": float(improvement_pcts.std()),
        "accepted_mean": float(accepted.mean()),
        "accepted_std": float(accepted.std()),
    }

    if len(results) > 1:
        try:
            point, ci_lo, ci_hi = bootstrap_ci(finals)
            summary["final_95ci"] = [float(ci_lo), float(ci_hi)]
        except Exception:
            pass

    logger.info("=" * 60)
    logger.info("SUMMARY: %s / %s", experiment, fitness_name)
    logger.info("=" * 60)
    logger.info(
        "Baseline: %.2f ± %.2f",
        summary["baseline_mean"], summary["baseline_std"],
    )
    logger.info(
        "Final:    %.2f ± %.2f",
        summary["final_mean"], summary["final_std"],
    )
    logger.info(
        "Improvement: %.1f%% ± %.1f%%",
        summary["improvement_pct_mean"], summary["improvement_pct_std"],
    )
    logger.info(
        "Accepted mutations: %.1f ± %.1f",
        summary["accepted_mean"], summary["accepted_std"],
    )

    return summary


# ── Analysis ──────────────────────────────────────────────────────────────

def analyze_results(results_dir: str) -> None:
    """
    Compare results across experiments.

    Reads experiment_results.json from each subdirectory and produces
    a comparison table.
    """
    results_dir = Path(results_dir)
    experiments = {}

    for exp_dir in sorted(results_dir.iterdir()):
        if not exp_dir.is_dir():
            continue
        for fit_dir in sorted(exp_dir.iterdir()):
            if not fit_dir.is_dir():
                continue
            result_file = fit_dir / "experiment_results.json"
            if result_file.exists():
                with open(result_file) as f:
                    data = json.load(f)
                key = (data["experiment"], data["fitness_name"])
                experiments[key] = data["summary"]

    if not experiments:
        logger.warning("No results found in %s", results_dir)
        return

    # Print comparison table
    print("\n" + "=" * 80)
    print("HUB ARCHITECTURE EXPERIMENT RESULTS")
    print("=" * 80)
    print(f"{'Experiment':<12} {'Fitness':<12} {'Baseline':>10} {'Final':>10} "
          f"{'Improv%':>10} {'Accepted':>10}")
    print("-" * 80)

    for (exp, fit), s in sorted(experiments.items()):
        print(
            f"{exp:<12} {fit:<12} {s['baseline_mean']:>10.2f} "
            f"{s['final_mean']:>10.2f} {s['improvement_pct_mean']:>9.1f}% "
            f"{s['accepted_mean']:>10.1f}"
        )

    print("=" * 80)

    # Key comparisons
    print("\n── KEY QUESTIONS ──")
    for fit in ["navigation", "escape", "turning"]:
        baseline_key = ("baseline", fit)
        if baseline_key not in experiments:
            continue
        bio = experiments[baseline_key]
        print(f"\n{fit.upper()}:")
        print(f"  Biological:     {bio['final_mean']:.2f} ({bio['improvement_pct_mean']:+.1f}%)")

        for exp in ["flat", "swap", "more"]:
            key = (exp, fit)
            if key in experiments:
                s = experiments[key]
                diff = s["final_mean"] - bio["final_mean"]
                print(f"  {exp:<14}: {s['final_mean']:.2f} ({s['improvement_pct_mean']:+.1f}%) "
                      f"[vs bio: {diff:+.2f}]")

    print("\n── INTERPRETATION ──")
    for fit in ["navigation", "escape", "turning"]:
        flat_key = ("flat", fit)
        bio_key = ("baseline", fit)
        if flat_key in experiments and bio_key in experiments:
            flat_final = experiments[flat_key]["final_mean"]
            bio_final = experiments[bio_key]["final_mean"]
            if flat_final >= bio_final * 0.8:
                print(f"  {fit}: Flat architecture WORKS — hubs may not be necessary")
            else:
                print(f"  {fit}: Flat architecture FAILS — hubs are required")

        swap_key = ("swap", fit)
        if swap_key in experiments and bio_key in experiments:
            swap_final = experiments[swap_key]["final_mean"]
            bio_final = experiments[bio_key]["final_mean"]
            if swap_final >= bio_final * 0.8:
                print(f"  {fit}: Alternative hubs WORK — hub location is flexible")
            else:
                print(f"  {fit}: Alternative hubs FAIL — modules 4,19 are special")

        more_key = ("more", fit)
        if more_key in experiments and bio_key in experiments:
            more_final = experiments[more_key]["final_mean"]
            bio_final = experiments[bio_key]["final_mean"]
            if more_final > bio_final * 1.1:
                print(f"  {fit}: More hubs IMPROVES capacity — 2-hub is a bottleneck")
            else:
                print(f"  {fit}: More hubs does NOT help — 2 hubs is sufficient")


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Hub architecture optimality experiments"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Run experiment
    run_parser = subparsers.add_parser("run", help="Run an experiment")
    run_parser.add_argument(
        "--experiment", required=True,
        choices=["baseline", "flat", "swap", "more"],
        help="Which experiment to run",
    )
    run_parser.add_argument(
        "--fitness", required=True, nargs="+",
        choices=list(FITNESS_FUNCTIONS.keys()),
        help="Fitness function(s) to test",
    )
    run_parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    run_parser.add_argument("--generations", type=int, default=DEFAULT_GENERATIONS)
    run_parser.add_argument("--mutations", type=int, default=DEFAULT_MUTATIONS)
    run_parser.add_argument("--n-steps", type=int, default=DEFAULT_STEPS)
    run_parser.add_argument("--output-dir", default="results/hub_architecture")
    run_parser.add_argument("--max-ratio", type=float, default=2.0,
                            help="Max connectivity ratio for flat experiment")

    # Analyze results
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    analyze_parser.add_argument("results_dir", default="results/hub_architecture", nargs="?")

    args = parser.parse_args()

    if args.command == "run":
        for fit in args.fitness:
            run_experiment(
                experiment=args.experiment,
                fitness_name=fit,
                seeds=args.seeds,
                n_generations=args.generations,
                n_mutations=args.mutations,
                n_steps=args.n_steps,
                output_dir=args.output_dir,
                max_ratio=args.max_ratio,
            )
    elif args.command == "analyze":
        analyze_results(args.results_dir)
    else:
        parser.print_help()
