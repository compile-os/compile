#!/usr/bin/env python3
"""
EXPERIMENT 4: Composition Test

Take two copies of the minimum processor.
Configure one for navigation. Configure the other for escape.
Connect them through shared neurons. Does the combined system work?

Tests whether biological processors snap together like Lego.
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path

print("=" * 60)
print("COMPOSITION TEST: Two processors, one system")
print("=" * 60)

# Load connectome
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
labels = np.load('/home/ubuntu/module_labels_v2.npy')
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

DN = {
    'P9_left': 83620, 'P9_right': 119032,
    'P9_oDN1_left': 78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431,
    'DNa02_left': 904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1': 57246, 'GF_2': 108748,
    'aDN1_left': 65709, 'aDN1_right': 26421,
    'MN9_left': 138332, 'MN9_right': 34268,
}
dn_names = sorted(DN.keys())

STIM_SUGAR = [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
              129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842,
              90589, 92298, 12494]
STIM_LC4 = [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
            45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424,
            100901, 124935, 264, 9350, 13067, 13728, 13909, 14284, 14345, 15883,
            17935, 18045, 20770, 20810, 22455, 22751, 23130, 24281, 25985, 28213,
            29383, 30533, 33149, 34245, 34246, 34402, 34409, 34445, 34603, 36093,
            36239, 36310, 38907, 42880, 42886, 45196, 46146, 47583, 49698, 51100,
            54455, 55583, 57783, 64467, 68119, 68461, 73496, 73522, 73846, 73964,
            77031, 79150, 82937, 86033, 86146, 88184, 88693, 89165, 89200, 89699,
            90786, 95107, 96243, 97190, 98862, 101707, 101892, 103513, 108651,
            109680, 109955, 110942, 111699, 112907, 115387, 118928, 121451,
            124829, 127954, 129665, 130519, 134682, 136520, 137218]

DT, W_SCALE, GAIN = 0.5, 0.275, 8.0
POISSON_WEIGHT, POISSON_RATE = 15.0, 150.0

# Build the FULL processor (not 20%, use more neurons for composition)
_conflict_mods = set([40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41])
_dn_mods = set(int(labels[DN[n]]) for n in DN)
_stim_mods = set(int(labels[i]) for i in STIM_SUGAR + STIM_LC4)
ALL_MODS = sorted(_conflict_mods | _dn_mods | _stim_mods)

pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

# Use 30% fraction for better connectivity
rng = np.random.RandomState(42)
essential_set = set(DN.values()) | set(STIM_SUGAR) | set(STIM_LC4)
keep_neurons = []
for mod in ALL_MODS:
    neurons = np.where(labels == mod)[0]
    n_keep = max(1, int(len(neurons) * 0.3))
    mod_essential = [n for n in neurons if n in essential_set]
    non_essential = [n for n in neurons if n not in essential_set]
    rng.shuffle(non_essential)
    keep = sorted(set(mod_essential) | set(non_essential[:max(0, n_keep - len(mod_essential))]))
    keep_neurons.extend(keep)

keep_set = set(keep_neurons)
keep_neurons = sorted(keep_set)
n_sub = len(keep_neurons)
old_to_new = {old: new for new, old in enumerate(keep_neurons)}
print(f"Circuit: {n_sub} neurons")

mask = np.array([pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(df_conn))])
pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
vals_sub = vals_full[mask] * GAIN
print(f"Synapses: {len(pre_sub)}")

# Neuron types
a = np.full(n_sub, 0.02, dtype=np.float32)
b_arr = np.full(n_sub, 0.2, dtype=np.float32)
c_arr = np.full(n_sub, -65.0, dtype=np.float32)
d_arr = np.full(n_sub, 8.0, dtype=np.float32)
for new_idx, old_idx in enumerate(keep_neurons):
    nid = neuron_ids[old_idx]
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.02, 0.2, -55.0, 4.0
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.1, 0.2, -65.0, 2.0

a_t, b_t, c_t, d_t = torch.tensor(a), torch.tensor(b_arr), torch.tensor(c_arr), torch.tensor(d_arr)

dn_new = {name: old_to_new[idx] for name, idx in DN.items() if idx in old_to_new}
stim_sugar_new = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
stim_lc4_new = [old_to_new[i] for i in STIM_LC4 if i in old_to_new]

def run_sim(syn_vals, stim_indices, n_steps=500):
    """Run Izhikevich simulation."""
    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_sub, dtype=torch.long),
                    torch.tensor(pre_sub, dtype=torch.long)]),
        syn_vals, (n_sub, n_sub), dtype=torch.float32
    ).to_sparse_csr()

    v = torch.full((1, n_sub), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_sub)
    rates = torch.zeros(1, n_sub)
    for idx in stim_indices:
        rates[0, idx] = POISSON_RATE

    dn_total = {n: 0 for n in dn_names}
    dn_idx = [dn_new.get(n, -1) for n in dn_names]

    for step in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE
        v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new = u + DT * a_t * (b_t * v_new - u)
        fired = (v_new >= 30.0).float()
        v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new = torch.clamp(v_new, -100.0, 30.0)
        v, u, spikes = v_new, u_new, fired
        spk = spikes.squeeze(0)
        for j in range(len(dn_names)):
            if dn_idx[j] >= 0:
                dn_total[dn_names[j]] += int(spk[dn_idx[j]].item())

    return dn_total

def nav_score(dn):
    return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])

def esc_score(dn):
    return sum(dn.get(n, 0) for n in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])

syn_vals_base = torch.tensor(vals_sub, dtype=torch.float32)

# ============================================================
# Phase 1: Individual baselines
# ============================================================
print(f"\n{'='*60}")
print("PHASE 1: Individual baselines")
print("="*60)

t0 = time.time()
dn_nav = run_sim(syn_vals_base, stim_sugar_new)
nav_bl = nav_score(dn_nav)
esc_bl_sugar = esc_score(dn_nav)
print(f"Sugar stim: nav={nav_bl}, esc={esc_bl_sugar} ({time.time()-t0:.1f}s)")

dn_esc = run_sim(syn_vals_base, stim_lc4_new)
nav_bl_lc4 = nav_score(dn_esc)
esc_bl = esc_score(dn_esc)
print(f"LC4 stim:   nav={nav_bl_lc4}, esc={esc_bl}")

# ============================================================
# Phase 2: Evolve for navigation
# ============================================================
print(f"\n{'='*60}")
print("PHASE 2: Evolve for navigation (15 gen)")
print("="*60)

# Build edge index
sub_pre_mods = labels[np.array([pre_full[i] for i in range(len(df_conn)) if mask[i]])].astype(int)
sub_post_mods = labels[np.array([post_full[i] for i in range(len(df_conn)) if mask[i]])].astype(int)
edge_syn_idx = {}
for i in range(len(pre_sub)):
    edge = (int(sub_pre_mods[i]), int(sub_post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)
inter_edges = [e for e in edge_syn_idx if e[0] != e[1]]

np.random.seed(42)
best_nav = syn_vals_base.clone()
current_nav_fit = nav_bl
for gen in range(15):
    for mi in range(10):
        edge = inter_edges[np.random.randint(len(inter_edges))]
        syns = edge_syn_idx[edge]
        old = best_nav[syns].clone()
        scale = np.random.uniform(0.5, 4.0)
        test = best_nav.clone()
        test[syns] = old * scale
        dn = run_sim(test, stim_sugar_new)
        fit = nav_score(dn)
        if fit > current_nav_fit:
            current_nav_fit = fit
            best_nav[syns] = old * scale
            print(f"  G{gen}: nav={fit} ACCEPTED")

print(f"Nav evolved: {nav_bl} → {current_nav_fit}")

# ============================================================
# Phase 3: Evolve for escape
# ============================================================
print(f"\n{'='*60}")
print("PHASE 3: Evolve for escape (15 gen)")
print("="*60)

np.random.seed(123)
best_esc = syn_vals_base.clone()
current_esc_fit = esc_bl
for gen in range(15):
    for mi in range(10):
        edge = inter_edges[np.random.randint(len(inter_edges))]
        syns = edge_syn_idx[edge]
        old = best_esc[syns].clone()
        scale = np.random.uniform(0.5, 4.0)
        test = best_esc.clone()
        test[syns] = old * scale
        dn = run_sim(test, stim_lc4_new)
        fit = esc_score(dn)
        if fit > current_esc_fit:
            current_esc_fit = fit
            best_esc[syns] = old * scale
            print(f"  G{gen}: esc={fit} ACCEPTED")

print(f"Escape evolved: {esc_bl} → {current_esc_fit}")

# ============================================================
# Phase 4: Compose — merge both evolved weight sets
# ============================================================
print(f"\n{'='*60}")
print("PHASE 4: Composition — merge nav and escape weights")
print("="*60)

# Strategy: average the two evolved weight sets
composed = (best_nav + best_esc) / 2.0

# Test on both stimuli
dn_comp_sugar = run_sim(composed, stim_sugar_new)
dn_comp_lc4 = run_sim(composed, stim_lc4_new)

comp_nav = nav_score(dn_comp_sugar)
comp_esc = esc_score(dn_comp_lc4)

# Also test: nav weights on escape, escape weights on nav (interference)
dn_nav_on_esc = run_sim(best_nav, stim_lc4_new)
dn_esc_on_nav = run_sim(best_esc, stim_sugar_new)

print(f"\n  {'Config':>20} {'Nav':>8} {'Escape':>8}")
print(f"  {'-'*40}")
print(f"  {'Baseline':>20} {nav_bl:>8} {esc_bl:>8}")
print(f"  {'Nav-evolved':>20} {current_nav_fit:>8} {esc_score(dn_nav_on_esc):>8}")
print(f"  {'Esc-evolved':>20} {nav_score(dn_esc_on_nav):>8} {current_esc_fit:>8}")
print(f"  {'COMPOSED (avg)':>20} {comp_nav:>8} {comp_esc:>8}")

# Did composition preserve both?
nav_preserved = comp_nav >= nav_bl * 0.8
esc_preserved = comp_esc >= esc_bl * 0.8

if nav_preserved and esc_preserved:
    print(f"\n>>> COMPOSITION WORKS. Both behaviors preserved in merged circuit.")
elif nav_preserved or esc_preserved:
    print(f"\n>>> PARTIAL COMPOSITION. One behavior preserved, one degraded.")
else:
    print(f"\n>>> COMPOSITION FAILED. Merging destroys both behaviors.")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
with open(f'{outdir}/composition_test.json', 'w') as f:
    json.dump({
        'baseline_nav': nav_bl, 'baseline_esc': esc_bl,
        'evolved_nav': current_nav_fit, 'evolved_esc': current_esc_fit,
        'composed_nav': comp_nav, 'composed_esc': comp_esc,
        'nav_preserved': nav_preserved, 'esc_preserved': esc_preserved,
    }, f, indent=2)
print(f"\nSaved to {outdir}/composition_test.json")
print("DONE.")
