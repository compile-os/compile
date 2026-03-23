#!/usr/bin/env python3
"""
EXPERIMENT 1: Developmental Gene Signature

Map every neuron in the 20,626-neuron processor to its cell type and
developmental transcription factors. Compare essential modules (4, 19)
against dispensable modules (24, 30, 31, 35, 40, 41, 46).

Is there a gene expression pattern that predicts which modules are essential?
"""
import sys, os, json
os.chdir("/home/ubuntu/fly-brain-embodied")
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
from pathlib import Path

print("=" * 60)
print("DEVELOPMENTAL GENE SIGNATURE ANALYSIS")
print("=" * 60)

labels = np.load('/home/ubuntu/module_labels_v2.npy')
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
neuron_ids = comp.index.astype(str).tolist()

# Build ID mappings
rid_to = {}
for col in ['super_class', 'cell_class', 'cell_sub_class', 'cell_type', 'hemibrain_type',
            'ito_lee_hemilineage', 'hartenstein_hemilineage', 'top_nt', 'flow']:
    rid_to[col] = dict(zip(ann['root_id'].astype(str), ann[col].fillna('unknown')))

ESSENTIAL = [4, 19]
HELPFUL = [5, 17, 23, 28, 32, 36, 37, 45]
DISPENSABLE = [24, 30, 31, 35, 40, 41, 46]
ALL_PROCESSOR = sorted(set(ESSENTIAL + HELPFUL + DISPENSABLE))

print(f"Essential modules: {ESSENTIAL}")
print(f"Helpful modules: {HELPFUL}")
print(f"Dispensable modules: {DISPENSABLE}")

# Analyze each annotation type per module group
for ann_type in ['super_class', 'cell_class', 'ito_lee_hemilineage', 'hartenstein_hemilineage', 'top_nt', 'flow']:
    print(f"\n{'='*60}")
    print(f"ANNOTATION: {ann_type}")
    print("="*60)

    for group_name, modules in [('ESSENTIAL', ESSENTIAL), ('HELPFUL', HELPFUL), ('DISPENSABLE', DISPENSABLE)]:
        counts = Counter()
        total = 0
        for mod in modules:
            mod_neurons = np.where(labels == mod)[0]
            for idx in mod_neurons:
                nid = neuron_ids[idx]
                val = rid_to[ann_type].get(nid, 'unknown')
                counts[val] += 1
                total += 1

        print(f"\n  {group_name} ({total} neurons across modules {modules}):")
        for val, count in counts.most_common(10):
            pct = 100 * count / total
            print(f"    {val:>30}: {count:>5} ({pct:>5.1f}%)")

# Hemilineage analysis — developmental origin
print(f"\n{'='*60}")
print("HEMILINEAGE ENRICHMENT: Essential vs Dispensable")
print("="*60)

for hemi_type in ['ito_lee_hemilineage', 'hartenstein_hemilineage']:
    print(f"\n--- {hemi_type} ---")
    essential_hemi = Counter()
    dispensable_hemi = Counter()
    e_total, d_total = 0, 0

    for mod in ESSENTIAL:
        for idx in np.where(labels == mod)[0]:
            val = rid_to[hemi_type].get(neuron_ids[idx], 'unknown')
            essential_hemi[val] += 1
            e_total += 1

    for mod in DISPENSABLE:
        for idx in np.where(labels == mod)[0]:
            val = rid_to[hemi_type].get(neuron_ids[idx], 'unknown')
            dispensable_hemi[val] += 1
            d_total += 1

    # Find hemilineages enriched in essential vs dispensable
    all_hemis = set(essential_hemi.keys()) | set(dispensable_hemi.keys())
    enriched = []
    for h in all_hemis:
        if h == 'unknown':
            continue
        e_pct = 100 * essential_hemi.get(h, 0) / max(e_total, 1)
        d_pct = 100 * dispensable_hemi.get(h, 0) / max(d_total, 1)
        ratio = e_pct / max(d_pct, 0.01)
        enriched.append((h, e_pct, d_pct, ratio))

    enriched.sort(key=lambda x: -x[3])
    print(f"  Top hemilineages ENRICHED in essential modules:")
    for h, e_pct, d_pct, ratio in enriched[:10]:
        marker = " ***" if ratio > 2 else ""
        print(f"    {h:>30}: essential={e_pct:>5.1f}% dispensable={d_pct:>5.1f}% ratio={ratio:>5.1f}x{marker}")

    print(f"  Top hemilineages ENRICHED in dispensable modules:")
    enriched.sort(key=lambda x: x[3])
    for h, e_pct, d_pct, ratio in enriched[:10]:
        marker = " ***" if ratio < 0.5 else ""
        print(f"    {h:>30}: essential={e_pct:>5.1f}% dispensable={d_pct:>5.1f}% ratio={ratio:>5.1f}x{marker}")

# Cell type specificity
print(f"\n{'='*60}")
print("CELL TYPE SPECIFICITY: Module 4 vs Module 19")
print("="*60)

for mod in ESSENTIAL:
    print(f"\n  Module {mod} ({np.sum(labels == mod)} neurons):")
    for ann_type in ['cell_class', 'top_nt', 'ito_lee_hemilineage']:
        counts = Counter()
        for idx in np.where(labels == mod)[0]:
            val = rid_to[ann_type].get(neuron_ids[idx], 'unknown')
            counts[val] += 1
        print(f"    {ann_type}:")
        for val, count in counts.most_common(5):
            print(f"      {val}: {count}")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)

# Build summary for JSON
summary = {}
for group_name, modules in [('essential', ESSENTIAL), ('helpful', HELPFUL), ('dispensable', DISPENSABLE)]:
    group_data = {}
    for ann_type in ['super_class', 'cell_class', 'top_nt', 'ito_lee_hemilineage']:
        counts = Counter()
        for mod in modules:
            for idx in np.where(labels == mod)[0]:
                val = rid_to[ann_type].get(neuron_ids[idx], 'unknown')
                counts[val] += 1
        group_data[ann_type] = dict(counts.most_common(15))
    summary[group_name] = group_data

with open(f'{outdir}/developmental_genes.json', 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\nSaved to {outdir}/developmental_genes.json")
print("DONE.")
