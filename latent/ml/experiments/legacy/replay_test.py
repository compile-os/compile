#!/usr/bin/env python3
"""
REPLAY TEST: Apply known evolution recipes to a fresh brain and verify behavior changes.

For each behavior (navigation, escape, turning, arousal):
1. Measure baseline DN activity
2. Apply the known evolvable pair mutations (scale factors from evolution)
3. Measure DN activity after
4. Check: did the TARGET behavior improve? Did OTHER behaviors stay the same?

This proves the programming language works — specific connections produce predictable behavior changes.
"""
import sys, os
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/autoresearch")

import torch
import numpy as np
import json
import time
from brain_body_bridge import BrainEngine

# Load module labels and mutation data
labels = np.load('/home/ubuntu/module_labels_v2.npy')
mf_data = json.load(open('/home/ubuntu/multifitness_results/../compile_platform_data.json', 'r')
                     if os.path.exists('/home/ubuntu/compile_platform_data.json')
                     else open('/home/ubuntu/multifitness_results/navigation_seed42_final.json'))

# Try loading the consolidated data
data_path = None
for p in ['/home/ubuntu/compile_platform_data.json',
          '/home/ubuntu/multifitness_results/compile_platform_data.json']:
    if os.path.exists(p):
        data_path = p
        break

if data_path:
    mf_data = json.load(open(data_path))
else:
    # Build from individual files
    print("Building from individual result files...")
    mf_data = {"fitness_functions": {}}
    import glob
    for f in glob.glob('/home/ubuntu/multifitness_results/*_final.json'):
        d = json.load(open(f))
        name = d['fitness_name']
        if name not in mf_data['fitness_functions']:
            mf_data['fitness_functions'][name] = {'evolvable_pairs': [], 'all_mutations': []}
        for m in d['mutations']:
            if m['accepted']:
                pair_key = (m['pre_module'], m['post_module'])
                existing = [p for p in mf_data['fitness_functions'][name]['evolvable_pairs']
                           if p['pre_module'] == m['pre_module'] and p['post_module'] == m['post_module']]
                if not existing:
                    mf_data['fitness_functions'][name]['evolvable_pairs'].append({
                        'pre_module': m['pre_module'],
                        'post_module': m['post_module'],
                        'n_synapses': m['n_synapses'],
                        'best_delta': m['delta'],
                        'best_scale': m['scale'],
                    })

# Build module-edge synapse index
import pandas as pd
df = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')
pre_mods = labels[df['Presynaptic_Index'].values].astype(int)
post_mods = labels[df['Postsynaptic_Index'].values].astype(int)

edge_syn_idx = {}
for i in range(len(df)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)

# Fitness measurement functions
STIMULI_FOR_BEHAVIOR = {
    'navigation': 'sugar',
    'escape': 'lc4',
    'turning': 'jo',
    'arousal': 'sugar',
}

def measure_dn_activity(brain, stimulus, n_steps=300):
    """Run brain sim and return DN spike counts."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    dn_spikes = {name: 0 for name in brain.dn_indices}
    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for name, idx in brain.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
    return dn_spikes

def compute_fitness(dn_spikes, behavior):
    """Same fitness functions as evolution."""
    if behavior == 'navigation':
        p9 = sum(dn_spikes.get(n, 0) for n in ['P9_left', 'P9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
        mn9 = sum(dn_spikes.get(n, 0) for n in ['MN9_left', 'MN9_right'])
        return p9 + 0.5 * mn9
    elif behavior == 'escape':
        gf = sum(dn_spikes.get(n, 0) for n in ['GF_1', 'GF_2'])
        mdn = sum(dn_spikes.get(n, 0) for n in ['MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])
        return gf + mdn
    elif behavior == 'turning':
        left = sum(dn_spikes.get(n, 0) for n in ['DNa01_left', 'DNa02_left'])
        right = sum(dn_spikes.get(n, 0) for n in ['DNa01_right', 'DNa02_right'])
        return abs(left - right) + (left + right) * 0.1
    elif behavior == 'arousal':
        return sum(dn_spikes.values())
    return 0

# Initialize brain with gain amplification
GAIN = 8.0
brain = BrainEngine(device='cpu')
original_weights = brain._syn_vals.clone()
brain._syn_vals.mul_(GAIN)
amplified_baseline = brain._syn_vals.clone()

print("=" * 70)
print("REPLAY TEST: Can we program the fly brain?")
print("=" * 70)

# Measure baseline for all behaviors
print("\n--- BASELINE (unmodified brain) ---")
baselines = {}
for behavior in ['navigation', 'escape', 'turning', 'arousal']:
    stimulus = STIMULI_FOR_BEHAVIOR[behavior]
    brain._syn_vals.copy_(amplified_baseline)  # reset to baseline
    dn = measure_dn_activity(brain, stimulus)
    fitness = compute_fitness(dn, behavior)
    baselines[behavior] = fitness
    active_dns = {k: v for k, v in dn.items() if v > 0}
    print("  %s (stim=%s): fitness=%.1f  dns=%s" % (behavior, stimulus, fitness, active_dns))

# For each behavior, apply its recipe and measure ALL behaviors
print("\n" + "=" * 70)
print("APPLYING RECIPES")
print("=" * 70)

results = {}

for target_behavior in ['navigation', 'escape', 'turning', 'arousal']:
    ff = mf_data.get('fitness_functions', {}).get(target_behavior, {})
    pairs = ff.get('evolvable_pairs', [])

    if not pairs:
        print("\n--- %s: NO RECIPE (0 evolvable pairs) ---" % target_behavior.upper())
        continue

    print("\n--- Applying %s recipe (%d connections) ---" % (target_behavior.upper(), len(pairs)))

    # Reset to baseline
    brain._syn_vals.copy_(amplified_baseline)

    # Apply each evolvable pair's scale factor
    applied = []
    for pair in pairs:
        src, tgt = pair['pre_module'], pair['post_module']
        scale = pair['best_scale']
        edge = (src, tgt)
        syn_indices = edge_syn_idx.get(edge, [])
        if syn_indices:
            brain._syn_vals[syn_indices] *= scale
            applied.append("%d→%d (×%.2f, %d synapses)" % (src, tgt, scale, len(syn_indices)))
            print("  Applied: %d→%d scale=%.2f (%d synapses)" % (src, tgt, scale, len(syn_indices)))

    # Now measure ALL behaviors with this modification
    behavior_results = {}
    for measure_behavior in ['navigation', 'escape', 'turning', 'arousal']:
        stimulus = STIMULI_FOR_BEHAVIOR[measure_behavior]
        dn = measure_dn_activity(brain, stimulus)
        fitness = compute_fitness(dn, measure_behavior)
        baseline = baselines[measure_behavior]
        change = fitness - baseline
        pct = 100 * change / max(abs(baseline), 0.001)
        behavior_results[measure_behavior] = {
            'fitness': fitness,
            'baseline': baseline,
            'change': change,
            'pct_change': pct,
        }
        marker = "✓ TARGET" if measure_behavior == target_behavior else ""
        direction = "↑" if change > 0 else "↓" if change < 0 else "="
        print("  %s %s: %.1f → %.1f (%s%.1f, %+.0f%%) %s" % (
            direction, measure_behavior, baseline, fitness,
            "+" if change > 0 else "", change, pct, marker))

    results[target_behavior] = behavior_results

# Summary
print("\n" + "=" * 70)
print("SUMMARY: Does programming work?")
print("=" * 70)

print("\n%-12s | %-15s | %-15s | %-15s | %-15s" % ("Recipe", "Navigation", "Escape", "Turning", "Arousal"))
print("-" * 78)

for recipe in ['navigation', 'escape', 'turning', 'arousal']:
    if recipe not in results:
        continue
    row = "%-12s |" % recipe
    for behavior in ['navigation', 'escape', 'turning', 'arousal']:
        r = results[recipe][behavior]
        is_target = recipe == behavior
        marker = " *" if is_target else ""
        row += " %+6.0f%%%s%s |" % (r['pct_change'], marker, " " * (8 - len(marker)))
    print(row)

print("\n* = target behavior (should improve)")
print("Other columns should ideally stay near 0% (no interference)")

# Save results
output = {
    'baselines': baselines,
    'recipes': {},
}
for recipe, behavior_results in results.items():
    ff = mf_data.get('fitness_functions', {}).get(recipe, {})
    pairs = ff.get('evolvable_pairs', [])
    output['recipes'][recipe] = {
        'connections': [{'src': p['pre_module'], 'tgt': p['post_module'], 'scale': p['best_scale']} for p in pairs],
        'results': behavior_results,
    }

with open('/home/ubuntu/multifitness_results/replay_test.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nSaved to /home/ubuntu/multifitness_results/replay_test.json")
