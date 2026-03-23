#!/usr/bin/env python3
"""
Discrete Gauge Theory Test v2 - Better clustering and holonomy
"""

import numpy as np
import pandas as pd
from collections import Counter, defaultdict
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import MiniBatchKMeans
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("DISCRETE GAUGE THEORY TEST v2")
print("="*70)

# Load connectivity
print("\n[1] Loading connectome...")
conn = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')

pre = conn['Presynaptic_Index'].values
post = conn['Postsynaptic_Index'].values
weights = conn['Connectivity'].values

n_neurons = max(pre.max(), post.max()) + 1
print(f"  Neurons: {n_neurons:,}")

# Build sparse adjacency
adj = sparse.csr_matrix((weights, (pre, post)), shape=(n_neurons, n_neurons))

# Compute neuron features for balanced clustering
print("\n[2] Computing neuron features for clustering...")
in_degree = np.array(adj.sum(axis=0)).flatten()
out_degree = np.array(adj.sum(axis=1)).flatten()
total_degree = in_degree + out_degree

# Use index + degree as proxy for spatial/functional grouping
# Neuron indices in FlyWire often have spatial meaning
neuron_features = np.column_stack([
    np.arange(n_neurons) / n_neurons,  # Normalized index
    np.log1p(in_degree) / np.log1p(in_degree.max()),
    np.log1p(out_degree) / np.log1p(out_degree.max()),
    (in_degree - out_degree) / (total_degree + 1),  # Balance
])

# Use MiniBatchKMeans for balanced clusters
print("\n[3] Clustering neurons into balanced modules...")
N_MODULES = 50  # Fewer modules for denser inter-module graph

kmeans = MiniBatchKMeans(n_clusters=N_MODULES, random_state=42, batch_size=10000)
module_labels = kmeans.fit_predict(neuron_features)

module_sizes = Counter(module_labels)
sizes = list(module_sizes.values())
print(f"  Module sizes: min={min(sizes)}, max={max(sizes)}, mean={np.mean(sizes):.0f}")
print(f"  Size std: {np.std(sizes):.0f}")

# Build module-level weighted directed graph
print("\n[4] Building module-level graph...")
module_weights = np.zeros((N_MODULES, N_MODULES))
module_counts = np.zeros((N_MODULES, N_MODULES))

for i in range(len(pre)):
    m_pre = module_labels[pre[i]]
    m_post = module_labels[post[i]]
    module_weights[m_pre, m_post] += weights[i]
    module_counts[m_pre, m_post] += 1

# Compute inter vs intra module connections
intra_module = sum(module_counts[i, i] for i in range(N_MODULES))
inter_module = module_counts.sum() - intra_module
print(f"  Intra-module connections: {int(intra_module):,}")
print(f"  Inter-module connections: {int(inter_module):,}")
print(f"  Ratio: {inter_module / (inter_module + intra_module):.2%}")

# For gauge theory: use inter-module weights as the "connection"
# Normalize by geometric mean to get transition probabilities
module_out_total = module_weights.sum(axis=1, keepdims=True)
module_out_total[module_out_total == 0] = 1
transition = module_weights / module_out_total  # Markov transition matrix

# Compute Forman-Ricci curvature on the module graph
print("\n[5] Computing Forman-Ricci curvature...")
module_degree_out = (module_weights > 0).sum(axis=1)
module_degree_in = (module_weights > 0).sum(axis=0)
module_degree = module_degree_out + module_degree_in

forman_curvature = {}
for i in range(N_MODULES):
    for j in range(N_MODULES):
        if i != j and module_weights[i, j] > 0:
            d_i = module_degree[i]
            d_j = module_degree[j]
            # Count triangles
            n_triangles = 0
            for k in range(N_MODULES):
                if k != i and k != j:
                    if module_weights[i, k] > 0 and module_weights[k, j] > 0:
                        n_triangles += 1
                    if module_weights[j, k] > 0 and module_weights[k, i] > 0:
                        n_triangles += 1
            F = 4 - d_i - d_j + 3 * n_triangles
            forman_curvature[(i, j)] = F

curvatures = list(forman_curvature.values())
print(f"  Edges: {len(curvatures)}")
print(f"  Curvature range: [{min(curvatures):.1f}, {max(curvatures):.1f}]")
print(f"  Mean: {np.mean(curvatures):.2f}, Std: {np.std(curvatures):.2f}")

# Compute discrete holonomy around directed 3-cycles
print("\n[6] Computing discrete holonomy (directed 3-cycles)...")
# Holonomy = how a signal transforms around a loop
# Use the transition matrix: H(i→j→k→i) = T[i,j] * T[j,k] * T[k,i]

holonomies = []
cycles = []
for i in range(N_MODULES):
    for j in range(N_MODULES):
        if i != j and transition[i, j] > 0:
            for k in range(N_MODULES):
                if k != i and k != j:
                    if transition[j, k] > 0 and transition[k, i] > 0:
                        H = transition[i, j] * transition[j, k] * transition[k, i]
                        holonomies.append(H)
                        cycles.append((i, j, k))

holonomies = np.array(holonomies)
print(f"  Directed 3-cycles: {len(cycles)}")
if len(holonomies) > 0:
    print(f"  Holonomy range: [{holonomies.min():.6f}, {holonomies.max():.6f}]")
    print(f"  Mean: {holonomies.mean():.6f}, Std: {holonomies.std():.6f}")
    # Log-holonomy (additive)
    log_H = np.log(holonomies + 1e-12)
    print(f"  Log-holonomy mean: {log_H.mean():.3f}, std: {log_H.std():.3f}")

# Per-module curvature and holonomy
module_curvature = np.zeros(N_MODULES)
module_curv_count = np.zeros(N_MODULES)
for (i, j), F in forman_curvature.items():
    module_curvature[i] += F
    module_curvature[j] += F
    module_curv_count[i] += 1
    module_curv_count[j] += 1
module_curvature = module_curvature / (module_curv_count + 1e-6)

module_holonomy = np.zeros(N_MODULES)
module_hol_count = np.zeros(N_MODULES)
for idx, (i, j, k) in enumerate(cycles):
    H = holonomies[idx]
    module_holonomy[i] += H
    module_holonomy[j] += H
    module_holonomy[k] += H
    module_hol_count[i] += 1
    module_hol_count[j] += 1
    module_hol_count[k] += 1
module_holonomy = module_holonomy / (module_hol_count + 1e-6)

# Correlations
print("\n[7] Gauge-theoretic feature analysis...")
from scipy.stats import pearsonr, spearmanr

# Module size and degree
module_size_arr = np.array([module_sizes[m] for m in range(N_MODULES)])

r1, p1 = pearsonr(module_curvature, module_degree)
r2, p2 = pearsonr(module_holonomy, module_degree)
r3, p3 = pearsonr(module_curvature, module_holonomy)
r4, p4 = pearsonr(module_curvature, module_size_arr)
r5, p5 = pearsonr(module_holonomy, module_size_arr)

print(f"  Curvature vs Degree: r={r1:.3f}, p={p1:.4f}")
print(f"  Holonomy vs Degree: r={r2:.3f}, p={p2:.4f}")
print(f"  Curvature vs Holonomy: r={r3:.3f}, p={p3:.4f}")
print(f"  Curvature vs Size: r={r4:.3f}, p={p4:.4f}")
print(f"  Holonomy vs Size: r={r5:.3f}, p={p5:.4f}")

# Key insight: which modules are "gauge-special"?
print("\n[8] Identifying gauge-theoretically special modules...")

# Modules with extreme curvature
top_curv = np.argsort(module_curvature)[-5:]
bot_curv = np.argsort(module_curvature)[:5]

# Modules with high holonomy (lots of signal transformation)
top_hol = np.argsort(module_holonomy)[-5:]

print("\n  HIGHEST CURVATURE (most clustered, clique-like):")
for m in reversed(top_curv):
    print(f"    Module {m}: curv={module_curvature[m]:.1f}, degree={module_degree[m]:.0f}, size={module_sizes[m]}")

print("\n  LOWEST CURVATURE (tree-like, information bottleneck):")
for m in bot_curv:
    print(f"    Module {m}: curv={module_curvature[m]:.1f}, degree={module_degree[m]:.0f}, size={module_sizes[m]}")

print("\n  HIGHEST HOLONOMY (transformation hubs):")
for m in reversed(top_hol):
    print(f"    Module {m}: holonomy={module_holonomy[m]:.6f}, curv={module_curvature[m]:.1f}, degree={module_degree[m]:.0f}")

# THE KEY TEST: Does gauge structure predict which modules matter for behavior?
print("\n" + "="*70)
print("[9] THE GAUGE THEORY HYPOTHESIS TEST")
print("="*70)

# From evolution results: modifications to INTER-module wiring improved behavior
# If gauge theory is correct: high-holonomy loops should be the ones that matter

# Identify the "critical" modules (high degree AND high holonomy)
critical_score = (module_degree / module_degree.max()) * (module_holonomy / (module_holonomy.max() + 1e-6))
critical_modules = np.argsort(critical_score)[-10:]

print("\n  CRITICAL MODULES (high degree AND high holonomy):")
print("  These should be where evolution made its changes")
for m in reversed(critical_modules):
    print(f"    Module {m}: critical_score={critical_score[m]:.4f}, holonomy={module_holonomy[m]:.6f}, degree={module_degree[m]:.0f}")

# Compute the "gauge potential" - which neurons are in critical vs non-critical modules
critical_set = set(critical_modules)
neurons_in_critical = sum(1 for n in range(n_neurons) if module_labels[n] in critical_set)
print(f"\n  Neurons in critical modules: {neurons_in_critical:,} ({100*neurons_in_critical/n_neurons:.1f}%)")

# Save for comparison with evolution results
np.save('/home/ubuntu/module_labels_v2.npy', module_labels)
np.save('/home/ubuntu/module_curvature_v2.npy', module_curvature)
np.save('/home/ubuntu/module_holonomy_v2.npy', module_holonomy)
np.save('/home/ubuntu/critical_score.npy', critical_score)

print("\n" + "="*70)
print("GAUGE THEORY FEATURES COMPUTED")
print("="*70)
print("\nTo validate: check if the 23 evolutionary mutations")
print("preferentially occurred in connections involving critical modules.")
print("If yes: gauge-theoretic structure predicts evolvability.")
