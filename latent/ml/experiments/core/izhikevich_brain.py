#!/usr/bin/env python3
"""
Izhikevich Brain Engine -- demo / integration test.

The actual model implementation now lives in ``compile.simulate``.  This script
is a thin wrapper that imports the shared engine and runs the three standard
validation tests:

  1. Baseline (no stimulus, 500 steps) -- spontaneous activity check
  2. Sugar stimulus (500 steps) -- verify DN neuron activation
  3. Persistence (200 steps stimulus, then 500 steps silence) -- attractor test

Run directly to verify the engine is working::

    python izhikevich_brain.py
    python izhikevich_brain.py --device cuda  # GPU test
    python izhikevich_brain.py --steps 1000   # longer simulation

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import logging
import time

import torch

from compile.simulate import IzhikevichBrainEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

def test_baseline(brain, n_steps: int = 500):
    """Test 1: baseline activity with no stimulus."""
    logger.info("--- Test 1: Baseline (no stimulus, %d steps) ---", n_steps)
    brain.state = brain.model.state_init()
    brain.rates.zero_()
    brain._spike_acc.zero_()

    t0 = time.time()
    total_spikes = 0.0
    for _ in range(n_steps):
        brain.step()
        total_spikes += brain.state[2].sum().item()
    elapsed = time.time() - t0
    logger.info("  Spontaneous spikes: %.0f in %.1fs", total_spikes, elapsed)
    return total_spikes


def test_sugar(brain, n_steps: int = 500):
    """Test 2: sugar stimulus activation."""
    logger.info("--- Test 2: Sugar stimulus (%d steps) ---", n_steps)
    brain.state = brain.model.state_init()
    brain.set_stimulus("sugar")
    brain._spike_acc.zero_()

    total_spikes = 0.0
    dn_total = {}
    for _ in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        total_spikes += spk.sum().item()
        for name, idx in brain.dn_indices.items():
            dn_total[name] = dn_total.get(name, 0) + int(spk[idx].item())

    logger.info("  Total spikes: %.0f", total_spikes)
    active_dn = {k: v for k, v in sorted(dn_total.items()) if v > 0}
    logger.info("  DN spikes: %s", active_dn)
    return dn_total


def test_persistence(brain, stim_steps: int = 200, post_steps: int = 500, window: int = 50):
    """Test 3: persistence -- stimulus then silence."""
    logger.info(
        "--- Test 3: PERSISTENCE (%d steps stimulus, then %d steps silence) ---",
        stim_steps, post_steps,
    )
    brain.state = brain.model.state_init()
    brain.set_stimulus("sugar")

    stim_spikes = 0.0
    for _ in range(stim_steps):
        brain.step()
        stim_spikes += brain.state[2].sum().item()
    logger.info("  During stimulus: %.0f total spikes", stim_spikes)

    # Remove stimulus
    brain.rates.zero_()
    n_windows = post_steps // window
    post_windows = []
    for w in range(n_windows):
        window_spikes = 0.0
        for _ in range(window):
            brain.step()
            window_spikes += brain.state[2].sum().item()
        post_windows.append(window_spikes)
        status = "ACTIVE" if window_spikes > 5 else "silent"
        logger.info(
            "  Post-stimulus %d-%d: %.0f spikes [%s]",
            w * window, (w + 1) * window, window_spikes, status,
        )

    if post_windows[-1] > 5:
        logger.info("  >>> PERSISTENT ACTIVITY DETECTED! Attractor dynamics working!")
    elif any(w > 5 for w in post_windows[3:]):
        logger.info("  >>> DELAYED PERSISTENCE -- recurrent reverberation present")
    else:
        decay = next((i * window for i, w in enumerate(post_windows) if w < 2), post_steps)
        logger.info("  >>> Activity decayed after ~%d steps", decay)

    return post_windows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Izhikevich Brain Engine -- validation tests")
    parser.add_argument("--device", default="cpu", help="Device: cpu or cuda")
    parser.add_argument("--steps", type=int, default=500, help="Steps per test phase")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("=" * 60)
    logger.info("IZHIKEVICH BRAIN ENGINE TEST")
    logger.info("=" * 60)

    brain = IzhikevichBrainEngine(device=args.device)

    test_baseline(brain, n_steps=args.steps)
    test_sugar(brain, n_steps=args.steps)
    test_persistence(brain, stim_steps=min(200, args.steps), post_steps=args.steps)

    logger.info("DONE.")


if __name__ == "__main__":
    main()
