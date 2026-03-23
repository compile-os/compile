#!/usr/bin/env python3
"""
Experiment 2: Plasticity training.

Can the processor LEARN through Hebbian plasticity?  Present training
pairs (stimulus + desired DN output).  Then present stimulus alone.
Does the circuit produce the trained output?
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import torch

from compile.constants import DN_NEURONS, DN_NAMES, DT, GAIN, POISSON_RATE, POISSON_WEIGHT, STIM_SUGAR, W_SCALE
from compile.data import build_annotation_maps, load_annotations, load_connectome, load_module_labels
from compile.fitness import f_nav
from compile.simulate import assign_neuron_types, izh_step

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HEBB_LR = 0.001
HEBB_MAX = 3.0


def build_subcircuit(df_conn, df_comp, labels, neuron_ids, maps, fraction=0.2):
    """Build a subcircuit at given fraction of processor modules."""
    _conflict_mods = {40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41}
    _dn_mods = {int(labels[DN_NEURONS[n]]) for n in DN_NEURONS}
    _stim_mods = {int(labels[i]) for i in STIM_SUGAR}
    all_mods = sorted(_conflict_mods | _dn_mods | _stim_mods)

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    rng = np.random.RandomState(42)
    essential_set = set(DN_NEURONS.values()) | set(STIM_SUGAR)
    keep_neurons = []
    for mod in all_mods:
        neurons = np.where(labels == mod)[0]
        n_keep = max(1, int(len(neurons) * fraction))
        mod_essential = [n for n in neurons if n in essential_set]
        non_essential = [n for n in neurons if n not in essential_set]
        rng.shuffle(non_essential)
        keep = sorted(set(mod_essential) | set(non_essential[:max(0, n_keep - len(mod_essential))]))
        keep_neurons.extend(keep)

    keep_set = set(keep_neurons)
    keep_neurons = sorted(keep_set)
    n_sub = len(keep_neurons)
    old_to_new = {old: new for new, old in enumerate(keep_neurons)}

    mask = np.array([pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(df_conn))])
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
    vals_sub = vals_full[mask] * GAIN

    neuron_params = assign_neuron_types(
        n_sub, [neuron_ids[keep_neurons[i]] for i in range(n_sub)],
        maps["rid_to_nt"], maps["rid_to_class"],
    )

    dn_new = {nm: old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in old_to_new}
    stim_new = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
    nav_dn = [dn_new[n] for n in ["P9_left", "P9_right", "MN9_left", "MN9_right",
                                     "P9_oDN1_left", "P9_oDN1_right"] if n in dn_new]

    return n_sub, pre_sub, post_sub, vals_sub, neuron_params, dn_new, stim_new, nav_dn


def run_with_plasticity(syn_vals, stim_indices, reinforce_indices, n_steps,
                        n_sub, pre_sub, post_sub, neuron_params, dn_new,
                        plasticity=True):
    """Run simulation with optional Hebbian plasticity."""
    a_t = torch.tensor(neuron_params["a"])
    b_t = torch.tensor(neuron_params["b"])
    c_t = torch.tensor(neuron_params["c"])
    d_t = torch.tensor(neuron_params["d"])

    W_vals = syn_vals.clone()
    v = torch.full((1, n_sub), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_sub)
    rates = torch.zeros(1, n_sub)
    for idx in stim_indices:
        rates[0, idx] = POISSON_RATE

    reinforce_rates = torch.zeros(1, n_sub)
    if reinforce_indices:
        for idx in reinforce_indices:
            reinforce_rates[0, idx] = POISSON_RATE * 2

    dn_names = DN_NAMES
    dn_total = {n: 0 for n in dn_names}
    dn_idx_list = [dn_new.get(n, -1) for n in dn_names]

    pre_t = torch.tensor(pre_sub, dtype=torch.long)
    post_t = torch.tensor(post_sub, dtype=torch.long)
    orig_abs = W_vals.abs().clamp(min=0.01)

    for step in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        reinforce = (torch.rand_like(reinforce_rates) < reinforce_rates * DT / 1000.0).float()

        W = torch.sparse_coo_tensor(
            torch.stack([post_t, pre_t]), W_vals, (n_sub, n_sub), dtype=torch.float32,
        ).to_sparse_csr()

        I = (poisson + reinforce) * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE
        v_n, u_n, fired = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)
        v_n = torch.clamp(v_n, -100.0, 30.0)

        if plasticity and step % 10 == 0:
            spk_flat = fired.squeeze(0)
            pre_fired = spk_flat[pre_sub] > 0
            post_fired = spk_flat[post_sub] > 0
            both = pre_fired & post_fired
            pre_only = pre_fired & ~post_fired
            W_vals[both] += HEBB_LR * orig_abs[both]
            W_vals[pre_only] -= HEBB_LR * 0.5 * orig_abs[pre_only]
            W_vals = torch.clamp(W_vals, -HEBB_MAX * orig_abs, HEBB_MAX * orig_abs)

        v, u, spikes = v_n, u_n, fired
        spk = spikes.squeeze(0)
        for j in range(len(dn_names)):
            if dn_idx_list[j] >= 0:
                dn_total[dn_names[j]] += int(spk[dn_idx_list[j]].item())

    return dn_total, W_vals


def main():
    parser = argparse.ArgumentParser(description="Plasticity training experiment")
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PLASTICITY TRAINING EXPERIMENT")
    logger.info("=" * 60)

    df_conn, df_comp, _ = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    n_sub, pre_sub, post_sub, vals_sub, neuron_params, dn_new, stim_new, nav_dn = \
        build_subcircuit(df_conn, df_comp, labels, neuron_ids, maps, fraction=0.2)
    logger.info("Subcircuit: %d neurons, %d synapses", n_sub, len(pre_sub))

    sim_kwargs = dict(n_sub=n_sub, pre_sub=pre_sub, post_sub=post_sub,
                      neuron_params=neuron_params, dn_new=dn_new)

    syn_vals_base = torch.tensor(vals_sub, dtype=torch.float32)
    dn_baseline, _ = run_with_plasticity(syn_vals_base.clone(), stim_new, [], 500,
                                          plasticity=False, **sim_kwargs)
    baseline_nav = f_nav(dn_baseline)
    logger.info("Baseline nav: %.0f", baseline_nav)

    protocols = [
        {"name": "light", "reps": 10, "steps_per_rep": 100},
        {"name": "medium", "reps": 50, "steps_per_rep": 100},
        {"name": "heavy", "reps": 200, "steps_per_rep": 100},
        {"name": "intensive", "reps": 500, "steps_per_rep": 100},
    ]

    results = []
    for protocol in protocols:
        logger.info("--- Protocol: %s (%d reps x %d steps) ---",
                     protocol["name"], protocol["reps"], protocol["steps_per_rep"])
        syn_vals = syn_vals_base.clone()
        t0 = time.time()

        for rep in range(protocol["reps"]):
            _, syn_vals = run_with_plasticity(syn_vals, stim_new, nav_dn,
                                               protocol["steps_per_rep"], plasticity=True, **sim_kwargs)

        dn_trained, _ = run_with_plasticity(syn_vals.clone(), stim_new, [], 500,
                                             plasticity=False, **sim_kwargs)
        trained_nav = f_nav(dn_trained)
        improvement = (trained_nav - baseline_nav) / max(abs(baseline_nav), 1) * 100
        learned = trained_nav > baseline_nav * 1.1

        results.append({
            "protocol": protocol["name"], "reps": protocol["reps"],
            "baseline_nav": baseline_nav, "trained_nav": trained_nav,
            "improvement_pct": improvement, "learned": learned,
            "train_time": time.time() - t0,
        })
        logger.info("  Result: %.0f -> %.0f (%+.1f%%) [%s]",
                     baseline_nav, trained_nav, improvement, "LEARNED" if learned else "no change")

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "plasticity_training.json", "w") as f:
        json.dump({"results": results, "any_learned": any(r["learned"] for r in results)}, f, indent=2)
    logger.info("Saved. DONE.")


if __name__ == "__main__":
    main()
