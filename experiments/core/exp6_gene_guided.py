#!/usr/bin/env python3
"""
EXPERIMENT 6: Gene-Guided Circuit Extraction

Instead of extracting the processor by module ID, extract by DEVELOPMENTAL SIGNATURE.
Take the transcription factor / hemilineage profile of essential modules 4 and 19.
Select ALL neurons in the full connectome matching that profile.
Build a subcircuit. Compile 6 behaviors on it.

If it works: you specified a biological processor in purely genetic terms.
"Grow these cell types in these proportions" = the growth program.
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
print("GENE-GUIDED CIRCUIT EXTRACTION")
print("=" * 60)

# Load data
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons_full = len(df_comp)
labels = np.load('/home/ubuntu/module_labels_v2.npy')
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()

# Build annotation mappings
rid_to_hemi = dict(zip(ann['root_id'].astype(str), ann['ito_lee_hemilineage'].fillna('unknown')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('unknown')))
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('unknown')))
rid_to_super = dict(zip(ann['root_id'].astype(str), ann['super_class'].fillna('unknown')))

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
            100901, 124935]
STIM_JO = [133917, 23290, 40779, 42646, 43215, 100833, 108537, 114244, 1828, 4290,
           6375, 24322, 43314, 51816, 54541, 59929, 74572, 82120, 96822, 107107]

# ============================================================
# Phase 1: Profile essential modules 4 and 19
# ============================================================
print(f"\n=== Phase 1: Developmental profile of essential modules ===")

essential_mods = [4, 19]
essential_profile = {'hemilineages': Counter(), 'cell_classes': Counter(), 'nt': Counter(), 'super': Counter()}

for mod in essential_mods:
    mod_neurons = np.where(labels == mod)[0]
    print(f"\nModule {mod} ({len(mod_neurons)} neurons):")
    for idx in mod_neurons:
        nid = neuron_ids[idx]
        essential_profile['hemilineages'][rid_to_hemi.get(nid, 'unknown')] += 1
        essential_profile['cell_classes'][rid_to_class.get(nid, 'unknown')] += 1
        essential_profile['nt'][rid_to_nt.get(nid, 'unknown')] += 1
        essential_profile['super'][rid_to_super.get(nid, 'unknown')] += 1

    for ann_type in ['hemilineages', 'cell_classes', 'nt']:
        # Show top for this module
        mod_counts = Counter()
        for idx in mod_neurons:
            nid = neuron_ids[idx]
            if ann_type == 'hemilineages':
                mod_counts[rid_to_hemi.get(nid, 'unknown')] += 1
            elif ann_type == 'cell_classes':
                mod_counts[rid_to_class.get(nid, 'unknown')] += 1
            elif ann_type == 'nt':
                mod_counts[rid_to_nt.get(nid, 'unknown')] += 1
        top3 = mod_counts.most_common(5)
        print(f"  {ann_type}: {top3}")

# Identify the signature: top hemilineages and cell classes from essential modules
print(f"\nCombined essential profile:")
for ann_type, counts in essential_profile.items():
    print(f"  {ann_type}: {counts.most_common(8)}")

# The developmental signature = hemilineages that are enriched in essential modules
# vs the whole brain
whole_brain_hemi = Counter()
for idx in range(num_neurons_full):
    whole_brain_hemi[rid_to_hemi.get(neuron_ids[idx], 'unknown')] += 1

essential_total = sum(essential_profile['hemilineages'].values())
brain_total = sum(whole_brain_hemi.values())

print(f"\nEnriched hemilineages in essential modules:")
signature_hemis = set()
for hemi, count in essential_profile['hemilineages'].most_common(20):
    if hemi == 'unknown':
        continue
    essential_pct = 100 * count / essential_total
    brain_pct = 100 * whole_brain_hemi.get(hemi, 0) / brain_total
    enrichment = essential_pct / max(brain_pct, 0.01)
    if enrichment > 1.5 and count > 10:  # >1.5x enriched, at least 10 neurons
        signature_hemis.add(hemi)
        print(f"  {hemi}: {essential_pct:.1f}% in essential vs {brain_pct:.1f}% in brain ({enrichment:.1f}x) ***")
    elif count > 10:
        print(f"  {hemi}: {essential_pct:.1f}% in essential vs {brain_pct:.1f}% in brain ({enrichment:.1f}x)")

# Also use cell class
essential_classes = set()
for cls, count in essential_profile['cell_classes'].most_common(10):
    if cls == 'unknown' or count < 20:
        continue
    essential_pct = 100 * count / essential_total
    essential_classes.add(cls)

print(f"\nSignature hemilineages: {signature_hemis}")
print(f"Signature cell classes: {essential_classes}")

# ============================================================
# Phase 2: Select ALL neurons matching the developmental signature
# ============================================================
print(f"\n=== Phase 2: Gene-guided neuron selection ===")

# Strategy: select neurons that match ANY of the enriched hemilineages
# OR that are in the same cell classes as essential modules
# PLUS all DN and stimulus neurons (they're the I/O interface)

gene_selected = set()
essential_io = set(DN.values()) | set(STIM_SUGAR) | set(STIM_LC4) | set(STIM_JO)

# Method 1: Hemilineage match
hemi_selected = set()
for idx in range(num_neurons_full):
    nid = neuron_ids[idx]
    hemi = rid_to_hemi.get(nid, 'unknown')
    if hemi in signature_hemis:
        hemi_selected.add(idx)

# Method 2: Cell class match
class_selected = set()
for idx in range(num_neurons_full):
    nid = neuron_ids[idx]
    cls = rid_to_class.get(nid, 'unknown')
    if cls in essential_classes:
        class_selected.add(idx)

# Method 3: Union + I/O neurons
gene_selected = hemi_selected | essential_io
gene_selected_with_class = hemi_selected | class_selected | essential_io

print(f"Hemilineage-selected: {len(hemi_selected)} neurons")
print(f"Cell class-selected: {len(class_selected)} neurons")
print(f"Gene-selected (hemi + I/O): {len(gene_selected)} neurons")
print(f"Gene-selected (hemi + class + I/O): {len(gene_selected_with_class)} neurons")

# Which modules do gene-selected neurons come from?
gene_mod_dist = Counter(int(labels[idx]) for idx in gene_selected)
print(f"\nGene-selected neurons by module:")
for mod, count in gene_mod_dist.most_common(10):
    in_essential = "ESSENTIAL" if mod in essential_mods else ""
    print(f"  Module {mod}: {count} neurons {in_essential}")

# ============================================================
# Phase 3: Build gene-guided subcircuit and test
# ============================================================
print(f"\n=== Phase 3: Build and test gene-guided circuit ===")

pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

DT, W_SCALE, GAIN = 0.5, 0.275, 8.0
POISSON_WEIGHT, POISSON_RATE = 15.0, 150.0

def build_and_test(neuron_set, name):
    """Build subcircuit from neuron set, run 6 behaviors."""
    keep = sorted(neuron_set)
    keep_set = set(keep)
    n = len(keep)
    old_to_new = {old: new for new, old in enumerate(keep)}

    # Filter synapses
    mask = np.array([pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(df_conn))])
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
    vals_sub = vals_full[mask] * GAIN
    n_syn = len(pre_sub)

    if n_syn == 0:
        print(f"  {name}: 0 synapses, skipping")
        return None

    # Neuron types
    a = np.full(n, 0.02, dtype=np.float32)
    b_arr = np.full(n, 0.2, dtype=np.float32)
    c_arr = np.full(n, -65.0, dtype=np.float32)
    d_arr = np.full(n, 8.0, dtype=np.float32)
    for new_idx, old_idx in enumerate(keep):
        nid = neuron_ids[old_idx]
        cc = rid_to_class.get(nid, '')
        if isinstance(cc, str) and 'CX' in cc:
            a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.02, 0.2, -55.0, 4.0
        elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
            a[new_idx], b_arr[new_idx], c_arr[new_idx], d_arr[new_idx] = 0.1, 0.2, -65.0, 2.0

    a_t = torch.tensor(a); b_t = torch.tensor(b_arr)
    c_t = torch.tensor(c_arr); d_t = torch.tensor(d_arr)

    dn_new = {nm: old_to_new[idx] for nm, idx in DN.items() if idx in old_to_new}
    stim_sugar = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
    stim_lc4 = [old_to_new[i] for i in STIM_LC4 if i in old_to_new]
    stim_jo = [old_to_new[i] for i in STIM_JO if i in old_to_new]

    def run_sim(stim_indices, n_steps=500):
        W = torch.sparse_coo_tensor(
            torch.stack([torch.tensor(post_sub, dtype=torch.long),
                        torch.tensor(pre_sub, dtype=torch.long)]),
            torch.tensor(vals_sub, dtype=torch.float32),
            (n, n), dtype=torch.float32
        ).to_sparse_csr()

        v = torch.full((1, n), -65.0); u = b_t.unsqueeze(0) * v
        spikes = torch.zeros(1, n); rates = torch.zeros(1, n)
        for idx in stim_indices:
            rates[0, idx] = POISSON_RATE

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
                if dn_idx[j] >= 0:
                    dn_total[dn_names[j]] += int(spk[dn_idx[j]].item())
        return dn_total

    # Fitness functions
    def f_nav(dn):
        return sum(dn.get(nm, 0) for nm in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])
    def f_esc(dn):
        return sum(dn.get(nm, 0) for nm in ['GF_1', 'GF_2', 'MDN_1', 'MDN_2', 'MDN_3', 'MDN_4'])
    def f_turn(dn):
        l = sum(dn.get(nm, 0) for nm in ['DNa01_left', 'DNa02_left'])
        r = sum(dn.get(nm, 0) for nm in ['DNa01_right', 'DNa02_right'])
        return abs(l - r) + (l + r) * 0.1
    def f_arousal(dn):
        return sum(dn.values())
    def f_circles(dn):
        return f_turn(dn) + f_nav(dn) * 0.1
    def f_rhythm(dn):
        return f_arousal(dn) * 0.05

    stim_map = {'navigation': stim_sugar, 'escape': stim_lc4, 'turning': stim_jo,
                'arousal': stim_sugar, 'circles': stim_sugar, 'rhythm': stim_sugar}
    fit_map = {'navigation': f_nav, 'escape': f_esc, 'turning': f_turn,
               'arousal': f_arousal, 'circles': f_circles, 'rhythm': f_rhythm}

    print(f"\n  {name}: {n} neurons, {n_syn} synapses, {len(dn_new)} DN mapped")

    results = {}
    for bname in ['navigation', 'escape', 'turning', 'arousal', 'circles', 'rhythm']:
        stim = stim_map[bname]
        if not stim:
            results[bname] = {'baseline': 0, 'status': 'no_stim'}
            continue
        t0 = time.time()
        dn = run_sim(stim)
        bl = fit_map[bname](dn)
        results[bname] = {'baseline': bl, 'status': 'active' if bl > 0 else 'silent'}
        print(f"    {bname:>12}: {bl:>6.1f} {'ACTIVE' if bl > 0 else 'silent'} ({time.time()-t0:.1f}s)")

    return {'name': name, 'n_neurons': n, 'n_synapses': n_syn, 'dn_mapped': len(dn_new), 'behaviors': results}


# Test gene-guided circuit
result_gene = build_and_test(gene_selected, "Gene-guided (hemi)")
result_gene_class = build_and_test(gene_selected_with_class, "Gene-guided (hemi+class)")

# Compare against module-selected (the original 20K processor)
module_mods = set([40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41])
module_mods |= set(int(labels[DN[n]]) for n in DN)
module_mods |= set(int(labels[i]) for i in STIM_SUGAR + STIM_LC4 + STIM_JO)
module_neurons = set()
rng = np.random.RandomState(42)
for mod in sorted(module_mods):
    neurons = np.where(labels == mod)[0]
    n_keep = max(1, int(len(neurons) * 0.2))
    mod_essential = [n for n in neurons if n in essential_io]
    non_essential = [n for n in neurons if n not in essential_io]
    rng.shuffle(non_essential)
    module_neurons.update(set(mod_essential) | set(non_essential[:max(0, n_keep - len(mod_essential))]))

result_module = build_and_test(module_neurons, "Module-selected (20%)")

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*60}")
print("COMPARISON: Gene-guided vs Module-selected")
print("="*60)

all_results = [r for r in [result_gene, result_gene_class, result_module] if r is not None]

print(f"\n{'Circuit':>25} {'Neurons':>8} {'Synapses':>10} {'DN':>4}", end="")
for b in ['navigation', 'escape', 'turning', 'arousal', 'circles', 'rhythm']:
    print(f" {b[:4]:>6}", end="")
print()
print("-" * 90)

for r in all_results:
    print(f"{r['name']:>25} {r['n_neurons']:>8} {r['n_synapses']:>10} {r['dn_mapped']:>4}", end="")
    for b in ['navigation', 'escape', 'turning', 'arousal', 'circles', 'rhythm']:
        bl = r['behaviors'].get(b, {}).get('baseline', 0)
        print(f" {bl:>6.0f}", end="")
    print()

gene_active = sum(1 for b in (result_gene or {}).get('behaviors', {}).values()
                   if isinstance(b, dict) and b.get('baseline', 0) > 0)
module_active = sum(1 for b in (result_module or {}).get('behaviors', {}).values()
                     if isinstance(b, dict) and b.get('baseline', 0) > 0)

print(f"\nGene-guided active behaviors: {gene_active}/6")
print(f"Module-selected active behaviors: {module_active}/6")

if gene_active >= 4:
    print(f"\n>>> GENE-GUIDED CIRCUIT WORKS. Cell type specification is sufficient.")
    print(f">>> Growth program: differentiate these hemilineages → processor emerges.")
    print(f">>> Signature hemilineages: {signature_hemis}")
elif gene_active >= 2:
    print(f"\n>>> PARTIAL SUCCESS. Gene-guided circuit supports some but not all behaviors.")
    print(f">>> Need additional specification beyond cell type identity.")
else:
    print(f"\n>>> Gene-guided circuit does NOT work. Cell type alone is insufficient.")
    print(f">>> Specific connectivity within cell types matters. Harder growth program needed.")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'experiment': 'gene_guided_extraction',
    'signature_hemilineages': list(signature_hemis),
    'signature_cell_classes': list(essential_classes),
    'results': {r['name']: r for r in all_results},
    'gene_active_behaviors': gene_active,
    'module_active_behaviors': module_active,
}
with open(f'{outdir}/gene_guided.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)
print(f"\nSaved to {outdir}/gene_guided.json")
print("DONE.")
