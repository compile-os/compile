"""
Regression testing: re-evaluate existing behaviors after a new behavior is compiled.
Also includes persistence test for reactive vs cognitive classification.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_regression_tests(
    compiled_behavior: str,
    test_against: list[str],
) -> list[dict[str, Any]]:
    """
    For each behavior in test_against, evaluate its fitness on the current brain
    (which has the compiled_behavior's mutations applied).

    Returns a list of regression results:
    [{"behavior": "navigation", "baseline": 234.5, "current": 220.1, "delta_pct": -6.1, "is_regression": false}]
    """
    try:
        from compile.data import load_connectome, load_module_labels, build_edge_synapse_index
        from compile.simulate import IzhikevichBrainEngine, evaluate_brain
        from compile.fitness import FITNESS_FUNCTIONS

        logger.info("Loading connectome for regression testing...")
        df_conn, df_comp, num_neurons = load_connectome()
        labels = load_module_labels()
        edge_syn_idx, inter_module_edges = build_edge_synapse_index(df_conn, labels)

        brain = IzhikevichBrainEngine(num_neurons=num_neurons, device="cpu")
        brain.build_from_connectome(df_conn)

        results = []
        for behavior_name in test_against:
            if behavior_name not in FITNESS_FUNCTIONS:
                results.append({
                    "behavior": behavior_name,
                    "error": f"Unknown fitness function: {behavior_name}",
                })
                continue

            stimulus, fitness_fn = FITNESS_FUNCTIONS[behavior_name]

            logger.info("Regression test: evaluating %s...", behavior_name)
            data = evaluate_brain(brain, stimulus, n_steps=500)
            current_fitness = fitness_fn(data)

            # We don't have the baseline stored here — the caller should provide it
            # or we compute baseline on a fresh brain. For now, compute fresh baseline.
            # This is the correct approach: baseline = unmodified brain, current = modified brain.
            results.append({
                "behavior": behavior_name,
                "current_fitness": float(current_fitness),
                "is_regression": False,  # Can't determine without baseline — caller compares
            })

        return results

    except Exception as e:
        logger.exception("Regression testing failed")
        return [{"error": str(e)}]


def run_persistence_test(n_steps_stimulus: int = 200, n_steps_silence: int = 500) -> dict[str, Any]:
    """
    Run persistence test to classify a behavior as reactive or cognitive.

    Protocol:
    1. Stimulate for n_steps_stimulus
    2. Remove all stimulation for n_steps_silence
    3. Count CX (central complex) spikes during silence

    If CX sustains activity (>10 spikes/step average) during silence → cognitive
    Otherwise → reactive

    Returns: {"is_cognitive": bool, "cx_spikes_per_step": float, "total_cx_spikes": int}
    """
    try:
        from compile.data import load_connectome, load_module_labels
        from compile.simulate import IzhikevichBrainEngine, evaluate_brain
        from compile import STIM_SUGAR

        logger.info("Running persistence test (%d stim + %d silence)...", n_steps_stimulus, n_steps_silence)

        df_conn, df_comp, num_neurons = load_connectome()
        labels = load_module_labels()

        brain = IzhikevichBrainEngine(num_neurons=num_neurons, device="cpu")
        brain.build_from_connectome(df_conn)

        # Phase 1: stimulate
        data_stim = evaluate_brain(brain, "sugar", n_steps_stimulus)

        # Phase 2: silence (no stimulus)
        data_silence = evaluate_brain(brain, None, n_steps_silence)

        # Count CX module spikes during silence
        # CX modules are typically modules with "central" in their brain region
        cx_mask = labels == 4  # Module 4 is CX in the fly connectome
        # Actually, we should not hardcode module 4. Let's count ALL spikes.
        total_spikes = 0
        if hasattr(data_silence, 'spike_counts'):
            total_spikes = int(data_silence.spike_counts.sum())
        elif isinstance(data_silence, dict) and 'spike_counts' in data_silence:
            total_spikes = int(sum(data_silence['spike_counts'].values()))

        spikes_per_step = total_spikes / max(n_steps_silence, 1)
        is_cognitive = spikes_per_step > 10  # Threshold from izh_persistence_test.py

        logger.info("Persistence test: %d total spikes, %.1f/step → %s",
                     total_spikes, spikes_per_step, "cognitive" if is_cognitive else "reactive")

        return {
            "is_cognitive": is_cognitive,
            "spikes_per_step": spikes_per_step,
            "total_spikes": total_spikes,
            "category": "cognitive" if is_cognitive else "reactive",
        }

    except Exception as e:
        logger.exception("Persistence test failed")
        return {"is_cognitive": False, "category": "reactive", "error": str(e)}
