#!/usr/bin/env python3
"""
Calibrate subsumption architecture from real FlyWire data.

Maps the fly brain's functional organization onto a subsumption architecture:
  - Layer 0 (escape): GF neurons + their upstream interneurons
  - Layer 1 (avoidance): MDN neurons + their upstream interneurons
  - Layer 2 (navigation): P9/MN9 neurons + their upstream interneurons
  - Sensory: STIM_SUGAR, STIM_LC4, STIM_JO neurons
  - Motor: DN neurons (outputs)
  - Suppression: inhibitory interneurons between layers

For each pair of functional groups, computes the real connection probability
from the FlyWire connectome. These probabilities replace the made-up ones
in the subsumption architecture spec.

Also extracts the real weight distribution per connection type.

Usage:
    python scripts/calibrate_subsumption.py
    python scripts/calibrate_subsumption.py --output compile/calibrated_subsumption.json
"""

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np

from compile.constants import (
    DN_NEURONS, STIM_SUGAR, STIM_LC4, STIM_JO,
)
from compile.data import load_connectome, load_annotations, load_module_labels, build_annotation_maps

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def main(output_path: str = "results/calibrated_subsumption.json"):
    df_conn, df_comp, num_neurons = load_connectome()
    ann = load_annotations()
    maps = build_annotation_maps(ann)
    labels = load_module_labels()
    neuron_ids = df_comp.index.astype(str).tolist()

    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    vals = df_conn["Excitatory x Connectivity"].values.astype(np.float32)

    # ── Define functional groups ──────────────────────────────────────

    # Motor neurons by function
    escape_dns = {DN_NEURONS["GF_1"], DN_NEURONS["GF_2"]}
    avoid_dns = {DN_NEURONS[n] for n in ["MDN_1", "MDN_2", "MDN_3", "MDN_4"]}
    nav_dns = {DN_NEURONS[n] for n in ["P9_left", "P9_right", "P9_oDN1_left", "P9_oDN1_right", "MN9_left", "MN9_right"]}
    turn_dns = {DN_NEURONS[n] for n in ["DNa01_left", "DNa01_right", "DNa02_left", "DNa02_right"]}
    all_dns = escape_dns | avoid_dns | nav_dns | turn_dns

    # Sensory neurons
    sensory_set = set(STIM_SUGAR + STIM_LC4 + STIM_JO)

    # Find interneurons upstream of each DN group (1 hop back)
    # These form the "layers" of the subsumption architecture
    def get_upstream(dn_set, max_neurons=2000):
        """Find neurons that synapse onto the DN set."""
        upstream = defaultdict(float)
        for i in range(len(df_conn)):
            if post[i] in dn_set and pre[i] not in all_dns and pre[i] not in sensory_set:
                upstream[pre[i]] += abs(vals[i])
        # Return top neurons by total weight
        sorted_up = sorted(upstream.items(), key=lambda x: -x[1])
        return {n for n, _ in sorted_up[:max_neurons]}

    logger.info("Finding upstream interneurons for each DN group...")
    escape_interneurons = get_upstream(escape_dns, max_neurons=1500)
    avoid_interneurons = get_upstream(avoid_dns, max_neurons=1500)
    nav_interneurons = get_upstream(nav_dns, max_neurons=1500)

    # Inhibitory interneurons: GABA neurons that connect between layers
    gaba_set = set()
    for i, nid in enumerate(neuron_ids):
        nt = maps["rid_to_nt"].get(nid, "").lower()
        if "gaba" in nt:
            gaba_set.add(i)

    # Suppression neurons: GABA neurons upstream of each layer
    suppress_1to0 = gaba_set & escape_interneurons  # inhibit escape from avoidance layer
    suppress_2to1 = gaba_set & avoid_interneurons  # inhibit avoidance from nav layer

    # Build functional group mapping
    groups = {
        "sensory": sensory_set,
        "layer0_escape": escape_interneurons - gaba_set,
        "layer1_avoid": avoid_interneurons - gaba_set,
        "layer2_navigate": nav_interneurons - gaba_set,
        "suppress_1to0": suppress_1to0 if suppress_1to0 else gaba_set & escape_interneurons,
        "suppress_2to1": suppress_2to1 if suppress_2to1 else gaba_set & avoid_interneurons,
        "emergency": sensory_set & set(STIM_LC4),  # LC4 = looming detector = emergency
        "motor": all_dns,
    }

    logger.info("Functional group sizes:")
    for name, neurons in groups.items():
        logger.info("  %-20s: %d neurons", name, len(neurons))

    # ── Compute real connection probabilities ─────────────────────────

    logger.info("Computing connection probabilities from FlyWire data...")

    group_names = list(groups.keys())
    conn_stats = {}

    for src_name in group_names:
        src_set = groups[src_name]
        if not src_set:
            continue
        for tgt_name in group_names:
            tgt_set = groups[tgt_name]
            if not tgt_set or src_name == tgt_name:
                continue

            # Count actual connections
            n_connections = 0
            weights = []
            for i in range(len(df_conn)):
                if pre[i] in src_set and post[i] in tgt_set:
                    n_connections += 1
                    weights.append(abs(vals[i]))

            # Connection probability = actual connections / possible connections
            n_possible = len(src_set) * len(tgt_set)
            prob = n_connections / n_possible if n_possible > 0 else 0

            if prob > 0.0001:  # Only keep meaningful connections
                key = f"{src_name}->{tgt_name}"
                conn_stats[key] = {
                    "from": src_name,
                    "to": tgt_name,
                    "n_connections": n_connections,
                    "n_possible": n_possible,
                    "prob": round(prob, 6),
                    "mean_weight": round(np.mean(weights), 2) if weights else 0,
                    "median_weight": round(np.median(weights), 2) if weights else 0,
                    "p95_weight": round(np.percentile(weights, 95), 2) if weights else 0,
                }

    # Sort by probability
    sorted_conns = sorted(conn_stats.items(), key=lambda x: -x[1]["prob"])

    logger.info("\nReal connection probabilities (FlyWire v783):")
    logger.info("%-35s %10s %8s %10s %10s", "Connection", "Prob", "N_conn", "Mean_w", "P95_w")
    logger.info("-" * 80)
    for key, s in sorted_conns:
        logger.info(
            "%-35s %10.6f %8d %10.2f %10.2f",
            key, s["prob"], s["n_connections"], s["mean_weight"], s["p95_weight"],
        )

    # ── Build calibrated spec ─────────────────────────────────────────

    calibrated_rules = []
    for key, s in sorted_conns:
        calibrated_rules.append({
            "from": s["from"],
            "to": s["to"],
            "prob": s["prob"],
            "mean_weight": s["mean_weight"],
            "type": "calibrated_from_flywire",
        })

    calibrated_proportions = {}
    total = sum(len(v) for v in groups.values())
    for name, neurons in groups.items():
        calibrated_proportions[name] = round(len(neurons) / total, 4)

    output = {
        "architecture": "subsumption_calibrated",
        "source": "FlyWire v783 connectome",
        "description": "Subsumption architecture with connection probabilities extracted from real fly brain functional groups",
        "group_sizes": {k: len(v) for k, v in groups.items()},
        "proportions": calibrated_proportions,
        "connection_rules": calibrated_rules,
        "weight_stats": {
            "global_mean": round(np.abs(vals[vals != 0]).mean(), 2),
            "global_median": round(np.median(np.abs(vals[vals != 0])), 2),
        },
    }

    outpath = Path(output_path)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if hasattr(x, 'item') else str(x))
    logger.info("\nSaved calibrated spec to %s", outpath)

    # Print the spec in a format that can be pasted into architecture_specs.py
    logger.info("\n" + "=" * 60)
    logger.info("CALIBRATED SUBSUMPTION SPEC (paste into architecture_specs.py)")
    logger.info("=" * 60)
    logger.info("connection_rules = [")
    for r in calibrated_rules:
        logger.info('    {"from": "%s", "to": "%s", "prob": %.6f, "type": "calibrated"},',
                     r["from"], r["to"], r["prob"])
    logger.info("]")
    logger.info("\nproportions = %s", json.dumps(calibrated_proportions, indent=4))

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="results/calibrated_subsumption.json")
    args = parser.parse_args()
    main(args.output)
