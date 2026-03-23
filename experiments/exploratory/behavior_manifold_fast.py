#!/usr/bin/env python3
"""
BEHAVIOR MANIFOLD (FAST): Map the space of possible behaviors.

Optimized: 100 perturbations x 1 scale x 3 stimuli = 300 sims (~1.5 hrs)
Plus module-level perturbations (50 modules x 1 scale x 3 stimuli = 150 sims)
Total: ~500 sims x ~18s = ~2.5 hrs
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
print(f"Inter-module edges: {len(inter_module_edges)}")

GAIN = 8.0
N_STEPS = 300
STIMULI = ['sugar', 'lc4', 'jo']  # navigation, escape, turning

def get_dn_vector(brain, stimulus):
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)
    dn_spikes = {name: 0 for name in brain.dn_indices}
    for step in range(N_STEPS):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for name, idx in brain.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
    return dn_spikes

brain = BrainEngine(device='cpu')
brain._syn_vals.mul_(GAIN)
baseline_weights = brain._syn_vals.clone()

dn_names = sorted(brain.dn_indices.keys())
print(f"DN neurons: {len(dn_names)}: {dn_names}")

results = []
t0_global = time.time()

def record(stim, perturbation, edge, scale, dn, label):
    vec = [dn.get(n, 0) for n in dn_names]
    results.append({
        'stimulus': stim, 'perturbation': perturbation,
        'edge': edge, 'scale': scale,
        'dn_vector': vec, 'total_spikes': sum(vec),
        'label': label,
    })

# PHASE 1: Baselines
print("\n=== PHASE 1: Baselines ===")
for stim in STIMULI:
    brain._syn_vals.copy_(baseline_weights)
    dn = get_dn_vector(brain, stim)
    record(stim, 'baseline', None, 1.0, dn, f'baseline_{stim}')
    print(f"  {stim}: {sum(dn.values())} spikes | {dict(sorted([(k,v) for k,v in dn.items() if v > 0]))}")

# PHASE 2: 100 random edge perturbations (scale=2x only)
print(f"\n=== PHASE 2: 100 random edge perturbations ===")
rng = np.random.RandomState(42)
random_edges = rng.choice(len(inter_module_edges), 100, replace=False)
t0 = time.time()

for pi, eidx in enumerate(random_edges):
    edge = inter_module_edges[eidx]
    syns = edge_syn_idx[edge]
    brain._syn_vals.copy_(baseline_weights)
    brain._syn_vals[syns] *= 2.0

    for stim in STIMULI:
        dn = get_dn_vector(brain, stim)
        record(stim, 'single_edge', list(edge), 2.0, dn, f'e{edge[0]}_{edge[1]}_{stim}')

    if (pi + 1) % 10 == 0:
        elapsed = time.time() - t0
        remaining = elapsed / (pi + 1) * (100 - pi - 1)
        print(f"  [{pi+1}/100] {elapsed:.0f}s elapsed, {remaining:.0f}s remaining | {len(results)} pts")

# PHASE 3: Module-level perturbations (all 50 modules, scale=2x)
print(f"\n=== PHASE 3: Module-level perturbations ===")
n_modules = int(labels.max()) + 1
for mod in range(n_modules):
    mod_syns = [i for i in range(len(df)) if pre_mods[i] == mod or post_mods[i] == mod]
    if not mod_syns:
        continue
    brain._syn_vals.copy_(baseline_weights)
    brain._syn_vals[mod_syns] *= 2.0
    for stim in STIMULI:
        dn = get_dn_vector(brain, stim)
        record(stim, 'module_scale', mod, 2.0, dn, f'mod{mod}_{stim}')
    if (mod + 1) % 10 == 0:
        print(f"  [{mod+1}/{n_modules}] {len(results)} pts")

# PHASE 4: Multi-edge combos (30 random combos of 5 edges)
print(f"\n=== PHASE 4: 30 multi-edge combos ===")
for ci in range(30):
    combo = rng.choice(len(inter_module_edges), 5, replace=False)
    brain._syn_vals.copy_(baseline_weights)
    edges_used = []
    for eidx in combo:
        edge = inter_module_edges[eidx]
        brain._syn_vals[edge_syn_idx[edge]] *= 2.0
        edges_used.append(list(edge))
    for stim in STIMULI:
        dn = get_dn_vector(brain, stim)
        record(stim, 'multi_edge', edges_used, 2.0, dn, f'combo{ci}_{stim}')
    if (ci + 1) % 10 == 0:
        print(f"  [{ci+1}/30] {len(results)} pts")

# PHASE 5: Embedding
print(f"\n=== PHASE 5: Embedding {len(results)} points ===")
vectors = np.array([r['dn_vector'] for r in results], dtype=float)
print(f"Shape: {vectors.shape}, non-zero rows: {np.sum(np.any(vectors > 0, axis=1))}")

norms = np.linalg.norm(vectors, axis=1, keepdims=True)
norms[norms == 0] = 1
vectors_norm = vectors / norms

from sklearn.decomposition import PCA
pca = PCA(n_components=min(10, vectors.shape[1]))
pca_coords = pca.fit_transform(vectors_norm)
print(f"PCA variance: {pca.explained_variance_ratio_[:5].round(4)}")
print(f"Dims for 90% var: {np.argmax(np.cumsum(pca.explained_variance_ratio_) >= 0.9) + 1}")

try:
    import umap
    umap_coords = umap.UMAP(n_components=2, random_state=42, n_neighbors=30, min_dist=0.3).fit_transform(vectors_norm)
    has_umap = True
    print("UMAP done")
except ImportError:
    umap_coords = pca_coords[:, :2]
    has_umap = False
    print("No UMAP, using PCA")

for i, r in enumerate(results):
    r['pca'] = pca_coords[i, :3].tolist()
    r['umap'] = umap_coords[i].tolist()

# PHASE 6: Analysis
print(f"\n=== PHASE 6: Analysis ===")
from sklearn.metrics.pairwise import cosine_similarity

baselines = [r for r in results if r['perturbation'] == 'baseline']
bl_vecs = np.array([r['dn_vector'] for r in baselines], dtype=float)
bl_names = [r['stimulus'] for r in baselines]

if np.any(bl_vecs > 0):
    cos = cosine_similarity(bl_vecs)
    print("\nBehavior distances (1 - cosine similarity):")
    for i in range(len(baselines)):
        for j in range(i+1, len(baselines)):
            print(f"  {bl_names[i]} vs {bl_names[j]}: {1-cos[i,j]:.4f}")

# How perturbations move behaviors in the space
print("\nPerturbation displacement from baseline (L2 in PCA space):")
for stim in STIMULI:
    bl = [r for r in results if r['perturbation'] == 'baseline' and r['stimulus'] == stim]
    if not bl:
        continue
    bl_pca = np.array(bl[0]['pca'])
    perturbed = [r for r in results if r['perturbation'] == 'single_edge' and r['stimulus'] == stim]
    if not perturbed:
        continue
    displacements = [np.linalg.norm(np.array(r['pca']) - bl_pca) for r in perturbed]
    print(f"  {stim}: mean={np.mean(displacements):.4f}, max={np.max(displacements):.4f}, std={np.std(displacements):.4f}")

# Which DN neurons are most variable across perturbations?
print("\nDN neuron variability (std across all perturbations):")
for stim in STIMULI:
    stim_vecs = np.array([r['dn_vector'] for r in results if r['stimulus'] == stim], dtype=float)
    stds = np.std(stim_vecs, axis=0)
    ranked = sorted(zip(dn_names, stds), key=lambda x: -x[1])
    print(f"  {stim}: {', '.join(f'{n}={s:.2f}' for n, s in ranked[:5])}")

# Save
output = {
    'metadata': {
        'dn_names': dn_names,
        'n_points': len(results),
        'stimuli': STIMULI,
        'gain': GAIN,
        'n_steps': N_STEPS,
        'pca_explained_variance': pca.explained_variance_ratio_.tolist(),
        'has_umap': has_umap,
        'total_time': time.time() - t0_global,
    },
    'points': results,
}

outpath = '/home/ubuntu/bulletproof_results/behavior_manifold.json'
with open(outpath, 'w') as f:
    json.dump(output, f)
print(f"\nSaved {len(results)} points to {outpath}")
print(f"Total time: {time.time() - t0_global:.0f}s")
print("DONE.")
