#!/usr/bin/env python3
"""
BEHAVIOR MANIFOLD: Map the space of possible behaviors.

Instead of reducing neural activity to a single fitness scalar,
record the FULL DN output vector for each perturbation.
Each vector IS a behavior — a point in high-dimensional space.

1. Run baseline (unperturbed) with each stimulus → 4 reference points
2. Run 200 random single-edge perturbations with each stimulus → 800 points
3. Run the evolved connectomes (if available) → additional reference points
4. Embed everything with UMAP and PCA
5. Output: behavior_manifold.json with coordinates + metadata

This is the seed of the Behavior Atlas.
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
inter_module_edges = sorted([e for e in edge_syn_idx if e[0] != e[1]])
print(f"Inter-module edges: {len(inter_module_edges)}")

GAIN = 8.0
N_STEPS = 300
N_RANDOM_PERTURBATIONS = 200  # random edge perturbations per stimulus
STIMULI = ['sugar', 'lc4', 'jo']  # navigation, escape, turning contexts

def get_dn_vector(brain, stimulus, n_steps=N_STEPS):
    """Run simulation and return FULL DN spike vector as dict AND list."""
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

def dn_dict_to_vector(dn_dict, dn_names):
    """Convert DN dict to fixed-order vector."""
    return [dn_dict.get(n, 0) for n in dn_names]

# Initialize brain
brain = BrainEngine(device='cpu')
brain._syn_vals.mul_(GAIN)
baseline_weights = brain._syn_vals.clone()

dn_names = sorted(brain.dn_indices.keys())
print(f"DN neurons: {len(dn_names)}")
print(f"DN names: {dn_names}")

results = []  # list of {stimulus, perturbation, dn_vector, metadata}

# ============================================================
# PHASE 1: Baselines — unperturbed brain with each stimulus
# ============================================================
print("\n=== PHASE 1: Baselines ===")
for stim in STIMULI:
    brain._syn_vals.copy_(baseline_weights)
    dn = get_dn_vector(brain, stim)
    vec = dn_dict_to_vector(dn, dn_names)
    results.append({
        'stimulus': stim,
        'perturbation': 'baseline',
        'edge': None,
        'scale': 1.0,
        'dn_vector': vec,
        'total_spikes': sum(vec),
        'label': f'baseline_{stim}',
    })
    print(f"  {stim} baseline: {sum(vec)} total DN spikes")

# Also run with NO stimulus (spontaneous activity)
brain._syn_vals.copy_(baseline_weights)
brain.state = brain.model.state_init()
brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
brain._spike_acc.zero_()
brain._hebb_count = 0
# Don't set stimulus — measure spontaneous
dn_spont = {name: 0 for name in brain.dn_indices}
for step in range(N_STEPS):
    brain.step()
    spk = brain.state[2].squeeze(0)
    for name, idx in brain.dn_indices.items():
        dn_spont[name] += int(spk[idx].item())
vec = dn_dict_to_vector(dn_spont, dn_names)
results.append({
    'stimulus': 'none',
    'perturbation': 'baseline',
    'edge': None,
    'scale': 1.0,
    'dn_vector': vec,
    'total_spikes': sum(vec),
    'label': 'spontaneous',
})
print(f"  spontaneous: {sum(vec)} total DN spikes")

# ============================================================
# PHASE 2: Random edge perturbations
# ============================================================
print(f"\n=== PHASE 2: {N_RANDOM_PERTURBATIONS} random perturbations x {len(STIMULI)} stimuli ===")
rng = np.random.RandomState(42)
random_edges = rng.choice(len(inter_module_edges), N_RANDOM_PERTURBATIONS, replace=False)

t0 = time.time()
for pi, edge_idx in enumerate(random_edges):
    edge = inter_module_edges[edge_idx]
    syns = edge_syn_idx[edge]

    for scale in [2.0, 0.5, 4.0]:  # amplify, attenuate, strong amplify
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= scale

        for stim in STIMULI:
            dn = get_dn_vector(brain, stim)
            vec = dn_dict_to_vector(dn, dn_names)
            results.append({
                'stimulus': stim,
                'perturbation': 'single_edge',
                'edge': list(edge),
                'scale': scale,
                'dn_vector': vec,
                'total_spikes': sum(vec),
                'label': f'edge_{edge[0]}_{edge[1]}_x{scale}_{stim}',
            })

    if (pi + 1) % 25 == 0:
        elapsed = time.time() - t0
        remaining = elapsed / (pi + 1) * (N_RANDOM_PERTURBATIONS - pi - 1)
        print(f"  [{pi+1}/{N_RANDOM_PERTURBATIONS}] {elapsed:.0f}s elapsed, {remaining:.0f}s remaining, {len(results)} points total")

# ============================================================
# PHASE 3: Multi-edge perturbations (combinations)
# ============================================================
print(f"\n=== PHASE 3: Multi-edge perturbations (50 random combos of 5 edges) ===")
for ci in range(50):
    combo_edges = rng.choice(len(inter_module_edges), 5, replace=False)
    brain._syn_vals.copy_(baseline_weights)
    edge_list = []
    for eidx in combo_edges:
        edge = inter_module_edges[eidx]
        syns = edge_syn_idx[edge]
        brain._syn_vals[syns] *= 2.0
        edge_list.append(list(edge))

    for stim in STIMULI:
        dn = get_dn_vector(brain, stim)
        vec = dn_dict_to_vector(dn, dn_names)
        results.append({
            'stimulus': stim,
            'perturbation': 'multi_edge',
            'edge': edge_list,
            'scale': 2.0,
            'dn_vector': vec,
            'total_spikes': sum(vec),
            'label': f'combo_{ci}_{stim}',
        })

    if (ci + 1) % 10 == 0:
        print(f"  [{ci+1}/50] {len(results)} points total")

# ============================================================
# PHASE 4: Extreme perturbations (whole module scaling)
# ============================================================
print(f"\n=== PHASE 4: Module-level perturbations ===")
n_modules = int(labels.max()) + 1
for mod in range(n_modules):
    mod_syns = [i for i in range(len(df)) if pre_mods[i] == mod or post_mods[i] == mod]
    if not mod_syns:
        continue

    for scale in [2.0, 0.5]:
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[mod_syns] *= scale

        for stim in STIMULI:
            dn = get_dn_vector(brain, stim)
            vec = dn_dict_to_vector(dn, dn_names)
            results.append({
                'stimulus': stim,
                'perturbation': 'module_scale',
                'edge': mod,
                'scale': scale,
                'dn_vector': vec,
                'total_spikes': sum(vec),
                'label': f'module_{mod}_x{scale}_{stim}',
            })

    if (mod + 1) % 10 == 0:
        print(f"  [{mod+1}/{n_modules}] {len(results)} points total")

# ============================================================
# PHASE 5: Embedding
# ============================================================
print(f"\n=== PHASE 5: Embedding {len(results)} points ===")

# Extract vectors
vectors = np.array([r['dn_vector'] for r in results], dtype=float)
print(f"Vector shape: {vectors.shape}")
print(f"Non-zero vectors: {np.sum(np.any(vectors > 0, axis=1))}/{len(vectors)}")

# Normalize for embedding (L2 norm per row)
norms = np.linalg.norm(vectors, axis=1, keepdims=True)
norms[norms == 0] = 1  # avoid div by zero
vectors_norm = vectors / norms

# PCA
from sklearn.decomposition import PCA
pca = PCA(n_components=min(10, vectors.shape[1]))
pca_coords = pca.fit_transform(vectors_norm)
print(f"PCA explained variance (first 5): {pca.explained_variance_ratio_[:5]}")

# UMAP
try:
    import umap
    reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=30, min_dist=0.3)
    umap_coords = reducer.fit_transform(vectors_norm)
    has_umap = True
    print("UMAP embedding complete")
except ImportError:
    print("UMAP not available, using PCA only")
    has_umap = False
    umap_coords = pca_coords[:, :2]

# Add coordinates to results
for i, r in enumerate(results):
    r['pca'] = pca_coords[i, :3].tolist()  # first 3 PCA components
    r['umap'] = umap_coords[i].tolist() if has_umap else pca_coords[i, :2].tolist()
    # Remove raw vector for JSON size (keep summary stats)
    r['dn_vector_nonzero'] = int(np.sum(np.array(r['dn_vector']) > 0))
    r['dn_vector_max'] = int(max(r['dn_vector']))
    # Keep the full vector for downstream analysis
    # r.pop('dn_vector')  # uncomment to reduce file size

# ============================================================
# PHASE 6: Analysis
# ============================================================
print("\n=== PHASE 6: Analysis ===")

# Find distances between baseline behaviors
baselines = [r for r in results if r['perturbation'] == 'baseline' and r['stimulus'] != 'none']
print(f"\nBaseline behavior distances (cosine):")
from sklearn.metrics.pairwise import cosine_similarity
bl_vecs = np.array([r['dn_vector'] for r in baselines], dtype=float)
bl_names = [r['stimulus'] for r in baselines]
if np.any(bl_vecs > 0):
    cos_sim = cosine_similarity(bl_vecs)
    for i in range(len(baselines)):
        for j in range(i+1, len(baselines)):
            print(f"  {bl_names[i]} vs {bl_names[j]}: similarity={cos_sim[i,j]:.4f}, distance={1-cos_sim[i,j]:.4f}")

# Cluster analysis
from sklearn.cluster import KMeans
if len(vectors_norm) > 10:
    inertias = []
    for k in range(2, min(15, len(vectors_norm))):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(vectors_norm)
        inertias.append((k, km.inertia_))
    print(f"\nK-means inertia: {[(k, f'{v:.1f}') for k, v in inertias[:6]]}")

# Save
output = {
    'metadata': {
        'dn_names': dn_names,
        'n_points': len(results),
        'n_random_perturbations': N_RANDOM_PERTURBATIONS,
        'stimuli': STIMULI,
        'gain': GAIN,
        'n_steps': N_STEPS,
        'pca_explained_variance': pca.explained_variance_ratio_.tolist(),
        'has_umap': has_umap,
    },
    'points': results,
}

outpath = '/home/ubuntu/bulletproof_results/behavior_manifold.json'
with open(outpath, 'w') as f:
    json.dump(output, f)
print(f"\nSaved {len(results)} points to {outpath}")
print(f"Total time: {time.time() - t0:.0f}s")

# Quick summary
print("\n" + "="*60)
print("BEHAVIOR MANIFOLD SUMMARY")
print("="*60)
by_stim = {}
for r in results:
    s = r['stimulus']
    if s not in by_stim:
        by_stim[s] = []
    by_stim[s].append(r['total_spikes'])

for s, spikes in by_stim.items():
    print(f"  {s}: {len(spikes)} points, mean spikes={np.mean(spikes):.1f}, std={np.std(spikes):.1f}")

print(f"\nPCA dims needed for 90% variance: {np.argmax(np.cumsum(pca.explained_variance_ratio_) >= 0.9) + 1}")
print("DONE.")
