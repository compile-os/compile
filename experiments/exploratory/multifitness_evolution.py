#!/usr/bin/env python3
"""
Compile Multi-Fitness Convergent Evolution
Run evolution with spike-based fitness functions to map the brain's complete API surface.

Usage: python3 multifitness_evolution.py --fitness SPEED --seed 42 --gain 8.0
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
import argparse
from pathlib import Path
from brain_body_bridge import BrainEngine, STIMULI, DN_NEURONS

# ─── Fitness Functions ────────────────────────────────────────────────────────
# Each returns a scalar fitness from spike data.
# Higher = better.

def fitness_navigation(brain, dn_spikes_total):
    """Forward walking toward food: maximize P9 drive."""
    p9 = sum(dn_spikes_total.get(n, 0) for n in ['P9_left', 'P9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
    mn9 = sum(dn_spikes_total.get(n, 0) for n in ['MN9_left', 'MN9_right'])
    return p9 + 0.5 * mn9

def fitness_escape(brain, dn_spikes_total):
    """Escape response: maximize Giant Fiber + backward drive."""
    gf = sum(dn_spikes_total.get(n, 0) for n in ['GF_1', 'GF_2'])
    mdn = sum(dn_spikes_total.get(n, 0) for n in ['MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])
    return gf + mdn

def fitness_turning(brain, dn_spikes_total):
    """Turning ability: maximize DNa01/DNa02 asymmetry."""
    left = sum(dn_spikes_total.get(n, 0) for n in ['DNa01_left', 'DNa02_left'])
    right = sum(dn_spikes_total.get(n, 0) for n in ['DNa01_right', 'DNa02_right'])
    return abs(left - right) + (left + right) * 0.1  # Reward asymmetry + some baseline activity

def fitness_arousal(brain, dn_spikes_total):
    """General arousal: maximize total DN output."""
    return sum(dn_spikes_total.values())

def fitness_efficiency(brain, dn_spikes_total):
    """Efficiency: maximize P9 forward drive while minimizing total activity."""
    p9 = sum(dn_spikes_total.get(n, 0) for n in ['P9_left', 'P9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
    total = sum(dn_spikes_total.values()) + 1
    return p9 / total

def fitness_inhibition(brain, dn_spikes_total):
    """Motor inhibition: minimize ALL motor output (freeze response)."""
    total = sum(dn_spikes_total.values())
    return -total  # Less output = higher fitness

FITNESS_FUNCTIONS = {
    'navigation': ('sugar', fitness_navigation),
    'escape': ('lc4', fitness_escape),
    'turning': ('jo', fitness_turning),
    'arousal': ('sugar', fitness_arousal),
    'efficiency': ('sugar', fitness_efficiency),
    'inhibition': ('bitter', fitness_inhibition),
}

# ─── Brain Evaluation ─────────────────────────────────────────────────────────

def evaluate_brain(brain, stimulus, n_steps=300, gain=8.0):
    """Run brain simulation and return DN spike counts."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    # Count spikes per DN neuron across all steps
    dn_spikes = {name: 0 for name in brain.dn_indices}
    total_network_spikes = 0

    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)  # Direct from state, not _spike_acc
        for name, idx in brain.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
        total_network_spikes += int(spk.sum().item())

    return dn_spikes, total_network_spikes

# ─── Evolution ────────────────────────────────────────────────────────────────

def run_evolution(fitness_name, seed, gain=8.0, n_generations=50, n_mutations=5,
                  n_steps=300, output_dir='/home/ubuntu/multifitness_results'):
    """Run evolution for one fitness function and seed."""
    np.random.seed(seed)
    torch.manual_seed(seed)

    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Initialize brain
    brain = BrainEngine(device='cpu')

    # Amplify weights for signal propagation
    original_weights = brain._syn_vals.clone()
    brain._syn_vals.mul_(gain)

    # Load module labels
    labels = np.load('/home/ubuntu/module_labels_v2.npy')

    # Build module-edge index
    import pandas as pd
    df = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')
    pre_mods = labels[df['Presynaptic_Index'].values].astype(int)
    post_mods = labels[df['Postsynaptic_Index'].values].astype(int)

    # Synapse indices per module edge
    edge_syn_idx = {}
    for i in range(len(df)):
        edge = (int(pre_mods[i]), int(post_mods[i]))
        if edge not in edge_syn_idx:
            edge_syn_idx[edge] = []
        edge_syn_idx[edge].append(i)

    inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]
    print("Inter-module edges: %d" % len(inter_module_edges))

    # Baseline fitness
    dn_spikes, total_spikes = evaluate_brain(brain, stimulus, n_steps, gain)
    baseline_fitness = fitness_fn(brain, dn_spikes)
    current_fitness = baseline_fitness
    print("Baseline fitness (%s): %.4f (total_spikes=%d, dn_spikes=%s)" % (
        fitness_name, baseline_fitness, total_spikes,
        {k: v for k, v in dn_spikes.items() if v > 0}))

    # Evolution loop
    all_mutations = []
    accepted_count = 0

    for gen in range(n_generations):
        gen_accepted = 0
        for mut_i in range(n_mutations):
            # Pick random inter-module edge
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syn_indices = edge_syn_idx[edge]
            n_syn = len(syn_indices)

            # Save old weights
            old_vals = brain._syn_vals[syn_indices].clone()

            # Mutate: scale weights on this edge
            scale = np.random.uniform(0.3, 3.0)
            brain._syn_vals[syn_indices] = old_vals * scale

            # Evaluate
            dn_new, total_new = evaluate_brain(brain, stimulus, n_steps, gain)
            new_fitness = fitness_fn(brain, dn_new)

            accepted = new_fitness > current_fitness
            delta = new_fitness - current_fitness

            # Record mutation
            mutation_record = {
                'seed': int(seed),
                'generation': gen,
                'mutation_index': mut_i,
                'pre_module': int(edge[0]),
                'post_module': int(edge[1]),
                'n_synapses': n_syn,
                'scale': float(scale),
                'fitness_before': float(current_fitness),
                'fitness_after': float(new_fitness),
                'delta': float(delta),
                'accepted': accepted,
                'dn_spikes': {k: int(v) for k, v in dn_new.items() if v > 0},
                'total_spikes': total_new,
            }
            all_mutations.append(mutation_record)

            if accepted:
                current_fitness = new_fitness
                gen_accepted += 1
                accepted_count += 1
            else:
                # Revert
                brain._syn_vals[syn_indices] = old_vals

            # Progress
            status = "ACCEPTED" if accepted else "rejected"
            print("  Gen%d M%d: %d->%d nsyn=%d scale=%.2f f=%.4f Δ=%.4f %s" % (
                gen, mut_i, edge[0], edge[1], n_syn, scale,
                new_fitness, delta, status))

        print("Gen %d: fitness=%.4f accepted=%d/%d total=%d" % (
            gen, current_fitness, gen_accepted, n_mutations,
            len(all_mutations)))

        # Save intermediate results every 10 generations
        if (gen + 1) % 10 == 0:
            outfile = '%s/%s_seed%d_intermediate.json' % (output_dir, fitness_name, seed)
            with open(outfile, 'w') as f:
                json.dump({
                    'fitness_name': fitness_name,
                    'seed': seed,
                    'gain': gain,
                    'baseline_fitness': baseline_fitness,
                    'current_fitness': current_fitness,
                    'generations_complete': gen + 1,
                    'total_accepted': accepted_count,
                    'total_mutations': len(all_mutations),
                    'mutations': all_mutations,
                }, f)

    # Save final results
    outfile = '%s/%s_seed%d_final.json' % (output_dir, fitness_name, seed)
    result = {
        'fitness_name': fitness_name,
        'seed': seed,
        'gain': gain,
        'n_steps': n_steps,
        'n_generations': n_generations,
        'n_mutations_per_gen': n_mutations,
        'baseline_fitness': baseline_fitness,
        'final_fitness': current_fitness,
        'improvement': current_fitness - baseline_fitness,
        'total_accepted': accepted_count,
        'total_mutations': len(all_mutations),
        'mutations': all_mutations,
    }
    with open(outfile, 'w') as f:
        json.dump(result, f, indent=2)
    print("\nDone! Saved to %s" % outfile)
    print("Final fitness: %.4f (%.2f%% improvement)" % (
        current_fitness,
        100 * (current_fitness - baseline_fitness) / max(abs(baseline_fitness), 0.001)))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitness', required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--gain', type=float, default=8.0)
    parser.add_argument('--generations', type=int, default=50)
    parser.add_argument('--mutations', type=int, default=5)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--output', default='/home/ubuntu/multifitness_results')
    args = parser.parse_args()

    run_evolution(args.fitness, args.seed, args.gain,
                  args.generations, args.mutations, args.steps, args.output)
