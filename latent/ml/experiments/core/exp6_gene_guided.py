#!/usr/bin/env python3
"""
Experiment 6: Gene-guided circuit extraction.

Instead of extracting the processor by module ID, extract by DEVELOPMENTAL
SIGNATURE.  Take the transcription factor / hemilineage profile of essential
modules 4 and 19.  Select ALL neurons in the full connectome matching that
profile.  Build a subcircuit.  Compile 6 behaviors on it.

If it works: you specified a biological processor in purely genetic terms.
"Grow these cell types in these proportions" = the growth program.

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from compile.constants import (
    DN_NEURONS, DN_NAMES, STIM_SUGAR, STIM_LC4, STIM_JO,
    SIGNATURE_HEMIS, NEURON_TYPES, GAIN,
    DT, W_SCALE, POISSON_WEIGHT, POISSON_RATE,
)
from compile.data import load_connectome, load_annotations, load_module_labels, build_annotation_maps
from compile.fitness import f_nav, f_esc, f_turn, f_arousal, f_circles, f_rhythm
from compile.simulate import run_simulation
from compile.stats import bootstrap_ci, permutation_test, cohens_d

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subcircuit builder and tester
# ---------------------------------------------------------------------------

def build_and_test(
    neuron_set: set,
    name: str,
    pre_full: np.ndarray,
    post_full: np.ndarray,
    vals_full: np.ndarray,
    neuron_ids: list,
    rid_to_class: dict,
    rid_to_nt: dict,
    n_conn: int,
) -> dict | None:
    """Build subcircuit from neuron set, run 6 behaviors, return results."""
    keep = sorted(neuron_set)
    keep_set = set(keep)
    n = len(keep)
    old_to_new = {old: new for new, old in enumerate(keep)}

    # Filter synapses
    mask = np.array([
        pre_full[i] in keep_set and post_full[i] in keep_set
        for i in range(n_conn)
    ])
    pre_sub = np.array([old_to_new[pre_full[i]] for i in range(n_conn) if mask[i]])
    post_sub = np.array([old_to_new[post_full[i]] for i in range(n_conn) if mask[i]])
    vals_sub = vals_full[mask] * GAIN
    n_syn = len(pre_sub)

    if n_syn == 0:
        logger.info("  %s: 0 synapses, skipping", name)
        return None

    # Neuron types
    rs = NEURON_TYPES["RS"]
    ib = NEURON_TYPES["IB"]
    fs = NEURON_TYPES["FS"]

    a = np.full(n, rs["a"], dtype=np.float32)
    b_arr = np.full(n, rs["b"], dtype=np.float32)
    c_arr = np.full(n, rs["c"], dtype=np.float32)
    d_arr = np.full(n, rs["d"], dtype=np.float32)

    for new_idx, old_idx in enumerate(keep):
        nid = neuron_ids[old_idx]
        cc = rid_to_class.get(nid, "")
        if isinstance(cc, str) and "CX" in cc:
            a[new_idx], b_arr[new_idx] = ib["a"], ib["b"]
            c_arr[new_idx], d_arr[new_idx] = ib["c"], ib["d"]
        elif rid_to_nt.get(nid, "") in ("gaba", "GABA"):
            a[new_idx], b_arr[new_idx] = fs["a"], fs["b"]
            c_arr[new_idx], d_arr[new_idx] = fs["c"], fs["d"]

    neuron_params = {"a": a, "b": b_arr, "c": c_arr, "d": d_arr}

    dn_new = {nm: old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in old_to_new}
    stim_sugar = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]
    stim_lc4 = [old_to_new[i] for i in STIM_LC4 if i in old_to_new]
    stim_jo = [old_to_new[i] for i in STIM_JO if i in old_to_new]

    syn_vals = torch.tensor(vals_sub, dtype=torch.float32)

    stim_map = {
        "navigation": stim_sugar, "escape": stim_lc4, "turning": stim_jo,
        "arousal": stim_sugar, "circles": stim_sugar, "rhythm": stim_sugar,
    }
    fit_map = {
        "navigation": f_nav, "escape": f_esc, "turning": f_turn,
        "arousal": f_arousal, "circles": f_circles, "rhythm": f_rhythm,
    }

    logger.info("  %s: %d neurons, %d synapses, %d DN mapped", name, n, n_syn, len(dn_new))

    results = {}
    for bname in ["navigation", "escape", "turning", "arousal", "circles", "rhythm"]:
        stim = stim_map[bname]
        if not stim:
            results[bname] = {"baseline": 0, "status": "no_stim"}
            continue
        t0 = time.time()
        dn = run_simulation(
            syn_vals=syn_vals,
            pre=pre_sub, post=post_sub,
            num_neurons=n,
            neuron_params=neuron_params,
            stim_indices=stim,
            dn_indices=dn_new,
            n_steps=500,
        )
        bl = fit_map[bname](dn)
        results[bname] = {"baseline": bl, "status": "active" if bl > 0 else "silent"}
        logger.info("    %12s: %6.1f %s (%.1fs)", bname, bl, "ACTIVE" if bl > 0 else "silent", time.time() - t0)

    return {
        "name": name,
        "n_neurons": n,
        "n_synapses": n_syn,
        "dn_mapped": len(dn_new),
        "behaviors": results,
    }


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(output_dir: str = "results"):
    """Run the full gene-guided extraction experiment."""
    logger.info("=" * 60)
    logger.info("GENE-GUIDED CIRCUIT EXTRACTION")
    logger.info("=" * 60)

    # Load data
    df_conn, df_comp, num_neurons_full = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    maps = build_annotation_maps(ann)
    rid_to_hemi = maps["rid_to_hemi"]
    rid_to_class = maps["rid_to_class"]
    rid_to_nt = maps["rid_to_nt"]
    rid_to_super = maps["rid_to_super"]
    neuron_ids = df_comp.index.astype(str).tolist()

    # ================================================================
    # Phase 1: Profile essential modules 4 and 19
    # ================================================================
    logger.info("=== Phase 1: Developmental profile of essential modules ===")

    essential_mods = [4, 19]
    essential_profile = {
        "hemilineages": Counter(), "cell_classes": Counter(),
        "nt": Counter(), "super": Counter(),
    }

    for mod in essential_mods:
        mod_neurons = np.where(labels == mod)[0]
        logger.info("Module %d (%d neurons):", mod, len(mod_neurons))
        for idx in mod_neurons:
            nid = neuron_ids[idx]
            essential_profile["hemilineages"][rid_to_hemi.get(nid, "unknown")] += 1
            essential_profile["cell_classes"][rid_to_class.get(nid, "unknown")] += 1
            essential_profile["nt"][rid_to_nt.get(nid, "unknown")] += 1
            essential_profile["super"][rid_to_super.get(nid, "unknown")] += 1

        for ann_type in ["hemilineages", "cell_classes", "nt"]:
            mod_counts = Counter()
            for idx in mod_neurons:
                nid = neuron_ids[idx]
                if ann_type == "hemilineages":
                    mod_counts[rid_to_hemi.get(nid, "unknown")] += 1
                elif ann_type == "cell_classes":
                    mod_counts[rid_to_class.get(nid, "unknown")] += 1
                elif ann_type == "nt":
                    mod_counts[rid_to_nt.get(nid, "unknown")] += 1
            logger.info("  %s: %s", ann_type, mod_counts.most_common(5))

    logger.info("Combined essential profile:")
    for ann_type, counts in essential_profile.items():
        logger.info("  %s: %s", ann_type, counts.most_common(8))

    # Enrichment analysis
    whole_brain_hemi = Counter()
    for idx in range(num_neurons_full):
        whole_brain_hemi[rid_to_hemi.get(neuron_ids[idx], "unknown")] += 1

    essential_total = sum(essential_profile["hemilineages"].values())
    brain_total = sum(whole_brain_hemi.values())

    logger.info("Enriched hemilineages in essential modules:")
    signature_hemis = set()
    for hemi, count in essential_profile["hemilineages"].most_common(20):
        if hemi == "unknown":
            continue
        essential_pct = 100 * count / essential_total
        brain_pct = 100 * whole_brain_hemi.get(hemi, 0) / brain_total
        enrichment = essential_pct / max(brain_pct, 0.01)
        if enrichment > 1.5 and count > 10:
            signature_hemis.add(hemi)
            logger.info("  %s: %.1f%% in essential vs %.1f%% in brain (%.1fx) ***", hemi, essential_pct, brain_pct, enrichment)
        elif count > 10:
            logger.info("  %s: %.1f%% in essential vs %.1f%% in brain (%.1fx)", hemi, essential_pct, brain_pct, enrichment)

    essential_classes = set()
    for cls, count in essential_profile["cell_classes"].most_common(10):
        if cls == "unknown" or count < 20:
            continue
        essential_classes.add(cls)

    logger.info("Signature hemilineages: %s", signature_hemis)
    logger.info("Signature cell classes: %s", essential_classes)

    # ================================================================
    # Phase 2: Select ALL neurons matching the developmental signature
    # ================================================================
    logger.info("=== Phase 2: Gene-guided neuron selection ===")

    essential_io = set(DN_NEURONS.values()) | set(STIM_SUGAR) | set(STIM_LC4) | set(STIM_JO)

    hemi_selected = set()
    for idx in range(num_neurons_full):
        nid = neuron_ids[idx]
        if rid_to_hemi.get(nid, "unknown") in signature_hemis:
            hemi_selected.add(idx)

    class_selected = set()
    for idx in range(num_neurons_full):
        nid = neuron_ids[idx]
        if rid_to_class.get(nid, "unknown") in essential_classes:
            class_selected.add(idx)

    gene_selected = hemi_selected | essential_io
    gene_selected_with_class = hemi_selected | class_selected | essential_io

    logger.info("Hemilineage-selected: %d neurons", len(hemi_selected))
    logger.info("Cell class-selected: %d neurons", len(class_selected))
    logger.info("Gene-selected (hemi + I/O): %d neurons", len(gene_selected))
    logger.info("Gene-selected (hemi + class + I/O): %d neurons", len(gene_selected_with_class))

    gene_mod_dist = Counter(int(labels[idx]) for idx in gene_selected)
    logger.info("Gene-selected neurons by module:")
    for mod, count in gene_mod_dist.most_common(10):
        tag = "ESSENTIAL" if mod in essential_mods else ""
        logger.info("  Module %d: %d neurons %s", mod, count, tag)

    # ================================================================
    # Phase 3: Build gene-guided subcircuit and test
    # ================================================================
    logger.info("=== Phase 3: Build and test gene-guided circuit ===")

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)
    n_conn = len(df_conn)

    result_gene = build_and_test(
        gene_selected, "Gene-guided (hemi)",
        pre_full, post_full, vals_full, neuron_ids, rid_to_class, rid_to_nt, n_conn,
    )
    result_gene_class = build_and_test(
        gene_selected_with_class, "Gene-guided (hemi+class)",
        pre_full, post_full, vals_full, neuron_ids, rid_to_class, rid_to_nt, n_conn,
    )

    # Module-selected comparison
    module_mods = {40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41}
    module_mods |= {int(labels[DN_NEURONS[n]]) for n in DN_NEURONS}
    module_mods |= {int(labels[i]) for i in STIM_SUGAR + STIM_LC4 + STIM_JO}
    module_neurons = set()
    rng = np.random.RandomState(42)
    for mod in sorted(module_mods):
        neurons = np.where(labels == mod)[0]
        n_keep = max(1, int(len(neurons) * 0.2))
        mod_essential = [n for n in neurons if n in essential_io]
        non_essential = [n for n in neurons if n not in essential_io]
        rng.shuffle(non_essential)
        module_neurons.update(set(mod_essential) | set(non_essential[:max(0, n_keep - len(mod_essential))]))

    result_module = build_and_test(
        module_neurons, "Module-selected (20%)",
        pre_full, post_full, vals_full, neuron_ids, rid_to_class, rid_to_nt, n_conn,
    )

    # ================================================================
    # Summary
    # ================================================================
    logger.info("=" * 60)
    logger.info("COMPARISON: Gene-guided vs Module-selected")
    logger.info("=" * 60)

    all_results = [r for r in [result_gene, result_gene_class, result_module] if r is not None]

    header = f"{'Circuit':>25} {'Neurons':>8} {'Synapses':>10} {'DN':>4}"
    for b in ["navigation", "escape", "turning", "arousal", "circles", "rhythm"]:
        header += f" {b[:4]:>6}"
    logger.info(header)
    logger.info("-" * 90)

    for r in all_results:
        line = f"{r['name']:>25} {r['n_neurons']:>8} {r['n_synapses']:>10} {r['dn_mapped']:>4}"
        for b in ["navigation", "escape", "turning", "arousal", "circles", "rhythm"]:
            bl = r["behaviors"].get(b, {}).get("baseline", 0)
            line += f" {bl:>6.0f}"
        logger.info(line)

    gene_active = sum(
        1 for b in (result_gene or {}).get("behaviors", {}).values()
        if isinstance(b, dict) and b.get("baseline", 0) > 0
    )
    module_active = sum(
        1 for b in (result_module or {}).get("behaviors", {}).values()
        if isinstance(b, dict) and b.get("baseline", 0) > 0
    )

    logger.info("Gene-guided active behaviors: %d/6", gene_active)
    logger.info("Module-selected active behaviors: %d/6", module_active)

    # ================================================================
    # Statistical comparison: gene-guided vs module-selected
    # ================================================================
    behaviors_list = ["navigation", "escape", "turning", "arousal", "circles", "rhythm"]
    if result_gene is not None and result_module is not None:
        gene_scores = np.array([
            result_gene["behaviors"].get(b, {}).get("baseline", 0.0)
            for b in behaviors_list
        ], dtype=np.float64)
        module_scores = np.array([
            result_module["behaviors"].get(b, {}).get("baseline", 0.0)
            for b in behaviors_list
        ], dtype=np.float64)

        logger.info("=" * 60)
        logger.info("STATISTICAL COMPARISON: Gene-guided vs Module-selected")
        logger.info("=" * 60)

        obs_diff, p_val = permutation_test(gene_scores, module_scores)
        d = cohens_d(gene_scores, module_scores)
        logger.info(
            "Permutation test: observed diff = %.1f, p = %.4f",
            obs_diff, p_val,
        )
        logger.info("Cohen's d (effect size): %.2f", d)

        gene_pt, gene_lo, gene_hi = bootstrap_ci(gene_scores)
        module_pt, module_lo, module_hi = bootstrap_ci(module_scores)
        logger.info(
            "Gene-guided mean fitness: %.1f [95%% CI: %.1f, %.1f]",
            gene_pt, gene_lo, gene_hi,
        )
        logger.info(
            "Module-selected mean fitness: %.1f [95%% CI: %.1f, %.1f]",
            module_pt, module_lo, module_hi,
        )

    if gene_active >= 4:
        logger.info(">>> GENE-GUIDED CIRCUIT WORKS. Cell type specification is sufficient.")
        logger.info(">>> Growth program: differentiate these hemilineages -> processor emerges.")
        logger.info(">>> Signature hemilineages: %s", signature_hemis)
    elif gene_active >= 2:
        logger.info(">>> PARTIAL SUCCESS. Gene-guided circuit supports some but not all behaviors.")
    else:
        logger.info(">>> Gene-guided circuit does NOT work. Cell type alone is insufficient.")

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    stats_output = {}
    if result_gene is not None and result_module is not None:
        stats_output = {
            "permutation_test_p": float(p_val),
            "permutation_test_observed_diff": float(obs_diff),
            "cohens_d": float(d),
            "gene_guided_fitness_ci": [float(gene_pt), float(gene_lo), float(gene_hi)],
            "module_selected_fitness_ci": [float(module_pt), float(module_lo), float(module_hi)],
        }
    output = {
        "experiment": "gene_guided_extraction",
        "signature_hemilineages": list(signature_hemis),
        "signature_cell_classes": list(essential_classes),
        "results": {r["name"]: r for r in all_results},
        "gene_active_behaviors": gene_active,
        "module_active_behaviors": module_active,
        "statistics": stats_output,
    }
    out_path = outdir / "gene_guided.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    logger.info("Saved to %s", out_path)

    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Gene-guided circuit extraction experiment")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    args = parser.parse_args()

    run_experiment(output_dir=args.output_dir)
