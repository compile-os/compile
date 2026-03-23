#!/usr/bin/env python3
"""
EXPERIMENT A: COMPILE STRATEGY SWITCHING

Can evolution find wiring that enables the brain to CHANGE behavior mid-simulation?

Two-phase fitness:
  Phase 1 (steps 0-500): Stimulate sugar (navigate toward food at position A)
  Phase 2 (steps 500-1000): Switch to JO stimulus (obstacle/wind from different direction)

  Fitness = min(phase1_nav_score, phase2_turning_score)

  Using min forces the brain to be good at BOTH phases. A brain that just navigates
  and ignores the switch scores 0. A brain that detects the context change and adapts
  its behavior scores high on both.

This tests whether the compiler can produce self-monitoring, context-switching behavior.
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

GAIN = 8.0
PHASE1_STEPS = 500
PHASE2_STEPS = 500

def evaluate_switching(brain, n_steps_per_phase=500):
    """Two-phase evaluation: sugar then JO. Returns both phase scores."""
    dn_names = list(brain.dn_indices.keys())
    dn_idx = [brain.dn_indices[n] for n in dn_names]

    # PHASE 1: Sugar stimulus (navigation context)
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus('sugar')

    phase1_spikes = np.zeros(len(dn_names))
    for step in range(n_steps_per_phase):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            phase1_spikes[j] += spk[idx].item()

    # PHASE 2: Switch to JO stimulus (turning context) — KEEP the neural state!
    # Don't reset — the brain must detect the context change from ongoing activity
    brain.set_stimulus('jo')

    phase2_spikes = np.zeros(len(dn_names))
    for step in range(n_steps_per_phase):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            phase2_spikes[j] += spk[idx].item()

    return {
        'dn_names': dn_names,
        'phase1': phase1_spikes,
        'phase2': phase2_spikes,
    }


def fitness_switching(data):
    """
    Phase 1: reward navigation (P9/MN9 activation)
    Phase 2: reward turning (DNa01/DNa02 asymmetry)
    Fitness = min(phase1, phase2) — forces competence at BOTH
    """
    names = data['dn_names']

    # Phase 1: navigation score
    p9_idx = [i for i, n in enumerate(names) if 'P9' in n or 'MN9' in n]
    nav_score = float(sum(data['phase1'][i] for i in p9_idx))

    # Phase 2: turning score
    da01_l = names.index('DNa01_left') if 'DNa01_left' in names else -1
    da01_r = names.index('DNa01_right') if 'DNa01_right' in names else -1
    da02_l = names.index('DNa02_left') if 'DNa02_left' in names else -1
    da02_r = names.index('DNa02_right') if 'DNa02_right' in names else -1
    left = data['phase2'][da01_l] + (data['phase2'][da02_l] if da02_l >= 0 else 0)
    right = data['phase2'][da01_r] + (data['phase2'][da02_r] if da02_r >= 0 else 0)
    turn_score = float(abs(left - right) + (left + right) * 0.1)

    # min forces competence at BOTH phases
    # Normalize so they're on comparable scales
    nav_norm = nav_score / max(nav_score + turn_score, 1)
    turn_norm = turn_score / max(nav_score + turn_score, 1)

    return {
        'fitness': min(nav_score, turn_score),
        'nav_score': nav_score,
        'turn_score': turn_score,
        'phase1_total': float(data['phase1'].sum()),
        'phase2_total': float(data['phase2'].sum()),
        'phase1_vector': data['phase1'].tolist(),
        'phase2_vector': data['phase2'].tolist(),
    }


def run_evolution(seed, n_generations=25, n_mutations=10):
    np.random.seed(seed)
    torch.manual_seed(seed)

    brain = BrainEngine(device='cpu')
    brain._syn_vals.mul_(GAIN)
    baseline_weights = brain._syn_vals.clone()

    # Baseline
    data = evaluate_switching(brain)
    bl = fitness_switching(data)
    current_fitness = bl['fitness']
    print(f"\nSeed {seed} baseline:")
    print(f"  Phase 1 (nav):  {bl['nav_score']:.2f}")
    print(f"  Phase 2 (turn): {bl['turn_score']:.2f}")
    print(f"  Fitness (min):  {current_fitness:.2f}")

    all_mutations = []
    accepted = 0
    t0 = time.time()

    for gen in range(n_generations):
        ga = 0
        for mi in range(n_mutations):
            edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
            syns = edge_syn_idx[edge]
            old = brain._syn_vals[syns].clone()
            scale = np.random.uniform(0.2, 5.0)
            brain._syn_vals[syns] = old * scale

            data = evaluate_switching(brain)
            result = fitness_switching(data)
            new_fitness = result['fitness']

            acc = new_fitness > current_fitness
            delta = new_fitness - current_fitness

            mutation = {
                'seed': int(seed), 'gen': gen, 'mi': mi,
                'edge': [int(edge[0]), int(edge[1])],
                'n_synapses': len(syns), 'scale': float(scale),
                'fitness_before': float(current_fitness),
                'fitness_after': float(new_fitness),
                'delta': float(delta), 'accepted': acc,
                'nav_score': result['nav_score'],
                'turn_score': result['turn_score'],
                'phase1_vector': result['phase1_vector'],
                'phase2_vector': result['phase2_vector'],
            }
            all_mutations.append(mutation)

            if acc:
                current_fitness = new_fitness
                ga += 1
                accepted += 1
                print(f"  G{gen} M{mi}: {edge[0]}->{edge[1]} s={scale:.2f} "
                      f"nav={result['nav_score']:.1f} turn={result['turn_score']:.1f} "
                      f"fit={new_fitness:.2f} Δ={delta:+.2f} ACCEPTED")
            else:
                brain._syn_vals[syns] = old

        if gen % 5 == 4 or gen == n_generations - 1:
            elapsed = time.time() - t0
            remaining = elapsed / (gen + 1) * (n_generations - gen - 1)
            print(f"  Gen {gen}: fit={current_fitness:.2f} acc={ga}/{n_mutations} "
                  f"total_acc={accepted} [{elapsed:.0f}s elapsed, {remaining:.0f}s remaining]")

    return {
        'seed': seed,
        'baseline': bl,
        'final_fitness': current_fitness,
        'total_accepted': accepted,
        'total_mutations': len(all_mutations),
        'mutations': all_mutations,
    }


# Run 3 seeds
print("=" * 60)
print("STRATEGY SWITCHING EVOLUTION")
print("=" * 60)
print(f"Phases: sugar ({PHASE1_STEPS} steps) → JO ({PHASE2_STEPS} steps)")
print(f"Fitness: min(navigation_score, turning_score)")
print(f"Generations: 50, Mutations/gen: 10")

all_results = []
for seed in [42]:
    result = run_evolution(seed, n_generations=25, n_mutations=10)
    all_results.append(result)

# Analysis
print("\n" + "=" * 60)
print("STRATEGY SWITCHING RESULTS")
print("=" * 60)

for r in all_results:
    bl = r['baseline']
    print(f"\nSeed {r['seed']}:")
    print(f"  Baseline: nav={bl['nav_score']:.2f}, turn={bl['turn_score']:.2f}, fit={bl['fitness']:.2f}")
    print(f"  Final:    fit={r['final_fitness']:.2f} ({r['total_accepted']}/{r['total_mutations']} accepted)")

    # Which edges were accepted?
    acc_edges = [(m['edge'][0], m['edge'][1]) for m in r['mutations'] if m['accepted']]
    unique_edges = sorted(set(map(tuple, acc_edges)))
    print(f"  Evolvable edges: {len(unique_edges)}: {unique_edges[:15]}...")

    # Did it improve BOTH phases?
    last_acc = [m for m in r['mutations'] if m['accepted']]
    if last_acc:
        final = last_acc[-1]
        print(f"  Final state: nav={final['nav_score']:.2f}, turn={final['turn_score']:.2f}")
        if final['nav_score'] > bl['nav_score'] and final['turn_score'] > bl['turn_score']:
            print("  >>> BOTH phases improved! Strategy switching compiled.")
        elif final['nav_score'] > bl['nav_score']:
            print("  >>> Only navigation improved. No true switching.")
        elif final['turn_score'] > bl['turn_score']:
            print("  >>> Only turning improved. No true switching.")
        else:
            print("  >>> Neither phase improved significantly.")

# Cross-seed consistency
all_acc_edges = set()
per_seed_edges = []
for r in all_results:
    edges = set(tuple(m['edge']) for m in r['mutations'] if m['accepted'])
    per_seed_edges.append(edges)
    all_acc_edges.update(edges)

if len(per_seed_edges) >= 2:
    shared = per_seed_edges[0]
    for s in per_seed_edges[1:]:
        shared = shared.intersection(s)
    print(f"\nCross-seed analysis:")
    print(f"  Total unique evolvable edges: {len(all_acc_edges)}")
    print(f"  Shared across ALL seeds: {len(shared)}: {sorted(shared)}")
    print(f"  Per-seed counts: {[len(s) for s in per_seed_edges]}")

# Compare to single-behavior evolvable edges
print("\n--- Compare to single-behavior edges ---")
print("(Load from sweep results if available)")
try:
    with open('/home/ubuntu/bulletproof_results/sweep_navigation_0_1225.json') as f:
        nav_data = json.load(f)
    nav_evolvable = set(tuple(e) for e in nav_data.get('evolvable_pairs', []))
    switching_only = all_acc_edges - nav_evolvable
    nav_only = nav_evolvable - all_acc_edges
    both = all_acc_edges & nav_evolvable
    print(f"  Navigation evolvable: {len(nav_evolvable)}")
    print(f"  Switching evolvable: {len(all_acc_edges)}")
    print(f"  Shared: {len(both)}")
    print(f"  Switching-only (new!): {len(switching_only)}: {sorted(switching_only)[:20]}")
except Exception as e:
    print(f"  Could not load nav results: {e}")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'experiment': 'strategy_switching',
    'description': 'Two-phase evolution: sugar->JO, fitness=min(nav,turn)',
    'results': all_results,
    'cross_seed_shared': sorted(shared) if len(per_seed_edges) >= 2 else [],
    'all_evolvable_edges': sorted(all_acc_edges),
}
with open(f'{outdir}/strategy_switching.json', 'w') as f:
    json.dump(output, f)
print(f"\nSaved to {outdir}/strategy_switching.json")
print("DONE.")
