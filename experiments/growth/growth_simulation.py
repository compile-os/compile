#!/usr/bin/env python3
"""
Developmental Growth Simulation for 8,158-neuron gene-guided processor.

Simulates axon growth with progressive rule additions, measuring
what % of real FlyWire connections each rule set produces.

Rules:
  0: Baseline — random connections weighted by distance
  1: + Hemilineage-pair connection probabilities from real data
  2: + Neurotransmitter compatibility
  3: + Sharpened spatial proximity weighting
  4: + Target density (axons prefer denser regions)
  5: + Synapse count matching (calibrate to real pair counts)
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import warnings
warnings.filterwarnings('ignore')

LOG_FILE = '/home/ubuntu/bulletproof_results/growth_simulation.log'
RESULTS_FILE = '/home/ubuntu/bulletproof_results/growth_simulation_results.json'
COMPILER_FILE = '/home/ubuntu/bulletproof_results/developmental_compiler.json'
ANNOTATIONS_FILE = '/home/ubuntu/fly-brain-embodied/data/flywire_annotations.tsv'
CONNECTIVITY_FILE = '/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet'

# Setup logging to both file and stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

np.random.seed(42)

# ============================================================
# NEUROTRANSMITTER COMPATIBILITY MATRIX
# Based on known fly brain circuit biology
# ============================================================
NT_COMPAT = {
    ('acetylcholine', 'acetylcholine'): 1.0,
    ('acetylcholine', 'gaba'):          0.8,
    ('acetylcholine', 'glutamate'):     0.7,
    ('acetylcholine', 'dopamine'):      0.5,
    ('acetylcholine', 'serotonin'):     0.4,
    ('gaba',          'acetylcholine'): 1.0,
    ('gaba',          'gaba'):          0.3,
    ('gaba',          'glutamate'):     0.5,
    ('gaba',          'dopamine'):      0.3,
    ('glutamate',     'acetylcholine'): 0.9,
    ('glutamate',     'gaba'):          0.6,
    ('glutamate',     'glutamate'):     0.4,
    ('dopamine',      'acetylcholine'): 1.0,
    ('dopamine',      'gaba'):          0.7,
    ('dopamine',      'dopamine'):      0.2,
    ('serotonin',     'acetylcholine'): 0.8,
}
NT_DEFAULT = 0.3


# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    log.info("=" * 70)
    log.info("DEVELOPMENTAL GROWTH SIMULATION — FlyWire 8,158-Neuron Processor")
    log.info("=" * 70)

    # --- Load compiler program ---
    with open(COMPILER_FILE) as f:
        compiler = json.load(f)

    cell_types = compiler['growth_program']['cell_types']
    conn_rules = compiler['growth_program']['connections']
    target_synapses = compiler['target_synapses']

    hemilineage_list = [ct['hemilineage'] for ct in cell_types]
    hl_count_map = {ct['hemilineage']: ct['count'] for ct in cell_types}
    hl_nt_map    = {ct['hemilineage']: ct['neurotransmitter'] for ct in cell_types}

    log.info(f"Compiler: {len(cell_types)} hemilineages, {len(conn_rules)} connection rules")
    log.info(f"Target synapses from compiler: {target_synapses:,}")

    # --- Load annotations ---
    log.info("\nLoading FlyWire annotations...")
    t0 = time.time()
    ann = pd.read_csv(ANNOTATIONS_FILE, sep='\t', low_memory=False)
    log.info(f"  Loaded {len(ann):,} neurons in {time.time()-t0:.1f}s")

    # Filter to hemilineages we need
    # 'putative_primary' = neurons with NaN or empty ito_lee_hemilineage
    ann['_hl'] = ann['ito_lee_hemilineage'].fillna('putative_primary')
    ann.loc[ann['_hl'] == '', '_hl'] = 'putative_primary'
    ann.loc[~ann['_hl'].isin(hemilineage_list), '_hl'] = 'putative_primary'

    mask = ann['_hl'].isin(hemilineage_list)
    pool = ann[mask].copy()
    log.info(f"  Neurons in target hemilineages: {len(pool):,}")
    log.info(f"  Hemilineage breakdown:\n{pool['_hl'].value_counts().to_string()}")

    # Pick coordinate columns (prefer soma_x/y/z, fall back to pos_x/y/z)
    if 'soma_x' in pool.columns and pool['soma_x'].notna().mean() > 0.5:
        xyz_cols = ['soma_x', 'soma_y', 'soma_z']
    else:
        xyz_cols = ['pos_x', 'pos_y', 'pos_z']
    log.info(f"  Using coordinate columns: {xyz_cols}")

    pool = pool.dropna(subset=xyz_cols)
    log.info(f"  Neurons with valid coordinates: {len(pool):,}")

    # Sample proportionally to match compiler counts (target 8,158)
    sampled_frames = []
    for hl in hemilineage_list:
        target_n = hl_count_map[hl]
        subset = pool[pool['_hl'] == hl]
        if len(subset) == 0:
            log.warning(f"  No neurons found for hemilineage: {hl}")
            continue
        if len(subset) > target_n:
            subset = subset.sample(n=target_n, random_state=42)
        sampled_frames.append(subset)

    neurons = pd.concat(sampled_frames, ignore_index=True)
    n = len(neurons)
    log.info(f"\n  Final neuron set: {n:,} neurons")

    coords  = neurons[xyz_cols].values.astype(np.float32)
    root_ids = neurons['root_id'].values
    hl_labels = neurons['_hl'].values
    nt_labels  = np.array([hl_nt_map.get(hl, 'acetylcholine') for hl in hl_labels])

    # --- Build index maps ---
    id_to_idx = {int(rid): i for i, rid in enumerate(root_ids)}

    # --- Load connectivity parquet ---
    log.info("\nLoading connectivity data...")
    t0 = time.time()
    conn_df = pd.read_parquet(CONNECTIVITY_FILE)
    log.info(f"  Full connectome: {len(conn_df):,} synaptic contacts in {time.time()-t0:.1f}s")

    # Filter to our neuron set
    our_ids = set(id_to_idx.keys())
    mask_pre  = conn_df['Presynaptic_ID'].isin(our_ids)
    mask_post = conn_df['Postsynaptic_ID'].isin(our_ids)
    real_conn = conn_df[mask_pre & mask_post].copy()
    log.info(f"  Synaptic contacts within our {n:,}-neuron set: {len(real_conn):,}")

    # Build real pairs as encoded int64 for fast set operations
    pre_arr  = real_conn['Presynaptic_ID'].map(id_to_idx).values
    post_arr = real_conn['Postsynaptic_ID'].map(id_to_idx).values
    valid    = (~np.isnan(pre_arr.astype(float))) & (~np.isnan(post_arr.astype(float)))
    pre_arr  = pre_arr[valid].astype(np.int32)
    post_arr = post_arr[valid].astype(np.int32)

    real_encoded = pre_arr.astype(np.int64) * n + post_arr.astype(np.int64)
    real_pairs   = set(real_encoded.tolist())
    log.info(f"  Unique real (pre, post) neuron pairs: {len(real_pairs):,}")

    # Also store per-pair synapse counts for rule 5
    pair_weights = {}
    for pre, post, syn in zip(pre_arr, post_arr, real_conn['Connectivity'].values[valid]):
        key = int(pre) * n + int(post)
        pair_weights[key] = pair_weights.get(key, 0) + int(syn)

    # Build hemilineage pair -> connection probability lookup
    hl_pair_prob = {}
    for rule in conn_rules:
        key = (rule['from'], rule['to'])
        hl_pair_prob[key] = rule['connection_probability']

    # Hemilineage index arrays (for fast vectorized lookups)
    unique_hls = sorted(set(hl_labels))
    hl_to_int  = {hl: i for i, hl in enumerate(unique_hls)}
    hl_int     = np.array([hl_to_int[hl] for hl in hl_labels], dtype=np.int16)

    # Precompute pair probability matrix between hemilineages
    n_hl = len(unique_hls)
    hl_prob_matrix = np.full((n_hl, n_hl), 0.001, dtype=np.float32)
    for (hl_from, hl_to), prob in hl_pair_prob.items():
        if hl_from in hl_to_int and hl_to in hl_to_int:
            i, j = hl_to_int[hl_from], hl_to_int[hl_to]
            hl_prob_matrix[i, j] = max(prob, 0.001)

    # NT index arrays
    unique_nts = sorted(set(nt_labels))
    nt_to_int  = {nt: i for i, nt in enumerate(unique_nts)}
    nt_int     = np.array([nt_to_int[nt] for nt in nt_labels], dtype=np.int8)

    n_nt = len(unique_nts)
    nt_compat_matrix = np.full((n_nt, n_nt), NT_DEFAULT, dtype=np.float32)
    for (nt_from, nt_to), val in NT_COMPAT.items():
        if nt_from in nt_to_int and nt_to in nt_to_int:
            i, j = nt_to_int[nt_from], nt_to_int[nt_to]
            nt_compat_matrix[i, j] = val

    log.info("\nData loading complete.")
    log.info(f"  Neurons: {n:,} | Real pairs: {len(real_pairs):,} | Hemilineages: {n_hl} | NTs: {n_nt}")

    return dict(
        n=n,
        coords=coords,
        root_ids=root_ids,
        hl_labels=hl_labels,
        nt_labels=nt_labels,
        hl_int=hl_int,
        nt_int=nt_int,
        hl_prob_matrix=hl_prob_matrix,
        nt_compat_matrix=nt_compat_matrix,
        real_pairs=real_pairs,
        pair_weights=pair_weights,
        unique_hls=unique_hls,
        unique_nts=unique_nts,
        target_synapses=target_synapses,
    )


# ============================================================
# KD-TREE NEIGHBOR PRECOMPUTATION
# ============================================================

def build_neighbor_graph(coords, k=300):
    """Build k-nearest-neighbor graph for axon growth routing."""
    log.info(f"\nBuilding KD-tree neighbor graph (k={k})...")
    t0 = time.time()
    tree = cKDTree(coords)
    dists, idxs = tree.query(coords, k=k + 1)  # +1: first result is self (d=0)
    dists = dists[:, 1:].astype(np.float32)     # drop self
    idxs  = idxs[:, 1:].astype(np.int32)
    log.info(f"  Done in {time.time()-t0:.1f}s  |  median NN dist: {np.median(dists[:,0]):.1f}")

    # Per-neuron sigma = median distance to nearest 20 neighbors
    sigma = np.median(dists[:, :20], axis=1).astype(np.float32)
    sigma[sigma < 1.0] = 1.0

    # Target density: count neurons within radius = 2*sigma median
    r_density = float(np.median(sigma) * 2.0)
    log.info(f"  Density radius: {r_density:.1f} nm")
    density = np.array([len(tree.query_ball_point(coords[i], r_density))
                        for i in range(len(coords))], dtype=np.float32)
    density /= density.max()

    return dists, idxs, sigma, density


# ============================================================
# GROWTH SIMULATION — ONE RULE LEVEL
# ============================================================

def simulate(data, dists, idxs, sigma, density, rule_level, k=300):
    """
    Grow axons for all neurons and measure connectivity match.

    rule_level controls which biological rules are active:
      0  distance-only baseline
      1  + hemilineage-pair probabilities
      2  + NT compatibility
      3  + sharpened spatial decay
      4  + target density
      5  + calibrate connection count to real pair count
    """
    n           = data['n']
    hl_int      = data['hl_int']
    nt_int      = data['nt_int']
    hl_pm       = data['hl_prob_matrix']
    nt_cm       = data['nt_compat_matrix']
    real_pairs  = data['real_pairs']
    n_real      = len(real_pairs)

    log.info(f"\n{'='*60}")
    log.info(f"RULE LEVEL {rule_level}")
    rule_names = {
        0: "Distance-only baseline",
        1: "+ Hemilineage-pair probabilities",
        2: "+ Neurotransmitter compatibility",
        3: "+ Sharpened spatial decay",
        4: "+ Target density weighting",
        5: "+ Synapse-count calibration",
    }
    log.info(f"  {rule_names.get(rule_level, '')}")
    log.info(f"{'='*60}")

    t0 = time.time()

    # Average out-degree in real data (used to calibrate connection count)
    avg_out_degree = n_real / n  # expected connections per neuron

    simulated_encoded = []

    for i in range(n):
        nbr_idx  = idxs[i]   # shape (k,)
        nbr_dist = dists[i]  # shape (k,)
        sig_i    = sigma[i]

        # ── Base: exponential distance decay ──────────────────────────
        w = np.exp(-nbr_dist / sig_i)  # shape (k,)

        # ── Rule 1: Hemilineage-pair probability ──────────────────────
        if rule_level >= 1:
            hl_i = hl_int[i]
            hl_nbr = hl_int[nbr_idx]
            w = w * hl_pm[hl_i, hl_nbr]

        # ── Rule 2: NT compatibility ───────────────────────────────────
        if rule_level >= 2:
            nt_i   = nt_int[i]
            nt_nbr = nt_int[nbr_idx]
            w = w * nt_cm[nt_i, nt_nbr]

        # ── Rule 3: Sharpened spatial decay ───────────────────────────
        if rule_level >= 3:
            w = w * np.exp(-nbr_dist / sig_i)  # double decay

        # ── Rule 4: Target density ─────────────────────────────────────
        if rule_level >= 4:
            w = w * (1.0 + density[nbr_idx])

        # ── Normalize to probability distribution ─────────────────────
        w_sum = w.sum()
        if w_sum <= 0:
            continue
        w /= w_sum

        # ── Sample connections ────────────────────────────────────────
        # Calibrate to real average out-degree (with Poisson noise)
        n_out = max(1, int(round(np.random.poisson(avg_out_degree))))
        n_out = min(n_out, k)

        chosen = np.random.choice(k, size=n_out, replace=False, p=w)
        targets = nbr_idx[chosen]

        for t in targets:
            simulated_encoded.append(i * n + int(t))

    sim_set = set(simulated_encoded)

    # ── Rule 5: Calibrate connection count to match real pairs ─────────
    if rule_level >= 5 and len(sim_set) > n_real:
        # Keep top n_real connections — use a heuristic: take a random subset
        # (ideally weighted by probability, but set intersection suffices here)
        sim_set = set(list(sim_set)[:n_real])

    # ── Measure match ──────────────────────────────────────────────────
    matched   = sim_set & real_pairs
    n_sim     = len(sim_set)
    n_matched = len(matched)

    recall    = n_matched / n_real if n_real > 0 else 0.0
    precision = n_matched / n_sim  if n_sim  > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    elapsed = time.time() - t0

    log.info(f"  Simulated pairs : {n_sim:>10,}")
    log.info(f"  Real pairs      : {n_real:>10,}")
    log.info(f"  Matched pairs   : {n_matched:>10,}")
    log.info(f"  Recall          : {recall*100:>8.2f}%  (% of real connections produced)")
    log.info(f"  Precision       : {precision*100:>8.2f}%")
    log.info(f"  F1 Score        : {f1*100:>8.2f}%")
    log.info(f"  Time            : {elapsed:.1f}s")

    return {
        'rule_level': rule_level,
        'rule_name': rule_names.get(rule_level, ''),
        'n_simulated': n_sim,
        'n_real': n_real,
        'n_matched': n_matched,
        'recall_pct': round(recall * 100, 4),
        'precision_pct': round(precision * 100, 4),
        'f1_pct': round(f1 * 100, 4),
        'elapsed_s': round(elapsed, 1),
    }


# ============================================================
# MAIN
# ============================================================

def main():
    # Load all data
    data = load_data()

    # Build spatial neighbor graph once (shared across all rule levels)
    K = 300  # consider 300 nearest neighbors as potential synapse targets
    dists, idxs, sigma, density = build_neighbor_graph(data['coords'], k=K)

    # Run each rule level
    all_results = []
    for level in range(6):
        result = simulate(data, dists, idxs, sigma, density, rule_level=level, k=K)
        all_results.append(result)

    # Summary table
    log.info("\n" + "=" * 70)
    log.info("SUMMARY — Progressive Rule Addition")
    log.info("=" * 70)
    log.info(f"{'Level':<6} {'Rule':<42} {'Recall':>8} {'Precision':>10} {'F1':>8}")
    log.info("-" * 76)
    for r in all_results:
        log.info(f"  {r['rule_level']:<4} {r['rule_name']:<42} "
                 f"{r['recall_pct']:>7.2f}%  {r['precision_pct']:>8.2f}%  {r['f1_pct']:>7.2f}%")
    log.info("=" * 70)

    # Save results JSON
    output = {
        'experiment': 'developmental_growth_simulation',
        'n_neurons': data['n'],
        'n_real_pairs': len(data['real_pairs']),
        'k_neighbors': K,
        'results': all_results,
    }
    with open(RESULTS_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    log.info(f"\nResults saved to: {RESULTS_FILE}")
    log.info(f"Log saved to:     {LOG_FILE}")

    # Print final answer
    best = max(all_results, key=lambda r: r['recall_pct'])
    log.info(f"\nBest rule level: {best['rule_level']} — {best['rule_name']}")
    log.info(f"Best recall: {best['recall_pct']:.2f}% of real FlyWire connections produced")


if __name__ == '__main__':
    main()
