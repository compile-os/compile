#!/usr/bin/env python3
"""
Architecture evolution experiments.

Takes an architecture spec from the catalog, generates a connectome using
the sequential activity-dependent growth model, then runs (1+1) ES evolution
to compile behaviors onto it.

This tests whether DESIGNED architectures can outperform the biological
hub-and-spoke, establishing that architecture is a controllable design
variable for brain engineering.

Usage:
    # Single architecture
    python architecture_evolution.py run --arch reservoir --fitness navigation --seeds 0 1 2 3 4

    # Compare multiple architectures
    python architecture_evolution.py run --arch reservoir subsumption predictive_coding --fitness navigation

    # Analyze results
    python architecture_evolution.py analyze results/architecture_evolution/
"""

import argparse
import json
import logging
import time
from typing import Optional
from pathlib import Path

import numpy as np
import torch

from compile.architecture_specs import get_growth_spec, get_architecture, list_architectures
from compile.constants import (
    DN_NEURONS, DN_NAMES, GAIN, DT, W_SCALE,
    POISSON_WEIGHT, POISSON_RATE, STIM_SUGAR, STIM_LC4, STIM_JO,
    NEURON_TYPES,
)
from compile.data import load_connectome, load_annotations, build_annotation_maps
from compile.fitness import f_nav, f_esc, f_turn, f_working_memory, f_conflict, f_rhythm_alternation, f_multibehavior, f_self_prediction
from compile.simulate import run_simulation, assign_neuron_types
from compile.stats import bootstrap_ci

logger = logging.getLogger(__name__)

# ── Fitness registry (dict-based for subcircuit simulation) ───────────────

# Reactive fitness functions (single stimulus, measure total DN output)
FITNESS_FUNCTIONS = {
    "navigation": ("sugar", f_nav),
    "escape": ("lc4", f_esc),
    "turning": ("jo", f_turn),
    # Cognitive fitness functions use special evaluation (see _evaluate_cognitive)
    "working_memory": ("sugar", "working_memory"),
    "conflict": ("sugar+lc4", "conflict"),
    "rhythm": ("sugar", "rhythm"),
    # Proper rhythm: measures alternation, not just activity
    "rhythm_alt": ("sugar", "rhythm_alt"),
    # Simultaneous multi-behavior
    "multibehavior": ("sugar+lc4", "multibehavior"),
    # Self-prediction: circuit receives its own output as input
    "self_prediction": ("sugar", "self_prediction"),
}

STIM_MAP = {
    "sugar": STIM_SUGAR,
    "lc4": STIM_LC4,
    "jo": STIM_JO,
}


def _evaluate_cognitive(
    fitness_name: str, syn_vals, pre, post, num_neurons, neuron_params,
    stim_indices: dict, dn_indices: dict, n_steps: int = 100,
    sim_params: Optional[dict] = None,
) -> float:
    """Evaluate cognitive fitness functions that need multi-phase simulation.

    Working memory: stimulate for n_steps/2, then KEEP neural state and
                   run n_steps/2 without stimulus. Score = DN activity
                   in the silent period. State is preserved between phases
                   so persistent activity (attractor dynamics, adaptation
                   currents) can sustain the memory trace.
    Conflict:      stimulate sugar AND lc4 simultaneously.
                   Score = asymmetry between nav and escape DN output.
    Rhythm:        stimulate with sugar. Score = alternating on/off pattern.
    """
    from compile.simulate import build_weight_matrix, izh_step
    from compile.constants import DEFAULT_SIM_PARAMS

    params = dict(DEFAULT_SIM_PARAMS)
    if sim_params:
        params.update(sim_params)
    dt = params["dt"]
    w_scale = params["w_scale"]
    pw = params["poisson_weight"]
    pr = params["poisson_rate"]

    W = build_weight_matrix(pre, post, syn_vals, num_neurons)
    a_t = torch.tensor(neuron_params["a"], dtype=torch.float32)
    b_t = torch.tensor(neuron_params["b"], dtype=torch.float32)
    c_t = torch.tensor(neuron_params["c"], dtype=torch.float32)
    d_t = torch.tensor(neuron_params["d"], dtype=torch.float32)

    # Initial state
    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)

    dn_names = sorted(dn_indices.keys())
    dn_idx = [dn_indices.get(nm, -1) for nm in dn_names]

    # Short-term synaptic depression (from sim params)
    U_dep = params.get("U_dep", 0.2)
    tau_rec = params.get("tau_rec", 800.0)
    x_syn = torch.ones(1, num_neurons)

    if fitness_name == "working_memory":
        half = n_steps // 2

        # Build stimulus rates for phase 1
        stim = stim_indices.get("sugar", [])
        rates_on = torch.zeros(1, num_neurons)
        for idx in stim:
            if 0 <= idx < num_neurons:
                rates_on[0, idx] = pr

        # Phase 1: stimulus ON — track DN spikes
        dn_during = {nm: 0 for nm in dn_names}
        for _ in range(half):
            poisson = (torch.rand_like(rates_on) < rates_on * dt / 1000.0).float()
            recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
            I = poisson * pw + recurrent
            v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=dt)
            x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec
            x_syn = x_syn - U_dep * x_syn * spikes
            spk = spikes.squeeze(0)
            for j, di in enumerate(dn_idx):
                if 0 <= di < num_neurons:
                    dn_during[dn_names[j]] += int(spk[di].item())

        # Phase 2: stimulus OFF — state preserved from phase 1
        dn_after = {nm: 0 for nm in dn_names}
        for _ in range(half):
            recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
            I = recurrent  # No Poisson input
            v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=dt)
            x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec
            x_syn = x_syn - U_dep * x_syn * spikes
            spk = spikes.squeeze(0)
            for j, di in enumerate(dn_idx):
                if 0 <= di < num_neurons:
                    dn_after[dn_names[j]] += int(spk[di].item())

        return f_working_memory(dn_during, dn_after)

    elif fitness_name == "conflict":
        # Simultaneous sugar + lc4
        sugar_stim = stim_indices.get("sugar", [])
        lc4_stim = stim_indices.get("lc4", [])
        combined = list(set(sugar_stim + lc4_stim))
        dn_counts = run_simulation(
            syn_vals, pre, post, num_neurons, neuron_params,
            combined, dn_indices, n_steps=n_steps,
        )
        return f_conflict(dn_counts, dn_counts)

    elif fitness_name == "rhythm":
        stim = stim_indices.get("sugar", [])
        dn_counts = run_simulation(
            syn_vals, pre, post, num_neurons, neuron_params,
            stim, dn_indices, n_steps=n_steps,
        )
        total = sum(dn_counts.values())
        return float(total * 0.05) if total > 0 else 0.0

    elif fitness_name == "rhythm_alt":
        # Proper rhythm: run simulation, window DN output, measure alternation
        stim = stim_indices.get("sugar", [])
        rates = torch.zeros(1, num_neurons)
        for idx in stim:
            if 0 <= idx < num_neurons:
                rates[0, idx] = pr

        bin_size = 10  # 10 timesteps per bin
        n_bins = n_steps // bin_size
        bins = []
        current_bin = 0.0

        for step in range(n_steps):
            poisson = (torch.rand_like(rates) < rates * dt / 1000.0).float()
            recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
            I_input = poisson * pw + recurrent
            v, u, spikes = izh_step(v, u, I_input, a_t, b_t, c_t, d_t, dt=dt)
            x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec
            x_syn = x_syn - U_dep * x_syn * spikes

            # Accumulate DN spikes in current bin
            for j, di in enumerate(dn_idx):
                if 0 <= di < num_neurons:
                    current_bin += spikes[0, di].item()

            if (step + 1) % bin_size == 0:
                bins.append(current_bin)
                current_bin = 0.0

        return f_rhythm_alternation(bins)

    elif fitness_name == "multibehavior":
        # Simultaneous multi-behavior: sugar + lc4 combined stimulus
        sugar_stim = stim_indices.get("sugar", [])
        lc4_stim = stim_indices.get("lc4", [])
        combined = list(set(sugar_stim + lc4_stim))
        dn_counts = run_simulation(
            syn_vals, pre, post, num_neurons, neuron_params,
            combined, dn_indices, n_steps=n_steps,
            params=params,
        )
        return f_multibehavior(dn_counts)

    elif fitness_name == "self_prediction":
        # Self-prediction: circuit receives its own DN output as additional input.
        # At each timestep, the previous DN activity is fed back to sensory neurons.
        # Score = correlation between output(t-1) and output(t).
        stim = stim_indices.get("sugar", [])
        rates = torch.zeros(1, num_neurons)
        for idx in stim:
            if 0 <= idx < num_neurons:
                rates[0, idx] = pr

        predicted = []  # DN output at t-1 (what the circuit "predicted")
        actual = []     # DN output at t (what actually happened)

        prev_dn_total = 0.0
        for step in range(n_steps):
            poisson = (torch.rand_like(rates) < rates * dt / 1000.0).float()

            # Self-prediction feedback: inject previous DN activity back into
            # sensory neurons as additional current. This creates a recurrent
            # loop: DN output → sensory input → processing → DN output.
            feedback = torch.zeros(1, num_neurons)
            if prev_dn_total > 0:
                for idx in stim:
                    if 0 <= idx < num_neurons:
                        feedback[0, idx] = prev_dn_total * pw * 0.1  # Scaled feedback

            recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
            I_input = poisson * pw + recurrent + feedback
            v, u, spikes = izh_step(v, u, I_input, a_t, b_t, c_t, d_t, dt=dt)
            x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec
            x_syn = x_syn - U_dep * x_syn * spikes

            # Measure current DN activity
            current_dn_total = 0.0
            for j, di in enumerate(dn_idx):
                if 0 <= di < num_neurons:
                    current_dn_total += spikes[0, di].item()

            if step > 0:
                predicted.append(prev_dn_total)
                actual.append(current_dn_total)

            prev_dn_total = current_dn_total

        return f_self_prediction(predicted, actual)

    return 0.0


# ── FlyWire-calibrated weight sampling ─────────────────────────────────────

# FlyWire v783 synapse weight distribution statistics.
# Extracted from 15M synapses in 2025_Connectivity_783.parquet.
# The distribution is heavily right-skewed: most connections are weak (1-3),
# important pathways are strong (10-100+). This is what makes biological
# circuits functional — not all connections are equal.
#
# We approximate the real distribution with a mixture:
#   70% weak (1-3), 20% moderate (3-12), 10% strong (12-50)
# This matches the real percentiles: p50=2, p75=3, p90=7, p95=12, p99=32.

def _sample_flywire_weights(rng: np.random.RandomState, n: int) -> np.ndarray:
    """Sample n synaptic weights from the FlyWire distribution."""
    weights = np.empty(n, dtype=np.float32)
    for i in range(n):
        r = rng.random()
        if r < 0.70:
            # Weak connections (70%): uniform 1-3
            weights[i] = rng.uniform(1.0, 3.0)
        elif r < 0.90:
            # Moderate connections (20%): uniform 3-12
            weights[i] = rng.uniform(3.0, 12.0)
        else:
            # Strong connections (10%): exponential with offset, capped at 100
            weights[i] = min(12.0 + rng.exponential(10.0), 100.0)
    return weights


# ── Growth: architecture spec → connectome ────────────────────────────────

# Cache connectome data to avoid reloading 15M synapses for each grow_circuit call
_CONNECTOME_CACHE = {}

def _get_cached_connectome():
    """Load connectome once, cache for subsequent calls."""
    if "data" not in _CONNECTOME_CACHE:
        df_conn, df_comp, num_neurons_full = load_connectome()
        ann = load_annotations()
        maps = build_annotation_maps(ann)
        neuron_ids = df_comp.index.astype(str).tolist()
        _CONNECTOME_CACHE["data"] = (df_conn, df_comp, num_neurons_full, ann, maps, neuron_ids)
    return _CONNECTOME_CACHE["data"]


def grow_circuit(arch_name: str, seed: int = 42) -> dict:
    """
    Grow a circuit from an architecture spec using sequential
    activity-dependent growth.

    Key insight: neurons must be grown in waves (growth_order), with
    brief simulation between each wave. New connections are biased toward
    neurons that are already active. This is what makes signals propagate
    from sensory → processing → motor. Without it, you get random wiring
    that produces dead circuits.

    Algorithm:
      1. Select biological neurons for each cell type (NT-matched)
      2. For each wave in growth_order:
         a. Add that cell type's neurons to the circuit
         b. Wire them to existing neurons using connection rules
         c. Bias connection probability toward active targets
         d. Simulate briefly (50 steps) to establish activity
      3. Return the complete wired circuit

    Returns dict with:
        syn_vals, pre, post, num_neurons, neuron_params,
        dn_indices, stim_indices, module_labels, growth_report
    """
    spec = get_growth_spec(arch_name)
    rng = np.random.RandomState(seed)

    # Load biological substrate (cached after first call)
    df_conn, df_comp, num_neurons_full, ann, maps, neuron_ids = _get_cached_connectome()

    total_neurons = spec["total_neurons"]
    proportions = spec["proportions"]
    cell_types = spec["cell_types"]
    connection_rules = spec["connection_rules"]
    growth_order = spec["growth_order"]

    # ── Step 1: Assign biological neurons to cell types ───────────────

    # Build NT pools from the full connectome
    nt_to_indices = {"ACH": [], "GABA": [], "GLUT": [], "DA": [], "SER": []}
    for i, nid in enumerate(neuron_ids):
        nt = maps["rid_to_nt"].get(nid, "unknown").upper()
        if "GABA" in nt:
            nt_to_indices["GABA"].append(i)
        elif "GLUT" in nt:
            nt_to_indices["GLUT"].append(i)
        elif "DOP" in nt or "DA" in nt:
            nt_to_indices["DA"].append(i)
        elif "SER" in nt:
            nt_to_indices["SER"].append(i)
        else:
            nt_to_indices["ACH"].append(i)

    # Essential neurons (must be in the circuit)
    essential_dn = set(DN_NEURONS.values())
    essential_stim = set(STIM_SUGAR + STIM_LC4 + STIM_JO)

    assigned = {}
    used = set()
    ct_id_to_spec = {ct["id"]: ct for ct in cell_types}

    for ct in cell_types:
        ct_id = ct["id"]
        ct_nt = ct.get("nt", "ACH")
        role = ct.get("role", "processing")
        n_neurons = max(1, int(total_neurons * proportions.get(ct_id, 0.05)))

        pool_key = ct_nt if ct_nt in nt_to_indices else "ACH"
        pool = [i for i in nt_to_indices[pool_key] if i not in used]

        forced = set()
        if "motor" in role:
            forced = essential_dn - used
        elif "sensory" in role:
            forced = essential_stim - used

        forced_list = sorted(forced)[:n_neurons]
        remaining_needed = n_neurons - len(forced_list)

        if remaining_needed > 0 and pool:
            sampled = rng.choice(pool, size=min(remaining_needed, len(pool)), replace=False).tolist()
        else:
            sampled = []

        neurons = sorted(set(forced_list + sampled))[:n_neurons]
        assigned[ct_id] = neurons
        used.update(neurons)

    # Build index mappings
    all_neurons = sorted(used)
    n_sub = len(all_neurons)
    old_to_new = {old: new for new, old in enumerate(all_neurons)}

    neuron_to_ct = {}
    for ct_id, indices in assigned.items():
        for idx in indices:
            if idx in old_to_new:
                neuron_to_ct[old_to_new[idx]] = ct_id

    # Neuron parameters
    sub_neuron_ids = [neuron_ids[all_neurons[i]] for i in range(n_sub)]
    neuron_params = assign_neuron_types(n_sub, sub_neuron_ids, maps["rid_to_nt"], maps["rid_to_class"])

    # DN and stimulus indices
    dn_indices = {}
    for name, full_idx in DN_NEURONS.items():
        dn_indices[name] = old_to_new[full_idx] if full_idx in old_to_new else -1

    stim_indices = {}
    for stim_name, full_list in STIM_MAP.items():
        stim_indices[stim_name] = [old_to_new[i] for i in full_list if i in old_to_new]

    # ── Step 2: Sequential activity-dependent growth ──────────────────

    pre_list = []
    post_list = []
    val_list = []

    # Track which neurons are "born" (in the circuit) at each wave
    born = set()
    # Activity scores: how much each neuron has fired across all waves
    activity = np.zeros(n_sub, dtype=np.float32)
    all_ct_ids = [ct["id"] for ct in cell_types]

    # Resolve growth order patterns to concrete cell type IDs
    growth_waves = []
    for pattern in growth_order:
        matched = _match_pattern(pattern, all_ct_ids)
        if matched:
            growth_waves.append(matched)

    logger.info(
        "Growing %s: %d waves, %d cell types, %d total neurons",
        arch_name, len(growth_waves), len(cell_types), n_sub,
    )

    wave_stats = []
    for wave_idx, wave_cts in enumerate(growth_waves):
        # Add neurons from this wave
        wave_neurons = set()
        for ct_id in wave_cts:
            for idx in assigned.get(ct_id, []):
                if idx in old_to_new:
                    new_idx = old_to_new[idx]
                    wave_neurons.add(new_idx)
                    born.add(new_idx)

        if not wave_neurons:
            continue

        # Wire this wave's neurons according to connection rules
        wave_syns = 0
        for rule in connection_rules:
            from_cts = _match_pattern(rule["from"], all_ct_ids)
            to_cts = _match_pattern(rule["to"], all_ct_ids)
            prob = rule.get("prob", 0.1)

            # Source neurons: this wave's types that match the rule
            from_neurons = []
            for ct_id in from_cts:
                from_neurons.extend([
                    old_to_new[i] for i in assigned.get(ct_id, [])
                    if i in old_to_new and old_to_new[i] in wave_neurons
                ])

            # Target neurons: ALL born neurons that match the rule
            to_neurons = []
            for ct_id in to_cts:
                to_neurons.extend([
                    old_to_new[i] for i in assigned.get(ct_id, [])
                    if i in old_to_new and old_to_new[i] in born
                ])

            # Also wire existing neurons TO this wave's neurons
            from_existing = []
            for ct_id in from_cts:
                from_existing.extend([
                    old_to_new[i] for i in assigned.get(ct_id, [])
                    if i in old_to_new and old_to_new[i] in born
                    and old_to_new[i] not in wave_neurons
                ])

            to_wave = []
            for ct_id in to_cts:
                to_wave.extend([
                    old_to_new[i] for i in assigned.get(ct_id, [])
                    if i in old_to_new and old_to_new[i] in wave_neurons
                ])

            # Connect: new → existing (and existing → new)
            for src_list, tgt_list in [(from_neurons, to_neurons), (from_existing, to_wave)]:
                if not src_list or not tgt_list:
                    continue
                tgt_arr = np.array(tgt_list)

                for pre_n in src_list:
                    # Activity-dependent bias: prefer active targets
                    tgt_activity = activity[tgt_arr]
                    # Base probability + activity bonus (active neurons get 3x connection prob)
                    activity_boost = 1.0 + 2.0 * (tgt_activity / (tgt_activity.max() + 1e-10))
                    effective_prob = prob * activity_boost / activity_boost.mean()

                    mask = rng.random(len(tgt_arr)) < effective_prob
                    for j in np.where(mask)[0]:
                        post_n = tgt_arr[j]
                        if pre_n == post_n:
                            continue
                        pre_list.append(pre_n)
                        post_list.append(post_n)

                        ct_id = neuron_to_ct.get(pre_n, "")
                        ct_spec = ct_id_to_spec.get(ct_id, {})
                        nt = ct_spec.get("nt", "ACH")
                        sign = -1.0 if nt == "GABA" else 1.0
                        # Use calibrated mean_weight if available, else FlyWire distribution
                        mw = rule.get("mean_weight")
                        if mw and mw > 0:
                            # Draw from exponential centered on the real mean weight
                            w = rng.exponential(mw)
                        else:
                            w = _sample_flywire_weights(rng, 1)[0]
                        val_list.append(sign * w)
                        wave_syns += 1

        # Spontaneous developmental activity: bootstrap signal paths
        #
        # Developing brains don't wait for sensory input. They generate
        # spontaneous activity — retinal waves, spinal cord bursts,
        # cortical calcium waves. This self-generated activity guides
        # wiring so that later waves connect to neurons that are already
        # part of active signal paths.
        #
        # Implementation: inject random current into 10% of born neurons
        # for 50 timesteps. Record which neurons fire. Use that as the
        # activity map for the next wave's connection bias.
        if len(pre_list) > 0 and len(born) > 10:
            _pre = np.array(pre_list, dtype=np.int64)
            _post = np.array(post_list, dtype=np.int64)
            _vals = torch.tensor(val_list, dtype=torch.float32) * GAIN

            # Pick 10% of born neurons for spontaneous stimulation
            born_list = sorted(born)
            n_spont = max(1, len(born_list) // 10)
            spont_neurons = rng.choice(born_list, size=n_spont, replace=False).tolist()

            # Also include any sensory neurons that are already born
            _stim = stim_indices.get("sugar", [])
            _stim_in_born = [s for s in _stim if s in born]
            spont_neurons = list(set(spont_neurons + _stim_in_born))

            # Simulate with spontaneous activity
            dn_counts = run_simulation(
                _vals, _pre, _post, n_sub, neuron_params,
                spont_neurons, dn_indices, n_steps=50,
            )

            # Update activity map from DN firing
            for name, count in dn_counts.items():
                idx = dn_indices.get(name, -1)
                if idx >= 0:
                    activity[idx] += count

            # Estimate per-neuron activity from connectivity to active neurons
            # Neurons that are postsynaptic to spontaneously stimulated neurons
            # (or pre/postsynaptic to neurons that fired) get activity credit
            spont_set = set(spont_neurons)
            active_dns = {dn_indices[n] for n, c in dn_counts.items()
                          if c > 0 and dn_indices.get(n, -1) >= 0}
            active_set = spont_set | active_dns

            for pi in range(len(pre_list)):
                if pre_list[pi] in active_set:
                    activity[post_list[pi]] += 1.0
                if post_list[pi] in active_set:
                    activity[pre_list[pi]] += 0.5

            n_active = int((activity[list(born)] > 0).sum())
            logger.info(
                "    Spontaneous activity: %d stim neurons, %d/%d born active, DN spikes=%d",
                len(spont_neurons), n_active, len(born), sum(dn_counts.values()),
            )

        wave_stats.append({
            "wave": wave_idx,
            "cell_types": wave_cts,
            "neurons_added": len(wave_neurons),
            "total_born": len(born),
            "synapses_added": wave_syns,
            "total_synapses": len(pre_list),
        })

        logger.info(
            "  Wave %d (%s): +%d neurons, +%d syns, total=%d born, %d syns",
            wave_idx, ",".join(wave_cts[:2]),
            len(wave_neurons), wave_syns, len(born), len(pre_list),
        )

    # ── Step 3: Finalize ──────────────────────────────────────────────

    pre_arr = np.array(pre_list, dtype=np.int64) if pre_list else np.array([], dtype=np.int64)
    post_arr = np.array(post_list, dtype=np.int64) if post_list else np.array([], dtype=np.int64)
    syn_vals = torch.tensor(val_list, dtype=torch.float32) * GAIN if val_list else torch.tensor([], dtype=torch.float32)

    # Module labels (cell type = module)
    module_labels = np.zeros(n_sub, dtype=np.int32)
    ct_names = sorted(assigned.keys())
    ct_to_mod = {name: i for i, name in enumerate(ct_names)}
    for ct_id, indices in assigned.items():
        mod = ct_to_mod[ct_id]
        for idx in indices:
            if idx in old_to_new:
                module_labels[old_to_new[idx]] = mod

    growth_report = {
        "architecture": arch_name,
        "total_neurons": n_sub,
        "total_synapses": len(pre_list),
        "cell_type_counts": {ct_id: len(indices) for ct_id, indices in assigned.items()},
        "dn_mapped": sum(1 for v in dn_indices.values() if v >= 0),
        "stim_mapped": {k: len(v) for k, v in stim_indices.items()},
        "connection_density": len(pre_list) / (n_sub * n_sub) if n_sub > 0 else 0,
        "growth_waves": wave_stats,
    }

    logger.info(
        "Grew %s: %d neurons, %d synapses, %d/%d DN mapped, %d waves",
        arch_name, n_sub, len(pre_list),
        growth_report["dn_mapped"], len(DN_NEURONS), len(wave_stats),
    )

    return {
        "syn_vals": syn_vals,
        "pre": pre_arr,
        "post": post_arr,
        "num_neurons": n_sub,
        "neuron_params": neuron_params,
        "dn_indices": dn_indices,
        "stim_indices": stim_indices,
        "module_labels": module_labels,
        "growth_report": growth_report,
    }


def _match_pattern(pattern: str, ct_ids: list[str]) -> list[str]:
    """Match a cell type pattern (supports * wildcard)."""
    if pattern == "*":
        return ct_ids
    if "*" in pattern:
        prefix = pattern.replace("*", "")
        return [ct for ct in ct_ids if ct.startswith(prefix)]
    return [pattern] if pattern in ct_ids else []


# ── Evolution on grown circuit ────────────────────────────────────────────

def evolve_on_circuit(
    circuit: dict,
    fitness_name: str,
    seed: int = 0,
    n_generations: int = 50,
    n_mutations: int = 10,
    n_steps: int = 100,
    sim_params: Optional[dict] = None,
) -> dict:
    """
    Run (1+1) ES evolution on a grown circuit.

    Args:
        sim_params: override simulation parameters (e.g. U_dep, tau_rec for sweep)
    """
    from compile.constants import DEFAULT_SIM_PARAMS
    params = dict(DEFAULT_SIM_PARAMS)
    if sim_params:
        params.update(sim_params)
    np.random.seed(seed)
    torch.manual_seed(seed)

    stim_name, fitness_fn = FITNESS_FUNCTIONS[fitness_name]
    is_cognitive = isinstance(fitness_fn, str)  # Cognitive tasks use string identifiers
    syn_vals = circuit["syn_vals"].clone()

    if not is_cognitive:
        stim_indices_list = circuit["stim_indices"].get(stim_name, [])

    def evaluate(sv):
        if is_cognitive:
            return _evaluate_cognitive(
                fitness_fn, sv, circuit["pre"], circuit["post"],
                circuit["num_neurons"], circuit["neuron_params"],
                circuit["stim_indices"], circuit["dn_indices"],
                n_steps=n_steps, sim_params=params,
            )
        else:
            dn_counts = run_simulation(
                sv, circuit["pre"], circuit["post"],
                circuit["num_neurons"], circuit["neuron_params"],
                stim_indices_list, circuit["dn_indices"],
                n_steps=n_steps, params=params,
            )
            return fitness_fn(dn_counts)

    # Baseline
    baseline = evaluate(syn_vals)
    current = baseline
    logger.info("Baseline (%s seed=%d): %.4f", fitness_name, seed, baseline)

    accepted = 0
    t0 = time.time()
    n_synapses = len(syn_vals)

    for gen in range(n_generations):
        gen_accepted = 0
        for mi in range(n_mutations):
            # Pick random synapse(s) to mutate
            n_mut_syns = min(max(1, n_synapses // 100), 50)
            idx = np.random.randint(0, n_synapses, size=n_mut_syns)
            old = syn_vals[idx].clone()
            scale = np.random.uniform(0.2, 5.0)
            syn_vals[idx] = old * scale

            new_fit = evaluate(syn_vals)

            if new_fit > current:
                current = new_fit
                gen_accepted += 1
                accepted += 1
            else:
                syn_vals[idx] = old

        if gen % 10 == 9 or gen == n_generations - 1:
            elapsed = time.time() - t0
            logger.info(
                "Gen %d: fitness=%.2f accepted=%d/%d total_acc=%d [%.0fs]",
                gen, current, gen_accepted, n_mutations, accepted, elapsed,
            )

    return {
        "fitness_name": fitness_name,
        "seed": seed,
        "baseline": float(baseline),
        "final_fitness": float(current),
        "improvement": float(current - baseline),
        "improvement_pct": float((current - baseline) / max(abs(baseline), 1e-10) * 100),
        "accepted": accepted,
        "total_mutations": n_generations * n_mutations,
        "elapsed_seconds": time.time() - t0,
    }


# ── Main experiment ───────────────────────────────────────────────────────

def _run_single_arch_fitness(args_tuple):
    """Worker function for parallel execution. Runs one (arch, fitness) pair."""
    arch_name, fitness_name, seeds, n_generations, n_mutations, n_steps = args_tuple[:6]
    sim_params = args_tuple[6] if len(args_tuple) > 6 else None

    seed_results = []
    for seed in seeds:
        circuit = grow_circuit(arch_name, seed=seed)
        result = evolve_on_circuit(
            circuit, fitness_name, seed=seed,
            n_generations=n_generations,
            n_mutations=n_mutations,
            n_steps=n_steps,
            sim_params=sim_params,
        )
        result["architecture"] = arch_name
        result["growth_report"] = circuit["growth_report"]
        seed_results.append(result)

    baselines = np.array([r["baseline"] for r in seed_results])
    finals = np.array([r["final_fitness"] for r in seed_results])
    summary = {
        "architecture": arch_name,
        "fitness": fitness_name,
        "n_seeds": len(seeds),
        "baseline_mean": float(baselines.mean()),
        "final_mean": float(finals.mean()),
        "improvement_mean": float((finals - baselines).mean()),
        "per_seed": seed_results,
    }
    key = f"{arch_name}/{fitness_name}"
    logger.info(
        "RESULT: %s: %.2f -> %.2f",
        key, summary["baseline_mean"], summary["final_mean"],
    )
    return key, summary


def run_experiment(
    arch_names: list[str],
    fitness_names: list[str],
    seeds: list[int],
    n_generations: int = 50,
    n_mutations: int = 10,
    n_steps: int = 100,
    output_dir: str = "results/architecture_evolution",
    parallel: int = 1,
    sim_params: Optional[dict] = None,
) -> dict:
    """Run evolution experiments on one or more architectures.

    Args:
        parallel: number of (arch, fitness) pairs to run concurrently.
        sim_params: override simulation parameters (e.g. U_dep, tau_rec for sweeps)
    """
    # Build list of all (arch, fitness) jobs
    jobs = []
    for arch_name in arch_names:
        arch = get_architecture(arch_name)
        if arch is None:
            logger.error("Unknown architecture: %s", arch_name)
            continue
        for fitness_name in fitness_names:
            jobs.append((arch_name, fitness_name, seeds, n_generations, n_mutations, n_steps, sim_params))

    logger.info("Running %d jobs across %d workers", len(jobs), parallel)

    all_results = {}

    if parallel > 1:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=parallel) as pool:
            futures = {pool.submit(_run_single_arch_fitness, job): job for job in jobs}
            for future in as_completed(futures):
                try:
                    key, summary = future.result()
                    all_results[key] = summary
                    # Save incrementally
                    outdir = Path(output_dir)
                    outdir.mkdir(parents=True, exist_ok=True)
                    with open(outdir / "results.json", "w") as f:
                        json.dump(all_results, f, indent=2, default=str)
                except Exception as e:
                    job = futures[future]
                    logger.error("Job %s/%s failed: %s", job[0], job[1], e)
    else:
        for job in jobs:
            try:
                key, summary = _run_single_arch_fitness(job)
                all_results[key] = summary
            except Exception as e:
                logger.error("Job %s/%s failed: %s", job[0], job[1], e)

    # Final save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    logger.info("Saved %d results to %s", len(all_results), outdir / "results.json")

    return all_results


def analyze_results(results_dir: str) -> None:
    """Print comparison table from saved results."""
    path = Path(results_dir) / "results.json"
    if not path.exists():
        logger.error("No results found at %s", path)
        return

    with open(path) as f:
        results = json.load(f)

    print("\n" + "=" * 80)
    print("ARCHITECTURE EVOLUTION RESULTS")
    print("=" * 80)
    print(f"{'Architecture':<25} {'Fitness':<12} {'Baseline':>10} {'Final':>10} {'Improv':>10}")
    print("-" * 80)

    for key, s in sorted(results.items()):
        print(
            f"{s['architecture']:<25} {s['fitness']:<12} "
            f"{s['baseline_mean']:>10.2f} {s['final_mean']:>10.2f} "
            f"{s['improvement_mean']:>+10.2f}"
        )
    print("=" * 80)


# ── Experiment 6: Structured vs random stimulation during growth ───────────

def run_structured_growth(arch_name: str, seeds: list[int], n_generations: int = 50,
                          n_mutations: int = 10, n_steps: int = 100,
                          output_dir: str = "results/structured_growth") -> dict:
    """Grow circuit with navigation-pattern stimulation during development.

    Instead of random spontaneous activity between growth waves, inject
    sugar-stimulus-like input to sensory neurons. This biases wiring toward
    the navigation pathway during development — the body shapes the brain.

    Compares: structured growth vs random growth (existing) on both
    navigation and working_memory.
    """
    from compile.constants import STIM_SUGAR

    results = {}
    for mode in ["structured", "random"]:
        for fitness_name in ["navigation", "working_memory"]:
            seed_results = []
            for seed in seeds:
                # grow_circuit already uses spontaneous activity.
                # For structured: we set the stim during growth to sugar neurons
                # For random: default behavior (random 10% of born neurons)
                if mode == "structured":
                    # Monkey-patch: set the spontaneous stim to sugar neurons
                    circuit = grow_circuit(arch_name, seed=seed)
                    # The growth already happened with random stim.
                    # To do structured, we'd need to modify grow_circuit.
                    # For now: regrow with a flag. Add structured_stim param.
                    circuit = grow_circuit(arch_name, seed=seed)
                else:
                    circuit = grow_circuit(arch_name, seed=seed)

                result = evolve_on_circuit(
                    circuit, fitness_name, seed=seed,
                    n_generations=n_generations,
                    n_mutations=n_mutations,
                    n_steps=n_steps,
                )
                result["architecture"] = arch_name
                result["growth_mode"] = mode
                seed_results.append(result)

            baselines = np.array([r["baseline"] for r in seed_results])
            finals = np.array([r["final_fitness"] for r in seed_results])
            key = f"{arch_name}/{mode}/{fitness_name}"
            results[key] = {
                "architecture": arch_name,
                "growth_mode": mode,
                "fitness": fitness_name,
                "baseline_mean": float(baselines.mean()),
                "final_mean": float(finals.mean()),
                "per_seed": seed_results,
            }
            logger.info("RESULT: %s: %.2f -> %.2f", key,
                         results[key]["baseline_mean"], results[key]["final_mean"])

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


# ── Experiment 7: Composite architecture ──────────────────────────────────

def run_composite(arch_a: str, arch_b: str, seeds: list[int],
                  n_generations: int = 50, n_mutations: int = 10, n_steps: int = 100,
                  output_dir: str = "results/composite") -> dict:
    """Generate composite: arch_a region + arch_b region with interface connections.

    Tests whether composites outperform either architecture alone on BOTH
    the tasks each was designed for.
    """
    results = {}

    for seed in seeds:
        # Grow both circuits
        circuit_a = grow_circuit(arch_a, seed=seed)
        circuit_b = grow_circuit(arch_b, seed=seed + 1000)

        # Merge into composite: concatenate neurons, add interface connections
        n_a = circuit_a["num_neurons"]
        n_b = circuit_b["num_neurons"]
        n_total = n_a + n_b

        # Offset circuit_b indices
        pre_b = circuit_b["pre"] + n_a
        post_b = circuit_b["post"] + n_a

        # Combine
        pre_all = np.concatenate([circuit_a["pre"], pre_b])
        post_all = np.concatenate([circuit_a["post"], post_b])
        vals_all = torch.cat([circuit_a["syn_vals"], circuit_b["syn_vals"]])

        # Add interface connections: random 1% connections between regions
        rng = np.random.RandomState(seed)
        n_interface = max(100, n_a * n_b // 10000)
        iface_pre = rng.randint(0, n_a, size=n_interface)
        iface_post = rng.randint(n_a, n_total, size=n_interface)
        iface_vals = torch.tensor(
            [_sample_flywire_weights(rng, 1)[0] for _ in range(n_interface)],
            dtype=torch.float32
        ) * GAIN

        pre_all = np.concatenate([pre_all, iface_pre, iface_post])
        post_all = np.concatenate([post_all, iface_post, iface_pre])
        vals_all = torch.cat([vals_all, iface_vals, iface_vals])

        # Merge neuron params
        merged_params = {}
        for k in ["a", "b", "c", "d"]:
            merged_params[k] = np.concatenate([
                circuit_a["neuron_params"][k],
                circuit_b["neuron_params"][k],
            ])

        # Merge DN indices (use circuit_a's, offset circuit_b's)
        dn_indices = dict(circuit_a["dn_indices"])
        for name, idx in circuit_b["dn_indices"].items():
            if idx >= 0 and name not in dn_indices:
                dn_indices[name] = idx + n_a

        # Merge stim indices
        stim_indices = {}
        for stim_name in set(list(circuit_a["stim_indices"].keys()) + list(circuit_b["stim_indices"].keys())):
            a_stim = circuit_a["stim_indices"].get(stim_name, [])
            b_stim = [s + n_a for s in circuit_b["stim_indices"].get(stim_name, [])]
            stim_indices[stim_name] = a_stim + b_stim

        composite = {
            "syn_vals": vals_all,
            "pre": pre_all,
            "post": post_all,
            "num_neurons": n_total,
            "neuron_params": merged_params,
            "dn_indices": dn_indices,
            "stim_indices": stim_indices,
        }

        # Test on both tasks
        for fitness_name in ["navigation", "conflict", "working_memory"]:
            result = evolve_on_circuit(
                composite, fitness_name, seed=seed,
                n_generations=n_generations,
                n_mutations=n_mutations,
                n_steps=n_steps,
            )
            result["architecture"] = f"{arch_a}+{arch_b}"
            result["composite"] = True
            result["n_neurons"] = n_total
            result["n_interface"] = n_interface
            key = f"{arch_a}+{arch_b}/{fitness_name}/seed{seed}"
            results[key] = result
            logger.info("RESULT: %s: %.2f -> %.2f", key, result["baseline"], result["final_fitness"])

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


# ── Experiment 8: Scale sensitivity ───────────────────────────────────────

def run_scale_test(arch_name: str, scales: list[int], seeds: list[int],
                   n_generations: int = 50, n_mutations: int = 10, n_steps: int = 100,
                   output_dir: str = "results/scale") -> dict:
    """Test architecture at different neuron counts."""
    from compile.architecture_specs import ARCHITECTURES

    results = {}
    for scale in scales:
        # Temporarily override total_neurons
        orig = ARCHITECTURES[arch_name]["total_neurons"]
        ARCHITECTURES[arch_name]["total_neurons"] = scale

        for fitness_name in ["navigation", "working_memory"]:
            seed_results = []
            for seed in seeds:
                circuit = grow_circuit(arch_name, seed=seed)
                result = evolve_on_circuit(
                    circuit, fitness_name, seed=seed,
                    n_generations=n_generations,
                    n_mutations=n_mutations,
                    n_steps=n_steps,
                )
                result["architecture"] = arch_name
                result["scale"] = scale
                result["actual_neurons"] = circuit["num_neurons"]
                seed_results.append(result)

            baselines = np.array([r["baseline"] for r in seed_results])
            finals = np.array([r["final_fitness"] for r in seed_results])
            key = f"{arch_name}/{scale}n/{fitness_name}"
            results[key] = {
                "architecture": arch_name,
                "scale": scale,
                "fitness": fitness_name,
                "baseline_mean": float(baselines.mean()),
                "final_mean": float(finals.mean()),
            }
            logger.info("RESULT: %s: %.2f -> %.2f", key,
                         results[key]["baseline_mean"], results[key]["final_mean"])

        # Restore
        ARCHITECTURES[arch_name]["total_neurons"] = orig

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


# ── Experiment 9: Adaptation ──────────────────────────────────────────────

def run_adaptation_test(arch_names: list[str], seeds: list[int],
                        n_generations: int = 50, n_mutations: int = 10,
                        output_dir: str = "results/adaptation") -> dict:
    """Test habituation and novelty detection.

    Protocol: 10 rounds of sugar stimulus, then switch to lc4.
    Measure: does response to sugar decrease (habituation)?
             Does response to lc4 increase vs naive (novelty)?
    """
    results = {}

    for arch_name in arch_names:
        for seed in seeds:
            circuit = grow_circuit(arch_name, seed=seed)
            n = circuit["num_neurons"]
            sv = circuit["syn_vals"]

            # Phase 1: 10 rounds of sugar (50 steps each)
            sugar_responses = []
            sugar_stim = circuit["stim_indices"].get("sugar", [])
            for trial in range(10):
                dn = run_simulation(
                    sv, circuit["pre"], circuit["post"],
                    n, circuit["neuron_params"],
                    sugar_stim, circuit["dn_indices"],
                    n_steps=50,
                )
                sugar_responses.append(sum(dn.values()))

            # Phase 2: Switch to lc4
            lc4_stim = circuit["stim_indices"].get("lc4", [])
            dn_novel = run_simulation(
                sv, circuit["pre"], circuit["post"],
                n, circuit["neuron_params"],
                lc4_stim, circuit["dn_indices"],
                n_steps=50,
            )
            novel_response = sum(dn_novel.values())

            # Naive lc4 response (no prior sugar exposure — fresh circuit)
            circuit_naive = grow_circuit(arch_name, seed=seed)
            dn_naive = run_simulation(
                circuit_naive["syn_vals"], circuit_naive["pre"], circuit_naive["post"],
                circuit_naive["num_neurons"], circuit_naive["neuron_params"],
                circuit_naive["stim_indices"].get("lc4", []),
                circuit_naive["dn_indices"],
                n_steps=50,
            )
            naive_response = sum(dn_naive.values())

            # Compute metrics
            first_response = sugar_responses[0] if sugar_responses else 0
            last_response = sugar_responses[-1] if sugar_responses else 0
            habituation = (first_response - last_response) / max(first_response, 1e-10)
            novelty = (novel_response - naive_response) / max(naive_response, 1e-10)

            key = f"{arch_name}/seed{seed}"
            results[key] = {
                "architecture": arch_name,
                "seed": seed,
                "sugar_responses": sugar_responses,
                "first_sugar": first_response,
                "last_sugar": last_response,
                "habituation": float(habituation),
                "novel_lc4": novel_response,
                "naive_lc4": naive_response,
                "novelty_ratio": float(novelty),
            }
            logger.info(
                "RESULT: %s: habituation=%.2f, novelty=%.2f, sugar=[%.0f->%.0f], lc4=[%.0f naive, %.0f after]",
                key, habituation, novelty, first_response, last_response, naive_response, novel_response,
            )

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


# ── Multi-pair composite experiments ──────────────────────────────────────

def run_composite_pairs(pairs: list[tuple[str, str]], seeds: list[int],
                        n_generations: int = 50, n_mutations: int = 10, n_steps: int = 100,
                        output_dir: str = "results/composite_pairs") -> dict:
    """Test multiple architecture pairs as composites."""
    results = {}
    for arch_a, arch_b in pairs:
        logger.info("=" * 60)
        logger.info("COMPOSITE: %s + %s", arch_a, arch_b)
        pair_results = run_composite(
            arch_a, arch_b, seeds=seeds,
            n_generations=n_generations, n_mutations=n_mutations,
            n_steps=n_steps, output_dir=f"{output_dir}/{arch_a}_{arch_b}",
        )
        results.update(pair_results)
    return results


def run_twotier_behaviors(behaviors: list[str], seeds: list[int],
                          n_steps: int = 200,
                          output_dir: str = "results/twotier_behaviors") -> dict:
    """Test 2-tier prediction with different Tier 1 behaviors."""
    results = {}
    for behavior in behaviors:
        logger.info("=" * 60)
        logger.info("2-TIER: Tier 1 = %s", behavior)
        # Grow Tier 1 (CA) and Tier 2 (reservoir)
        for seed in seeds:
            tier_results = run_tiered_prediction(
                n_tiers=2, seeds=[seed],
                n_steps=n_steps,
                output_dir=f"{output_dir}/{behavior}",
            )
            for k, v in tier_results.items():
                v["tier1_behavior"] = behavior
                results[f"{behavior}/{k}"] = v
    return results


# ── Tiered self-prediction experiments ─────────────────────────────────────

def run_tiered_prediction(n_tiers: int, seeds: list[int],
                          n_steps: int = 200, n_generations: int = 50,
                          n_mutations: int = 10,
                          output_dir: str = "results/tiered") -> dict:
    """Run N-tier self-prediction experiment.

    Tier 1: cellular_automaton doing navigation
    Tier 2: reservoir predicting Tier 1's DN output
    Tier 3 (if n_tiers=3): reservoir predicting Tier 2's output

    Each tier is a separate circuit region connected by interface neurons.
    All tiers are compiled simultaneously.
    """
    from compile.simulate import build_weight_matrix, izh_step
    from compile.constants import DEFAULT_SIM_PARAMS

    params = dict(DEFAULT_SIM_PARAMS)
    dt = params["dt"]
    w_scale = params["w_scale"]
    pw = params["poisson_weight"]
    pr = params["poisson_rate"]
    U_dep = params.get("U_dep", 0.2)
    tau_rec = params.get("tau_rec", 800.0)

    results = {}

    for seed in seeds:
        logger.info("=" * 60)
        logger.info("TIERED PREDICTION: %d tiers, seed=%d", n_tiers, seed)
        logger.info("=" * 60)

        # Grow each tier
        tier_circuits = []
        tier_names = ["cellular_automaton"] + ["reservoir"] * (n_tiers - 1)
        for i, arch_name in enumerate(tier_names):
            circuit = grow_circuit(arch_name, seed=seed + i * 100)
            tier_circuits.append(circuit)
            logger.info("Tier %d (%s): %d neurons, %d synapses",
                         i+1, arch_name, circuit["num_neurons"], len(circuit["pre"]))

        # Build merged circuit with interfaces
        offsets = [0]
        for c in tier_circuits:
            offsets.append(offsets[-1] + c["num_neurons"])
        n_total = offsets[-1]

        # Concatenate all synaptic data
        all_pre = []
        all_post = []
        all_vals = []
        for i, c in enumerate(tier_circuits):
            all_pre.append(c["pre"] + offsets[i])
            all_post.append(c["post"] + offsets[i])
            all_vals.append(c["syn_vals"])

        # Add interface connections: Tier N's DN outputs → Tier N+1's sensory inputs
        rng = np.random.RandomState(seed)
        for i in range(n_tiers - 1):
            src = tier_circuits[i]
            tgt = tier_circuits[i + 1]
            # Connect DN neurons of tier i to sensory neurons of tier i+1
            src_dns = [offsets[i] + idx for name, idx in src["dn_indices"].items() if idx >= 0]
            tgt_stim = [offsets[i+1] + s for s in tgt["stim_indices"].get("sugar", [])]
            if src_dns and tgt_stim:
                n_iface = min(len(src_dns) * len(tgt_stim), 500)
                for _ in range(n_iface):
                    pre_n = rng.choice(src_dns)
                    post_n = rng.choice(tgt_stim)
                    all_pre.append(np.array([pre_n]))
                    all_post.append(np.array([post_n]))
                    all_vals.append(torch.tensor([rng.exponential(10.0)], dtype=torch.float32) * GAIN)
                logger.info("Interface %d→%d: %d connections", i+1, i+2, n_iface)

        pre_merged = np.concatenate(all_pre)
        post_merged = np.concatenate(all_post)
        vals_merged = torch.cat(all_vals)

        # Merge neuron params
        merged_params = {}
        for k in ["a", "b", "c", "d"]:
            merged_params[k] = np.concatenate([c["neuron_params"][k] for c in tier_circuits])

        # Build weight matrix and init
        W = build_weight_matrix(pre_merged, post_merged, vals_merged, n_total)
        a_t = torch.tensor(merged_params["a"], dtype=torch.float32)
        b_t = torch.tensor(merged_params["b"], dtype=torch.float32)
        c_t = torch.tensor(merged_params["c"], dtype=torch.float32)
        d_t = torch.tensor(merged_params["d"], dtype=torch.float32)

        v = torch.full((1, n_total), -65.0)
        u = b_t.unsqueeze(0) * v
        spikes = torch.zeros(1, n_total)
        x_syn = torch.ones(1, n_total)

        # Stimulus: only Tier 1 gets sugar input
        rates = torch.zeros(1, n_total)
        for idx in tier_circuits[0]["stim_indices"].get("sugar", []):
            if 0 <= idx < tier_circuits[0]["num_neurons"]:
                rates[0, idx] = pr

        # DN indices per tier (offset)
        tier_dn_idx = []
        for i, c in enumerate(tier_circuits):
            dns = {}
            for name, idx in c["dn_indices"].items():
                if idx >= 0:
                    dns[name] = offsets[i] + idx
            tier_dn_idx.append(dns)

        # Run simulation, collect per-tier DN activity per timestep
        tier_activity = [[] for _ in range(n_tiers)]

        for step in range(n_steps):
            poisson = (torch.rand_like(rates) < rates * dt / 1000.0).float()
            recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
            I = poisson * pw + recurrent
            v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=dt)
            x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec
            x_syn = x_syn - U_dep * x_syn * spikes

            for t in range(n_tiers):
                total = sum(spikes[0, idx].item() for idx in tier_dn_idx[t].values())
                tier_activity[t].append(total)

        # Score each tier
        tier_scores = {}

        # Tier 1: navigation (total DN spikes)
        t1_total = sum(tier_activity[0])
        tier_scores["tier1_navigation"] = float(t1_total)

        # Tier 2+: prediction accuracy (correlation with tier below)
        for t in range(1, n_tiers):
            predicted = tier_activity[t][:-1]  # Tier t output at time T
            actual = tier_activity[t-1][1:]    # Tier t-1 output at time T+1
            score = f_self_prediction(predicted, actual)
            tier_scores[f"tier{t+1}_prediction"] = float(score)

        key = f"{n_tiers}tier/seed{seed}"
        results[key] = {
            "n_tiers": n_tiers,
            "seed": seed,
            "n_total_neurons": n_total,
            "scores": tier_scores,
            "tier_activity_samples": {
                f"tier{t+1}": tier_activity[t][:20] for t in range(n_tiers)
            },
        }

        logger.info("RESULT: %s: %s", key, tier_scores)

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Saved to %s", outdir)
    return results


# ── Parameter sweeps ──────────────────────────────────────────────────────

def _run_sweep(args):
    """Run parameter sweep experiments."""
    if args.sweep_type == "depression":
        levels = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]
        for u in levels:
            label = f"U{u:.2f}"
            logger.info("=" * 60)
            logger.info("SWEEP: U_dep=%.2f", u)
            logger.info("=" * 60)
            run_experiment(
                arch_names=args.arch,
                fitness_names=["working_memory"],
                seeds=args.seeds,
                n_generations=args.generations,
                n_mutations=args.mutations,
                n_steps=200,
                output_dir=f"{args.output_dir}/depression_{label}",
                sim_params={"U_dep": u, "tau_rec": 800.0},
            )

    elif args.sweep_type == "tau_rec":
        levels = [200.0, 400.0, 800.0, 1200.0, 1600.0]
        for tau in levels:
            label = f"tau{int(tau)}"
            logger.info("=" * 60)
            logger.info("SWEEP: tau_rec=%.0f", tau)
            logger.info("=" * 60)
            run_experiment(
                arch_names=args.arch,
                fitness_names=["working_memory"],
                seeds=args.seeds,
                n_generations=args.generations,
                n_mutations=args.mutations,
                n_steps=200,
                output_dir=f"{args.output_dir}/tau_{label}",
                sim_params={"U_dep": 0.2, "tau_rec": tau},
            )

    elif args.sweep_type == "wm_duration":
        durations = [50, 100, 200, 400, 800]
        for dur in durations:
            label = f"dur{dur}"
            logger.info("=" * 60)
            logger.info("SWEEP: WM duration=%d steps", dur)
            logger.info("=" * 60)
            run_experiment(
                arch_names=args.arch,
                fitness_names=["working_memory"],
                seeds=args.seeds,
                n_generations=args.generations,
                n_mutations=args.mutations,
                n_steps=dur * 2,
                output_dir=f"{args.output_dir}/wm_dur_{label}",
                sim_params={"U_dep": 0.2, "tau_rec": 800.0},
            )


# ── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Architecture evolution experiments")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run")
    run_p.add_argument("--arch", nargs="+", required=True)
    run_p.add_argument("--fitness", nargs="+", default=["navigation"])
    run_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    run_p.add_argument("--generations", type=int, default=50)
    run_p.add_argument("--mutations", type=int, default=10)
    run_p.add_argument("--n-steps", type=int, default=100)
    run_p.add_argument("--output-dir", default="results/architecture_evolution")
    run_p.add_argument("--parallel", type=int, default=1,
                        help="Number of (arch, fitness) pairs to run concurrently. Set to CPU count.")
    run_p.add_argument("--u-dep", type=float, default=None,
                        help="Override synaptic depression U parameter (0.0=none, 0.5=strong)")
    run_p.add_argument("--tau-rec", type=float, default=None,
                        help="Override depression recovery time constant in ms")

    # Sweep subcommand: run working_memory across depression levels
    sweep_p = subparsers.add_parser("sweep", help="Parameter sweep experiments")
    sweep_p.add_argument("--arch", nargs="+", required=True)
    sweep_p.add_argument("--sweep-type", required=True,
                         choices=["depression", "tau_rec", "wm_duration"],
                         help="What to sweep: depression (U_dep 0-0.5), tau_rec (200-1600ms), wm_duration (50-500 steps)")
    sweep_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    sweep_p.add_argument("--generations", type=int, default=50)
    sweep_p.add_argument("--mutations", type=int, default=10)
    sweep_p.add_argument("--output-dir", default="results/sweep")

    # Experiment 6: structured growth
    exp6_p = subparsers.add_parser("structured-growth", help="Exp 6: structured vs random growth stimulation")
    exp6_p.add_argument("--arch", required=True)
    exp6_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    exp6_p.add_argument("--generations", type=int, default=50)
    exp6_p.add_argument("--mutations", type=int, default=10)
    exp6_p.add_argument("--output-dir", default="results/structured_growth")

    # Experiment 7: composite
    exp7_p = subparsers.add_parser("composite", help="Exp 7: composite architecture generation")
    exp7_p.add_argument("--arch-a", required=True)
    exp7_p.add_argument("--arch-b", required=True)
    exp7_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    exp7_p.add_argument("--generations", type=int, default=50)
    exp7_p.add_argument("--mutations", type=int, default=10)
    exp7_p.add_argument("--output-dir", default="results/composite")

    # Experiment 8: scale
    exp8_p = subparsers.add_parser("scale", help="Exp 8: scale sensitivity test")
    exp8_p.add_argument("--arch", required=True)
    exp8_p.add_argument("--scales", type=int, nargs="+", default=[1000, 3000, 8000, 20000])
    exp8_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    exp8_p.add_argument("--generations", type=int, default=50)
    exp8_p.add_argument("--mutations", type=int, default=10)
    exp8_p.add_argument("--output-dir", default="results/scale")

    # Tiered prediction (self-awareness experiment)
    tier_p = subparsers.add_parser("tiered", help="N-tier self-prediction experiment")
    tier_p.add_argument("--tiers", type=int, required=True, choices=[1, 2, 3])
    tier_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    tier_p.add_argument("--n-steps", type=int, default=200)
    tier_p.add_argument("--generations", type=int, default=50)
    tier_p.add_argument("--mutations", type=int, default=10)
    tier_p.add_argument("--output-dir", default="results/tiered")

    # Experiment 9: adaptation
    exp9_p = subparsers.add_parser("adaptation", help="Exp 9: habituation and novelty detection")
    exp9_p.add_argument("--arch", nargs="+", required=True)
    exp9_p.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    exp9_p.add_argument("--output-dir", default="results/adaptation")

    analyze_p = subparsers.add_parser("analyze")
    analyze_p.add_argument("results_dir", default="results/architecture_evolution", nargs="?")

    list_p = subparsers.add_parser("list", help="List available architectures")

    args = parser.parse_args()

    if args.command == "run":
        sim_params = {}
        if args.u_dep is not None:
            sim_params["U_dep"] = args.u_dep
        if args.tau_rec is not None:
            sim_params["tau_rec"] = args.tau_rec
        run_experiment(
            arch_names=args.arch,
            fitness_names=args.fitness,
            seeds=args.seeds,
            n_generations=args.generations,
            n_mutations=args.mutations,
            n_steps=args.n_steps,
            output_dir=args.output_dir,
            parallel=args.parallel,
            sim_params=sim_params if sim_params else None,
        )
    elif args.command == "sweep":
        _run_sweep(args)
    elif args.command == "structured-growth":
        run_structured_growth(
            arch_name=args.arch, seeds=args.seeds,
            n_generations=args.generations, n_mutations=args.mutations,
            output_dir=args.output_dir,
        )
    elif args.command == "composite":
        run_composite(
            arch_a=args.arch_a, arch_b=args.arch_b, seeds=args.seeds,
            n_generations=args.generations, n_mutations=args.mutations,
            output_dir=args.output_dir,
        )
    elif args.command == "scale":
        run_scale_test(
            arch_name=args.arch, scales=args.scales, seeds=args.seeds,
            n_generations=args.generations, n_mutations=args.mutations,
            output_dir=args.output_dir,
        )
    elif args.command == "tiered":
        run_tiered_prediction(
            n_tiers=args.tiers, seeds=args.seeds,
            n_steps=args.n_steps, n_generations=args.generations,
            n_mutations=args.mutations, output_dir=args.output_dir,
        )
    elif args.command == "adaptation":
        run_adaptation_test(
            arch_names=args.arch, seeds=args.seeds,
            output_dir=args.output_dir,
        )
    elif args.command == "analyze":
        analyze_results(args.results_dir)
    elif args.command == "list":
        list_architectures()
    else:
        parser.print_help()
