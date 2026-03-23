#!/usr/bin/env python3
"""
EDGE SWEEP: Systematically test every inter-module edge for every fitness function.
No evolution. No randomness. No path-dependence.

For each edge, scale by 2x and measure fitness change.
Classifies every edge as: frozen (fitness decreases), irrelevant (no change), or evolvable (fitness improves).

This gives us:
1. Complete coverage (all 2450 edges tested, not 641)
2. Deterministic classification (same result every run)
3. True sensitivity map per fitness function
"""
import sys, os
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/autoresearch")

import torch
import numpy as np
import json
import argparse
import time
from pathlib import Path
from brain_body_bridge import BrainEngine

labels = np.load('/home/ubuntu/module_labels_v2.npy')
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
inter_module_edges = sorted([e for e in edge_syn_idx if e[0] != e[1]])
print(f"Total inter-module edges: {len(inter_module_edges)}")

# Synaptic gain multiplier. Validated at 4x-8x (see gain_sensitivity experiment). 7x is optimal.
GAIN = 8.0

def evaluate_brain(brain, stimulus, n_steps=300):
    """Fast evaluation — 300 steps for speed."""
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


def fitness_navigation(dn):
    return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'P9_oDN1_left', 'P9_oDN1_right']) + \
           0.5 * sum(dn.get(n, 0) for n in ['MN9_left', 'MN9_right'])

def fitness_escape(dn):
    return sum(dn.get(n, 0) for n in ['GF_1', 'GF_2']) + \
           sum(dn.get(n, 0) for n in ['MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])

def fitness_turning(dn):
    left = sum(dn.get(n, 0) for n in ['DNa01_left', 'DNa02_left'])
    right = sum(dn.get(n, 0) for n in ['DNa01_right', 'DNa02_right'])
    return abs(left - right) + (left + right) * 0.1

def fitness_arousal(dn):
    return sum(dn.values())


FITNESS_FUNCTIONS = {
    'navigation': ('sugar', fitness_navigation),
    'escape': ('lc4', fitness_escape),
    'turning': ('jo', fitness_turning),
    'arousal': ('sugar', fitness_arousal),
}

# Allow partitioning edges across instances
def run_sweep(fitness_name, start_idx=0, end_idx=None):
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    brain = BrainEngine(device='cpu')
    brain._syn_vals.mul_(GAIN)
    baseline_weights = brain._syn_vals.clone()

    # Measure baseline
    dn_base = evaluate_brain(brain, stimulus)
    baseline = fitness_fn(dn_base)
    print(f"Baseline ({fitness_name}): {baseline:.4f}")

    edges = inter_module_edges[start_idx:end_idx]
    print(f"Sweeping edges {start_idx} to {start_idx + len(edges)} of {len(inter_module_edges)}")

    results = []
    t0 = time.time()

    for i, edge in enumerate(edges):
        syns = edge_syn_idx[edge]

        # Test scale=2.0 (amplify)
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= 2.0
        dn_amp = evaluate_brain(brain, stimulus)
        fitness_amp = fitness_fn(dn_amp)

        # Test scale=0.5 (attenuate)
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= 0.5
        dn_att = evaluate_brain(brain, stimulus)
        fitness_att = fitness_fn(dn_att)

        delta_amp = fitness_amp - baseline
        delta_att = fitness_att - baseline

        # Classify
        if delta_amp > 0 or delta_att > 0:
            classification = "evolvable"
        elif delta_amp < 0 or delta_att < 0:
            classification = "frozen"
        else:
            classification = "irrelevant"

        results.append({
            'pre_module': int(edge[0]),
            'post_module': int(edge[1]),
            'n_synapses': len(syns),
            'delta_amplify': float(delta_amp),
            'delta_attenuate': float(delta_att),
            'fitness_amplify': float(fitness_amp),
            'fitness_attenuate': float(fitness_att),
            'classification': classification,
        })

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = elapsed / (i + 1)
            remaining = rate * (len(edges) - i - 1)
            counts = {'evolvable': 0, 'frozen': 0, 'irrelevant': 0}
            for r in results:
                counts[r['classification']] += 1
            print(f"  [{i+1}/{len(edges)}] {elapsed:.0f}s elapsed, {remaining:.0f}s remaining | {counts}")

    # Reset brain
    brain._syn_vals.copy_(baseline_weights)

    # Summary
    counts = {'evolvable': 0, 'frozen': 0, 'irrelevant': 0}
    for r in results:
        counts[r['classification']] += 1

    total = len(results)
    print(f"\n=== SWEEP RESULTS: {fitness_name} ===")
    print(f"Edges tested: {total}")
    print(f"Frozen: {counts['frozen']} ({100*counts['frozen']/total:.1f}%)")
    print(f"Irrelevant: {counts['irrelevant']} ({100*counts['irrelevant']/total:.1f}%)")
    print(f"Evolvable: {counts['evolvable']} ({100*counts['evolvable']/total:.1f}%)")

    evolvable = [(r['pre_module'], r['post_module']) for r in results if r['classification'] == 'evolvable']
    print(f"Evolvable pairs: {sorted(evolvable)}")

    # Save
    outdir = '/home/ubuntu/bulletproof_results'
    Path(outdir).mkdir(parents=True, exist_ok=True)
    output = {
        'fitness_name': fitness_name,
        'baseline_fitness': baseline,
        'n_edges_tested': total,
        'n_total_edges': len(inter_module_edges),
        'start_idx': start_idx,
        'end_idx': start_idx + len(edges),
        'classification_counts': counts,
        'results': results,
    }
    suffix = f"_{start_idx}_{start_idx + len(edges)}" if end_idx else ""
    with open(f'{outdir}/sweep_{fitness_name}{suffix}.json', 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Saved to {outdir}/sweep_{fitness_name}{suffix}.json")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitness', required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--end', type=int, default=None)
    args = parser.parse_args()
    run_sweep(args.fitness, args.start, args.end)
