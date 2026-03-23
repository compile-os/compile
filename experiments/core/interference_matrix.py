#!/usr/bin/env python3
"""
INTERFERENCE MATRIX: The processor's spec sheet.

5 compiled brains × 5 fitness functions = 25 evaluations.
Each cell: compiling behavior X changed behavior Y by how much?

Diagonal = direct improvement (expected).
Off-diagonal positive = synergy (compiling X helps Y).
Off-diagonal negative = interference (compiling X breaks Y).
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
print("INTERFERENCE MATRIX")
print("The processor's spec sheet")
print("=" * 60)

# Load connectome
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_hemi = dict(zip(ann['root_id'].astype(str), ann['ito_lee_hemilineage'].fillna('unknown')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('unknown')))
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('unknown')))

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

# Build gene-guided circuit
essential_io = set(DN.values())
for s in STIM.values():
    essential_io.update(s)

gene_neurons = []
for idx, nid in enumerate(neuron_ids):
    if rid_to_hemi.get(nid, 'unknown') in SIGNATURE_HEMIS or idx in essential_io:
        gene_neurons.append(idx)
gene_set = set(gene_neurons)
gene_neurons = sorted(gene_set)
n_sub = len(gene_neurons)
old_to_new = {old: new for new, old in enumerate(gene_neurons)}
print(f"Gene-guided circuit: {n_sub} neurons")

pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
mask = np.array([pre_full[i] in gene_set and post_full[i] in gene_set for i in range(len(df_conn))])
pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
vals_sub = vals_full[mask] * 8.0
n_syn = len(pre_sub)

# Build hemilineage-pair edge index for evolution
hemi_of = {}
for idx in gene_neurons:
    hemi_of[old_to_new[idx]] = rid_to_hemi.get(neuron_ids[idx], 'unknown')
edge_syn_idx = defaultdict(list)
for i in range(n_syn):
    edge = (hemi_of.get(pre_sub[i], '?'), hemi_of.get(post_sub[i], '?'))
    edge_syn_idx[edge].append(i)
inter_edges = [(k, v) for k, v in edge_syn_idx.items() if k[0] != k[1]]

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

DT, W_SCALE, PW, PR = 0.5, 0.275, 15.0, 150.0

def run_sim(syn_vals_local, stim_indices, n_steps=500):
    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_sub, dtype=torch.long), torch.tensor(pre_sub, dtype=torch.long)]),
        syn_vals_local, (n_sub, n_sub), dtype=torch.float32).to_sparse_csr()
    v = torch.full((1, n_sub), -65.0); u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_sub); rates = torch.zeros(1, n_sub)
    for idx in stim_indices: rates[0, idx] = PR
    dn_total = {nm: 0 for nm in dn_names}
    dn_idx = [dn_new.get(nm, -1) for nm in dn_names]
    for step in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * PW + torch.mm(spikes, W.t()) * W_SCALE
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

# Fitness functions
def f_nav(dn): return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
def f_esc(dn): return sum(dn.get(n, 0) for n in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])
def f_turn(dn):
    l = sum(dn.get(n, 0) for n in ['DNa01_left', 'DNa02_left'])
    r = sum(dn.get(n, 0) for n in ['DNa01_right', 'DNa02_right'])
    return abs(l - r) + (l + r) * 0.1
def f_arousal(dn): return sum(dn.values())
def f_circles(dn): return f_turn(dn) + f_nav(dn) * 0.1

BEHAVIORS = {
    'navigation': ('sugar', f_nav),
    'escape': ('lc4', f_esc),
    'turning': ('jo', f_turn),
    'arousal': ('sugar', f_arousal),
    'circles': ('sugar', f_circles),
}

# ============================================================
# Phase 1: Compile each behavior independently
# ============================================================
print(f"\n{'='*60}")
print("PHASE 1: Compile each behavior (15 gen x 10 mut)")
print("="*60)

syn_base = torch.tensor(vals_sub, dtype=torch.float32)
compiled_weights = {}  # behavior -> evolved weights

for bname, (stim_name, fit_fn) in BEHAVIORS.items():
    np.random.seed(42); torch.manual_seed(42)
    best = syn_base.clone()
    stim_idx = stim_new.get(stim_name, [])
    dn = run_sim(best, stim_idx)
    current = fit_fn(dn)

    for gen in range(15):
        for mi in range(10):
            edge_key, syns = inter_edges[np.random.randint(len(inter_edges))]
            old = best[syns].clone()
            scale = np.random.uniform(0.5, 4.0)
            test = best.clone(); test[syns] = old * scale
            dn = run_sim(test, stim_idx)
            fit = fit_fn(dn)
            if fit > current:
                current = fit; best[syns] = old * scale

    compiled_weights[bname] = best
    print(f"  {bname:>12}: compiled fitness = {current:.0f}")

# ============================================================
# Phase 2: Cross-evaluate — the interference matrix
# ============================================================
print(f"\n{'='*60}")
print("PHASE 2: Interference Matrix (5x5)")
print("="*60)

# Baselines
baselines = {}
for bname, (stim_name, fit_fn) in BEHAVIORS.items():
    stim_idx = stim_new.get(stim_name, [])
    dn = run_sim(syn_base, stim_idx)
    baselines[bname] = fit_fn(dn)

# Matrix
matrix = {}  # (compiled_for, tested_on) -> score
bnames = list(BEHAVIORS.keys())

print(f"\n{'Compiled →':>14}", end="")
for b in bnames:
    print(f" {b[:6]:>8}", end="")
print(f" {'baseline':>8}")

for compiled_for in bnames:
    weights = compiled_weights[compiled_for]
    print(f"\n{'Test ↓ ' + compiled_for[:6]:>14}", end="")
    for tested_on in bnames:
        stim_name, fit_fn = BEHAVIORS[tested_on]
        stim_idx = stim_new.get(stim_name, [])
        dn = run_sim(weights, stim_idx)
        score = fit_fn(dn)
        bl = baselines[tested_on]
        delta_pct = (score - bl) / max(abs(bl), 1) * 100
        matrix[(compiled_for, tested_on)] = {'score': score, 'baseline': bl, 'delta_pct': delta_pct}

        # Color code: positive = synergy, negative = interference
        marker = '+' if delta_pct > 5 else '-' if delta_pct < -5 else '='
        print(f" {delta_pct:>+7.0f}%", end="")
    print(f" {baselines[compiled_for]:>8.0f}")

# ============================================================
# Analysis
# ============================================================
print(f"\n{'='*60}")
print("ANALYSIS")
print("="*60)

# Diagonal (direct improvement)
print(f"\nDirect improvements (diagonal):")
for b in bnames:
    d = matrix[(b, b)]['delta_pct']
    print(f"  {b:>12}: {d:>+.0f}%")

# Synergies (off-diagonal positive > 10%)
print(f"\nSynergies (off-diagonal > +10%):")
for cf in bnames:
    for to in bnames:
        if cf != to:
            d = matrix[(cf, to)]['delta_pct']
            if d > 10:
                print(f"  Compiling {cf} → {to}: {d:>+.0f}%")

# Interference (off-diagonal negative < -10%)
print(f"\nInterference (off-diagonal < -10%):")
for cf in bnames:
    for to in bnames:
        if cf != to:
            d = matrix[(cf, to)]['delta_pct']
            if d < -10:
                print(f"  Compiling {cf} → {to}: {d:>+.0f}%")

# Compatible pairs
print(f"\nCompatibility matrix (can be co-compiled):")
for i, b1 in enumerate(bnames):
    for j, b2 in enumerate(bnames):
        if i < j:
            d12 = matrix[(b1, b2)]['delta_pct']
            d21 = matrix[(b2, b1)]['delta_pct']
            compatible = d12 > -10 and d21 > -10
            status = "COMPATIBLE" if compatible else "CONFLICT"
            print(f"  {b1:>12} + {b2:<12}: {status} (cross-effects: {d12:>+.0f}%, {d21:>+.0f}%)")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'baselines': baselines,
    'matrix': {f"{cf}->{to}": v for (cf, to), v in matrix.items()},
    'behaviors': bnames,
}
with open(f'{outdir}/interference_matrix.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f"\nSaved to {outdir}/interference_matrix.json")
print("DONE.")
