#!/usr/bin/env python3
"""
NOVEL BEHAVIOR COMPILATION: Prove the compiler works on arbitrary inputs.

Behavior 1: CIRCLES — sustained rotational locomotion (total angular displacement)
Behavior 2: RHYTHM — walk 3 seconds, stop 1 second, repeat (alternating movement/stillness)

These have never been evolved for. If evolution finds distinct connection sets,
the compiler works on arbitrary programs.
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
from brain_body_bridge import BrainEngine

# Load module labels
labels = np.load('/home/ubuntu/module_labels_v2.npy')

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

inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]

# ── FITNESS FUNCTIONS ──────────────────────────────────────────────────────

def evaluate_brain(brain, stimulus, n_steps=300):
    """Run brain sim and return per-step DN spike vectors."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    step_data = []
    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        dn_step = {}
        for name, idx in brain.dn_indices.items():
            dn_step[name] = int(spk[idx].item())
        step_data.append(dn_step)
    return step_data


def fitness_circles(step_data):
    """Sustained rotation: maximize asymmetric turning over entire simulation.

    Fitness = total |left_turn - right_turn| accumulated over all steps.
    A fly turning consistently in one direction scores high.
    A fly that turns left then right (zigzag) scores low.
    """
    cumulative_angle = 0.0
    running_direction = 0.0

    for step in step_data:
        left = step.get('DNa01_left', 0) + step.get('DNa02_left', 0)
        right = step.get('DNa01_right', 0) + step.get('DNa02_right', 0)
        # Signed turn signal: positive = left, negative = right
        turn = left - right
        running_direction += turn

    # Reward total angular displacement (absolute value of cumulative turning)
    # Plus a bonus for consistent direction (penalize reversals)
    return abs(running_direction)


def fitness_rhythm(step_data):
    """Rhythmic behavior: alternating activity and stillness.

    Divide simulation into windows of 75 steps (~7.5ms each).
    Odd windows should have HIGH total DN activity.
    Even windows should have LOW total DN activity.
    Fitness = contrast between active and quiet windows.
    """
    window_size = 75  # 4 windows in 300 steps
    n_windows = len(step_data) // window_size

    window_activity = []
    for w in range(n_windows):
        start = w * window_size
        end = start + window_size
        total = 0
        for step in step_data[start:end]:
            total += sum(step.values())
        window_activity.append(total)

    if len(window_activity) < 2:
        return 0.0

    # Odd windows (0, 2) should be active, even windows (1, 3) should be quiet
    active_sum = sum(window_activity[i] for i in range(0, len(window_activity), 2))
    quiet_sum = sum(window_activity[i] for i in range(1, len(window_activity), 2))

    # Reward high contrast: active windows should have MORE activity than quiet ones
    contrast = active_sum - quiet_sum
    # Also reward having SOME activity (don't reward a dead brain)
    total_activity = sum(window_activity)

    return max(0, contrast) + total_activity * 0.1


FITNESS_FUNCTIONS = {
    'circles': ('sugar', fitness_circles),    # sugar stimulus, optimize for rotation
    'rhythm': ('sugar', fitness_rhythm),       # sugar stimulus, optimize for rhythmic pattern
}


# ── EVOLUTION ──────────────────────────────────────────────────────────────

def run_evolution(fitness_name, seed, gain=8.0, n_generations=50, n_mutations=5, n_steps=300):
    np.random.seed(seed)
    torch.manual_seed(seed)

    stimulus, fitness_fn = FITNESS_FUNCTIONS[fitness_name]

    brain = BrainEngine(device='cpu')
    original_weights = brain._syn_vals.clone()
    brain._syn_vals.mul_(gain)

    # Baseline
    step_data = evaluate_brain(brain, stimulus, n_steps)
    baseline_fitness = fitness_fn(step_data)
    current_fitness = baseline_fitness
    print("Baseline fitness (%s): %.4f" % (fitness_name, baseline_fitness))

    all_mutations = []
    accepted_count = 0

    for gen in range(n_generations):
        gen_accepted = 0
        for mut_i in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syn_indices = edge_syn_idx[edge]

            old_vals = brain._syn_vals[syn_indices].clone()
            scale = np.random.uniform(0.3, 3.0)
            brain._syn_vals[syn_indices] = old_vals * scale

            rng_state = np.random.get_state()
            step_data = evaluate_brain(brain, stimulus, n_steps)
            new_fitness = fitness_fn(step_data)
            np.random.set_state(rng_state)

            accepted = new_fitness > current_fitness
            delta = new_fitness - current_fitness

            all_mutations.append({
                'seed': int(seed),
                'generation': gen,
                'mutation_index': mut_i,
                'pre_module': int(edge[0]),
                'post_module': int(edge[1]),
                'n_synapses': len(syn_indices),
                'scale': float(scale),
                'fitness_before': float(current_fitness),
                'fitness_after': float(new_fitness),
                'delta': float(delta),
                'accepted': accepted,
            })

            if accepted:
                current_fitness = new_fitness
                gen_accepted += 1
                accepted_count += 1
            else:
                brain._syn_vals[syn_indices] = old_vals

            status = "ACCEPTED" if accepted else "rejected"
            print("  Gen%d M%d: %d->%d scale=%.2f f=%.1f Δ=%.1f %s" % (
                gen, mut_i, edge[0], edge[1], scale, new_fitness, delta, status))

        print("Gen %d: fitness=%.1f accepted=%d/%d" % (gen, current_fitness, gen_accepted, n_mutations))

    # Save
    outdir = '/home/ubuntu/multifitness_results'
    Path(outdir).mkdir(parents=True, exist_ok=True)
    result = {
        'fitness_name': fitness_name,
        'seed': seed,
        'gain': gain,
        'n_steps': n_steps,
        'n_generations': n_generations,
        'baseline_fitness': baseline_fitness,
        'final_fitness': current_fitness,
        'improvement': current_fitness - baseline_fitness,
        'total_accepted': accepted_count,
        'total_mutations': len(all_mutations),
        'mutations': all_mutations,
    }
    outfile = '%s/%s_seed%d_final.json' % (outdir, fitness_name, seed)
    with open(outfile, 'w') as f:
        json.dump(result, f, indent=2)
    print("\nDone! %s seed %d: %.1f → %.1f (%+.1f%%)" % (
        fitness_name, seed, baseline_fitness, current_fitness,
        100 * (current_fitness - baseline_fitness) / max(abs(baseline_fitness), 0.001)))

    # Print evolvable pairs
    accepted_pairs = set()
    for m in all_mutations:
        if m['accepted']:
            accepted_pairs.add((m['pre_module'], m['post_module']))
    print("Evolvable pairs: %s" % sorted(accepted_pairs))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fitness', required=True, choices=list(FITNESS_FUNCTIONS.keys()))
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--generations', type=int, default=50)
    args = parser.parse_args()

    run_evolution(args.fitness, args.seed, n_generations=args.generations)
