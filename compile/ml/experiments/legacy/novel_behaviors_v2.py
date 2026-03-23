#!/usr/bin/env python3
"""
NOVEL BEHAVIOR COMPILATION v2
- Continuous fitness (float, not integer spike counts)
- Longer simulations (1000 steps) for more spike accumulation
- Windowed rate measurement instead of raw counts
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


def evaluate_brain(brain, stimulus, n_steps=1000):
    """Run brain and return windowed DN spike RATES (continuous)."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    # Collect per-step DN spikes
    dn_names = list(brain.dn_indices.keys())
    dn_indices = [brain.dn_indices[n] for n in dn_names]
    steps_data = np.zeros((n_steps, len(dn_names)), dtype=np.float32)

    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_indices):
            steps_data[step, j] = spk[idx].item()

    # Compute windowed rates (50-step windows = 5ms windows)
    window = 50
    n_windows = n_steps // window
    windowed = np.zeros((n_windows, len(dn_names)))
    for w in range(n_windows):
        windowed[w] = steps_data[w*window:(w+1)*window].sum(axis=0)

    return {
        'dn_names': dn_names,
        'windowed_rates': windowed,  # (n_windows, n_dns) - spike count per window
        'total_spikes': steps_data.sum(axis=0),  # total per DN
        'n_windows': n_windows,
    }


def fitness_circles(data):
    """Sustained rotation: maximize consistent turning asymmetry.

    Use windowed turn signal. Reward consistency (same direction every window)
    plus magnitude (stronger turning).
    """
    names = data['dn_names']
    rates = data['windowed_rates']

    # Find DNa indices
    da01_l = names.index('DNa01_left') if 'DNa01_left' in names else -1
    da01_r = names.index('DNa01_right') if 'DNa01_right' in names else -1
    da02_l = names.index('DNa02_left') if 'DNa02_left' in names else -1
    da02_r = names.index('DNa02_right') if 'DNa02_right' in names else -1

    if da01_l < 0: return 0.0

    # Per-window turn signal
    turn_per_window = np.zeros(data['n_windows'])
    for w in range(data['n_windows']):
        left = rates[w, da01_l] + (rates[w, da02_l] if da02_l >= 0 else 0)
        right = rates[w, da01_r] + (rates[w, da02_r] if da02_r >= 0 else 0)
        turn_per_window[w] = left - right  # positive = left turn

    # Cumulative angular displacement
    cumulative = np.cumsum(turn_per_window)
    total_displacement = abs(cumulative[-1]) if len(cumulative) > 0 else 0

    # Consistency bonus: reward if all windows turn the same direction
    if len(turn_per_window) > 0 and np.std(turn_per_window) > 0:
        sign_consistency = abs(np.mean(np.sign(turn_per_window + 1e-10)))  # 1.0 if all same sign
    else:
        sign_consistency = 0

    # Total forward drive (fly needs to actually move, not just sit and turn)
    p9_indices = [i for i, n in enumerate(names) if 'P9' in n or 'MN9' in n]
    forward_drive = sum(data['total_spikes'][i] for i in p9_indices) if p9_indices else 0

    return float(total_displacement + sign_consistency * 5.0 + forward_drive * 0.1)


def fitness_rhythm(data):
    """Rhythmic alternation: reward contrast between active and quiet periods.

    Windows alternate: odd = should be active, even = should be quiet.
    Continuous fitness based on rate differences.
    """
    rates = data['windowed_rates']
    n_windows = data['n_windows']

    if n_windows < 4:
        return 0.0

    # Total activity per window (all DNs)
    activity = rates.sum(axis=1)  # shape: (n_windows,)

    # Split into "on" windows (0, 2, 4...) and "off" windows (1, 3, 5...)
    on_activity = activity[0::2].mean() if len(activity[0::2]) > 0 else 0
    off_activity = activity[1::2].mean() if len(activity[1::2]) > 0 else 0

    # Reward contrast (on > off) and total activity (not dead)
    contrast = float(on_activity - off_activity)
    total = float(activity.mean())

    return max(0, contrast) + total * 0.05


FITNESS_FUNCTIONS = {
    'circles': ('sugar', fitness_circles),
    'rhythm': ('sugar', fitness_rhythm),
}


def run_evolution(fitness_name, seed, gain=8.0, n_generations=50, n_mutations=5, n_steps=1000):
    np.random.seed(seed)
    torch.manual_seed(seed)
    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    brain = BrainEngine(device='cpu')
    brain._syn_vals.mul_(gain)

    data = evaluate_brain(brain, stimulus, n_steps)
    baseline = fitness_fn(data)
    current = baseline
    print("Baseline (%s s%d): %.4f" % (fitness_name, seed, baseline))

    all_mutations = []
    accepted = 0

    for gen in range(n_generations):
        ga = 0
        for mi in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syns = edge_syn_idx[edge]
            old = brain._syn_vals[syns].clone()
            scale = np.random.uniform(0.2, 5.0)  # wider range
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

            s = "ACCEPTED" if acc else "rejected"
            print("  G%d M%d: %d->%d s=%.2f f=%.2f Δ=%+.2f %s" % (
                gen, mi, edge[0], edge[1], scale, new_fit, delta, s))

        print("Gen %d: f=%.2f acc=%d/%d total_acc=%d" % (gen, current, ga, n_mutations, accepted))

    outdir = '/home/ubuntu/multifitness_results'
    Path(outdir).mkdir(parents=True, exist_ok=True)
    result = {
        'fitness_name': fitness_name, 'seed': seed, 'gain': gain,
        'n_steps': n_steps, 'n_generations': n_generations,
        'baseline_fitness': baseline, 'final_fitness': current,
        'improvement': current - baseline,
        'total_accepted': accepted, 'total_mutations': len(all_mutations),
        'mutations': all_mutations,
    }
    outfile = '%s/%s_seed%d_final.json' % (outdir, fitness_name, seed)
    with open(outfile, 'w') as f:
        json.dump(result, f, indent=2)

    pairs = sorted(set((m['pre_module'], m['post_module']) for m in all_mutations if m['accepted']))
    print("\nDone! %s s%d: %.2f → %.2f (%+.1f%%)" % (
        fitness_name, seed, baseline, current,
        100 * (current - baseline) / max(abs(baseline), 0.001)))
    print("Evolvable pairs: %s" % pairs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitness', required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--generations', type=int, default=50)
    args = parser.parse_args()
    run_evolution(args.fitness, args.seed, n_generations=args.generations)
