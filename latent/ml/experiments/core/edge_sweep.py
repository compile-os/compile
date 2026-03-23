#!/usr/bin/env python3
"""
Edge sweep: systematically test every inter-module edge for every fitness function.

No evolution, no randomness, no path-dependence. For each edge, scale by 2x and
0.5x, then measure fitness change. Classifies every edge as frozen (fitness
decreases), irrelevant (no change), or evolvable (fitness improves).

This produces:
  1. Complete coverage (all inter-module edges tested)
  2. Deterministic classification (same result every run)
  3. True sensitivity map per fitness function

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
import time
from pathlib import Path

import torch

from compile.constants import DN_NEURONS, GAIN, STIMULUS_MAP
from compile.data import load_connectome, load_module_labels, build_edge_synapse_index
from compile.fitness import f_nav, f_esc, f_turn, f_arousal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fitness registry (dict-based fitness for the fast evaluate_brain)
# ---------------------------------------------------------------------------

FITNESS_FUNCTIONS = {
    "navigation": ("sugar", f_nav),
    "escape":     ("lc4",   f_esc),
    "turning":    ("jo",    f_turn),
    "arousal":    ("sugar", f_arousal),
}


# ---------------------------------------------------------------------------
# Fast evaluation (returns DN spike dict, not windowed data)
# ---------------------------------------------------------------------------

def evaluate_brain(brain, stimulus: str, n_steps: int = 300) -> dict:
    """Fast evaluation -- returns {dn_name: spike_count} dict."""
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


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------

def run_sweep(
    fitness_name: str,
    start_idx: int = 0,
    end_idx: int | None = None,
    model: str = "lif",
    output_dir: str = "results",
    n_steps: int = 300,
):
    """Sweep all inter-module edges for a single fitness function."""
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    # Load edge index
    df_conn, df_comp, num_neurons = load_connectome()
    labels = load_module_labels()
    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = sorted(inter_module_edges)
    logger.info("Total inter-module edges: %d", len(inter_module_edges))

    # Build brain engine
    if model == "lif":
        from brain_body_bridge import BrainEngine
        brain = BrainEngine(device="cpu")
        brain._syn_vals.mul_(GAIN)
    else:
        from compile.simulate import IzhikevichBrainEngine
        brain = IzhikevichBrainEngine(device="cpu")

    baseline_weights = brain._syn_vals.clone()

    # Baseline
    dn_base = evaluate_brain(brain, stimulus, n_steps)
    baseline = fitness_fn(dn_base)
    logger.info("Baseline (%s): %.4f", fitness_name, baseline)

    edges = inter_module_edges[start_idx:end_idx]
    logger.info(
        "Sweeping edges %d to %d of %d",
        start_idx, start_idx + len(edges), len(inter_module_edges),
    )

    results = []
    t0 = time.time()

    for i, edge in enumerate(edges):
        syns = edge_syn_idx[edge]

        # Test scale=2.0 (amplify)
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= 2.0
        dn_amp = evaluate_brain(brain, stimulus, n_steps)
        fitness_amp = fitness_fn(dn_amp)

        # Test scale=0.5 (attenuate)
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= 0.5
        dn_att = evaluate_brain(brain, stimulus, n_steps)
        fitness_att = fitness_fn(dn_att)

        delta_amp = fitness_amp - baseline
        delta_att = fitness_att - baseline

        if delta_amp > 0 or delta_att > 0:
            classification = "evolvable"
        elif delta_amp < 0 or delta_att < 0:
            classification = "frozen"
        else:
            classification = "irrelevant"

        results.append({
            "pre_module": int(edge[0]),
            "post_module": int(edge[1]),
            "n_synapses": len(syns),
            "delta_amplify": float(delta_amp),
            "delta_attenuate": float(delta_att),
            "fitness_amplify": float(fitness_amp),
            "fitness_attenuate": float(fitness_att),
            "classification": classification,
        })

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = elapsed / (i + 1)
            remaining = rate * (len(edges) - i - 1)
            counts = {"evolvable": 0, "frozen": 0, "irrelevant": 0}
            for r in results:
                counts[r["classification"]] += 1
            logger.info(
                "[%d/%d] %.0fs elapsed, %.0fs remaining | %s",
                i + 1, len(edges), elapsed, remaining, counts,
            )

    # Reset brain
    brain._syn_vals.copy_(baseline_weights)

    # Summary
    counts = {"evolvable": 0, "frozen": 0, "irrelevant": 0}
    for r in results:
        counts[r["classification"]] += 1

    total = len(results)
    logger.info("=== SWEEP RESULTS: %s ===", fitness_name)
    logger.info("Edges tested: %d", total)
    logger.info("Frozen: %d (%.1f%%)", counts["frozen"], 100 * counts["frozen"] / total)
    logger.info("Irrelevant: %d (%.1f%%)", counts["irrelevant"], 100 * counts["irrelevant"] / total)
    logger.info("Evolvable: %d (%.1f%%)", counts["evolvable"], 100 * counts["evolvable"] / total)

    evolvable = [
        (r["pre_module"], r["post_module"])
        for r in results
        if r["classification"] == "evolvable"
    ]
    logger.info("Evolvable pairs: %s", sorted(evolvable))

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "fitness_name": fitness_name,
        "baseline_fitness": baseline,
        "n_edges_tested": total,
        "n_total_edges": len(inter_module_edges),
        "start_idx": start_idx,
        "end_idx": start_idx + len(edges),
        "classification_counts": counts,
        "results": results,
    }
    suffix = f"_{start_idx}_{start_idx + len(edges)}" if end_idx else ""
    out_path = outdir / f"sweep_{fitness_name}{suffix}.json"
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

    parser = argparse.ArgumentParser(description="Edge sweep: deterministic edge classification")
    parser.add_argument("--fitness", required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument("--start", type=int, default=0, help="Start edge index")
    parser.add_argument("--end", type=int, default=None, help="End edge index (exclusive)")
    parser.add_argument("--model", choices=["lif", "izh"], default="lif",
                        help="Neuron model: lif (BrainEngine) or izh (Izhikevich)")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    parser.add_argument("--n-steps", type=int, default=300, help="Simulation steps per evaluation")
    args = parser.parse_args()

    run_sweep(
        args.fitness,
        start_idx=args.start,
        end_idx=args.end,
        model=args.model,
        output_dir=args.output_dir,
        n_steps=args.n_steps,
    )
