#!/usr/bin/env python3
"""
CRITICAL CONTROLS — Must pass before publishing.

Control 1: Random neuron selection baseline for gene-guided extraction.
Does a RANDOM selection of 8,158 neurons perform similarly to gene-guided?
If yes: "cell type specification is sufficient" is FALSE.

Control 2: Edge sweep at different perturbation scales.
Do the same edges classify as evolvable at 1.5x and 3x as they do at 2x?
If no: classification depends on arbitrary scale choice.
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

print("=" * 60)
print("CRITICAL CONTROLS")
print("=" * 60)

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

SIGNATURE_HEMIS = {'VPNd2', 'VLPp2', 'DM3_CX_d2', 'LB23', 'LB12', 'VLPl2_medial',
                   'LB7', 'VLPl&p2_posterior', 'MD3', 'MX12', 'VLPl&p2_lateral',
                   'DM1_CX_d2', 'WEDd1', 'MX3', 'VPNd1', 'putative_primary',
                   'CREa2_medial', 'CREa1_dorsal', 'SLPal3_and_SLPal4_dorsal'}

pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

essential_io = set(DN.values()) | set(STIM_SUGAR)
DT, W_SCALE, GAIN, PW, PR = 0.5, 0.275, 8.0, 15.0, 150.0

def build_circuit(neuron_list):
    """Build Izhikevich circuit from neuron list. Return nav score."""
    keep = sorted(set(neuron_list))
    keep_set = set(keep)
    n = len(keep)
    old_to_new = {old: new for new, old in enumerate(keep)}

    mask = np.array([pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(df_conn))])
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
    vals_sub = vals_full[mask] * GAIN
    n_syn = len(pre_sub)

    if n_syn == 0:
        return 0, n, n_syn

    a = np.full(n, 0.02, dtype=np.float32); b = np.full(n, 0.2, dtype=np.float32)
    c = np.full(n, -65.0, dtype=np.float32); d = np.full(n, 8.0, dtype=np.float32)
    for new_idx, old_idx in enumerate(keep):
        nid = neuron_ids[old_idx]
        cc = rid_to_class.get(nid, '')
        if isinstance(cc, str) and 'CX' in cc:
            a[new_idx], b[new_idx], c[new_idx], d[new_idx] = 0.02, 0.2, -55.0, 4.0
        elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
            a[new_idx], b[new_idx], c[new_idx], d[new_idx] = 0.1, 0.2, -65.0, 2.0

    a_t, b_t, c_t, d_t = torch.tensor(a), torch.tensor(b), torch.tensor(c), torch.tensor(d)
    dn_new = {nm: old_to_new[idx] for nm, idx in DN.items() if idx in old_to_new}
    stim_new = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]

    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_sub, dtype=torch.long), torch.tensor(pre_sub, dtype=torch.long)]),
        torch.tensor(vals_sub, dtype=torch.float32), (n, n)).to_sparse_csr()

    v = torch.full((1, n), -65.0); u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n); rates = torch.zeros(1, n)
    for idx in stim_new: rates[0, idx] = PR

    dn_total = {nm: 0 for nm in dn_names}
    dn_idx = [dn_new.get(nm, -1) for nm in dn_names]
    for step in range(500):
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

    nav = sum(dn_total.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
    return nav, n, n_syn

# ============================================================
# CONTROL 1: Gene-guided vs random selection
# ============================================================
print(f"\n{'='*60}")
print("CONTROL 1: Gene-guided vs Random neuron selection")
print("="*60)

# Gene-guided selection
gene_neurons = []
for idx, nid in enumerate(neuron_ids):
    if rid_to_hemi.get(nid, 'unknown') in SIGNATURE_HEMIS or idx in essential_io:
        gene_neurons.append(idx)
gene_neurons = sorted(set(gene_neurons))
n_gene = len(gene_neurons)

t0 = time.time()
gene_nav, gene_n, gene_syn = build_circuit(gene_neurons)
print(f"  Gene-guided: {gene_n} neurons, {gene_syn} synapses, nav={gene_nav} ({time.time()-t0:.1f}s)")

# Random selections (5 trials, same size as gene-guided)
random_navs = []
for trial in range(5):
    rng = np.random.RandomState(trial)
    # Must include essential I/O neurons
    non_essential = [i for i in range(num_neurons) if i not in essential_io]
    random_pick = list(essential_io) + rng.choice(non_essential, n_gene - len(essential_io), replace=False).tolist()
    t0 = time.time()
    rand_nav, rand_n, rand_syn = build_circuit(random_pick)
    random_navs.append(rand_nav)
    print(f"  Random {trial}: {rand_n} neurons, {rand_syn} synapses, nav={rand_nav} ({time.time()-t0:.1f}s)")

mean_random = np.mean(random_navs)
std_random = np.std(random_navs)

print(f"\n  Gene-guided nav:  {gene_nav}")
print(f"  Random mean nav:  {mean_random:.1f} +/- {std_random:.1f}")
print(f"  Random range:     {min(random_navs)} - {max(random_navs)}")

if gene_nav > mean_random + 2 * std_random:
    print(f"  >>> GENE-GUIDED IS SIGNIFICANTLY BETTER. Cell type selection matters.")
elif gene_nav > mean_random:
    print(f"  >>> Gene-guided is better but NOT significantly (within 2 std).")
    print(f"  >>> The claim 'cell type specification is sufficient' should be softened.")
else:
    print(f"  >>> GENE-GUIDED IS NOT BETTER THAN RANDOM. Cell type claim is FALSE.")

# ============================================================
# CONTROL 2: Edge sweep at multiple perturbation scales
# ============================================================
print(f"\n{'='*60}")
print("CONTROL 2: Edge sweep scale sensitivity")
print("="*60)

# Use the full brain for this (not gene-guided)
from brain_body_bridge import BrainEngine
brain = BrainEngine(device='cpu')
brain._syn_vals.mul_(GAIN)
baseline_weights = brain._syn_vals.clone()

pre_mods = labels[df_conn['Presynaptic_Index'].values].astype(int)
post_mods = labels[df_conn['Postsynaptic_Index'].values].astype(int)
edge_syn_idx = {}
for i in range(len(df_conn)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)
inter_edges = sorted([e for e in edge_syn_idx if e[0] != e[1]])

def evaluate_nav(brain_eng, stim='sugar', n_steps=300):
    brain_eng.state = brain_eng.model.state_init()
    brain_eng.rates = torch.zeros(1, brain_eng.num_neurons, device=brain_eng.device)
    brain_eng._spike_acc.zero_()
    brain_eng._hebb_count = 0
    brain_eng.set_stimulus(stim)
    dn_spikes = {name: 0 for name in brain_eng.dn_indices}
    for step in range(n_steps):
        brain_eng.step()
        spk = brain_eng.state[2].squeeze(0)
        for name, idx in brain_eng.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
    return sum(dn_spikes.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])

# Measure baseline
brain._syn_vals.copy_(baseline_weights)
baseline = evaluate_nav(brain)
print(f"  Baseline nav: {baseline}")

# Test 50 random edges at scales 1.5x, 2x, 3x, 5x
scales = [1.5, 2.0, 3.0, 5.0]
rng = np.random.RandomState(42)
test_edges = [inter_edges[i] for i in rng.choice(len(inter_edges), 50, replace=False)]

classifications = {s: [] for s in scales}
for edge in test_edges:
    syns = edge_syn_idx[edge]
    for scale in scales:
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= scale
        fit = evaluate_nav(brain)
        delta = fit - baseline
        if delta > 0:
            cls = 'evolvable'
        elif delta < 0:
            cls = 'frozen'
        else:
            cls = 'irrelevant'
        classifications[scale].append(cls)

print(f"\n  Classification consistency across scales (50 edges):")
print(f"  {'Scale':>6} {'Frozen':>8} {'Evolvable':>10} {'Irrelevant':>11}")
for s in scales:
    counts = Counter(classifications[s])
    print(f"  {s:>5.1f}x {counts.get('frozen',0):>8} {counts.get('evolvable',0):>10} {counts.get('irrelevant',0):>11}")

# Agreement between 2x and other scales
for s in scales:
    if s == 2.0:
        continue
    agree = sum(1 for a, b in zip(classifications[2.0], classifications[s]) if a == b)
    print(f"  Agreement 2x vs {s}x: {agree}/50 ({100*agree/50:.0f}%)")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'control1_gene_nav': gene_nav,
    'control1_random_navs': random_navs,
    'control1_random_mean': float(mean_random),
    'control1_random_std': float(std_random),
    'control1_gene_significantly_better': bool(gene_nav > mean_random + 2 * std_random),
    'control2_classifications': {str(s): classifications[s] for s in scales},
}
with open(f'{outdir}/critical_controls.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f"\nSaved to {outdir}/critical_controls.json")
print("DONE.")
