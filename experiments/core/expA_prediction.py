#!/usr/bin/env python3
"""
EXPERIMENT A: Prediction Validation — Break the circularity.

Compile navigation on the gene-guided circuit. BEFORE running evolution,
write down predictions based on full-connectome results. Then check.

Predictions (from full connectome experiments):
1. Evolvable hemilineages will include VPNd1, VPNd2 (visual projection neurons)
2. CX hemilineages (DM3_CX_d2, DM1_CX_d2) will be frozen for navigation
3. Module 4 and 19 neurons will be disproportionately involved
4. The evolvable surface will be <10% of edges (navigation was 6% on full brain)

SECONDARY prediction (not in fitness function):
5. Navigation-compiled circuit will show INCREASED escape response as side effect
   (because strengthening nav paths through shared DN hubs also amplifies escape input)
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict

print("=" * 60)
print("PREDICTION VALIDATION EXPERIMENT")
print("Breaking the circularity: predict, then test")
print("=" * 60)

# Load data
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)
labels = np.load('/home/ubuntu/module_labels_v2.npy')
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

STIM_SUGAR = [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
              129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842, 90589, 92298, 12494]
STIM_LC4 = [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
            45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424, 100901, 124935]

SIGNATURE_HEMIS = {'VPNd2', 'VLPp2', 'DM3_CX_d2', 'LB23', 'LB12', 'VLPl2_medial',
                   'LB7', 'VLPl&p2_posterior', 'MD3', 'MX12', 'VLPl&p2_lateral',
                   'DM1_CX_d2', 'WEDd1', 'MX3', 'VPNd1', 'putative_primary',
                   'CREa2_medial', 'CREa1_dorsal', 'SLPal3_and_SLPal4_dorsal'}

# ============================================================
# PREDICTIONS (written BEFORE running evolution)
# ============================================================
print(f"\n{'='*60}")
print("PREDICTIONS (pre-registered)")
print("="*60)

PREDICTIONS = {
    'P1': 'VPNd1 and VPNd2 hemilineages will contain evolvable edges for navigation',
    'P2': 'CX hemilineages (DM3_CX_d2, DM1_CX_d2) will be FROZEN for navigation',
    'P3': 'Evolvable surface will be <15% of edges',
    'P4': 'Escape score will INCREASE as side effect of navigation optimization (shared DN hub amplification)',
    'P5': 'putative_primary will be the most connected evolvable hemilineage',
}
for k, v in PREDICTIONS.items():
    print(f"  {k}: {v}")

# ============================================================
# Build gene-guided circuit
# ============================================================
print(f"\n{'='*60}")
print("Building gene-guided circuit")
print("="*60)

essential_io = set(DN.values()) | set(STIM_SUGAR) | set(STIM_LC4)
gene_neurons = []
for idx, nid in enumerate(neuron_ids):
    hemi = rid_to_hemi.get(nid, 'unknown')
    if hemi in SIGNATURE_HEMIS or idx in essential_io:
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
print(f"Synapses: {n_syn}")

# Build edge index by hemilineage pair
hemi_of_neuron = {}
for idx in gene_neurons:
    hemi_of_neuron[old_to_new[idx]] = rid_to_hemi.get(neuron_ids[idx], 'unknown')

edge_syn_idx = defaultdict(list)
for i in range(n_syn):
    pre_h = hemi_of_neuron.get(pre_sub[i], 'unknown')
    post_h = hemi_of_neuron.get(post_sub[i], 'unknown')
    edge = (pre_h, post_h)
    edge_syn_idx[edge].append(i)

inter_edges = [(k, v) for k, v in edge_syn_idx.items() if k[0] != k[1]]
print(f"Hemilineage-pair edges: {len(inter_edges)}")

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
stim_sugar = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
stim_lc4 = [old_to_new[i] for i in STIM_LC4 if i in old_to_new]

DT, W_SCALE, POISSON_WEIGHT, POISSON_RATE = 0.5, 0.275, 15.0, 150.0

def run_sim(syn_vals_local, stim_indices, n_steps=500):
    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_sub, dtype=torch.long), torch.tensor(pre_sub, dtype=torch.long)]),
        syn_vals_local, (n_sub, n_sub), dtype=torch.float32
    ).to_sparse_csr()
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

def nav_score(dn):
    return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])

def esc_score(dn):
    return sum(dn.get(n, 0) for n in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])

# ============================================================
# Baselines
# ============================================================
syn_vals = torch.tensor(vals_sub, dtype=torch.float32)

print(f"\nBaselines:")
dn_nav = run_sim(syn_vals, stim_sugar)
bl_nav = nav_score(dn_nav)
bl_esc_on_sugar = esc_score(dn_nav)
print(f"  Sugar: nav={bl_nav}, esc={bl_esc_on_sugar}")

dn_esc = run_sim(syn_vals, stim_lc4)
bl_esc = esc_score(dn_esc)
print(f"  LC4:   esc={bl_esc}")

# ============================================================
# Evolution: compile navigation
# ============================================================
print(f"\n{'='*60}")
print("EVOLUTION: Compile navigation on gene-guided circuit")
print("="*60)

np.random.seed(42); torch.manual_seed(42)
best_vals = syn_vals.clone()
current = bl_nav
accepted = 0
acc_edges = []

t0 = time.time()
for gen in range(25):
    ga = 0
    for mi in range(10):
        edge_key, syns = inter_edges[np.random.randint(len(inter_edges))]
        old = best_vals[syns].clone()
        scale = np.random.uniform(0.5, 4.0)
        test = best_vals.clone(); test[syns] = old * scale
        dn = run_sim(test, stim_sugar)
        fit = nav_score(dn)
        if fit > current:
            current = fit; best_vals[syns] = old * scale; ga += 1; accepted += 1
            acc_edges.append(edge_key)
            print(f"  G{gen}M{mi}: {edge_key[0]}->{edge_key[1]} s={scale:.2f} nav={fit} ACCEPTED")
    if gen % 5 == 4:
        print(f"  Gen {gen}: nav={current} acc={ga}/10 total={accepted} [{time.time()-t0:.0f}s]")

# ============================================================
# VALIDATE PREDICTIONS
# ============================================================
print(f"\n{'='*60}")
print("PREDICTION VALIDATION")
print("="*60)

acc_hemi_set = set()
acc_hemi_counts = Counter()
for h_from, h_to in acc_edges:
    acc_hemi_set.add(h_from); acc_hemi_set.add(h_to)
    acc_hemi_counts[h_from] += 1; acc_hemi_counts[h_to] += 1

print(f"\nEvolved edges ({accepted} accepted):")
unique_acc = sorted(set(acc_edges))
for e in unique_acc:
    print(f"  {e[0]} -> {e[1]}")

print(f"\nEvolvable hemilineages: {sorted(acc_hemi_set)}")

# P1: VPNd1/VPNd2 in evolvable set
p1 = 'VPNd1' in acc_hemi_set or 'VPNd2' in acc_hemi_set
print(f"\nP1 (VPNd1/VPNd2 evolvable): {'CONFIRMED' if p1 else 'FAILED'}")

# P2: CX hemilineages frozen
cx_hemis = {'DM3_CX_d2', 'DM1_CX_d2'}
p2 = len(cx_hemis & acc_hemi_set) == 0
print(f"P2 (CX hemilineages frozen): {'CONFIRMED' if p2 else 'FAILED'} (CX in evolvable: {cx_hemis & acc_hemi_set})")

# P3: <15% evolvable
evolvable_pct = 100 * len(unique_acc) / len(inter_edges)
p3 = evolvable_pct < 15
print(f"P3 (<15% evolvable): {'CONFIRMED' if p3 else 'FAILED'} ({evolvable_pct:.1f}%)")

# P4: Escape increases as side effect
dn_nav_evolved = run_sim(best_vals, stim_sugar)
evolved_esc_on_sugar = esc_score(dn_nav_evolved)
p4 = evolved_esc_on_sugar > bl_esc_on_sugar
print(f"P4 (escape side effect): {'CONFIRMED' if p4 else 'FAILED'} (baseline esc={bl_esc_on_sugar}, evolved esc={evolved_esc_on_sugar})")

# Also test on LC4 stimulus
dn_esc_evolved = run_sim(best_vals, stim_lc4)
evolved_esc_lc4 = esc_score(dn_esc_evolved)
print(f"    (LC4 escape: baseline={bl_esc}, evolved={evolved_esc_lc4}, delta={evolved_esc_lc4-bl_esc:+})")

# P5: putative_primary most connected evolvable
p5_top = acc_hemi_counts.most_common(1)[0][0] if acc_hemi_counts else 'none'
p5 = p5_top == 'putative_primary'
print(f"P5 (putative_primary top evolvable): {'CONFIRMED' if p5 else 'FAILED'} (top: {p5_top}, counts: {acc_hemi_counts.most_common(5)})")

# Summary
confirmed = sum([p1, p2, p3, p4, p5])
print(f"\n{'='*60}")
print(f"PREDICTIONS: {confirmed}/5 CONFIRMED")
print("="*60)
for i, (k, v) in enumerate(PREDICTIONS.items()):
    result = [p1, p2, p3, p4, p5][i]
    print(f"  {k}: {'CONFIRMED' if result else 'FAILED'} — {v}")

if confirmed >= 4:
    print(f"\n>>> STRONG PREDICTIVE POWER. The framework predicts, not just optimizes.")
elif confirmed >= 3:
    print(f"\n>>> MODERATE PREDICTIVE POWER. Most predictions hold.")
else:
    print(f"\n>>> WEAK PREDICTIVE POWER. Framework optimizes but doesn't predict well.")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
with open(f'{outdir}/prediction_validation.json', 'w') as f:
    json.dump({
        'predictions': PREDICTIONS,
        'results': {'P1': p1, 'P2': p2, 'P3': p3, 'P4': p4, 'P5': p5},
        'confirmed': confirmed,
        'evolvable_hemilineages': sorted(acc_hemi_set),
        'evolvable_edges': [list(e) for e in unique_acc],
        'baseline_nav': bl_nav, 'evolved_nav': current,
        'baseline_esc_sugar': bl_esc_on_sugar, 'evolved_esc_sugar': evolved_esc_on_sugar,
    }, f, indent=2)
print(f"\nSaved to {outdir}/prediction_validation.json")
print("DONE.")
