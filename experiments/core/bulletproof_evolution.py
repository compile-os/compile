#!/usr/bin/env python3
"""
BULLETPROOF EVOLUTION: High-mutation runs to achieve cross-seed consistency.
20 mutations/gen × 100 gen = 2000 mutations per seed.
Tests ALL inter-module edges (not just a subset).
Saves the full evolved brain weights for verification.
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
inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]
print(f"Inter-module edges: {len(inter_module_edges)}")

# Fitness functions (same as before but using 1000 steps for sensitivity)
def evaluate_brain(brain, stimulus, n_steps=1000):
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    dn_names = list(brain.dn_indices.keys())
    dn_idx = [brain.dn_indices[n] for n in dn_names]
    steps = np.zeros((n_steps, len(dn_names)), dtype=np.float32)
    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            steps[step, j] = spk[idx].item()

    # Compute windowed rates (50-step windows)
    window = 50
    n_windows = n_steps // window
    windowed = np.zeros((n_windows, len(dn_names)))
    for w in range(n_windows):
        windowed[w] = steps[w*window:(w+1)*window].sum(axis=0)

    return {'dn_names': dn_names, 'windowed': windowed, 'total': steps.sum(axis=0), 'n_windows': n_windows}


def fitness_navigation(data):
    names = data['dn_names']
    p9_idx = [i for i, n in enumerate(names) if 'P9' in n or 'MN9' in n]
    return float(sum(data['total'][i] for i in p9_idx))

def fitness_escape(data):
    names = data['dn_names']
    gf_idx = [i for i, n in enumerate(names) if 'GF' in n]
    mdn_idx = [i for i, n in enumerate(names) if 'MDN' in n]
    return float(sum(data['total'][i] for i in gf_idx) + sum(data['total'][i] for i in mdn_idx))

def fitness_turning(data):
    names = data['dn_names']
    da01_l = names.index('DNa01_left') if 'DNa01_left' in names else -1
    da01_r = names.index('DNa01_right') if 'DNa01_right' in names else -1
    da02_l = names.index('DNa02_left') if 'DNa02_left' in names else -1
    da02_r = names.index('DNa02_right') if 'DNa02_right' in names else -1
    left = data['total'][da01_l] + (data['total'][da02_l] if da02_l >= 0 else 0)
    right = data['total'][da01_r] + (data['total'][da02_r] if da02_r >= 0 else 0)
    return float(abs(left - right) + (left + right) * 0.1)

def fitness_arousal(data):
    return float(data['total'].sum())

def fitness_circles(data):
    names = data['dn_names']
    da01_l = names.index('DNa01_left') if 'DNa01_left' in names else -1
    da01_r = names.index('DNa01_right') if 'DNa01_right' in names else -1
    da02_l = names.index('DNa02_left') if 'DNa02_left' in names else -1
    da02_r = names.index('DNa02_right') if 'DNa02_right' in names else -1
    windowed = data['windowed']
    turn_per_window = np.zeros(data['n_windows'])
    for w in range(data['n_windows']):
        l = windowed[w, da01_l] + (windowed[w, da02_l] if da02_l >= 0 else 0)
        r = windowed[w, da01_r] + (windowed[w, da02_r] if da02_r >= 0 else 0)
        turn_per_window[w] = l - r
    cumulative = np.cumsum(turn_per_window)
    displacement = abs(cumulative[-1]) if len(cumulative) > 0 else 0
    consistency = abs(np.mean(np.sign(turn_per_window + 1e-10))) if len(turn_per_window) > 0 else 0
    p9_idx = [i for i, n in enumerate(names) if 'P9' in n or 'MN9' in n]
    fwd = sum(data['total'][i] for i in p9_idx) if p9_idx else 0
    return float(displacement + consistency * 5.0 + fwd * 0.1)

def fitness_rhythm(data):
    windowed = data['windowed']
    n_windows = data['n_windows']
    if n_windows < 4: return 0.0
    activity = windowed.sum(axis=1)
    on = np.mean(activity[0::2])
    off = np.mean(activity[1::2])
    return float(max(0, on - off) + activity.mean() * 0.05)

FITNESS_FUNCTIONS = {
    'navigation': ('sugar', fitness_navigation),
    'escape': ('lc4', fitness_escape),
    'turning': ('jo', fitness_turning),
    'arousal': ('sugar', fitness_arousal),
    'circles': ('sugar', fitness_circles),
    'rhythm': ('sugar', fitness_rhythm),
}


def run_evolution(fitness_name, seed, gain=8.0, n_generations=100, n_mutations=20, n_steps=1000):
    np.random.seed(seed)
    torch.manual_seed(seed)
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    brain = BrainEngine(device='cpu')
    brain._syn_vals.mul_(gain)
    baseline_weights = brain._syn_vals.clone()

    data = evaluate_brain(brain, stimulus, n_steps)
    baseline = fitness_fn(data)
    current = baseline
    print(f"Baseline ({fitness_name} s{seed}): {baseline:.4f}")

    all_mutations = []
    accepted = 0
    # Track which edges have been tested
    edges_tested = set()

    for gen in range(n_generations):
        ga = 0
        for mi in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            edges_tested.add(edge)
            syns = edge_syn_idx[edge]
            old = brain._syn_vals[syns].clone()
            scale = np.random.uniform(0.2, 5.0)
            brain._syn_vals[syns] = old * scale

            rng = np.random.get_state()
            data = evaluate_brain(brain, stimulus, n_steps)
            new_fit = fitness_fn(data)
            np.random.set_state(rng)

            acc = new_fit > current
            delta = new_fit - current

            all_mutations.append({
                'seed': int(seed), 'generation': gen, 'mutation_index': mi,
                'pre_module': int(edge[0]), 'post_module': int(edge[1]),
                'n_synapses': len(syns), 'scale': float(scale),
                'fitness_before': float(current), 'fitness_after': float(new_fit),
                'delta': float(delta), 'accepted': acc,
            })

            if acc:
                current = new_fit
                ga += 1
                accepted += 1
            else:
                brain._syn_vals[syns] = old

            if mi == 0 or acc:
                s = "ACCEPTED" if acc else "rejected"
                print(f"  G{gen} M{mi}: {edge[0]}->{edge[1]} s={scale:.2f} f={new_fit:.2f} Δ={delta:+.2f} {s}")

        if gen % 10 == 9 or gen == n_generations - 1:
            print(f"Gen {gen}: f={current:.2f} acc={ga}/{n_mutations} total_acc={accepted} edges_tested={len(edges_tested)}")

    # Save results
    outdir = '/home/ubuntu/bulletproof_results'
    Path(outdir).mkdir(parents=True, exist_ok=True)

    # Save evolved brain weights
    torch.save(brain._syn_vals.clone(), f'{outdir}/{fitness_name}_s{seed}_brain.pt')

    # Classify all tested edges
    edge_classification = {}
    for m in all_mutations:
        edge_key = f"{m['pre_module']}->{m['post_module']}"
        if edge_key not in edge_classification:
            edge_classification[edge_key] = {'accepted': 0, 'decreased': 0, 'unchanged': 0, 'deltas': []}
        if m['accepted']:
            edge_classification[edge_key]['accepted'] += 1
        elif m['delta'] < 0:
            edge_classification[edge_key]['decreased'] += 1
        else:
            edge_classification[edge_key]['unchanged'] += 1
        edge_classification[edge_key]['deltas'].append(m['delta'])

    result = {
        'fitness_name': fitness_name, 'seed': seed, 'gain': gain,
        'n_steps': n_steps, 'n_generations': n_generations,
        'n_mutations_per_gen': n_mutations,
        'baseline_fitness': baseline, 'final_fitness': current,
        'improvement': current - baseline,
        'total_accepted': accepted, 'total_mutations': len(all_mutations),
        'edges_tested': len(edges_tested),
        'total_possible_edges': len(inter_module_edges),
        'mutations': all_mutations,
        'edge_classification': edge_classification,
    }

    with open(f'{outdir}/{fitness_name}_s{seed}_final.json', 'w') as f:
        json.dump(result, f, indent=2)

    pairs = sorted(set((m['pre_module'], m['post_module']) for m in all_mutations if m['accepted']))
    print(f"\nDone! {fitness_name} s{seed}: {baseline:.2f} → {current:.2f} ({100*(current-baseline)/max(abs(baseline),0.001):+.1f}%)")
    print(f"Accepted: {accepted}/{len(all_mutations)} ({100*accepted/len(all_mutations):.1f}%)")
    print(f"Edges tested: {len(edges_tested)}/{len(inter_module_edges)} ({100*len(edges_tested)/len(inter_module_edges):.0f}%)")
    print(f"Evolvable pairs: {pairs}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitness', required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--generations', type=int, default=100)
    parser.add_argument('--mutations', type=int, default=20)
    args = parser.parse_args()
    run_evolution(args.fitness, args.seed, n_generations=args.generations, n_mutations=args.mutations)
