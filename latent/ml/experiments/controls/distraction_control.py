#!/usr/bin/env python3
"""
Distraction baseline control.

Run the UNCOMPILED brain through a distraction protocol.
If uncompiled brain also shows nav bias, distraction resistance is
Izhikevich dynamics, not the mutations.  If uncompiled brain shows no
bias or escape bias, distraction resistance is genuinely from the
6 mutations.
"""

import json
import logging
import time
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS,
    DN_NAMES,
    DT,
    GAIN,
    POISSON_RATE,
    POISSON_WEIGHT,
    STIM_LC4,
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
from compile.fitness import f_esc, f_nav
from compile.simulate import assign_neuron_types, build_weight_matrix, izh_step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Working-memory mutations from the compiled brain
WM_MUTATIONS = [
    (1, 26, 3.19),
    (11, 4, 1.92),
    (20, 0, 3.25),
    (45, 19, 2.99),
    (17, 21, 0.94),
    (24, 37, 4.80),
]


def run_distraction_protocol(
    syn_vals_local, label, *,
    pre, post, num_neurons, neuron_params, dn_names, dn_idx,
):
    """Run: 200 sugar, 200 silence, 100 distraction (lc4), 200 silence, 300 both."""
    a_t = torch.tensor(neuron_params["a"], dtype=torch.float32)
    b_t = torch.tensor(neuron_params["b"], dtype=torch.float32)
    c_t = torch.tensor(neuron_params["c"], dtype=torch.float32)
    d_t = torch.tensor(neuron_params["d"], dtype=torch.float32)

    W = build_weight_matrix(pre, post, syn_vals_local, num_neurons)

    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)
    rates = torch.zeros(1, num_neurons)

    phase_dn = {
        "P1_sugar": {n: 0 for n in dn_names},
        "P2_silence": {n: 0 for n in dn_names},
        "P3_distract": {n: 0 for n in dn_names},
        "P4_silence2": {n: 0 for n in dn_names},
        "P5_choice": {n: 0 for n in dn_names},
    }

    total_steps = 1000
    t0 = time.time()

    for step in range(total_steps):
        if step == 0:
            rates.zero_()
            for idx in STIM_SUGAR:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE
        elif step == 200:
            rates.zero_()
        elif step == 400:
            rates.zero_()
            for idx in STIM_LC4:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE
        elif step == 500:
            rates.zero_()
        elif step == 700:
            rates.zero_()
            for idx in STIM_SUGAR:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE
            for idx in STIM_LC4:
                if 0 <= idx < num_neurons:
                    rates[0, idx] = POISSON_RATE

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE
        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)

        spk = spikes.squeeze(0)
        current_phase = (
            "P1_sugar" if step < 200
            else "P2_silence" if step < 400
            else "P3_distract" if step < 500
            else "P4_silence2" if step < 700
            else "P5_choice"
        )
        for j, n in enumerate(dn_names):
            phase_dn[current_phase][n] += int(spk[dn_idx[j]].item())

    elapsed = time.time() - t0

    p5_nav = f_nav(phase_dn["P5_choice"])
    p5_esc = f_esc(phase_dn["P5_choice"])
    bias = p5_nav / max(p5_esc, 1)

    logger.info("  %s (%.1fs):", label, elapsed)
    for pname in ["P1_sugar", "P2_silence", "P3_distract", "P4_silence2", "P5_choice"]:
        logger.info(
            "    %s: nav=%d esc=%d",
            pname, f_nav(phase_dn[pname]), f_esc(phase_dn[pname]),
        )

    return p5_nav, p5_esc, bias


def main():
    logger.info("=" * 60)
    logger.info("DISTRACTION BASELINE CONTROL")
    logger.info("=" * 60)

    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    labels = load_module_labels()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    neuron_params = assign_neuron_types(
        num_neurons, neuron_ids, maps["rid_to_nt"], maps["rid_to_class"],
    )

    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    dn_names = DN_NAMES
    dn_idx = [DN_NEURONS[n] for n in dn_names]

    # Build edge index for applying mutations
    edge_syn_idx, _ = build_edge_synapse_index(df_conn, labels)

    # Build weight matrices
    syn_base = torch.tensor(vals * GAIN, dtype=torch.float32)

    # Compiled brain (with 6 WM mutations)
    syn_compiled = syn_base.clone()
    for src, tgt, scale in WM_MUTATIONS:
        edge = (src, tgt)
        if edge in edge_syn_idx:
            syn_compiled[edge_syn_idx[edge]] *= scale

    sim_kwargs = dict(
        pre=pre, post=post, num_neurons=num_neurons,
        neuron_params=neuron_params, dn_names=dn_names, dn_idx=dn_idx,
    )

    logger.info("TEST 1: UNCOMPILED BRAIN (baseline, no mutations)")
    uncomp_nav, uncomp_esc, uncomp_bias = run_distraction_protocol(
        syn_base, "UNCOMPILED", **sim_kwargs,
    )

    logger.info("TEST 2: COMPILED BRAIN (6 WM mutations applied)")
    comp_nav, comp_esc, comp_bias = run_distraction_protocol(
        syn_compiled, "COMPILED", **sim_kwargs,
    )

    logger.info("VERDICT")
    logger.info(
        "Uncompiled: nav=%d, esc=%d, bias=%.1fx", uncomp_nav, uncomp_esc, uncomp_bias,
    )
    logger.info(
        "Compiled:   nav=%d, esc=%d, bias=%.1fx", comp_nav, comp_esc, comp_bias,
    )

    if uncomp_bias > 2.0:
        logger.info(">>> DISTRACTION RESISTANCE IS A PROPERTY OF IZHIKEVICH DYNAMICS.")
    elif comp_bias > 2.0 and uncomp_bias < 1.5:
        logger.info(">>> DISTRACTION RESISTANCE IS GENUINE.")
    else:
        logger.info(">>> AMBIGUOUS. Uncompiled: %.1fx, Compiled: %.1fx.", uncomp_bias, comp_bias)

    logger.info("DONE.")


if __name__ == "__main__":
    main()
