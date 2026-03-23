#!/usr/bin/env python3
"""
Izhikevich strategy switching experiment.

Tests whether the brain can resolve conflicting internal representations when
the stimulus changes, without resetting neural state.

  Phase 1 (steps 0-500):   Sugar stimulus -> navigation behavior
  Phase 2 (steps 500-1000): LC4 stimulus  -> escape behavior
    NO STATE RESET -- neural activity carries over

Key measurement: the CONFLICT PERIOD (steps 500-550) where persistent
"navigate" representation competes with new "escape" stimulus.  Records
full DN vector at every timestep to capture the transition dynamics, then
runs a short (1+1) ES evolution to optimize switching fitness.

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
    DN_NEURONS, DN_NAMES, STIM_SUGAR, STIM_LC4_EXTENDED,
    DT, W_SCALE, GAIN, POISSON_WEIGHT, POISSON_RATE,
)
from compile.data import (
    load_connectome, load_annotations, load_module_labels,
    build_annotation_maps, build_edge_synapse_index,
)
from compile.simulate import assign_neuron_types, build_weight_matrix, izh_step
from compile.stats import bootstrap_ci, improvement_with_ci

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------

STIM = {
    "sugar": STIM_SUGAR,
    "lc4": STIM_LC4_EXTENDED,
}


def _load_simulation_data():
    """Load connectome, annotations, and build neuron parameters."""
    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    maps = build_annotation_maps(ann)
    neuron_ids = df_comp.index.astype(str).tolist()

    neuron_params = assign_neuron_types(
        num_neurons, neuron_ids, maps["rid_to_nt"], maps["rid_to_class"],
    )

    # Identify CX neurons for conflict analysis
    cx_neurons = []
    for idx, nid in enumerate(neuron_ids):
        cc = maps["rid_to_class"].get(nid, "")
        if isinstance(cc, str) and "CX" in cc:
            cx_neurons.append(idx)

    # Weight matrix
    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32)
    syn_vals = vals_tensor.clone()

    W = build_weight_matrix(pre, post, vals_tensor, num_neurons)

    # Edge index for evolution
    labels = load_module_labels()
    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)

    # Neuron param tensors
    a_t = torch.tensor(neuron_params["a"])
    b_t = torch.tensor(neuron_params["b"])
    c_t = torch.tensor(neuron_params["c"])
    d_t = torch.tensor(neuron_params["d"])

    dn_names = DN_NAMES
    dn_idx = [DN_NEURONS[n] for n in dn_names]

    return {
        "num_neurons": num_neurons,
        "pre": pre, "post": post,
        "syn_vals": syn_vals,
        "W": W,
        "a_t": a_t, "b_t": b_t, "c_t": c_t, "d_t": d_t,
        "cx_neurons": cx_neurons,
        "dn_names": dn_names, "dn_idx": dn_idx,
        "edge_syn_idx": edge_syn_idx,
        "inter_module_edges": inter_module_edges,
    }


# ---------------------------------------------------------------------------
# Two-phase switching simulation
# ---------------------------------------------------------------------------

def run_switching(
    data: dict,
    phase1_steps: int = 500,
    phase2_steps: int = 500,
    syn_vals_override=None,
    record_every: int = 1,
):
    """Run two-phase switching simulation. Returns per-step DN vectors + CX activity."""
    num_neurons = data["num_neurons"]
    pre, post = data["pre"], data["post"]
    a_t, b_t, c_t, d_t = data["a_t"], data["b_t"], data["c_t"], data["d_t"]
    cx_neurons = data["cx_neurons"]
    dn_names, dn_idx = data["dn_names"], data["dn_idx"]
    total_steps = phase1_steps + phase2_steps

    if syn_vals_override is not None:
        W_local = build_weight_matrix(pre, post, syn_vals_override, num_neurons)
    else:
        W_local = data["W"]

    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)
    rates = torch.zeros(1, num_neurons)

    # Phase 1: sugar
    rates[0, STIM["sugar"]] = POISSON_RATE

    dn_timeseries = []
    cx_timeseries = []
    total_timeseries = []

    for step in range(total_steps):
        # Switch stimulus at phase boundary
        if step == phase1_steps:
            rates.zero_()
            rates[0, STIM["lc4"]] = POISSON_RATE

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT
        recurrent = torch.mm(spikes, W_local.t()) * W_SCALE
        I = poisson_current + recurrent

        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)

        if step % record_every == 0:
            spk = spikes.squeeze(0)
            dn_vec = [int(spk[dn_idx[j]].item()) for j in range(len(dn_names))]
            cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
            dn_timeseries.append(dn_vec)
            cx_timeseries.append(cx_spk)
            total_timeseries.append(int(spk.sum().item()))

    return np.array(dn_timeseries), np.array(cx_timeseries), np.array(total_timeseries)


# ---------------------------------------------------------------------------
# Fitness functions (timeseries-based, unique to this experiment)
# ---------------------------------------------------------------------------

def fitness_nav_ts(dn_ts, dn_names, start, end):
    """Navigation score: P9 + MN9 during [start:end]."""
    p9_idx = [i for i, n in enumerate(dn_names) if "P9" in n or "MN9" in n]
    return float(dn_ts[start:end, p9_idx].sum())


def fitness_escape_ts(dn_ts, dn_names, start, end):
    """Escape score: GF + MDN during [start:end]."""
    gf_idx = [i for i, n in enumerate(dn_names) if "GF" in n or "MDN" in n]
    return float(dn_ts[start:end, gf_idx].sum())


def fitness_switching(dn_ts, dn_names, phase1_steps, total_steps, conflict_end):
    """
    Strategy switching fitness.

    Fitness = min(nav, escape) + conflict_bonus, where conflict bonus rewards
    fast escape activation and penalizes lingering navigation.
    """
    nav = fitness_nav_ts(dn_ts, dn_names, 0, phase1_steps)
    esc = fitness_escape_ts(dn_ts, dn_names, phase1_steps, total_steps)

    conflict_escape = fitness_escape_ts(dn_ts, dn_names, phase1_steps, conflict_end)
    conflict_nav = fitness_nav_ts(dn_ts, dn_names, phase1_steps, conflict_end)
    conflict_bonus = conflict_escape - 0.5 * conflict_nav

    return {
        "fitness": min(nav, esc) + max(0, conflict_bonus),
        "nav": nav,
        "escape": esc,
        "conflict_escape": conflict_escape,
        "conflict_nav": conflict_nav,
        "conflict_bonus": conflict_bonus,
    }


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def _run_single_seed(
    data: dict,
    phase1_steps: int,
    phase2_steps: int,
    n_generations: int,
    n_mutations: int,
    seed: int,
):
    """Run evolution for a single seed. Returns (baseline_dict, final_dict, final_fitness, all_mutations, best_syn_vals)."""
    total_steps = phase1_steps + phase2_steps
    conflict_end = phase1_steps + 50
    dn_names = data["dn_names"]
    inter_module_edges = data["inter_module_edges"]
    edge_syn_idx = data["edge_syn_idx"]
    syn_vals = data["syn_vals"]

    # Baseline
    dn_ts, cx_ts, total_ts = run_switching(data, phase1_steps, phase2_steps)
    bl = fitness_switching(dn_ts, dn_names, phase1_steps, total_steps, conflict_end)

    # Evolution
    np.random.seed(seed)
    torch.manual_seed(seed)

    baseline_fitness = bl["fitness"]
    current_fitness = baseline_fitness
    best_syn_vals = syn_vals.clone()
    all_mutations = []
    accepted = 0

    for gen in range(n_generations):
        for mi in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syns = edge_syn_idx[edge]
            old = best_syn_vals[syns].clone()
            scale = np.random.uniform(0.5, 4.0)
            test_vals = best_syn_vals.clone()
            test_vals[syns] = old * scale

            dn_ts_t, cx_ts_t, _ = run_switching(
                data, phase1_steps, phase2_steps, syn_vals_override=test_vals,
            )
            result = fitness_switching(dn_ts_t, dn_names, phase1_steps, total_steps, conflict_end)
            new_fitness = result["fitness"]
            delta = new_fitness - current_fitness
            acc = new_fitness > current_fitness

            mutation = {
                "gen": gen, "mi": mi,
                "edge": [int(edge[0]), int(edge[1])],
                "scale": float(scale),
                "fitness": float(new_fitness),
                "delta": float(delta),
                "accepted": acc,
                "nav": result["nav"],
                "escape": result["escape"],
                "conflict_escape": result["conflict_escape"],
                "conflict_nav": result["conflict_nav"],
            }
            all_mutations.append(mutation)

            if acc:
                current_fitness = new_fitness
                best_syn_vals[syns] = old * scale
                accepted += 1
                logger.info(
                    "  [s%d] G%d M%d: %d->%d s=%.2f fit=%.1f ACCEPTED",
                    seed, gen, mi, edge[0], edge[1], scale, new_fitness,
                )

    # Final evaluation
    dn_ts_final, _, _ = run_switching(
        data, phase1_steps, phase2_steps, syn_vals_override=best_syn_vals,
    )
    final = fitness_switching(dn_ts_final, dn_names, phase1_steps, total_steps, conflict_end)

    return bl, final, current_fitness, all_mutations, best_syn_vals, dn_ts, dn_ts_final


def run_experiment(
    phase1_steps: int = 500,
    phase2_steps: int = 500,
    n_generations: int = 25,
    n_mutations: int = 10,
    seed: int = 42,
    seeds: list | None = None,
    output_dir: str = "results",
):
    """Run the full strategy switching experiment: baseline, evolution, analysis."""
    total_steps = phase1_steps + phase2_steps
    conflict_start = phase1_steps
    conflict_end = phase1_steps + 50

    data = _load_simulation_data()
    dn_names = data["dn_names"]

    run_seeds = seeds if seeds is not None else [seed]

    # ---- Run all seeds ----
    seed_results = []
    t_start = time.time()

    for s in run_seeds:
        logger.info("=" * 60)
        logger.info("SEED %d", s)
        logger.info("=" * 60)
        bl, final, final_fit, mutations, best_vals, dn_ts_bl, dn_ts_final = _run_single_seed(
            data, phase1_steps, phase2_steps, n_generations, n_mutations, s,
        )
        seed_results.append({
            "seed": s,
            "baseline": bl,
            "final": final,
            "final_fitness": final_fit,
            "mutations": mutations,
            "best_syn_vals": best_vals,
            "dn_ts_bl": dn_ts_bl,
            "dn_ts_final": dn_ts_final,
        })
        logger.info(
            "  Seed %d: baseline=%.1f -> final=%.1f",
            s, bl["fitness"], final["fitness"],
        )

    # Use the first seed's results for detailed analysis (backward compatible)
    sr0 = seed_results[0]
    bl = sr0["baseline"]
    final = sr0["final"]
    best_syn_vals = sr0["best_syn_vals"]
    all_mutations = sr0["mutations"]
    dn_ts = sr0["dn_ts_bl"]
    dn_ts_final = sr0["dn_ts_final"]

    # ---- Analysis ----
    logger.info("=" * 60)
    logger.info("RESULTS")
    logger.info("=" * 60)

    logger.info("Baseline: nav=%.1f, escape=%.1f, fitness=%.1f", bl["nav"], bl["escape"], bl["fitness"])
    logger.info("Final:    nav=%.1f, escape=%.1f, fitness=%.1f", final["nav"], final["escape"], final["fitness"])

    accepted = sum(1 for m in all_mutations if m["accepted"])
    logger.info("Accepted: %d/%d", accepted, len(all_mutations))

    acc_edges = sorted(set(tuple(m["edge"]) for m in all_mutations if m["accepted"]))
    logger.info("Evolvable edges: %d: %s", len(acc_edges), acc_edges)

    # Transition comparison
    logger.info("--- TRANSITION COMPARISON (baseline vs evolved) ---")
    logger.info("%-15s %7s %7s %7s %7s %7s %7s", "Window", "BL_nav", "BL_esc", "EV_nav", "EV_esc", "dnav", "desc")
    for w_start in range(phase1_steps - 100, phase1_steps + 100, 25):
        w_end = min(w_start + 25, total_steps)
        bl_nav = fitness_nav_ts(dn_ts, dn_names, w_start, w_end)
        bl_esc = fitness_escape_ts(dn_ts, dn_names, w_start, w_end)
        ev_nav = fitness_nav_ts(dn_ts_final, dn_names, w_start, w_end)
        ev_esc = fitness_escape_ts(dn_ts_final, dn_names, w_start, w_end)
        logger.info(
            "  %d-%d %7.0f %7.0f %7.0f %7.0f %+7.0f %+7.0f",
            w_start, w_end, bl_nav, bl_esc, ev_nav, ev_esc,
            ev_nav - bl_nav, ev_esc - bl_esc,
        )

    # Conflict analysis
    logger.info("--- CONFLICT ANALYSIS ---")
    conflict_dn = dn_ts_final[conflict_start:conflict_end]
    nav_active = conflict_dn[:, [i for i, n in enumerate(dn_names) if "P9" in n or "MN9" in n]].sum(axis=1) > 0
    esc_active = conflict_dn[:, [i for i, n in enumerate(dn_names) if "GF" in n or "MDN" in n]].sum(axis=1) > 0
    both_active = nav_active & esc_active
    logger.info("Conflict period (steps %d-%d):", conflict_start, conflict_end)
    logger.info("  Nav DNs active: %d/%d steps", nav_active.sum(), len(nav_active))
    logger.info("  Escape DNs active: %d/%d steps", esc_active.sum(), len(esc_active))
    logger.info("  BOTH active simultaneously: %d/%d steps", both_active.sum(), len(both_active))
    if both_active.sum() > 5:
        logger.info("  >>> CONFLICT SIGNATURE DETECTED: competing representations coexist")
    else:
        logger.info("  >>> No conflict: transition is instant (stimulus-dominated)")

    # ---- Statistical summary across seeds ----
    logger.info("=" * 60)
    logger.info("STATISTICAL SUMMARY (%d seeds)", len(seed_results))
    logger.info("=" * 60)

    baseline_fitness = bl["fitness"]
    seed_fitnesses = np.array([sr["final_fitness"] for sr in seed_results])

    pt, ci_lo, ci_hi = bootstrap_ci(seed_fitnesses)
    logger.info(
        "Final switching fitness: %.1f [95%% CI: %.1f, %.1f]",
        pt, ci_lo, ci_hi,
    )

    imp = improvement_with_ci(baseline_fitness, seed_fitnesses)
    logger.info(
        "Improvement over baseline (%.1f): %.1f%% [95%% CI: %.1f%%, %.1f%%]",
        baseline_fitness, imp["improvement_pct"], imp["ci_lower_pct"], imp["ci_upper_pct"],
    )

    # Per-component CIs
    seed_navs = np.array([sr["final"]["nav"] for sr in seed_results])
    seed_escs = np.array([sr["final"]["escape"] for sr in seed_results])
    nav_pt, nav_lo, nav_hi = bootstrap_ci(seed_navs)
    esc_pt, esc_lo, esc_hi = bootstrap_ci(seed_escs)
    logger.info(
        "Nav component: %.1f [95%% CI: %.1f, %.1f]", nav_pt, nav_lo, nav_hi,
    )
    logger.info(
        "Escape component: %.1f [95%% CI: %.1f, %.1f]", esc_pt, esc_lo, esc_hi,
    )

    stats_output = {
        "n_seeds": len(seed_results),
        "seed_fitnesses": seed_fitnesses.tolist(),
        "fitness_mean_ci": [float(pt), float(ci_lo), float(ci_hi)],
        "improvement_pct": float(imp["improvement_pct"]),
        "improvement_pct_ci": [float(imp["ci_lower_pct"]), float(imp["ci_upper_pct"])],
        "nav_ci": [float(nav_pt), float(nav_lo), float(nav_hi)],
        "escape_ci": [float(esc_pt), float(esc_lo), float(esc_hi)],
    }

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "izhikevich_strategy_switching",
        "baseline": bl,
        "final": final,
        "accepted_edges": acc_edges,
        "total_accepted": accepted,
        "total_mutations": len(all_mutations),
        "mutations": all_mutations,
        "dn_names": dn_names,
        "conflict_both_active_steps": int(both_active.sum()),
        "statistics": stats_output,
    }
    out_path = outdir / "izh_strategy_switching.json"
    with open(out_path, "w") as f:
        json.dump(output, f)
    logger.info("Saved to %s", out_path)
    logger.info("Total time: %.0fs", time.time() - t_start)

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

    parser = argparse.ArgumentParser(description="Izhikevich strategy switching experiment")
    parser.add_argument("--phase1-steps", type=int, default=500, help="Steps for navigation phase")
    parser.add_argument("--phase2-steps", type=int, default=500, help="Steps for escape phase")
    parser.add_argument("--generations", type=int, default=25)
    parser.add_argument("--mutations", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=int, nargs="+", default=None,
                        help="Multiple seeds for cross-seed statistics (overrides --seed)")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    run_experiment(
        phase1_steps=args.phase1_steps,
        phase2_steps=args.phase2_steps,
        n_generations=args.generations,
        n_mutations=args.mutations,
        seed=args.seed,
        seeds=args.seeds,
        output_dir=args.output_dir,
    )
