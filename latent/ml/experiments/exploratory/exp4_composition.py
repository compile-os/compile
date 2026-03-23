#!/usr/bin/env python3
"""
Experiment 4: Composition test.

Take one circuit, evolve for navigation, evolve separately for escape,
then merge.  Tests whether biological processors snap together like Lego.
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import torch

from compile.constants import DN_NEURONS, DN_NAMES, DT, GAIN, POISSON_RATE, POISSON_WEIGHT, STIM_LC4_EXTENDED, STIM_SUGAR, W_SCALE
from compile.data import build_annotation_maps, load_annotations, load_connectome, load_module_labels
from compile.fitness import f_esc, f_nav
from compile.simulate import assign_neuron_types, run_simulation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_subcircuit(df_conn, df_comp, labels, neuron_ids, maps, fraction=0.3):
    """Build processor subcircuit at given fraction."""
    _conflict_mods = {40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41}
    _dn_mods = {int(labels[DN_NEURONS[n]]) for n in DN_NEURONS}
    _stim_mods = {int(labels[i]) for i in STIM_SUGAR + STIM_LC4_EXTENDED}
    all_mods = sorted(_conflict_mods | _dn_mods | _stim_mods)

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    rng = np.random.RandomState(42)
    essential_set = set(DN_NEURONS.values()) | set(STIM_SUGAR) | set(STIM_LC4_EXTENDED)
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
    stim_sugar_new = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
    stim_lc4_new = [old_to_new[i] for i in STIM_LC4_EXTENDED if i in old_to_new]

    # Build edge index for evolution
    sub_pre_orig = np.array([pre_full[i] for i in range(len(df_conn)) if mask[i]])
    sub_post_orig = np.array([post_full[i] for i in range(len(df_conn)) if mask[i]])
    sub_pre_mods = labels[sub_pre_orig].astype(int)
    sub_post_mods = labels[sub_post_orig].astype(int)
    edge_syn_idx = {}
    for i in range(len(pre_sub)):
        edge = (int(sub_pre_mods[i]), int(sub_post_mods[i]))
        if edge not in edge_syn_idx:
            edge_syn_idx[edge] = []
        edge_syn_idx[edge].append(i)
    inter_edges = [e for e in edge_syn_idx if e[0] != e[1]]

    return (n_sub, pre_sub, post_sub, vals_sub, neuron_params, dn_new,
            stim_sugar_new, stim_lc4_new, edge_syn_idx, inter_edges)


def run_sim(pre, post, vals, stim_indices, n_sub, neuron_params, dn_new, n_steps=500):
    """Run simulation and return DN spike dict."""
    syn_vals = torch.tensor(vals, dtype=torch.float32) if not isinstance(vals, torch.Tensor) else vals
    return run_simulation(syn_vals, pre, post, n_sub, neuron_params, stim_indices, dn_new, n_steps=n_steps)


def main():
    parser = argparse.ArgumentParser(description="Composition test: two processors, one system")
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("COMPOSITION TEST: Two processors, one system")
    logger.info("=" * 60)

    df_conn, df_comp, _ = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    (n_sub, pre_sub, post_sub, vals_sub, neuron_params, dn_new,
     stim_sugar_new, stim_lc4_new, edge_syn_idx, inter_edges) = \
        build_subcircuit(df_conn, df_comp, labels, neuron_ids, maps)
    logger.info("Circuit: %d neurons, %d synapses", n_sub, len(pre_sub))

    syn_vals_base = torch.tensor(vals_sub, dtype=torch.float32)

    # Phase 1: Baselines
    dn_nav = run_sim(pre_sub, post_sub, syn_vals_base, stim_sugar_new, n_sub, neuron_params, dn_new)
    nav_bl = f_nav(dn_nav)
    dn_esc = run_sim(pre_sub, post_sub, syn_vals_base, stim_lc4_new, n_sub, neuron_params, dn_new)
    esc_bl = f_esc(dn_esc)
    logger.info("Sugar: nav=%.0f, LC4: esc=%.0f", nav_bl, esc_bl)

    # Phase 2: Evolve for navigation
    logger.info("Evolving for navigation (15 gen)...")
    np.random.seed(42)
    best_nav = syn_vals_base.clone()
    current_nav_fit = nav_bl
    for gen in range(15):
        for mi in range(10):
            edge = inter_edges[np.random.randint(len(inter_edges))]
            syns = edge_syn_idx[edge]
            old = best_nav[syns].clone()
            scale = np.random.uniform(0.5, 4.0)
            test = best_nav.clone()
            test[syns] = old * scale
            dn = run_sim(pre_sub, post_sub, test, stim_sugar_new, n_sub, neuron_params, dn_new)
            fit = f_nav(dn)
            if fit > current_nav_fit:
                current_nav_fit = fit
                best_nav[syns] = old * scale
    logger.info("Nav evolved: %.0f -> %.0f", nav_bl, current_nav_fit)

    # Phase 3: Evolve for escape
    logger.info("Evolving for escape (15 gen)...")
    np.random.seed(123)
    best_esc = syn_vals_base.clone()
    current_esc_fit = esc_bl
    for gen in range(15):
        for mi in range(10):
            edge = inter_edges[np.random.randint(len(inter_edges))]
            syns = edge_syn_idx[edge]
            old = best_esc[syns].clone()
            scale = np.random.uniform(0.5, 4.0)
            test = best_esc.clone()
            test[syns] = old * scale
            dn = run_sim(pre_sub, post_sub, test, stim_lc4_new, n_sub, neuron_params, dn_new)
            fit = f_esc(dn)
            if fit > current_esc_fit:
                current_esc_fit = fit
                best_esc[syns] = old * scale
    logger.info("Escape evolved: %.0f -> %.0f", esc_bl, current_esc_fit)

    # Phase 4: Compose
    composed = (best_nav + best_esc) / 2.0
    dn_comp_sugar = run_sim(pre_sub, post_sub, composed, stim_sugar_new, n_sub, neuron_params, dn_new)
    dn_comp_lc4 = run_sim(pre_sub, post_sub, composed, stim_lc4_new, n_sub, neuron_params, dn_new)
    comp_nav = f_nav(dn_comp_sugar)
    comp_esc = f_esc(dn_comp_lc4)

    logger.info("Composed: nav=%.0f, esc=%.0f", comp_nav, comp_esc)
    nav_preserved = comp_nav >= nav_bl * 0.8
    esc_preserved = comp_esc >= esc_bl * 0.8

    if nav_preserved and esc_preserved:
        logger.info(">>> COMPOSITION WORKS. Both behaviors preserved.")
    elif nav_preserved or esc_preserved:
        logger.info(">>> PARTIAL COMPOSITION.")
    else:
        logger.info(">>> COMPOSITION FAILED.")

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "composition_test.json", "w") as f:
        json.dump({
            "baseline_nav": nav_bl, "baseline_esc": esc_bl,
            "evolved_nav": current_nav_fit, "evolved_esc": current_esc_fit,
            "composed_nav": comp_nav, "composed_esc": comp_esc,
            "nav_preserved": nav_preserved, "esc_preserved": esc_preserved,
        }, f, indent=2)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
