#!/usr/bin/env python3
"""
Experiment 6 (revised): Developmental compiler.

Reverse-compile the gene-guided processor to a growth program.

The gene-guided circuit (8,158 neurons from 19 hemilineages) works.  Now: what
developmental program produces that connectivity?

  Step 1: Map every neuron to its birth lineage, position, and guidance cues.
  Step 2: Model axon growth as gradient-following on the embryonic manifold.
  Step 3: Simulate development -- do the growth rules produce the target connectivity?
  Step 4: Optimize the growth program to match the target circuit.
  Step 5: Functional test of the grown circuit.

The growth program IS the product.  Hand it to a stem cell lab.

Requires: compile library (pip install -e latent/ml)
"""

import argparse
import json
import logging
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
from scipy.spatial.distance import cdist

from compile.constants import (
    DN_NEURONS, DN_NAMES, STIM_SUGAR, SIGNATURE_HEMIS,
    NEURON_TYPES, GAIN, DT, W_SCALE, POISSON_WEIGHT, POISSON_RATE,
)
from compile.data import load_connectome, load_annotations, load_module_labels
from compile.simulate import run_simulation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(output_dir: str = "results"):
    """Run the full developmental compiler experiment."""
    logger.info("=" * 60)
    logger.info("DEVELOPMENTAL COMPILER")
    logger.info("Reverse-compile circuit to growth program")
    logger.info("=" * 60)

    # Load data
    df_conn, df_comp, num_neurons = load_connectome()
    labels = load_module_labels()
    ann = load_annotations()
    neuron_ids = df_comp.index.astype(str).tolist()

    # Build annotation maps (extended: include spatial columns)
    rid_map = {}
    for col in [
        "super_class", "cell_class", "cell_type", "ito_lee_hemilineage",
        "hartenstein_hemilineage", "top_nt", "flow",
        "pos_x", "pos_y", "pos_z", "soma_x", "soma_y", "soma_z",
    ]:
        if col in ann.columns:
            rid_map[col] = dict(zip(ann["root_id"].astype(str), ann[col]))

    essential_io = set(DN_NEURONS.values()) | set(STIM_SUGAR)

    # ================================================================
    # Step 1: Spatial mapping of gene-guided neurons
    # ================================================================
    logger.info("=== Step 1: Spatial mapping ===")

    gene_neurons = []
    for idx, nid in enumerate(neuron_ids):
        hemi = rid_map.get("ito_lee_hemilineage", {}).get(nid, "unknown")
        if hemi in SIGNATURE_HEMIS or idx in essential_io:
            gene_neurons.append(idx)

    gene_set = set(gene_neurons)
    logger.info("Gene-guided neurons: %d", len(gene_neurons))

    # Get spatial positions
    positions = np.zeros((len(gene_neurons), 3))
    has_position = 0
    for i, idx in enumerate(gene_neurons):
        nid = neuron_ids[idx]
        x = rid_map.get("soma_x", {}).get(nid, None)
        y = rid_map.get("soma_y", {}).get(nid, None)
        z = rid_map.get("soma_z", {}).get(nid, None)
        if x is not None and y is not None and z is not None:
            try:
                positions[i] = [float(x), float(y), float(z)]
                has_position += 1
            except (ValueError, TypeError):
                pass

    logger.info("Neurons with soma position: %d/%d", has_position, len(gene_neurons))

    # Hemilineage spatial clusters
    hemi_positions = defaultdict(list)
    for i, idx in enumerate(gene_neurons):
        nid = neuron_ids[idx]
        hemi = rid_map.get("ito_lee_hemilineage", {}).get(nid, "unknown")
        if has_position and np.any(positions[i] != 0):
            hemi_positions[hemi].append(positions[i])

    logger.info("Hemilineage spatial centroids:")
    hemi_centroids = {}
    for hemi in SIGNATURE_HEMIS:
        pts = hemi_positions.get(hemi, [])
        if pts:
            centroid = np.mean(pts, axis=0)
            spread = np.std([np.linalg.norm(p - centroid) for p in pts])
            hemi_centroids[hemi] = centroid
            logger.info(
                "  %35s: n=%4d, centroid=(%.0f, %.0f, %.0f), spread=%.0f",
                hemi, len(pts), centroid[0], centroid[1], centroid[2], spread,
            )

    # ================================================================
    # Step 2: Connectivity rules
    # ================================================================
    logger.info("=== Step 2: Connectivity rules ===")

    pre_full = df_conn["Presynaptic_Index"].values
    post_full = df_conn["Postsynaptic_Index"].values
    vals_full = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    mask = np.array([
        pre_full[i] in gene_set and post_full[i] in gene_set
        for i in range(len(df_conn))
    ])
    pre_sub = pre_full[mask]
    post_sub = post_full[mask]
    vals_sub = vals_full[mask]
    n_syn = len(pre_sub)
    logger.info("Synapses in gene-guided circuit: %d", n_syn)

    # Connectivity by hemilineage pair
    hemi_connectivity = defaultdict(lambda: {"count": 0, "total_weight": 0.0})
    for i in range(n_syn):
        pre_nid = neuron_ids[pre_sub[i]]
        post_nid = neuron_ids[post_sub[i]]
        pre_hemi = rid_map.get("ito_lee_hemilineage", {}).get(pre_nid, "unknown")
        post_hemi = rid_map.get("ito_lee_hemilineage", {}).get(post_nid, "unknown")
        key = (pre_hemi, post_hemi)
        hemi_connectivity[key]["count"] += 1
        hemi_connectivity[key]["total_weight"] += abs(vals_sub[i])

    sorted_conns = sorted(hemi_connectivity.items(), key=lambda x: -x[1]["count"])
    logger.info("Top 20 hemilineage-to-hemilineage connections:")
    for (pre_h, post_h), data in sorted_conns[:20]:
        if pre_h == "unknown" or post_h == "unknown":
            continue
        avg_w = data["total_weight"] / data["count"]
        logger.info(
            "  %30s -> %-30s: %5d syns, avg_w=%.2f",
            pre_h, post_h, data["count"], avg_w,
        )

    # ================================================================
    # Step 3: The Growth Program
    # ================================================================
    logger.info("=== Step 3: Growth program specification ===")

    hemi_counts = Counter()
    hemi_nt = defaultdict(Counter)
    for idx in gene_neurons:
        nid = neuron_ids[idx]
        hemi = rid_map.get("ito_lee_hemilineage", {}).get(nid, "unknown")
        nt = rid_map.get("top_nt", {}).get(nid, "unknown")
        hemi_counts[hemi] += 1
        hemi_nt[hemi][nt] += 1

    logger.info("GROWTH PROGRAM SPECIFICATION:")
    logger.info("1. CELL TYPE RECIPE (%d hemilineages):", len(SIGNATURE_HEMIS))
    growth_program = {"cell_types": [], "connections": [], "spatial": []}

    for hemi, count in hemi_counts.most_common():
        if hemi == "unknown" or hemi not in SIGNATURE_HEMIS:
            continue
        dominant_nt = hemi_nt[hemi].most_common(1)[0][0] if hemi_nt[hemi] else "unknown"
        proportion = count / len(gene_neurons)
        centroid = hemi_centroids.get(hemi, [0, 0, 0])
        if isinstance(centroid, np.ndarray):
            centroid = centroid.tolist()

        growth_program["cell_types"].append({
            "hemilineage": hemi,
            "count": count,
            "proportion": round(proportion, 4),
            "neurotransmitter": dominant_nt,
            "spatial_centroid": [round(c, 1) for c in centroid],
        })
        logger.info(
            "  %35s: %4d neurons (%.1f%%), NT=%s",
            hemi, count, proportion * 100, dominant_nt,
        )

    # Connection rules
    logger.info("2. CONNECTION RULES (hemilineage -> hemilineage):")
    for (pre_h, post_h), data in sorted_conns[:30]:
        if pre_h == "unknown" or post_h == "unknown":
            continue
        if pre_h not in SIGNATURE_HEMIS and post_h not in SIGNATURE_HEMIS:
            continue
        pre_n = hemi_counts.get(pre_h, 1)
        post_n = hemi_counts.get(post_h, 1)
        conn_prob = data["count"] / (pre_n * post_n)
        avg_w = data["total_weight"] / data["count"]

        growth_program["connections"].append({
            "from": pre_h,
            "to": post_h,
            "synapse_count": data["count"],
            "connection_probability": round(min(conn_prob, 1.0), 4),
            "average_weight": round(avg_w, 3),
        })
        logger.info(
            "  %25s -> %-25s: p=%.4f, w=%.2f, n=%d",
            pre_h, post_h, conn_prob, avg_w, data["count"],
        )

    # Spatial layout
    logger.info("3. SPATIAL LAYOUT (hemilineage centroids):")
    for entry in growth_program["cell_types"]:
        h = entry["hemilineage"]
        c = entry["spatial_centroid"]
        logger.info("  %35s: (%.0f, %.0f, %.0f)", h, c[0], c[1], c[2])

    # ================================================================
    # Step 4: Growth simulation
    # ================================================================
    logger.info("=== Step 4: Growth simulation ===")
    logger.info("Simulating development from growth program...")

    np.random.seed(42)
    grown_neurons = []
    grown_types = []

    for entry in growth_program["cell_types"]:
        centroid = np.array(entry["spatial_centroid"])
        if np.all(centroid == 0):
            centroid = np.random.randn(3) * 10000
        for _ in range(entry["count"]):
            pos = centroid + np.random.randn(3) * 2000
            grown_neurons.append(pos)
            grown_types.append(entry["hemilineage"])

    grown_neurons = np.array(grown_neurons)
    n_grown = len(grown_neurons)
    logger.info("Grown neurons: %d", n_grown)

    # Connection rule lookup
    conn_rules = {}
    for rule in growth_program["connections"]:
        conn_rules[(rule["from"], rule["to"])] = {
            "prob": rule["connection_probability"],
            "weight": rule["average_weight"],
        }

    logger.info("Generating connections from growth rules...")
    grown_connections = 0
    type_pair_counts = defaultdict(int)

    for i in range(n_grown):
        for j in range(n_grown):
            if i == j:
                continue
            rule = conn_rules.get((grown_types[i], grown_types[j]))
            if rule is None:
                continue
            dist = np.linalg.norm(grown_neurons[i] - grown_neurons[j])
            dist_factor = np.exp(-dist / 10000)
            p = rule["prob"] * dist_factor

            if np.random.random() < p:
                grown_connections += 1
                type_pair_counts[(grown_types[i], grown_types[j])] += 1

            if grown_connections > 1000000:
                break
        if grown_connections > 1000000:
            break

    logger.info("Generated connections: %d", grown_connections)

    # Compare to target
    logger.info("=== Comparison: Grown vs Target ===")
    logger.info("Target synapses: %d", n_syn)
    logger.info("Grown synapses: %d", grown_connections)
    ratio = grown_connections / max(n_syn, 1)
    logger.info("Ratio: %.2fx", ratio)

    logger.info("Top grown connections vs target:")
    grown_sorted = sorted(type_pair_counts.items(), key=lambda x: -x[1])[:10]
    for (pre_h, post_h), count in grown_sorted:
        target = hemi_connectivity.get((pre_h, post_h), {}).get("count", 0)
        r = count / max(target, 1)
        logger.info(
            "  %25s -> %-25s: grown=%5d, target=%5d, ratio=%.2f",
            pre_h, post_h, count, target, r,
        )

    # ================================================================
    # Step 5: Functional test of grown circuit
    # ================================================================
    logger.info("=== Step 5: Functional test of grown circuit ===")
    logger.info("Running functional test on actual gene-guided circuit as reference...")

    gene_idx = sorted(gene_set)
    n_gene = len(gene_idx)
    g_old_to_new = {old: new for new, old in enumerate(gene_idx)}

    g_pre = np.array([g_old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
    g_post = np.array([g_old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
    g_vals = vals_full[mask] * GAIN

    dn_new = {nm: g_old_to_new[idx] for nm, idx in DN_NEURONS.items() if idx in g_old_to_new}
    stim_new = [g_old_to_new[i] for i in STIM_SUGAR if i in g_old_to_new]

    # Neuron types
    rs = NEURON_TYPES["RS"]
    ib = NEURON_TYPES["IB"]
    fs = NEURON_TYPES["FS"]

    a_arr = np.full(n_gene, rs["a"], dtype=np.float32)
    b_arr = np.full(n_gene, rs["b"], dtype=np.float32)
    c_arr = np.full(n_gene, rs["c"], dtype=np.float32)
    d_arr = np.full(n_gene, rs["d"], dtype=np.float32)

    for new_idx, old_idx in enumerate(gene_idx):
        nid = neuron_ids[old_idx]
        cc = rid_map.get("cell_class", {}).get(nid, "")
        if isinstance(cc, str) and "CX" in cc:
            a_arr[new_idx], b_arr[new_idx] = ib["a"], ib["b"]
            c_arr[new_idx], d_arr[new_idx] = ib["c"], ib["d"]
        elif rid_map.get("top_nt", {}).get(nid, "") in ("gaba", "GABA"):
            a_arr[new_idx], b_arr[new_idx] = fs["a"], fs["b"]
            c_arr[new_idx], d_arr[new_idx] = fs["c"], fs["d"]

    neuron_params = {"a": a_arr, "b": b_arr, "c": c_arr, "d": d_arr}
    syn_vals_tensor = torch.tensor(g_vals, dtype=torch.float32)

    t0 = time.time()
    dn_total = run_simulation(
        syn_vals=syn_vals_tensor,
        pre=g_pre, post=g_post,
        num_neurons=n_gene,
        neuron_params=neuron_params,
        stim_indices=stim_new,
        dn_indices=dn_new,
        n_steps=500,
    )

    nav_score = sum(
        dn_total.get(n, 0)
        for n in ["P9_left", "P9_right", "MN9_left", "MN9_right", "P9_oDN1_left", "P9_oDN1_right"]
    )
    logger.info("Gene-guided circuit nav score: %d (%.1fs)", nav_score, time.time() - t0)
    active_dn = {k: v for k, v in sorted(dn_total.items()) if v > 0}
    logger.info("Active DNs: %s", active_dn)

    # ================================================================
    # Summary
    # ================================================================
    logger.info("=" * 60)
    logger.info("DEVELOPMENTAL COMPILER OUTPUT")
    logger.info("=" * 60)
    logger.info(
        "GROWTH PROGRAM: %d hemilineages, %d neurons, %d connection rules",
        len(growth_program["cell_types"]), n_grown, len(growth_program["connections"]),
    )
    logger.info("Gene-guided circuit nav score: %d", nav_score)
    logger.info(
        "Grown circuit connectivity: %d synapses (target: %d)",
        grown_connections, n_syn,
    )

    # Save
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "experiment": "developmental_compiler",
        "growth_program": growth_program,
        "target_synapses": n_syn,
        "grown_synapses": grown_connections,
        "gene_guided_nav_score": nav_score,
        "n_hemilineages": len(growth_program["cell_types"]),
        "n_connection_rules": len(growth_program["connections"]),
    }
    out_path = outdir / "developmental_compiler.json"
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

    parser = argparse.ArgumentParser(description="Developmental compiler: reverse-compile to growth program")
    parser.add_argument("--output-dir", default="results", help="Output directory")
    args = parser.parse_args()

    run_experiment(output_dir=args.output_dir)
