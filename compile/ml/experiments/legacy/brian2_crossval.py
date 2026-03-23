#!/usr/bin/env python3
"""
BRIAN2 CROSS-VALIDATION: Run the same edge sweep on the Brian2 LIF model.
If the same edges are classified as frozen/evolvable in both PyTorch AND Brian2,
the findings are model-independent.

This uses the drosophila_brain_model_lif package's Brian2 model.
We test a SUBSET of edges (100 random edges) since Brian2 is slower.
"""
import sys
import os
import numpy as np
import json
import time
from pathlib import Path

# Setup paths
sys.path.insert(0, '/home/ubuntu/drosophila_brain_model_lif')

from model import create_model, run_trial, default_params, get_spk_trn
from brian2 import ms, Hz, mV

# Load module labels
labels = np.load('/home/ubuntu/module_labels_v2.npy')
import pandas as pd

# Build edge synapse index
conn_path = '/home/ubuntu/drosophila_brain_model_lif/Connectivity_783.parquet'
comp_path = '/home/ubuntu/drosophila_brain_model_lif/Completeness_783.csv'

df = pd.read_parquet(conn_path)
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

# DN neuron indices (same as in brain_body_bridge.py)
# We'll measure total spikes from sugar-stimulated neurons as a proxy for navigation fitness
comp_df = pd.read_csv(comp_path, index_col=0)
neuron_ids = comp_df.index.tolist()

# Sugar neuron FlyWire IDs (from brain_body_bridge.py STIMULI dict)
SUGAR_NEURONS = [
    720575940637240468, 720575940625824886, 720575940626476997,
    720575940625569537, 720575940636483358, 720575940624465498,
    720575940624469518, 720575940633498854, 720575940613498969,
    720575940637753498, 720575940613996621, 720575940613662738,
    720575940625756948, 720575940613637689, 720575940621809015,
    720575940604754683, 720575940604806596, 720575940609424399,
    720575940620587501, 720575940613704038, 720575940626099502,
]

# Map to indices
id2idx = {nid: i for i, nid in enumerate(neuron_ids)}
sugar_indices = [id2idx[nid] for nid in SUGAR_NEURONS if nid in id2idx]
print(f"Sugar neurons mapped: {len(sugar_indices)}")

# Fitness: total spikes from specific neuron populations
def compute_fitness(spk_trn, sugar_idx):
    """Navigation proxy: total spikes across all neurons (activity level)."""
    total = sum(len(v) for v in spk_trn.values())
    return total

def run_brian2_eval(conn_path, comp_path, params, sugar_idx):
    """Run one Brian2 trial and return fitness."""
    # Create model fresh each time (Brian2 doesn't support weight modification in-place well)
    neu, syn, spk_mon = create_model(comp_path, conn_path, params)

    # Activate sugar neurons
    from brian2 import PoissonInput, Network
    poi_list = []
    for idx in sugar_idx:
        pi = PoissonInput(neu[idx], 'v', N=1, rate=params['r_poi'], weight=params['w_syn'] * params['f_poi'])
        poi_list.append(pi)

    net = Network(neu, syn, spk_mon, *poi_list)
    net.run(params['t_run'])

    spk_trn = get_spk_trn(spk_mon)
    return compute_fitness(spk_trn, sugar_idx)


# Modified params for faster runs
params = dict(default_params)
params['t_run'] = 200 * ms  # 200ms instead of 1000ms for speed

# Sample 50 random edges to test (Brian2 is slow)
np.random.seed(42)
sample_edges = [inter_module_edges[i] for i in np.random.choice(len(inter_module_edges), 50, replace=False)]

print(f"Testing {len(sample_edges)} edges with Brian2")
print(f"Run time: {params['t_run']}")

# Baseline
print("\nMeasuring baseline...")
t0 = time.time()
baseline = run_brian2_eval(conn_path, comp_path, params, sugar_indices)
t1 = time.time()
print(f"Baseline fitness: {baseline} ({t1-t0:.1f}s)")

# Sweep
results = []
for i, edge in enumerate(sample_edges):
    syns = edge_syn_idx[edge]

    # Create a modified connectivity file (scale weights for this edge by 2x)
    df_mod = df.copy()
    weight_col = 'Excitatory x Connectivity'
    df_mod.iloc[syns, df_mod.columns.get_loc(weight_col)] = df_mod.iloc[syns][weight_col] * 2.0

    # Save temp modified file
    tmp_path = '/tmp/brian2_mod_conn.parquet'
    df_mod.to_parquet(tmp_path)

    # Evaluate
    t0 = time.time()
    fitness_2x = run_brian2_eval(tmp_path, comp_path, params, sugar_indices)
    elapsed = time.time() - t0

    delta = fitness_2x - baseline

    if delta > 0:
        classification = "evolvable"
    elif delta < 0:
        classification = "frozen"
    else:
        classification = "irrelevant"

    results.append({
        'pre_module': int(edge[0]),
        'post_module': int(edge[1]),
        'n_synapses': len(syns),
        'fitness_2x': fitness_2x,
        'delta': delta,
        'classification': classification,
    })

    print(f"  [{i+1}/{len(sample_edges)}] {edge[0]}->{edge[1]} f={fitness_2x} Δ={delta:+d} {classification} ({elapsed:.1f}s)")

# Summary
counts = {'evolvable': 0, 'frozen': 0, 'irrelevant': 0}
for r in results:
    counts[r['classification']] += 1

total = len(results)
print(f"\n=== BRIAN2 SWEEP RESULTS ===")
print(f"Edges tested: {total}")
print(f"Frozen: {counts['frozen']} ({100*counts['frozen']/total:.1f}%)")
print(f"Irrelevant: {counts['irrelevant']} ({100*counts['irrelevant']/total:.1f}%)")
print(f"Evolvable: {counts['evolvable']} ({100*counts['evolvable']/total:.1f}%)")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'model': 'brian2',
    'baseline_fitness': baseline,
    'n_edges_tested': total,
    'params': {'t_run_ms': 200, 'r_poi_Hz': 150, 'f_poi': 250},
    'classification_counts': counts,
    'results': results,
    'sample_edge_indices': [inter_module_edges.index(e) for e in sample_edges],
}
with open(f'{outdir}/brian2_crossval.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f"Saved to {outdir}/brian2_crossval.json")
