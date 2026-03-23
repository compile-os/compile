#!/usr/bin/env python3
"""
CURVATURE RETEST: Does curvature predict Izhikevich-evolvability?

The original test on LIF evolvability showed p=2.16e-21 but collapsed
after controlling for synapse count. The hypothesis: curvature predicts
which connections matter for COGNITIVE function (attractor dynamics,
persistent states) that LIF couldn't see.

This script:
1. Loads Izhikevich strategy switching results (evolvable edges)
2. Computes Ollivier-Ricci curvature on the module graph
3. Tests correlation between curvature and Izh-evolvability
4. Controls for synapse count confound
5. Compares to LIF evolvability correlation

If curvature correlates with Izh-evolvability AFTER confound control,
then geometry predicts cognitive function. GU connection rescued.
"""
import sys, os, json
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy import stats
import networkx as nx

os.chdir("/home/ubuntu/fly-brain-embodied")

# Load connectome
labels = np.load('/home/ubuntu/module_labels_v2.npy')
df = pd.read_parquet('data/2025_Connectivity_783.parquet')
pre_mods = labels[df['Presynaptic_Index'].values].astype(int)
post_mods = labels[df['Postsynaptic_Index'].values].astype(int)

# Build module graph with synapse counts
edge_syn_count = defaultdict(int)
for i in range(len(df)):
    e = (int(pre_mods[i]), int(post_mods[i]))
    edge_syn_count[e] += 1

G = nx.DiGraph()
n_modules = int(labels.max()) + 1
for mod in range(n_modules):
    G.add_node(mod)
for (src, tgt), count in edge_syn_count.items():
    if src != tgt:
        G.add_edge(src, tgt, weight=count)

inter_module_edges = [(s, t) for (s, t) in edge_syn_count if s != t]
print(f"Module graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# ============================================================
# Compute Ollivier-Ricci curvature
# ============================================================
print("\nComputing Ollivier-Ricci curvature...")

def ollivier_ricci_curvature(G, src, tgt, alpha=0.5):
    """Compute Ollivier-Ricci curvature for edge (src, tgt)."""
    from scipy.optimize import linear_sum_assignment

    # Probability distributions: alpha on self, (1-alpha) uniform on neighbors
    src_neighbors = list(G.successors(src))
    tgt_neighbors = list(G.successors(tgt))

    if not src_neighbors or not tgt_neighbors:
        return 0.0

    # Source distribution
    src_nodes = [src] + src_neighbors
    src_probs = [alpha] + [(1 - alpha) / len(src_neighbors)] * len(src_neighbors)

    # Target distribution
    tgt_nodes = [tgt] + tgt_neighbors
    tgt_probs = [alpha] + [(1 - alpha) / len(tgt_neighbors)] * len(tgt_neighbors)

    # Compute shortest path distances between all pairs
    # Use precomputed shortest paths for efficiency
    cost_matrix = np.zeros((len(src_nodes), len(tgt_nodes)))
    for i, s in enumerate(src_nodes):
        for j, t in enumerate(tgt_nodes):
            if s == t:
                cost_matrix[i, j] = 0
            else:
                try:
                    cost_matrix[i, j] = nx.shortest_path_length(G, s, t)
                except nx.NetworkXNoPath:
                    cost_matrix[i, j] = G.number_of_nodes()  # large penalty

    # Solve optimal transport (Earth Mover's Distance)
    # For discrete distributions, use the Kantorovich formulation
    src_probs = np.array(src_probs)
    tgt_probs = np.array(tgt_probs)

    # Expand to transport matrix dimensions
    n_src, n_tgt = len(src_nodes), len(tgt_nodes)

    # Simple Wasserstein via linear assignment (approximation for small distributions)
    # Scale cost by probabilities
    scaled_cost = np.zeros((n_src * 100, n_tgt * 100))
    src_counts = (src_probs * 100).astype(int)
    tgt_counts = (tgt_probs * 100).astype(int)

    # Fix rounding
    src_counts[-1] += 100 - src_counts.sum()
    tgt_counts[-1] += 100 - tgt_counts.sum()

    row = 0
    for i, sc in enumerate(src_counts):
        for _ in range(sc):
            col = 0
            for j, tc in enumerate(tgt_counts):
                for _ in range(tc):
                    scaled_cost[row, col] = cost_matrix[i, j]
                    col += 1
            row += 1

    # Use Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(scaled_cost[:row, :col])
    W1 = scaled_cost[row_ind, col_ind].sum() / min(row, col)

    # Graph distance between src and tgt
    try:
        d = nx.shortest_path_length(G, src, tgt)
    except nx.NetworkXNoPath:
        d = G.number_of_nodes()

    if d == 0:
        return 0.0

    kappa = 1.0 - W1 / d
    return kappa

# Compute curvature for all edges
curvatures = {}
for i, (src, tgt) in enumerate(inter_module_edges):
    curvatures[(src, tgt)] = ollivier_ricci_curvature(G, src, tgt)
    if (i + 1) % 500 == 0:
        print(f"  [{i+1}/{len(inter_module_edges)}]")

print(f"Curvature computed for {len(curvatures)} edges")
print(f"  Mean: {np.mean(list(curvatures.values())):.4f}")
print(f"  Std:  {np.std(list(curvatures.values())):.4f}")

# ============================================================
# Load evolvability classifications
# ============================================================
print("\nLoading evolvability data...")

# Load Izhikevich strategy switching results
izh_evolvable = set()
izh_results_path = '/home/ubuntu/bulletproof_results/izh_strategy_switching.json'
if os.path.exists(izh_results_path):
    with open(izh_results_path) as f:
        izh_data = json.load(f)
    izh_evolvable = set(tuple(e) for e in izh_data.get('accepted_edges', []))
    print(f"  Izhikevich evolvable: {len(izh_evolvable)}")
else:
    print(f"  WARNING: {izh_results_path} not found. Will use partial data from log.")
    # Parse from log if JSON not ready
    import re
    log_path = '/home/ubuntu/bulletproof_results/izh_strategy_switching_run.log'
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                m = re.search(r'(\d+)->(\d+).*ACCEPTED', line)
                if m:
                    izh_evolvable.add((int(m.group(1)), int(m.group(2))))
        print(f"  Izhikevich evolvable (from log): {len(izh_evolvable)}")

# Load LIF navigation sweep for comparison
lif_evolvable = set()
lif_frozen = set()
for fname in ['sweep_navigation_0_1225.json', 'sweep_navigation.json']:
    fpath = f'/home/ubuntu/bulletproof_results/{fname}'
    if os.path.exists(fpath):
        with open(fpath) as f:
            data = json.load(f)
        if 'results' in data:
            for r in data['results']:
                edge = (r.get('pre_module'), r.get('post_module'))
                if r.get('classification') == 'evolvable':
                    lif_evolvable.add(edge)
                elif r.get('classification') == 'frozen':
                    lif_frozen.add(edge)
print(f"  LIF evolvable: {len(lif_evolvable)}, frozen: {len(lif_frozen)}")

# ============================================================
# Correlation analysis
# ============================================================
print("\n" + "=" * 60)
print("CURVATURE vs EVOLVABILITY")
print("=" * 60)

# Prepare data
edges = list(curvatures.keys())
curv_vals = np.array([curvatures[e] for e in edges])
syn_counts = np.array([edge_syn_count[e] for e in edges])
log_syn = np.log1p(syn_counts)

# Binary evolvability labels
izh_evol = np.array([1 if e in izh_evolvable else 0 for e in edges])
lif_evol = np.array([1 if e in lif_evolvable else 0 for e in edges])
lif_froz = np.array([1 if e in lif_frozen else 0 for e in edges])

# 1. Raw correlation: curvature vs Izh evolvability
if izh_evol.sum() > 0:
    evol_curv = curv_vals[izh_evol == 1]
    non_evol_curv = curv_vals[izh_evol == 0]
    u_stat, p_raw = stats.mannwhitneyu(evol_curv, non_evol_curv, alternative='two-sided')
    print(f"\nIzhikevich evolvable vs non-evolvable curvature:")
    print(f"  Evolvable mean curvature:     {evol_curv.mean():.4f} (n={len(evol_curv)})")
    print(f"  Non-evolvable mean curvature: {non_evol_curv.mean():.4f} (n={len(non_evol_curv)})")
    print(f"  Mann-Whitney U: p = {p_raw:.6e}")

    # Point-biserial correlation
    r_pb, p_pb = stats.pointbiserialr(izh_evol, curv_vals)
    print(f"  Point-biserial r = {r_pb:.4f}, p = {p_pb:.6e}")

# 2. Confound check: curvature vs synapse count
r_curv_syn, p_curv_syn = stats.spearmanr(curv_vals, log_syn)
print(f"\nConfound check:")
print(f"  Curvature vs log(synapse count): r = {r_curv_syn:.4f}, p = {p_curv_syn:.6e}")

# 3. Partial correlation: curvature vs evolvability, controlling for synapse count
if izh_evol.sum() > 1:
    # Residualize curvature on synapse count
    from numpy.polynomial.polynomial import polyfit
    # Linear regression: curvature ~ synapse_count
    slope, intercept = np.polyfit(log_syn, curv_vals, 1)
    curv_residual = curv_vals - (slope * log_syn + intercept)

    r_partial, p_partial = stats.pointbiserialr(izh_evol, curv_residual)
    print(f"\nPartial correlation (controlling for synapse count):")
    print(f"  Curvature residual vs Izh evolvability: r = {r_partial:.4f}, p = {p_partial:.6e}")

    if p_partial < 0.05:
        print(f"  >>> SIGNIFICANT! Curvature predicts Izh-evolvability AFTER controlling for synapse count")
        print(f"  >>> Geometry predicts cognitive function. GU connection supported.")
    else:
        print(f"  >>> Not significant after confound control. Same result as LIF.")

# 4. Compare LIF vs Izhikevich evolvable sets
if lif_evolvable and izh_evolvable:
    overlap = lif_evolvable & izh_evolvable
    lif_only = lif_evolvable - izh_evolvable
    izh_only = izh_evolvable - lif_evolvable
    print(f"\nLIF vs Izhikevich evolvable edge comparison:")
    print(f"  LIF evolvable: {len(lif_evolvable)}")
    print(f"  Izh evolvable: {len(izh_evolvable)}")
    print(f"  Overlap: {len(overlap)}")
    print(f"  LIF-only: {len(lif_only)}")
    print(f"  Izh-only: {len(izh_only)}")

    # Curvature of Izh-only edges (the NEW cognitive edges)
    if izh_only:
        izh_only_curv = [curvatures[e] for e in izh_only if e in curvatures]
        lif_only_curv = [curvatures[e] for e in lif_only if e in curvatures]
        all_curv = list(curvatures.values())
        print(f"\n  Curvature of Izh-only edges: {np.mean(izh_only_curv):.4f}")
        print(f"  Curvature of LIF-only edges: {np.mean(lif_only_curv):.4f}")
        print(f"  Curvature of all edges:      {np.mean(all_curv):.4f}")

        if len(izh_only_curv) > 1 and len(lif_only_curv) > 1:
            u, p = stats.mannwhitneyu(izh_only_curv, lif_only_curv, alternative='two-sided')
            print(f"  Izh-only vs LIF-only curvature: p = {p:.6e}")

# 5. Module-level analysis: are Izh-evolvable edges in CX-heavy modules?
print(f"\nModule analysis of Izh-evolvable edges:")
mod_sizes = {m: int(np.sum(labels == m)) for m in range(n_modules)}
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = pd.read_csv('data/2025_Completeness_783.csv', index_col=0).index.astype(str).tolist()
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

cx_per_mod = defaultdict(int)
for idx, nid in enumerate(neuron_ids):
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        cx_per_mod[int(labels[idx])] += 1

for e in sorted(izh_evolvable):
    src_cx = cx_per_mod.get(e[0], 0)
    tgt_cx = cx_per_mod.get(e[1], 0)
    curv = curvatures.get(e, 'N/A')
    syns = edge_syn_count.get(e, 0)
    print(f"  {e[0]}->{e[1]}: curvature={curv:.4f}, synapses={syns}, "
          f"src_CX={src_cx}, tgt_CX={tgt_cx}")

# Save
output = {
    'curvatures': {f"{k[0]}->{k[1]}": float(v) for k, v in curvatures.items()},
    'izh_evolvable': sorted([list(e) for e in izh_evolvable]),
    'lif_evolvable_count': len(lif_evolvable),
    'raw_correlation_p': float(p_raw) if izh_evol.sum() > 0 else None,
    'partial_correlation_p': float(p_partial) if izh_evol.sum() > 1 else None,
}
with open('/home/ubuntu/bulletproof_results/curvature_retest.json', 'w') as f:
    json.dump(output, f)
print(f"\nSaved to /home/ubuntu/bulletproof_results/curvature_retest.json")
print("DONE.")
