#!/usr/bin/env python3
"""
Axon Trajectory Growth Model for FlyWire Connectome
=====================================================
Uses soma positions + connectivity as a proxy for axon trajectories.
Vector from pre-soma to post-soma approximates axon growth direction.
Simulates growth along hemilineage vector fields and predicts connections.
"""

import numpy as np
import pandas as pd
import json
import os
import sys
import time
import warnings
from datetime import datetime
from collections import defaultdict
from scipy.spatial import cKDTree
from sklearn.decomposition import PCA
warnings.filterwarnings('ignore')

LOG_FILE = '/home/ubuntu/bulletproof_results/trajectory_growth.log'
os.makedirs('/home/ubuntu/bulletproof_results', exist_ok=True)

def log(msg):
    ts = datetime.now().strftime('%H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

# ─────────────────────────────────────────────────────────────
# SECTION 1: DATA LOADING
# ─────────────────────────────────────────────────────────────

log("="*70)
log("AXON TRAJECTORY GROWTH MODEL v1.0")
log("="*70)

SIGNATURE_HEMILINEAGES = [
    'VPNd2','VLPp2','DM3_CX_d2','LB23','LB12','VLPl2_medial','LB7',
    'VLPl&p2_posterior','MD3','MX12','VLPl&p2_lateral','DM1_CX_d2',
    'WEDd1','MX3','VPNd1','putative_primary','CREa2_medial',
    'CREa1_dorsal','SLPal3_and_SLPal4_dorsal'
]
SIGNATURE_CELL_CLASSES = ['ME>LO.LOP','LOP','DAN','ME','LA','CX','ME>LA','LO','ME>LO']

log("Loading flywire_annotations.tsv ...")
ann = pd.read_csv('/home/ubuntu/fly-brain-embodied/data/flywire_annotations.tsv', sep='\t',
                  usecols=['root_id','soma_x','soma_y','soma_z','pos_x','pos_y','pos_z',
                           'ito_lee_hemilineage','hartenstein_hemilineage',
                           'cell_class','cell_sub_class','cell_type','flow','side'])
log(f"  Loaded {len(ann):,} neuron annotations")

# Use ito_lee_hemilineage as primary, fall back to hartenstein
ann['hemilineage'] = ann['ito_lee_hemilineage'].fillna(ann['hartenstein_hemilineage'])

# Gene-guided: neurons whose hemilineage is in signature OR cell_class is in signature
mask_hemi = ann['hemilineage'].isin(SIGNATURE_HEMILINEAGES)
mask_class = ann['cell_class'].isin(SIGNATURE_CELL_CLASSES)
gene_guided_ann = ann[mask_hemi].copy()
log(f"  Gene-guided neurons (hemi filter): {len(gene_guided_ann):,}")

# Require soma positions
gene_guided_ann = gene_guided_ann.dropna(subset=['soma_x','soma_y','soma_z'])
log(f"  With soma positions: {len(gene_guided_ann):,}")

# Build root_id -> soma position dict
soma_pos = dict(zip(gene_guided_ann['root_id'],
                    gene_guided_ann[['soma_x','soma_y','soma_z']].values))
soma_hemi = dict(zip(gene_guided_ann['root_id'], gene_guided_ann['hemilineage']))

gene_guided_ids = set(gene_guided_ann['root_id'].values)
log(f"  Unique gene-guided root IDs: {len(gene_guided_ids):,}")

log("Loading connectivity parquet ...")
t0 = time.time()
conn = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet',
                       columns=['Presynaptic_ID','Postsynaptic_ID','Connectivity'])
log(f"  Loaded {len(conn):,} connections in {time.time()-t0:.1f}s")

# Filter to gene-guided subnetwork
conn_gg = conn[conn['Presynaptic_ID'].isin(gene_guided_ids) &
               conn['Postsynaptic_ID'].isin(gene_guided_ids)].copy()
log(f"  Gene-guided internal connections: {len(conn_gg):,}")

# Ground truth set (pre_id, post_id) pairs
real_connections = set(zip(conn_gg['Presynaptic_ID'], conn_gg['Postsynaptic_ID']))
log(f"  Real connection pairs: {len(real_connections):,}")

# ─────────────────────────────────────────────────────────────
# SECTION 2: TRAJECTORY VECTOR COMPUTATION
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 2: Computing axon trajectory vectors")
log("─"*50)

# For each connection, compute vector: pre_soma -> post_soma
# This approximates the direction the axon grows
conn_gg = conn_gg[conn_gg['Presynaptic_ID'].isin(soma_pos) &
                  conn_gg['Postsynaptic_ID'].isin(soma_pos)].copy()

pre_somas = np.array([soma_pos[rid] for rid in conn_gg['Presynaptic_ID']])
post_somas = np.array([soma_pos[rid] for rid in conn_gg['Postsynaptic_ID']])
raw_vectors = post_somas - pre_somas

# Normalize vectors
norms = np.linalg.norm(raw_vectors, axis=1, keepdims=True)
norms = np.where(norms < 1e-6, 1.0, norms)
unit_vectors = raw_vectors / norms

conn_gg['pre_hemi'] = conn_gg['Presynaptic_ID'].map(soma_hemi)
conn_gg = conn_gg.dropna(subset=['pre_hemi'])

# Compute distances
conn_gg['distance'] = norms.flatten()

log(f"  Connections with both soma positions: {len(conn_gg):,}")
log(f"  Mean inter-soma distance: {conn_gg['distance'].mean():.0f} nm")
log(f"  Median inter-soma distance: {conn_gg['distance'].median():.0f} nm")

# ─────────────────────────────────────────────────────────────
# SECTION 3: HEMILINEAGE VECTOR FIELD
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 3: Fitting hemilineage vector fields")
log("─"*50)

# Group trajectory vectors by hemilineage
hemi_vectors = defaultdict(list)
for i, row in enumerate(conn_gg.itertuples()):
    hemi_vectors[row.pre_hemi].append(unit_vectors[i])

hemi_stats = {}
for hemi, vecs in hemi_vectors.items():
    vecs = np.array(vecs)
    n = len(vecs)
    # Mean direction (resultant vector)
    mean_dir = vecs.mean(axis=0)
    mean_norm = np.linalg.norm(mean_dir)
    if mean_norm > 1e-6:
        mean_dir_unit = mean_dir / mean_norm
    else:
        mean_dir_unit = np.array([1., 0., 0.])

    # Circular concentration: R = |mean resultant| (0=dispersed, 1=uniform)
    concentration = mean_norm

    # PCA to find principal growth axis
    if n >= 3:
        pca = PCA(n_components=min(3, n))
        pca.fit(vecs)
        principal_axis = pca.components_[0]
        # Align with mean direction
        if np.dot(principal_axis, mean_dir) < 0:
            principal_axis = -principal_axis
        var_explained = pca.explained_variance_ratio_[0]
    else:
        principal_axis = mean_dir_unit
        var_explained = 1.0

    hemi_stats[hemi] = {
        'n_connections': n,
        'mean_direction': mean_dir_unit,
        'principal_axis': principal_axis,
        'concentration': concentration,
        'var_explained': var_explained,
    }

log(f"  Hemilineages with trajectory data: {len(hemi_stats)}")
for hemi, s in sorted(hemi_stats.items(), key=lambda x: -x[1]['n_connections']):
    log(f"    {hemi:30s}  n={s['n_connections']:5d}  conc={s['concentration']:.3f}  "
        f"pca_var={s['var_explained']:.3f}  "
        f"dir=({s['mean_direction'][0]:+.2f},{s['mean_direction'][1]:+.2f},{s['mean_direction'][2]:+.2f})")

# ─────────────────────────────────────────────────────────────
# SECTION 4: TRAJECTORY SIMULATION
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 4: Simulating axon trajectory growth")
log("─"*50)

# Build KD-tree over all gene-guided soma positions
gg_ids = np.array(list(gene_guided_ids & set(soma_pos.keys())))
gg_somas = np.array([soma_pos[rid] for rid in gg_ids])
tree = cKDTree(gg_somas)
log(f"  KD-tree built over {len(gg_ids):,} gene-guided neurons")

def simulate_axon_growth(
    pre_id, soma_xyz, direction, all_ids, all_somas, kd_tree,
    step_size=None, n_steps=20, synapse_radius=None
):
    """
    Simulate axon growing from soma along direction vector.
    At each step, capture all neurons within synapse_radius as predicted targets.
    Returns set of predicted post-synaptic neuron IDs.
    """
    if step_size is None:
        step_size = 5000  # ~5 microns in nm
    if synapse_radius is None:
        synapse_radius = 8000  # ~8 microns capture radius

    predicted = set()
    pos = soma_xyz.copy().astype(float)

    for step in range(n_steps):
        # Move along trajectory
        pos = pos + direction * step_size
        # Find all neurons within synapse_radius
        idxs = kd_tree.query_ball_point(pos, synapse_radius)
        for idx in idxs:
            nid = all_ids[idx]
            if nid != pre_id:
                predicted.add(nid)

    return predicted

# Run simulation for all gene-guided neurons
log("  Running trajectory simulation ...")
t0 = time.time()

all_predicted = set()  # (pre_id, post_id)
n_simulated = 0
no_hemi_count = 0

# Parameters for first run
STEP_SIZE = 5000    # nm per step
N_STEPS = 25        # steps along trajectory
SYNAPSE_RADIUS = 7000  # nm capture radius

for pre_id in gene_guided_ids:
    if pre_id not in soma_pos:
        continue
    hemi = soma_hemi.get(pre_id)
    if hemi not in hemi_stats:
        no_hemi_count += 1
        continue

    soma_xyz = soma_pos[pre_id]
    direction = hemi_stats[hemi]['mean_direction']

    targets = simulate_axon_growth(
        pre_id, soma_xyz, direction, gg_ids, gg_somas, tree,
        step_size=STEP_SIZE, n_steps=N_STEPS, synapse_radius=SYNAPSE_RADIUS
    )

    for post_id in targets:
        all_predicted.add((pre_id, post_id))

    n_simulated += 1

elapsed = time.time() - t0
log(f"  Simulated {n_simulated:,} neurons in {elapsed:.1f}s")
log(f"  Neurons without hemilineage field: {no_hemi_count:,}")
log(f"  Total predicted connections: {len(all_predicted):,}")

# ─────────────────────────────────────────────────────────────
# SECTION 5: EVALUATION
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 5: Evaluation - Precision / Recall / F1")
log("─"*50)

def evaluate(predicted_set, real_set):
    tp = len(predicted_set & real_set)
    fp = len(predicted_set - real_set)
    fn = len(real_set - predicted_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall, 'f1': f1}

metrics = evaluate(all_predicted, real_connections)
log(f"  True Positives:  {metrics['tp']:>8,}")
log(f"  False Positives: {metrics['fp']:>8,}")
log(f"  False Negatives: {metrics['fn']:>8,}")
log(f"  Precision:       {metrics['precision']:.4f}  ({metrics['precision']*100:.2f}%)")
log(f"  Recall:          {metrics['recall']:.4f}  ({metrics['recall']*100:.2f}%)")
log(f"  F1 Score:        {metrics['f1']:.4f}  ({metrics['f1']*100:.2f}%)")

# Per-hemilineage breakdown
log("")
log("  Per-hemilineage evaluation:")
hemi_real = defaultdict(set)
for pid, qid in real_connections:
    h = soma_hemi.get(pid)
    if h:
        hemi_real[h].add((pid, qid))

hemi_pred = defaultdict(set)
for pid, qid in all_predicted:
    h = soma_hemi.get(pid)
    if h:
        hemi_pred[h].add((pid, qid))

hemi_results = {}
for hemi in SIGNATURE_HEMILINEAGES:
    m = evaluate(hemi_pred[hemi], hemi_real[hemi])
    hemi_results[hemi] = m
    if m['tp'] + m['fp'] + m['fn'] > 0:
        log(f"    {hemi:30s}  P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  "
            f"real={m['tp']+m['fn']:4d}  pred={m['tp']+m['fp']:4d}")

# ─────────────────────────────────────────────────────────────
# SECTION 6: PARAMETER SWEEP
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 6: Parameter sweep to optimize F1")
log("─"*50)

best_f1 = metrics['f1']
best_params = {'step_size': STEP_SIZE, 'n_steps': N_STEPS, 'synapse_radius': SYNAPSE_RADIUS}

sweep_configs = [
    (3000, 30, 5000),
    (3000, 30, 8000),
    (5000, 25, 5000),
    (5000, 25, 10000),
    (7000, 20, 6000),
    (7000, 20, 9000),
    (4000, 35, 7000),
    (10000, 15, 8000),
    (2000, 50, 4000),
]

for step, nstep, radius in sweep_configs:
    predicted_sweep = set()
    for pre_id in gene_guided_ids:
        if pre_id not in soma_pos:
            continue
        hemi = soma_hemi.get(pre_id)
        if hemi not in hemi_stats:
            continue
        soma_xyz = soma_pos[pre_id]
        direction = hemi_stats[hemi]['mean_direction']
        targets = simulate_axon_growth(
            pre_id, soma_xyz, direction, gg_ids, gg_somas, tree,
            step_size=step, n_steps=nstep, synapse_radius=radius
        )
        for post_id in targets:
            predicted_sweep.add((pre_id, post_id))

    m = evaluate(predicted_sweep, real_connections)
    flag = " *** BEST ***" if m['f1'] > best_f1 else ""
    log(f"  step={step:5d} nstep={nstep:2d} radius={radius:5d}  "
        f"P={m['precision']:.4f}  R={m['recall']:.4f}  F1={m['f1']:.4f}{flag}")
    if m['f1'] > best_f1:
        best_f1 = m['f1']
        best_params = {'step_size': step, 'n_steps': nstep, 'synapse_radius': radius}

log(f"")
log(f"  Best params: {best_params}  Best F1: {best_f1:.4f}")

# ─────────────────────────────────────────────────────────────
# SECTION 7: ENHANCED MODEL - PCA PRINCIPAL AXIS + BIDIRECTIONAL
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 7: Enhanced model - PCA axis + bidirectional growth")
log("─"*50)

# Use PCA principal axis and grow in BOTH directions (axon + dendrite)
def simulate_bidirectional(pre_id, soma_xyz, direction, all_ids, all_somas, kd_tree,
                            step_size=5000, n_steps=25, synapse_radius=7000, n_branches=1):
    predicted = set()
    directions = [direction, -direction * 0.5]  # axon + shorter dendrite direction

    for d in directions[:n_branches]:
        pos = soma_xyz.copy().astype(float)
        for step in range(n_steps):
            pos = pos + d * step_size
            idxs = kd_tree.query_ball_point(pos, synapse_radius)
            for idx in idxs:
                nid = all_ids[idx]
                if nid != pre_id:
                    predicted.add(nid)
    return predicted

best_step = best_params['step_size']
best_nstep = best_params['n_steps']
best_radius = best_params['synapse_radius']

# Try PCA axis
all_predicted_pca = set()
for pre_id in gene_guided_ids:
    if pre_id not in soma_pos:
        continue
    hemi = soma_hemi.get(pre_id)
    if hemi not in hemi_stats:
        continue
    soma_xyz = soma_pos[pre_id]
    direction = hemi_stats[hemi]['principal_axis']  # PCA instead of mean
    targets = simulate_axon_growth(
        pre_id, soma_xyz, direction, gg_ids, gg_somas, tree,
        step_size=best_step, n_steps=best_nstep, synapse_radius=best_radius
    )
    for post_id in targets:
        all_predicted_pca.add((pre_id, post_id))

m_pca = evaluate(all_predicted_pca, real_connections)
log(f"  PCA principal axis:      P={m_pca['precision']:.4f}  R={m_pca['recall']:.4f}  F1={m_pca['f1']:.4f}")

# Bidirectional
all_predicted_bidir = set()
for pre_id in gene_guided_ids:
    if pre_id not in soma_pos:
        continue
    hemi = soma_hemi.get(pre_id)
    if hemi not in hemi_stats:
        continue
    soma_xyz = soma_pos[pre_id]
    direction = hemi_stats[hemi]['mean_direction']
    targets = simulate_bidirectional(
        pre_id, soma_xyz, direction, gg_ids, gg_somas, tree,
        step_size=best_step, n_steps=best_nstep, synapse_radius=best_radius, n_branches=2
    )
    for post_id in targets:
        all_predicted_bidir.add((pre_id, post_id))

m_bidir = evaluate(all_predicted_bidir, real_connections)
log(f"  Bidirectional growth:    P={m_bidir['precision']:.4f}  R={m_bidir['recall']:.4f}  F1={m_bidir['f1']:.4f}")

# ─────────────────────────────────────────────────────────────
# SECTION 8: DISTANCE-WEIGHTED CONNECTIVITY MODEL
# ─────────────────────────────────────────────────────────────
log("")
log("─"*50)
log("SECTION 8: Distance-weighted synapse probability along trajectory")
log("─"*50)

# Instead of binary capture, weight by: proximity to trajectory line * synapse count
def trajectory_line_distance(soma_xyz, direction, target_xyz):
    """Minimum distance from target to the trajectory ray."""
    v = target_xyz - soma_xyz
    t = np.dot(v, direction)  # projection onto direction
    if t < 0:
        t = 0  # don't go backward
    closest = soma_xyz + t * direction
    return np.linalg.norm(target_xyz - closest), t

# Build distance-based predictions with a max-range threshold
MAX_TRAJECTORY_LENGTH = best_step * best_nstep  # total axon length
PROXIMITY_THRESHOLD = best_radius  # max distance from trajectory line

all_predicted_dist = set()
for pre_id in gene_guided_ids:
    if pre_id not in soma_pos:
        continue
    hemi = soma_hemi.get(pre_id)
    if hemi not in hemi_stats:
        continue
    soma_xyz = soma_pos[pre_id]
    direction = hemi_stats[hemi]['mean_direction']

    # Find all candidates near the trajectory line
    # Use sphere of max trajectory radius first for efficiency
    max_r = MAX_TRAJECTORY_LENGTH + PROXIMITY_THRESHOLD
    candidate_idxs = tree.query_ball_point(soma_xyz, max_r)

    for idx in candidate_idxs:
        post_id = gg_ids[idx]
        if post_id == pre_id:
            continue
        target_xyz = gg_somas[idx]
        dist_to_traj, t_proj = trajectory_line_distance(soma_xyz, direction, target_xyz)
        if dist_to_traj <= PROXIMITY_THRESHOLD and t_proj <= MAX_TRAJECTORY_LENGTH:
            all_predicted_dist.add((pre_id, post_id))

m_dist = evaluate(all_predicted_dist, real_connections)
log(f"  Trajectory-line model:   P={m_dist['precision']:.4f}  R={m_dist['recall']:.4f}  F1={m_dist['f1']:.4f}")
log(f"  Predicted: {len(all_predicted_dist):,}  Real: {len(real_connections):,}")

# ─────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────
log("")
log("="*70)
log("FINAL SUMMARY - Axon Trajectory Growth Model v1.0")
log("="*70)

all_models = [
    ("Baseline (step-along)",        metrics),
    ("Best params (sweep)",          evaluate(all_predicted if best_f1 == metrics['f1'] else set(), real_connections)),
    ("PCA principal axis",           m_pca),
    ("Bidirectional growth",         m_bidir),
    ("Trajectory-line proximity",    m_dist),
]

best_overall_f1 = 0
best_model_name = ""
for name, m in all_models:
    if m['f1'] > best_overall_f1:
        best_overall_f1 = m['f1']
        best_model_name = name
    log(f"  {name:35s}  P={m['precision']:.4f}  R={m['recall']:.4f}  F1={m['f1']:.4f}")

log("")
log(f"  BEST MODEL: {best_model_name}")
log(f"  BEST F1:    {best_overall_f1:.4f} ({best_overall_f1*100:.2f}%)")
log("")
log("  Next iterations to try:")
log("  1. Individual per-neuron trajectory fitting (not just hemilineage mean)")
log("  2. Attraction to target brain regions (VPN -> VLP, etc)")
log("  3. Weighted by synapse count (stronger = more directional signal)")
log("  4. Cross-hemisphere bilateral connections")
log("  5. Hierarchical vector field: coarse hemilineage + fine local adjustment")
log("="*70)

# Save results
results = {
    'timestamp': datetime.now().isoformat(),
    'version': '1.0',
    'n_neurons': len(gene_guided_ids),
    'n_real_connections': len(real_connections),
    'hemilineages': len(hemi_stats),
    'params': best_params,
    'models': {name: m for name, m in all_models},
    'best_model': best_model_name,
    'best_f1': best_overall_f1,
}
with open('/home/ubuntu/bulletproof_results/trajectory_results_v1.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)
log(f"Results saved to /home/ubuntu/bulletproof_results/trajectory_results_v1.json")
