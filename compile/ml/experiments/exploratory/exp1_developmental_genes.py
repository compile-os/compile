#!/usr/bin/env python3
"""
Experiment 1: Developmental gene signature analysis.

Map every neuron in the processor to its cell type and developmental
transcription factors.  Compare essential modules (4, 19) against
dispensable modules (24, 30, 31, 35, 40, 41, 46).

Question: Is there a gene expression pattern that predicts which
modules are essential?
"""

import json
import logging
from collections import Counter
from pathlib import Path

import numpy as np

from compile.data import build_annotation_maps, load_annotations, load_connectome, load_module_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ESSENTIAL = [4, 19]
HELPFUL = [5, 17, 23, 28, 32, 36, 37, 45]
DISPENSABLE = [24, 30, 31, 35, 40, 41, 46]


def main():
    logger.info("=" * 60)
    logger.info("DEVELOPMENTAL GENE SIGNATURE ANALYSIS")
    logger.info("=" * 60)

    labels = load_module_labels()
    ann = load_annotations()
    _, df_comp, _ = load_connectome()
    neuron_ids = df_comp.index.astype(str).tolist()

    # Build ID mappings for multiple annotation columns
    rid_to = {}
    for col in ["super_class", "cell_class", "cell_sub_class", "cell_type",
                 "hemibrain_type", "ito_lee_hemilineage", "hartenstein_hemilineage",
                 "top_nt", "flow"]:
        if col in ann.columns:
            rid_to[col] = dict(zip(ann["root_id"].astype(str), ann[col].fillna("unknown")))

    logger.info("Essential modules: %s", ESSENTIAL)
    logger.info("Helpful modules: %s", HELPFUL)
    logger.info("Dispensable modules: %s", DISPENSABLE)

    for ann_type in ["super_class", "cell_class", "ito_lee_hemilineage",
                      "hartenstein_hemilineage", "top_nt", "flow"]:
        if ann_type not in rid_to:
            continue
        logger.info("=" * 60)
        logger.info("ANNOTATION: %s", ann_type)

        for group_name, modules in [("ESSENTIAL", ESSENTIAL), ("HELPFUL", HELPFUL),
                                     ("DISPENSABLE", DISPENSABLE)]:
            counts = Counter()
            total = 0
            for mod in modules:
                for idx in np.where(labels == mod)[0]:
                    val = rid_to[ann_type].get(neuron_ids[idx], "unknown")
                    counts[val] += 1
                    total += 1

            logger.info("  %s (%d neurons across modules %s):", group_name, total, modules)
            for val, count in counts.most_common(10):
                pct = 100 * count / max(total, 1)
                logger.info("    %30s: %5d (%5.1f%%)", val, count, pct)

    # Hemilineage enrichment
    logger.info("=" * 60)
    logger.info("HEMILINEAGE ENRICHMENT: Essential vs Dispensable")

    for hemi_type in ["ito_lee_hemilineage", "hartenstein_hemilineage"]:
        if hemi_type not in rid_to:
            continue
        essential_hemi = Counter()
        dispensable_hemi = Counter()
        e_total = d_total = 0

        for mod in ESSENTIAL:
            for idx in np.where(labels == mod)[0]:
                essential_hemi[rid_to[hemi_type].get(neuron_ids[idx], "unknown")] += 1
                e_total += 1
        for mod in DISPENSABLE:
            for idx in np.where(labels == mod)[0]:
                dispensable_hemi[rid_to[hemi_type].get(neuron_ids[idx], "unknown")] += 1
                d_total += 1

        all_hemis = set(essential_hemi.keys()) | set(dispensable_hemi.keys())
        enriched = []
        for h in all_hemis:
            if h == "unknown":
                continue
            e_pct = 100 * essential_hemi.get(h, 0) / max(e_total, 1)
            d_pct = 100 * dispensable_hemi.get(h, 0) / max(d_total, 1)
            ratio = e_pct / max(d_pct, 0.01)
            enriched.append((h, e_pct, d_pct, ratio))

        enriched.sort(key=lambda x: -x[3])
        logger.info("  Top enriched in essential (via %s):", hemi_type)
        for h, e_pct, d_pct, ratio in enriched[:10]:
            logger.info("    %30s: essential=%.1f%% dispensable=%.1f%% ratio=%.1fx", h, e_pct, d_pct, ratio)

    # Save summary
    summary = {}
    for group_name, modules in [("essential", ESSENTIAL), ("helpful", HELPFUL), ("dispensable", DISPENSABLE)]:
        group_data = {}
        for ann_type in ["super_class", "cell_class", "top_nt", "ito_lee_hemilineage"]:
            if ann_type not in rid_to:
                continue
            counts = Counter()
            for mod in modules:
                for idx in np.where(labels == mod)[0]:
                    counts[rid_to[ann_type].get(neuron_ids[idx], "unknown")] += 1
            group_data[ann_type] = dict(counts.most_common(15))
        summary[group_name] = group_data

    outdir = Path("results/developmental_genes")
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "developmental_genes.json", "w") as f:
        json.dump(summary, f, indent=2)
    logger.info("Saved to %s", outdir / "developmental_genes.json")
    logger.info("DONE.")


if __name__ == "__main__":
    main()
