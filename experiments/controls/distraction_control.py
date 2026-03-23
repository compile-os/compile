#!/usr/bin/env python3
"""
DISTRACTION BASELINE CONTROL

Run the UNCOMPILED brain through the distraction protocol.
If uncompiled brain also shows nav bias → distraction resistance is Izhikevich dynamics, not the mutations.
If uncompiled brain shows no bias or escape bias → distraction resistance is genuinely from the 6 mutations.
"""
import sys, os, time
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd

print("=" * 60)
print("DISTRACTION BASELINE CONTROL")
print("=" * 60)

df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))
labels = np.load('/home/ubuntu/module_labels_v2.npy')

# Neuron types
a = np.full(num_neurons, 0.02, dtype=np.float32)
b = np.full(num_neurons, 0.2, dtype=np.float32)
c = np.full(num_neurons, -65.0, dtype=np.float32)
d = np.full(num_neurons, 8.0, dtype=np.float32)
for idx, nid in enumerate(neuron_ids):
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        a[idx], b[idx], c[idx], d[idx] = 0.02, 0.2, -55.0, 4.0
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        a[idx], b[idx], c[idx], d[idx] = 0.1, 0.2, -65.0, 2.0

a_t, b_t, c_t, d_t = torch.tensor(a), torch.tensor(b), torch.tensor(c), torch.tensor(d)

pre = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
GAIN = 8.0
DT, W_SCALE, PW, PR = 0.5, 0.275, 15.0, 150.0

DN = {
    'P9_left': 83620, 'P9_right': 119032, 'P9_oDN1_left': 78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431, 'DNa02_left': 904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1': 57246, 'GF_2': 108748, 'aDN1_left': 65709, 'aDN1_right': 26421,
    'MN9_left': 138332, 'MN9_right': 34268,
}
dn_names = sorted(DN.keys())
dn_idx = [DN[n] for n in dn_names]

SUGAR = [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
         129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842, 90589, 92298, 12494]
LC4 = [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
       45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424, 100901, 124935]

# WM mutations from the compiled brain
WM_MUTATIONS = [(1, 26, 3.19), (11, 4, 1.92), (20, 0, 3.25), (45, 19, 2.99), (17, 21, 0.94), (24, 37, 4.80)]

# Build edge index for applying mutations
pre_mods = labels[pre].astype(int)
post_mods = labels[post].astype(int)
edge_syn_idx = {}
for i in range(len(df_conn)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)

def run_distraction_protocol(syn_vals_local, label):
    """Run: 200 sugar, 200 silence, 100 distraction (lc4), 200 silence, 300 both"""
    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post, dtype=torch.long), torch.tensor(pre, dtype=torch.long)]),
        syn_vals_local, (num_neurons, num_neurons), dtype=torch.float32
    ).to_sparse_csr()

    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)
    rates = torch.zeros(1, num_neurons)

    phase_dn = {'P1_sugar': {n: 0 for n in dn_names},
                'P2_silence': {n: 0 for n in dn_names},
                'P3_distract': {n: 0 for n in dn_names},
                'P4_silence2': {n: 0 for n in dn_names},
                'P5_choice': {n: 0 for n in dn_names}}

    total_steps = 1000
    t0 = time.time()

    for step in range(total_steps):
        # Set stimulus by phase
        if step == 0:
            rates.zero_()
            for idx in SUGAR: rates[0, idx] = PR
            phase = 'P1_sugar'
        elif step == 200:
            rates.zero_()
            phase = 'P2_silence'
        elif step == 400:
            rates.zero_()
            for idx in LC4: rates[0, idx] = PR
            phase = 'P3_distract'
        elif step == 500:
            rates.zero_()
            phase = 'P4_silence2'
        elif step == 700:
            rates.zero_()
            for idx in SUGAR: rates[0, idx] = PR
            for idx in LC4: rates[0, idx] = PR
            phase = 'P5_choice'

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
        current_phase = 'P1_sugar' if step < 200 else 'P2_silence' if step < 400 else 'P3_distract' if step < 500 else 'P4_silence2' if step < 700 else 'P5_choice'
        for j, n in enumerate(dn_names):
            phase_dn[current_phase][n] += int(spk[dn_idx[j]].item())

    elapsed = time.time() - t0

    # Compute scores
    def nav_score(dn_dict):
        return sum(dn_dict.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
    def esc_score(dn_dict):
        return sum(dn_dict.get(n, 0) for n in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])

    p5_nav = nav_score(phase_dn['P5_choice'])
    p5_esc = esc_score(phase_dn['P5_choice'])
    bias = p5_nav / max(p5_esc, 1)

    print(f"\n  {label} ({elapsed:.1f}s):")
    print(f"    P1 (sugar):     nav={nav_score(phase_dn['P1_sugar']):>4} esc={esc_score(phase_dn['P1_sugar']):>4}")
    print(f"    P2 (silence):   nav={nav_score(phase_dn['P2_silence']):>4} esc={esc_score(phase_dn['P2_silence']):>4}")
    print(f"    P3 (distract):  nav={nav_score(phase_dn['P3_distract']):>4} esc={esc_score(phase_dn['P3_distract']):>4}")
    print(f"    P4 (silence2):  nav={nav_score(phase_dn['P4_silence2']):>4} esc={esc_score(phase_dn['P4_silence2']):>4}")
    print(f"    P5 (choice):    nav={p5_nav:>4} esc={p5_esc:>4} bias={bias:.1f}x")

    return p5_nav, p5_esc, bias

# Build weight matrices
print("Building circuits...")
syn_base = torch.tensor(vals * GAIN, dtype=torch.float32)

# Compiled brain (with 6 WM mutations)
syn_compiled = syn_base.clone()
for src, tgt, scale in WM_MUTATIONS:
    edge = (src, tgt)
    if edge in edge_syn_idx:
        syn_compiled[edge_syn_idx[edge]] *= scale

print(f"\n{'='*60}")
print("TEST 1: UNCOMPILED BRAIN (baseline, no mutations)")
print("="*60)
uncomp_nav, uncomp_esc, uncomp_bias = run_distraction_protocol(syn_base, "UNCOMPILED")

print(f"\n{'='*60}")
print("TEST 2: COMPILED BRAIN (6 WM mutations applied)")
print("="*60)
comp_nav, comp_esc, comp_bias = run_distraction_protocol(syn_compiled, "COMPILED")

print(f"\n{'='*60}")
print("VERDICT")
print("="*60)
print(f"  Uncompiled: nav={uncomp_nav}, esc={uncomp_esc}, bias={uncomp_bias:.1f}x")
print(f"  Compiled:   nav={comp_nav}, esc={comp_esc}, bias={comp_bias:.1f}x")

if uncomp_bias > 2.0:
    print(f"\n  >>> DISTRACTION RESISTANCE IS A PROPERTY OF IZHIKEVICH DYNAMICS.")
    print(f"  >>> The uncompiled brain ALSO shows {uncomp_bias:.1f}x nav bias.")
    print(f"  >>> The 6 mutations did NOT create distraction resistance.")
    print(f"  >>> REMOVE distraction resistance claim from docs.")
elif comp_bias > 2.0 and uncomp_bias < 1.5:
    print(f"\n  >>> DISTRACTION RESISTANCE IS GENUINE.")
    print(f"  >>> Uncompiled: {uncomp_bias:.1f}x (no bias). Compiled: {comp_bias:.1f}x (strong bias).")
    print(f"  >>> The 6 mutations CREATED distraction resistance.")
    print(f"  >>> KEEP the claim.")
else:
    print(f"\n  >>> AMBIGUOUS. Uncompiled: {uncomp_bias:.1f}x, Compiled: {comp_bias:.1f}x.")
    print(f"  >>> Both show some bias. The mutations AMPLIFIED but did not CREATE it.")
    print(f"  >>> SOFTEN the claim.")

print("\nDONE.")
