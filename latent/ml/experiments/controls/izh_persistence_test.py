#!/usr/bin/env python3
"""
Izhikevich persistence test.

Gate experiment: does the central complex sustain activity after input
removal?  Tests whether IB (Intrinsically Bursting) neurons assigned
to CX cell classes produce attractor dynamics and persistent activity.
"""

import logging
import time

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS,
    DT,
    GAIN,
    NEURON_TYPES,
    POISSON_RATE,
    POISSON_WEIGHT,
    STIM_JO_EXTENDED,
    STIM_LC4,
    STIM_SUGAR,
    W_SCALE,
)
from compile.data import (
    build_annotation_maps,
    load_annotations,
    load_connectome,
)
from compile.simulate import assign_neuron_types, build_weight_matrix, izh_step

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

STIM = {
    "sugar": STIM_SUGAR,
    "lc4": STIM_LC4,
    "jo": STIM_JO_EXTENDED,
}


def run_persistence_simulation(
    stim_name, stim_steps, post_steps, *,
    W, neuron_params, num_neurons, cx_neurons, device="cpu",
):
    """Run stimulus then silence, return per-step activity."""
    a_t = torch.tensor(neuron_params["a"], device=device)
    b_t = torch.tensor(neuron_params["b"], device=device)
    c_t = torch.tensor(neuron_params["c"], device=device)
    d_t = torch.tensor(neuron_params["d"], device=device)

    v = torch.full((1, num_neurons), -65.0, device=device)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons, device=device)
    rates = torch.zeros(1, num_neurons, device=device)

    if stim_name in STIM:
        for idx in STIM[stim_name]:
            if 0 <= idx < num_neurons:
                rates[0, idx] = POISSON_RATE

    cx_activity = []
    dn_activity = []
    total_activity = []
    total_steps = stim_steps + post_steps

    for step in range(total_steps):
        if step == stim_steps:
            rates.zero_()

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT
        recurrent = torch.mm(spikes, W.t()) * W_SCALE
        I = poisson_current + recurrent

        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)

        spk = spikes.squeeze(0)
        cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
        dn_spk = sum(int(spk[DN_NEURONS[name]].item()) for name in DN_NEURONS)
        total_spk = int(spk.sum().item())

        cx_activity.append(cx_spk)
        dn_activity.append(dn_spk)
        total_activity.append(total_spk)

    return cx_activity, dn_activity, total_activity


def main():
    logger.info("=" * 60)
    logger.info("IZHIKEVICH PERSISTENCE TEST")
    logger.info("=" * 60)

    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()
    maps = build_annotation_maps(ann)

    neuron_params = assign_neuron_types(
        num_neurons, neuron_ids, maps["rid_to_nt"], maps["rid_to_class"],
    )

    # Identify CX neurons for monitoring
    cx_neurons = []
    for idx, nid in enumerate(neuron_ids):
        cc = maps["rid_to_class"].get(nid, "")
        if isinstance(cc, str) and "CX" in cc:
            cx_neurons.append(idx)
    logger.info("CX neurons for monitoring: %d", len(cx_neurons))

    # Build weight matrix
    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32)

    W = build_weight_matrix(pre, post, vals_tensor, num_neurons)

    # Run for each stimulus
    for stim_name in ["lc4", "sugar", "jo"]:
        logger.info("=" * 60)
        logger.info("STIMULUS: %s", stim_name)
        logger.info("=" * 60)

        t0 = time.time()
        cx, dn, total = run_persistence_simulation(
            stim_name, stim_steps=200, post_steps=500,
            W=W, neuron_params=neuron_params,
            num_neurons=num_neurons, cx_neurons=cx_neurons,
        )
        elapsed = time.time() - t0

        stim_cx = cx[:200]
        stim_dn = dn[:200]
        stim_total = total[:200]
        logger.info("Stim phase (200 steps, %.1fs):", elapsed)
        logger.info("  CX: %d total, %.2f/step", sum(stim_cx), np.mean(stim_cx))
        logger.info("  DN: %d total", sum(stim_dn))
        logger.info("  All: %d total, %.1f/step", sum(stim_total), np.mean(stim_total))

        post_cx = cx[200:]
        post_dn = dn[200:]
        post_total = total[200:]

        logger.info("Post-stimulus activity (50-step windows):")
        for w in range(10):
            w_cx = post_cx[w * 50 : (w + 1) * 50]
            w_dn = post_dn[w * 50 : (w + 1) * 50]
            w_total = post_total[w * 50 : (w + 1) * 50]
            cx_mean = np.mean(w_cx)
            status = "ACTIVE" if cx_mean > 0.5 else "silent"
            logger.info(
                "  Steps %d-%d: CX=%d, DN=%d, Total=%d, CX/step=%.2f [%s]",
                w * 50, (w + 1) * 50, sum(w_cx), sum(w_dn), sum(w_total), cx_mean, status,
            )

        last_window_cx = np.mean(post_cx[-50:])
        mid_window_cx = np.mean(post_cx[200:250])

        if last_window_cx > 1.0:
            logger.info(">>> PERSISTENT ACTIVITY! CX=%.2f/step after 500 steps", last_window_cx)
            logger.info(">>> ATTRACTOR DYNAMICS CONFIRMED")
        elif mid_window_cx > 0.5:
            logger.info(
                ">>> PARTIAL PERSISTENCE: CX active at 200 steps (%.2f), decayed by 500 (%.2f)",
                mid_window_cx, last_window_cx,
            )
        else:
            logger.info(">>> NO PERSISTENCE: CX died quickly (%.2f/step at end)", last_window_cx)

    logger.info("PERSISTENCE TEST COMPLETE")


if __name__ == "__main__":
    main()
