"""
Izhikevich Brain Engine — standalone entry point.

This module re-exports the Izhikevich model from the compile package
for backward compatibility. New code should import directly from compile::

    from compile.simulate import IzhikevichBrainEngine, IzhikevichModel
    from compile.constants import NEURON_TYPES, DEFAULT_SIM_PARAMS
"""

# Re-export from compile package
from compile.simulate import (  # noqa: F401
    IzhikevichBrainEngine,
    IzhikevichModel,
    assign_neuron_types,
    build_weight_matrix,
    evaluate_brain,
    run_simulation,
)
from compile.constants import (  # noqa: F401
    DEFAULT_SIM_PARAMS,
    NEURON_TYPES,
)

# Keep DEFAULT_PARAMS alias for backward compat
DEFAULT_PARAMS = DEFAULT_SIM_PARAMS


if __name__ == "__main__":
    """Quick smoke test — same as the original."""
    import time

    print("=" * 60)
    print("IZHIKEVICH BRAIN ENGINE TEST")
    print("=" * 60)

    brain = IzhikevichBrainEngine(device="cpu")

    # Test 1: Baseline activity
    print("\n--- Test 1: Baseline (no stimulus, 500 steps) ---")
    brain.state = brain.model.state_init()
    brain.rates.zero_()
    brain._spike_acc.zero_()

    t0 = time.time()
    total_spikes = 0
    for step in range(500):
        brain.step()
        total_spikes += brain.state[2].sum().item()
    t1 = time.time()
    print(f"  Spontaneous spikes: {total_spikes:.0f} in {t1-t0:.1f}s")

    # Test 2: Sugar stimulus
    print("\n--- Test 2: Sugar stimulus (500 steps) ---")
    brain.state = brain.model.state_init()
    brain.set_stimulus("sugar")
    brain._spike_acc.zero_()

    total_spikes = 0
    dn_total = {}
    for step in range(500):
        brain.step()
        spk = brain.state[2].squeeze(0)
        total_spikes += spk.sum().item()
        for name, idx in brain.dn_indices.items():
            dn_total[name] = dn_total.get(name, 0) + int(spk[idx].item())
    print(f"  Total spikes: {total_spikes:.0f}")
    print(f"  DN spikes: {dict(sorted([(k, v) for k, v in dn_total.items() if v > 0]))}")

    # Test 3: Persistence
    print("\n--- Test 3: PERSISTENCE (200 steps stimulus, then 500 steps silence) ---")
    brain.state = brain.model.state_init()
    brain.set_stimulus("sugar")

    stim_spikes = 0
    for step in range(200):
        brain.step()
        stim_spikes += brain.state[2].sum().item()
    print(f"  During stimulus: {stim_spikes:.0f} total spikes")

    brain.rates.zero_()
    post_windows = []
    for window in range(10):
        window_spikes = 0
        for step in range(50):
            brain.step()
            window_spikes += brain.state[2].sum().item()
        post_windows.append(window_spikes)
        status = "ACTIVE" if window_spikes > 5 else "silent"
        print(f"  Post-stimulus {window*50}-{(window+1)*50}: {window_spikes:.0f} spikes [{status}]")

    if post_windows[-1] > 5:
        print("  >>> PERSISTENT ACTIVITY DETECTED!")
    elif any(w > 5 for w in post_windows[3:]):
        print("  >>> DELAYED PERSISTENCE — recurrent reverberation present")
    else:
        decay = next((i * 50 for i, w in enumerate(post_windows) if w < 2), 500)
        print(f"  >>> Activity decayed after ~{decay} steps")

    print("\nDONE.")
