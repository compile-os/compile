#!/usr/bin/env python3
"""
Critical controls that must pass before publishing.

Control 1: Random neuron selection baseline for gene-guided extraction.
    Does a RANDOM selection of 8,158 neurons perform similarly to gene-guided?
    If yes: "cell type specification is sufficient" is FALSE.

Control 2: Edge sweep at different perturbation scales.
    Do the same edges classify as evolvable at 1.5x and 3x as they do at 2x?
    If no: classification depends on arbitrary scale choice.
"""

import json
import logging
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS,
    DN_NAMES,
    GAIN,
    DT,
    POISSON_RATE,
    POISSON_WEIGHT,
    SIGNATURE_HEMIS,
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
from compile.fitness import f_nav
from compile.simulate import assign_neuron_types, build_weight_matrix, izh_step, run_simulation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def build_circuit(
    neuron_list,
    pre_full,
    post_full,
    vals_full,
    neuron_ids,
    rid_to_nt,
    rid_to_class,
    num_neurons_full,
):
    """Build Izhikevich circuit from neuron list and return nav score."""
    keep = sorted(set(neuron_list))
    keep_set = set(keep)
    n = len(keep)
    old_to_new = {old: new for new, old in enumerate(keep)}

    mask = np.array(
        [pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(pre_full))]
    )
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(pre_full)) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(len(pre_full)) if mask[i]])
    vals_sub = vals_full[mask] * GAIN
    n_syn = len(pre_sub)

    if n_syn == 0:
        return 0, n, n_syn

    # Build neuron params for subcircuit
    neuron_params = assign_neuron_types(
        n,
        [neuron_ids[keep[i]] for i in range(n)],
        rid_to_nt,
        rid_to_class,
    )

    # Map DN and stimulus indices into subcircuit
    dn_indices = {nm: old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in old_to_new}
    stim_indices = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]

    syn_vals = torch.tensor(vals_sub, dtype=torch.float32)
    dn_total = run_simulation(
        syn_vals, pre_sub, post_sub, n, neuron_params,
        stim_indices, dn_indices, n_steps=500,
    )

    nav = f_nav(dn_total)
    return int(nav), n, n_syn


def run_control1(
    neuron_ids, rid_to_hemi, rid_to_nt, rid_to_class,
    pre_full, post_full, vals_full, num_neurons,
):
    """Control 1: Gene-guided vs random neuron selection."""
    logger.info("=" * 60)
    logger.info("CONTROL 1: Gene-guided vs Random neuron selection")
    logger.info("=" * 60)

    essential_io = set(DN_NEURONS.values()) | set(STIM_SUGAR)

    # Gene-guided selection
    gene_neurons = []
    for idx, nid in enumerate(neuron_ids):
        if rid_to_hemi.get(nid, "unknown") in SIGNATURE_HEMIS or idx in essential_io:
            gene_neurons.append(idx)
    gene_neurons = sorted(set(gene_neurons))
    n_gene = len(gene_neurons)

    t0 = time.time()
    gene_nav, gene_n, gene_syn = build_circuit(
        gene_neurons, pre_full, post_full, vals_full,
        neuron_ids, rid_to_nt, rid_to_class, num_neurons,
    )
    logger.info(
        "Gene-guided: %d neurons, %d synapses, nav=%d (%.1fs)",
        gene_n, gene_syn, gene_nav, time.time() - t0,
    )

    # Random selections (5 trials, same size as gene-guided)
    random_navs = []
    for trial in range(5):
        rng = np.random.RandomState(trial)
        non_essential = [i for i in range(num_neurons) if i not in essential_io]
        random_pick = (
            list(essential_io)
            + rng.choice(non_essential, n_gene - len(essential_io), replace=False).tolist()
        )
        t0 = time.time()
        rand_nav, rand_n, rand_syn = build_circuit(
            random_pick, pre_full, post_full, vals_full,
            neuron_ids, rid_to_nt, rid_to_class, num_neurons,
        )
        random_navs.append(rand_nav)
        logger.info(
            "Random %d: %d neurons, %d synapses, nav=%d (%.1fs)",
            trial, rand_n, rand_syn, rand_nav, time.time() - t0,
        )

    mean_random = np.mean(random_navs)
    std_random = np.std(random_navs)
    logger.info("Gene-guided nav:  %d", gene_nav)
    logger.info("Random mean nav:  %.1f +/- %.1f", mean_random, std_random)
    logger.info("Random range:     %d - %d", min(random_navs), max(random_navs))

    significantly_better = bool(gene_nav > mean_random + 2 * std_random)
    if significantly_better:
        logger.info(">>> GENE-GUIDED IS SIGNIFICANTLY BETTER. Cell type selection matters.")
    elif gene_nav > mean_random:
        logger.info(">>> Gene-guided is better but NOT significantly (within 2 std).")
    else:
        logger.info(">>> GENE-GUIDED IS NOT BETTER THAN RANDOM. Cell type claim is FALSE.")

    return {
        "gene_nav": gene_nav,
        "random_navs": random_navs,
        "random_mean": float(mean_random),
        "random_std": float(std_random),
        "gene_significantly_better": significantly_better,
    }


def run_control2(df_conn, labels, num_neurons):
    """Control 2: Edge sweep at multiple perturbation scales.

    Uses BrainEngine (LIF model) if available, falls back to
    IzhikevichBrainEngine from compile.simulate.
    """
    logger.info("=" * 60)
    logger.info("CONTROL 2: Edge sweep scale sensitivity")
    logger.info("=" * 60)

    # Try BrainEngine first; fall back to IzhikevichBrainEngine
    try:
        from brain_body_bridge import BrainEngine
        brain = BrainEngine(device="cpu")
        logger.info("Using LIF BrainEngine")
    except ImportError:
        from compile.simulate import IzhikevichBrainEngine
        brain = IzhikevichBrainEngine(device="cpu")
        logger.info("Using IzhikevichBrainEngine (BrainEngine not available)")

    brain._syn_vals.mul_(GAIN)
    baseline_weights = brain._syn_vals.clone()

    edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)
    inter_edges = sorted(inter_module_edges)

    def evaluate_nav(brain_eng, stim="sugar", n_steps=300):
        brain_eng.state = brain_eng.model.state_init()
        brain_eng.rates = torch.zeros(1, brain_eng.num_neurons, device=brain_eng.device)
        brain_eng._spike_acc.zero_()
        brain_eng._hebb_count = 0
        brain_eng.set_stimulus(stim)
        dn_spikes = {name: 0 for name in brain_eng.dn_indices}
        for _ in range(n_steps):
            brain_eng.step()
            spk = brain_eng.state[2].squeeze(0)
            for name, idx in brain_eng.dn_indices.items():
                dn_spikes[name] += int(spk[idx].item())
        return int(f_nav(dn_spikes))

    brain._syn_vals.copy_(baseline_weights)
    baseline = evaluate_nav(brain)
    logger.info("Baseline nav: %d", baseline)

    scales = [1.5, 2.0, 3.0, 5.0]
    rng = np.random.RandomState(42)
    test_edges = [inter_edges[i] for i in rng.choice(len(inter_edges), 50, replace=False)]

    classifications = {s: [] for s in scales}
    for edge in test_edges:
        syns = edge_syn_idx[edge]
        for scale in scales:
            brain._syn_vals.copy_(baseline_weights)
            brain._syn_vals[syns] *= scale
            fit = evaluate_nav(brain)
            delta = fit - baseline
            if delta > 0:
                cls = "evolvable"
            elif delta < 0:
                cls = "frozen"
            else:
                cls = "irrelevant"
            classifications[scale].append(cls)

    logger.info("Classification consistency across scales (50 edges):")
    logger.info("  %6s %8s %10s %11s", "Scale", "Frozen", "Evolvable", "Irrelevant")
    for s in scales:
        counts = Counter(classifications[s])
        logger.info(
            "  %5.1fx %8d %10d %11d",
            s, counts.get("frozen", 0), counts.get("evolvable", 0), counts.get("irrelevant", 0),
        )

    for s in scales:
        if s == 2.0:
            continue
        agree = sum(1 for a, b in zip(classifications[2.0], classifications[s]) if a == b)
        logger.info("Agreement 2x vs %.1fx: %d/50 (%.0f%%)", s, agree, 100 * agree / 50)

    return {str(s): classifications[s] for s in scales}


def main():
    logger.info("=" * 60)
    logger.info("CRITICAL CONTROLS")
    logger.info("=" * 60)

    # Load data
    df_conn, df_comp, num_neurons = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    # Control 1
    control1 = run_control1(
        neuron_ids, maps["rid_to_hemi"], maps["rid_to_nt"], maps["rid_to_class"],
        pre_full, post_full, vals_full, num_neurons,
    )

    # Control 2
    control2 = run_control2(df_conn, labels, num_neurons)

    # Save results
    outdir = Path("results/critical_controls")
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "control1_gene_nav": control1["gene_nav"],
        "control1_random_navs": control1["random_navs"],
        "control1_random_mean": control1["random_mean"],
        "control1_random_std": control1["random_std"],
        "control1_gene_significantly_better": control1["gene_significantly_better"],
        "control2_classifications": control2,
    }
    out_path = outdir / "critical_controls.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Saved to %s", out_path)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
