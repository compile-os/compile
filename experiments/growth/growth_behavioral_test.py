#!/usr/bin/env python3
"""
END-TO-END BEHAVIORAL TEST OF THE GROWTH PROGRAM

Generate a synthetic circuit from scratch using ONLY implementable developmental rules
(distance + NT compatibility + flow). No FlyWire connectivity used in construction.
Then test: does it produce behavior? Does evolution improve it faster than random?

Three outcomes:
1. Grown circuit produces behavior at baseline → growth program works alone
2. Grown circuit + evolution > random + evolution → useful scaffold
3. Grown circuit = random → implementable rules insufficient
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

print("=" * 60)
print("GROWTH PROGRAM BEHAVIORAL TEST")
print("Does the growth program produce functional circuits?")
print("=" * 60)

# Load annotations for developmental features
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
num_neurons_full = len(df_comp)

rid_to_hemi = dict(zip(ann['root_id'].astype(str), ann['ito_lee_hemilineage'].fillna('unknown')))
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('unknown')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('unknown')))
rid_to_flow = dict(zip(ann['root_id'].astype(str), ann['flow'].fillna('unknown')))
rid_to_sx = dict(zip(ann['root_id'].astype(str), ann['soma_x']))
rid_to_sy = dict(zip(ann['root_id'].astype(str), ann['soma_y']))
rid_to_sz = dict(zip(ann['root_id'].astype(str), ann['soma_z']))

DN = {
    'P9_left': 83620, 'P9_right': 119032, 'P9_oDN1_left': 78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431, 'DNa02_left': 904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1': 57246, 'GF_2': 108748, 'aDN1_left': 65709, 'aDN1_right': 26421,
    'MN9_left': 138332, 'MN9_right': 34268,
}
dn_names = sorted(DN.keys())

STIM = {
    'sugar': [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
              129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842, 90589, 92298, 12494],
    'lc4': [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
            45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424, 100901, 124935],
    'jo': [133917, 23290, 40779, 42646, 43215, 100833, 108537, 114244, 1828, 4290,
           6375, 24322, 43314, 51816, 54541, 59929, 74572, 82120, 96822, 107107],
}

SIGNATURE_HEMIS = {'VPNd2', 'VLPp2', 'DM3_CX_d2', 'LB23', 'LB12', 'VLPl2_medial',
                   'LB7', 'VLPl&p2_posterior', 'MD3', 'MX12', 'VLPl&p2_lateral',
                   'DM1_CX_d2', 'WEDd1', 'MX3', 'VPNd1', 'putative_primary',
                   'CREa2_medial', 'CREa1_dorsal', 'SLPal3_and_SLPal4_dorsal'}

# Select gene-guided neurons
essential_io = set(DN.values())
for s in STIM.values():
    essential_io.update(s)

gene_neurons = []
for idx, nid in enumerate(neuron_ids):
    if rid_to_hemi.get(nid, 'unknown') in SIGNATURE_HEMIS or idx in essential_io:
        gene_neurons.append(idx)
gene_neurons = sorted(set(gene_neurons))
n_sub = len(gene_neurons)
old_to_new = {old: new for new, old in enumerate(gene_neurons)}
print(f"Gene-guided neurons: {n_sub}")

# Get positions and features for each neuron
positions = np.zeros((n_sub, 3))
nt_types = []
flow_types = []
hemi_types = []

for i, idx in enumerate(gene_neurons):
    nid = neuron_ids[idx]
    try:
        sx = float(rid_to_sx.get(nid, 0) or 0)
        sy = float(rid_to_sy.get(nid, 0) or 0)
        sz = float(rid_to_sz.get(nid, 0) or 0)
        positions[i] = [sx, sy, sz]
    except (ValueError, TypeError):
        pass
    nt_types.append(str(rid_to_nt.get(nid, 'unknown')))
    flow_types.append(str(rid_to_flow.get(nid, 'unknown')))
    hemi_types.append(str(rid_to_hemi.get(nid, 'unknown')))

has_pos = np.sum(np.any(positions != 0, axis=1))
print(f"Neurons with position: {has_pos}/{n_sub}")

# ============================================================
# GROWTH RULES (implementable only — no common neighbors)
# ============================================================

# NT compatibility matrix (excitatory->excitatory preferred, etc)
NT_COMPAT = {
    ('acetylcholine', 'acetylcholine'): 1.0,
    ('acetylcholine', 'gaba'): 0.5,
    ('gaba', 'acetylcholine'): 0.8,
    ('gaba', 'gaba'): 0.3,
    ('glutamate', 'acetylcholine'): 0.7,
    ('glutamate', 'gaba'): 0.4,
    ('dopamine', 'acetylcholine'): 0.6,
    ('serotonin', 'acetylcholine'): 0.5,
}

# Flow compatibility (intrinsic->intrinsic, sensory->intrinsic, etc)
FLOW_COMPAT = {
    ('intrinsic', 'intrinsic'): 1.0,
    ('sensory', 'intrinsic'): 0.8,
    ('intrinsic', 'descending'): 0.7,
    ('sensory', 'descending'): 0.3,
    ('ascending', 'intrinsic'): 0.6,
}

def growth_connection_prob(i, j):
    """Probability of connection from neuron i to j using ONLY implementable rules."""
    # Distance (weight 0.25 from inst4)
    dist = np.linalg.norm(positions[i] - positions[j])
    if dist == 0:
        dist_score = 1.0
    else:
        dist_score = np.exp(-dist / 15000)  # decay scale tuned to fly brain

    # NT compatibility (weight 0.25)
    nt_score = NT_COMPAT.get((nt_types[i], nt_types[j]), 0.1)

    # Flow compatibility (weight 1.0)
    flow_score = FLOW_COMPAT.get((flow_types[i], flow_types[j]), 0.2)

    # Combined
    prob = 0.25 * dist_score + 0.25 * nt_score + 1.0 * flow_score
    return prob


def generate_circuit(n_neurons, connection_density, use_growth_rules=True, seed=42):
    """Generate a synthetic circuit using growth rules or random."""
    rng = np.random.RandomState(seed)
    n_target = int(n_neurons * n_neurons * connection_density)

    pre_list, post_list, val_list = [], [], []

    if use_growth_rules:
        # Score all potential connections, sample top ones
        print(f"  Computing growth probabilities for {n_neurons} neurons...")
        # For efficiency, sample candidate pairs and score them
        n_candidates = min(n_target * 20, n_neurons * 1000)
        candidates_i = rng.randint(0, n_neurons, n_candidates)
        candidates_j = rng.randint(0, n_neurons, n_candidates)

        scores = np.zeros(n_candidates)
        for k in range(n_candidates):
            if candidates_i[k] != candidates_j[k]:
                scores[k] = growth_connection_prob(candidates_i[k], candidates_j[k])

        # Take top n_target by score
        top_idx = np.argsort(scores)[-n_target:]
        for k in top_idx:
            if scores[k] > 0:
                pre_list.append(candidates_i[k])
                post_list.append(candidates_j[k])
                # Weight proportional to growth score
                val_list.append(float(scores[k]))
    else:
        # Random connections
        print(f"  Generating {n_target} random connections...")
        for _ in range(n_target):
            i = rng.randint(0, n_neurons)
            j = rng.randint(0, n_neurons)
            if i != j:
                pre_list.append(i)
                post_list.append(j)
                val_list.append(rng.uniform(0.1, 2.0))

    # Deduplicate
    seen = set()
    pre_f, post_f, val_f = [], [], []
    for p, q, v in zip(pre_list, post_list, val_list):
        if (p, q) not in seen:
            seen.add((p, q))
            pre_f.append(p)
            post_f.append(q)
            val_f.append(v)

    return np.array(pre_f), np.array(post_f), np.array(val_f)


# Simulation setup
DT, W_SCALE, GAIN = 0.5, 0.275, 8.0
POISSON_WEIGHT, POISSON_RATE = 15.0, 150.0

# Neuron types
a = np.full(n_sub, 0.02, dtype=np.float32); b_arr = np.full(n_sub, 0.2, dtype=np.float32)
c_arr = np.full(n_sub, -65.0, dtype=np.float32); d_arr = np.full(n_sub, 8.0, dtype=np.float32)
for new_idx, old_idx in enumerate(gene_neurons):
    nid = neuron_ids[old_idx]
    if isinstance(rid_to_class.get(nid, ''), str) and 'CX' in rid_to_class.get(nid, ''):
        a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.02, 0.2, -55.0, 4.0
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.1, 0.2, -65.0, 2.0
a_t, b_t, c_t, d_t = torch.tensor(a), torch.tensor(b_arr), torch.tensor(c_arr), torch.tensor(d_arr)

dn_new = {nm: old_to_new[idx] for nm, idx in DN.items() if idx in old_to_new}
stim_new = {name: [old_to_new[i] for i in idxs if i in old_to_new] for name, idxs in STIM.items()}


def run_sim(pre_arr, post_arr, val_arr, stim_indices, n_steps=500):
    """Run Izhikevich simulation on given circuit."""
    syn_vals = torch.tensor(val_arr * GAIN, dtype=torch.float32)
    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_arr, dtype=torch.long), torch.tensor(pre_arr, dtype=torch.long)]),
        syn_vals, (n_sub, n_sub), dtype=torch.float32).to_sparse_csr()
    v = torch.full((1, n_sub), -65.0); u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_sub); rates = torch.zeros(1, n_sub)
    for idx in stim_indices: rates[0, idx] = POISSON_RATE
    dn_total = {nm: 0 for nm in dn_names}
    dn_idx = [dn_new.get(nm, -1) for nm in dn_names]
    for step in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE
        v_n = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_n = v_n + 0.5 * DT * (0.04 * v_n * v_n + 5.0 * v_n + 140.0 - u + I)
        u_n = u + DT * a_t * (b_t * v_n - u)
        fired = (v_n >= 30.0).float()
        v_n = torch.where(fired > 0, c_t.unsqueeze(0), v_n)
        u_n = torch.where(fired > 0, u_n + d_t.unsqueeze(0), u_n)
        v_n = torch.clamp(v_n, -100.0, 30.0)
        v, u, spikes = v_n, u_n, fired
        spk = spikes.squeeze(0)
        for j in range(len(dn_names)):
            if dn_idx[j] >= 0: dn_total[dn_names[j]] += int(spk[dn_idx[j]].item())
    return dn_total


def f_nav(dn): return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
def f_esc(dn): return sum(dn.get(n, 0) for n in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])
def f_turn(dn):
    l = sum(dn.get(n, 0) for n in ['DNa01_left', 'DNa02_left'])
    r = sum(dn.get(n, 0) for n in ['DNa01_right', 'DNa02_right'])
    return abs(l - r) + (l + r) * 0.1
def f_arousal(dn): return sum(dn.values())
def f_circles(dn): return f_turn(dn) + f_nav(dn) * 0.1
def f_rhythm(dn): return f_arousal(dn) * 0.05

BEHAVIORS = {
    'navigation': ('sugar', f_nav),
    'escape': ('lc4', f_esc),
    'turning': ('jo', f_turn),
    'arousal': ('sugar', f_arousal),
    'circles': ('sugar', f_circles),
    'rhythm': ('sugar', f_rhythm),
}

# Also load the REAL FlyWire circuit for comparison
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
gene_set = set(gene_neurons)
mask = np.array([pre_full[i] in gene_set and post_full[i] in gene_set for i in range(len(df_conn))])
real_pre = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
real_post = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
real_vals = vals_full[mask]
real_density = len(real_pre) / (n_sub * n_sub)
print(f"Real circuit: {len(real_pre)} synapses (density={real_density:.6f})")

# ============================================================
# Generate circuits
# ============================================================
print(f"\n{'='*60}")
print("Generating circuits...")
print("="*60)

t0 = time.time()
grown_pre, grown_post, grown_vals = generate_circuit(n_sub, real_density, use_growth_rules=True, seed=42)
print(f"  Grown circuit: {len(grown_pre)} synapses ({time.time()-t0:.1f}s)")

t0 = time.time()
rand_pre, rand_post, rand_vals = generate_circuit(n_sub, real_density, use_growth_rules=False, seed=42)
print(f"  Random circuit: {len(rand_pre)} synapses ({time.time()-t0:.1f}s)")

# ============================================================
# Phase 1: Baseline behavioral test
# ============================================================
print(f"\n{'='*60}")
print("PHASE 1: Baseline behavior (no evolution)")
print("="*60)

circuits = {
    'real': (real_pre, real_post, real_vals),
    'grown': (grown_pre, grown_post, grown_vals),
    'random': (rand_pre, rand_post, rand_vals),
}

baselines = {}
for cname, (pre, post, vals) in circuits.items():
    baselines[cname] = {}
    print(f"\n  {cname} circuit:")
    for bname, (stim_name, fit_fn) in BEHAVIORS.items():
        stim_idx = stim_new.get(stim_name, [])
        dn = run_sim(pre, post, vals, stim_idx)
        score = fit_fn(dn)
        baselines[cname][bname] = score
    print(f"    nav={baselines[cname]['navigation']:.0f} esc={baselines[cname]['escape']:.0f} "
          f"turn={baselines[cname]['turning']:.0f} arousal={baselines[cname]['arousal']:.0f} "
          f"circles={baselines[cname]['circles']:.0f} rhythm={baselines[cname]['rhythm']:.1f}")

# ============================================================
# Phase 2: Evolution comparison (15 gen x 10 mut on each)
# ============================================================
print(f"\n{'='*60}")
print("PHASE 2: Evolution (navigation fitness, 15 gen x 10 mut)")
print("="*60)

def evolve_circuit(pre, post, vals, stim_idx, fit_fn, n_gen=15, n_mut=10, seed=42):
    """Run evolution on a circuit. Returns fitness trajectory."""
    rng = np.random.RandomState(seed)
    best_vals = vals.copy()
    dn = run_sim(pre, post, best_vals, stim_idx)
    current = fit_fn(dn)
    trajectory = [current]
    accepted = 0

    for gen in range(n_gen):
        for mi in range(n_mut):
            # Mutate a random subset of synapses
            n_mutate = max(1, len(vals) // 100)
            mut_idx = rng.choice(len(vals), n_mutate, replace=False)
            old = best_vals[mut_idx].copy()
            scale = rng.uniform(0.5, 4.0)
            test_vals = best_vals.copy()
            test_vals[mut_idx] = old * scale

            dn = run_sim(pre, post, test_vals, stim_idx)
            fit = fit_fn(dn)
            if fit > current:
                current = fit
                best_vals[mut_idx] = old * scale
                accepted += 1

        trajectory.append(current)

    return trajectory, accepted

for cname in ['grown', 'random', 'real']:
    pre, post, vals = circuits[cname]
    stim_idx = stim_new.get('sugar', [])
    t0 = time.time()
    traj, acc = evolve_circuit(pre, post, vals, stim_idx, f_nav)
    elapsed = time.time() - t0
    print(f"  {cname:>8}: {traj[0]:.0f} → {traj[-1]:.0f} "
          f"({acc} accepted, {elapsed:.0f}s) "
          f"trajectory: {[f'{t:.0f}' for t in traj]}")

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*60}")
print("SUMMARY")
print("="*60)

print(f"\n{'Circuit':>8} {'Nav':>6} {'Esc':>6} {'Turn':>6} {'Arou':>6} {'Circ':>6} {'Rhyt':>6}")
print("-" * 50)
for cname in ['real', 'grown', 'random']:
    bl = baselines[cname]
    print(f"{cname:>8}", end="")
    for b in ['navigation', 'escape', 'turning', 'arousal', 'circles', 'rhythm']:
        print(f" {bl[b]:>6.0f}", end="")
    print()

grown_active = sum(1 for b in baselines['grown'].values() if b > 0)
random_active = sum(1 for b in baselines['random'].values() if b > 0)
real_active = sum(1 for b in baselines['real'].values() if b > 0)

print(f"\nActive behaviors: real={real_active}/6, grown={grown_active}/6, random={random_active}/6")

if grown_active > random_active:
    print(f"\n>>> GROWTH PROGRAM PRODUCES MORE BEHAVIOR THAN RANDOM")
elif grown_active == random_active and any(baselines['grown'][b] > baselines['random'][b] * 1.1 for b in BEHAVIORS):
    print(f"\n>>> GROWTH PROGRAM PRODUCES STRONGER BEHAVIOR THAN RANDOM")
else:
    print(f"\n>>> GROWTH PROGRAM NOT BETTER THAN RANDOM AT BASELINE")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
with open(f'{outdir}/growth_behavioral_test.json', 'w') as f:
    json.dump({
        'baselines': baselines,
        'grown_active': grown_active, 'random_active': random_active, 'real_active': real_active,
        'n_neurons': n_sub,
        'grown_synapses': len(grown_pre), 'random_synapses': len(rand_pre), 'real_synapses': len(real_pre),
    }, f, indent=2)
print(f"\nSaved to {outdir}/growth_behavioral_test.json")
print("DONE.")
