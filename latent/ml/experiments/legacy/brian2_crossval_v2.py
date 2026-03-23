#!/usr/bin/env python3
"""
BRIAN2 CROSS-VALIDATION v2: Use the model's built-in run_trial function.
Test 50 edges: does Brian2 agree with PyTorch on frozen/evolvable classification?
"""
import sys
import os
import numpy as np
import json
import time
from pathlib import Path

sys.path.insert(0, '/home/ubuntu/drosophila_brain_model_lif')
os.chdir('/home/ubuntu/drosophila_brain_model_lif')

from model import create_model, run_trial, default_params, get_spk_trn
import pandas as pd

# Load module labels
labels = np.load('/home/ubuntu/module_labels_v2.npy')

# Paths
conn_path = '/home/ubuntu/drosophila_brain_model_lif/Connectivity_783.parquet'
comp_path = '/home/ubuntu/drosophila_brain_model_lif/Completeness_783.csv'

# Build edge index
df_conn = pd.read_parquet(conn_path)
pre_mods = labels[df_conn['Presynaptic_Index'].values].astype(int)
post_mods = labels[df_conn['Postsynaptic_Index'].values].astype(int)

edge_syn_idx = {}
for i in range(len(df_conn)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)

inter_module_edges = sorted([e for e in edge_syn_idx if e[0] != e[1]])
print(f"Inter-module edges: {len(inter_module_edges)}")

# Sugar neuron TENSOR INDICES (from BrainEngine.stim_indices)
# These are the correct indices that both models share
SUGAR_NEURONS = [69093, 97602, 122795, 124291, 29281, 90403, 42133, 52613,
                 107587, 56757, 129936, 81506, 37488, 101750, 59299, 86155,
                 118497, 2949, 3558, 125478, 103698]
print(f"Sugar neurons: {len(SUGAR_NEURONS)} indices")

# Use run_trial which handles everything correctly
from brian2 import ms, Hz, mV

params = dict(default_params)
params['t_run'] = 500 * ms  # 500ms — enough for propagation
params['n_run'] = 1

def evaluate(conn_parquet_path):
    """Run one Brian2 trial, return total spike count."""
    try:
        result = run_trial(
            exc=SUGAR_NEURONS,
            exc2=[],
            slnc=[],
            path_comp=comp_path,
            path_con=conn_parquet_path,
            params=params,
        )
        return sum(len(v) for v in result.values())
    except Exception as e:
        print(f"  Error: {e}")
        return 0

# Sample 50 edges
np.random.seed(42)
sample_indices = np.random.choice(len(inter_module_edges), 50, replace=False)
sample_edges = [inter_module_edges[i] for i in sample_indices]

print(f"Testing {len(sample_edges)} edges")
print(f"Simulation: {params['t_run']}ms per trial")

# Create baseline with 8x gain (same as PyTorch experiments)
print("\nCreating 8x gain baseline...")
df_baseline = df_conn.copy()
wcol = 'Excitatory x Connectivity'
df_baseline[wcol] = df_baseline[wcol] * 8.0
baseline_path = '/tmp/brian2_baseline_8x.parquet'
df_baseline.to_parquet(baseline_path)

print("Measuring baseline...")
t0 = time.time()
baseline = evaluate(baseline_path)
t1 = time.time()
print(f"Baseline (8x gain): {baseline} spikes ({t1-t0:.1f}s)")

if baseline == 0:
    print("WARNING: Zero baseline spikes. Trying longer simulation...")
    params['t_run'] = 1000 * ms
    baseline = evaluate(conn_path)
    print(f"Baseline (1000ms): {baseline} spikes")

# Sweep
results = []
for i, edge in enumerate(sample_edges):
    syns = edge_syn_idx[edge]

    # Modify connectivity: apply 8x gain (same as PyTorch) + scale by 2x for this edge
    df_mod = df_conn.copy()
    wcol = 'Excitatory x Connectivity'
    df_mod[wcol] = df_mod[wcol] * 8.0  # Same gain as PyTorch experiments
    df_mod.iloc[syns, df_mod.columns.get_loc(wcol)] = df_mod.iloc[syns][wcol] * 2.0  # Additional 2x for test edge

    tmp_path = '/tmp/brian2_mod.parquet'
    df_mod.to_parquet(tmp_path)

    t0 = time.time()
    fitness = evaluate(tmp_path)
    elapsed = time.time() - t0

    delta = fitness - baseline
    if delta > 0:
        cls = "evolvable"
    elif delta < 0:
        cls = "frozen"
    else:
        cls = "irrelevant"

    results.append({
        'pre_module': int(edge[0]),
        'post_module': int(edge[1]),
        'edge_index': int(sample_indices[i]),
        'n_synapses': len(syns),
        'fitness': fitness,
        'delta': delta,
        'classification': cls,
    })

    print(f"  [{i+1}/{len(sample_edges)}] {edge[0]}->{edge[1]} f={fitness} Δ={delta:+d} {cls} ({elapsed:.1f}s)")

# Summary
counts = {'evolvable': 0, 'frozen': 0, 'irrelevant': 0}
for r in results:
    counts[r['classification']] += 1

total = len(results)
print(f"\n{'='*60}")
print(f"BRIAN2 CROSS-VALIDATION RESULTS")
print(f"{'='*60}")
print(f"Edges tested: {total}")
print(f"Frozen: {counts['frozen']} ({100*counts['frozen']/total:.1f}%)")
print(f"Irrelevant: {counts['irrelevant']} ({100*counts['irrelevant']/total:.1f}%)")
print(f"Evolvable: {counts['evolvable']} ({100*counts['evolvable']/total:.1f}%)")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
with open(f'{outdir}/brian2_crossval.json', 'w') as f:
    json.dump({
        'model': 'brian2',
        'baseline': baseline,
        'n_tested': total,
        'counts': counts,
        'results': results,
    }, f, indent=2)
print(f"\nSaved to {outdir}/brian2_crossval.json")
