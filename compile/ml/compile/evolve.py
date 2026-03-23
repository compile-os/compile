"""
Evolution routines for connectome optimization.

Implements a (1+1) evolutionary strategy: mutate one inter-module edge
at a time, evaluate, accept if fitness improves, reject otherwise.

**Why (1+1) ES and not CMA-ES / NSGA-II / population-based methods?**

1. The search space is discrete and structured: we mutate *synaptic weight
   scales* on specific inter-module edges (2,450 edges in the fly connectome).
   Each mutation is a scalar multiplier on a group of synapses.

2. Evaluation is expensive: each fitness evaluation requires simulating
   139,255 Izhikevich neurons for 500-1000 timesteps. Population-based
   methods would require N evaluations per generation.

3. The (1+1) ES is sufficient because we are not searching for a global
   optimum — we are testing whether *any* wiring change improves a specific
   behavior. The scientific question is about evolvability (which edges
   matter), not about finding the best possible brain.

4. Cross-seed consistency validates this choice: 5 independent seeds with
   different random mutation orders converge to the same set of important
   edges, suggesting the fitness landscape is smooth enough that greedy
   search finds the relevant structure.

**Limitations:** This approach cannot find solutions requiring coordinated
multi-edge changes that are individually neutral. A population-based method
with crossover could explore such combinations. Future work should test
whether CMA-ES or MAP-Elites discovers qualitatively different solutions.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import torch

from compile.simulate import IzhikevichBrainEngine, evaluate_brain

logger = logging.getLogger(__name__)


def run_evolution(
    brain: IzhikevichBrainEngine,
    fitness_name: str,
    fitness_fn: Callable,
    stimulus: str,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
    seed: int = 0,
    n_generations: int = 100,
    n_mutations: int = 20,
    n_steps: int = 1000,
    scale_range: tuple[float, float] = (0.2, 5.0),
    output_dir: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Run (1+1) ES evolution on inter-module edges.

    Args:
        brain: IzhikevichBrainEngine instance
        fitness_name: name of the behavior being optimized
        fitness_fn: callable that takes evaluate_brain output and returns float
        stimulus: stimulus name to apply during evaluation
        edge_syn_idx: mapping from (pre_mod, post_mod) -> synapse indices
        inter_module_edges: list of (pre_mod, post_mod) edge tuples
        seed: random seed for reproducibility
        n_generations: number of evolution generations
        n_mutations: mutations per generation
        n_steps: simulation steps per evaluation
        scale_range: (min, max) for uniform random weight multiplier
        output_dir: if set, save results to this directory

    Returns:
        dict with keys: baseline, final_fitness, accepted, mutations,
        edge_classification, edges_tested
    """
    np.random.seed(seed)
    torch.manual_seed(seed)

    # Baseline evaluation
    data = evaluate_brain(brain, stimulus, n_steps)
    baseline = fitness_fn(data)
    current = baseline
    logger.info("Baseline (%s seed=%d): %.4f", fitness_name, seed, baseline)

    all_mutations = []
    accepted = 0
    edges_tested = set()
    t0 = time.time()

    for gen in range(n_generations):
        gen_accepted = 0
        for mi in range(n_mutations):
            # Pick random inter-module edge
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            edges_tested.add(edge)
            syns = edge_syn_idx[edge]

            # Mutate: scale synaptic weights
            old = brain._syn_vals[syns].clone()
            scale = np.random.uniform(*scale_range)
            brain._syn_vals[syns] = old * scale

            # Save/restore RNG state around evaluation so that the random
            # mutation sequence is deterministic regardless of how many Poisson
            # spikes the simulator draws internally. This ensures cross-seed
            # comparisons are valid: seed X always tests the same sequence of
            # edges and scales, even if evaluate_brain's internal randomness varies.
            rng_state = np.random.get_state()
            data = evaluate_brain(brain, stimulus, n_steps)
            new_fit = fitness_fn(data)
            np.random.set_state(rng_state)

            acc = new_fit > current
            delta = new_fit - current

            all_mutations.append({
                "seed": int(seed),
                "generation": gen,
                "mutation_index": mi,
                "pre_module": int(edge[0]),
                "post_module": int(edge[1]),
                "n_synapses": len(syns),
                "scale": float(scale),
                "fitness_before": float(current),
                "fitness_after": float(new_fit),
                "delta": float(delta),
                "accepted": acc,
            })

            if acc:
                current = new_fit
                gen_accepted += 1
                accepted += 1
            else:
                brain._syn_vals[syns] = old

        if gen % 10 == 9 or gen == n_generations - 1:
            elapsed = time.time() - t0
            logger.info(
                "Gen %d: fitness=%.2f accepted=%d/%d total_acc=%d edges=%d [%.0fs]",
                gen, current, gen_accepted, n_mutations, accepted,
                len(edges_tested), elapsed,
            )

        if progress_callback is not None:
            progress_callback(gen + 1, n_generations, float(current), accepted)

    # Classify edges
    edge_classification = _classify_edges(all_mutations)

    result = {
        "fitness_name": fitness_name,
        "seed": seed,
        "baseline": float(baseline),
        "final_fitness": float(current),
        "improvement": float(current - baseline),
        "improvement_pct": float((current - baseline) / max(baseline, 1e-10) * 100),
        "accepted": accepted,
        "total_mutations": len(all_mutations),
        "edges_tested": len(edges_tested),
        "n_generations": n_generations,
        "n_mutations_per_gen": n_mutations,
        "mutations": all_mutations,
        "edge_classification": edge_classification,
    }

    # Save if output directory specified
    if output_dir:
        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        torch.save(
            brain._syn_vals.clone(),
            outdir / f"{fitness_name}_s{seed}_brain.pt",
        )
        with open(outdir / f"{fitness_name}_s{seed}_results.json", "w") as f:
            json.dump(
                {k: v for k, v in result.items() if k != "mutations"},
                f, indent=2,
            )
        logger.info("Saved results to %s", outdir)

    return result


def _classify_edges(mutations: list[dict]) -> dict:
    """Classify edges as frozen, evolvable, or irrelevant based on mutation history."""
    edges = {}
    for m in mutations:
        key = f"{m['pre_module']}->{m['post_module']}"
        if key not in edges:
            edges[key] = {"accepted": 0, "decreased": 0, "unchanged": 0, "deltas": []}
        if m["accepted"]:
            edges[key]["accepted"] += 1
        elif m["delta"] < 0:
            edges[key]["decreased"] += 1
        else:
            edges[key]["unchanged"] += 1
        edges[key]["deltas"].append(m["delta"])

    classified = {}
    for key, data in edges.items():
        total = data["accepted"] + data["decreased"] + data["unchanged"]
        if total == 0:
            continue
        if data["accepted"] > 0:
            category = "evolvable"
        elif data["decreased"] / total > 0.5:
            category = "frozen"
        else:
            category = "irrelevant"
        classified[key] = {
            "category": category,
            "accepted": data["accepted"],
            "decreased": data["decreased"],
            "unchanged": data["unchanged"],
            "total_tests": total,
            "mean_delta": float(np.mean(data["deltas"])),
        }

    return classified
