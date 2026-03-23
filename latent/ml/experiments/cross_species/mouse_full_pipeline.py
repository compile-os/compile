#!/usr/bin/env python3
"""
Full synthetic neuroscience pipeline -- mouse cortex (MICrONS).

Steps 1-5: Specify -> Compile -> Extract -> Identify -> Growth Program.
Species validation: Does the architecture from fly transfer to mouse?

Uses module-level Izhikevich simulation with orientation selectivity
fitness function.
"""

import argparse
import json
import logging
import os
import pickle
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from compile.constants import NEURON_TYPES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Izhikevich parameters per cell type class (mouse cortex)
IZH_PARAMS = {
    "pyramidal": dict(a=0.02, b=0.2, c=-65.0, d=8.0),
    "PV": dict(a=0.1, b=0.2, c=-65.0, d=2.0),
    "SST": dict(a=0.02, b=0.25, c=-65.0, d=2.0),
    "VIP": dict(a=0.02, b=0.2, c=-65.0, d=6.0),
}

MICRONS_DIR = os.environ.get("MICRONS_DATA_DIR", "data/microns")

# Literature-based inhibitory connection rules
INHIB_RULES = [
    ("V1_L2/3", "PV", 8000), ("V1_L2/3", "SST", 4000), ("V1_L2/3", "VIP", 1500),
    ("V1_L4", "PV", 9000), ("V1_L4", "SST", 3000),
    ("V1_L5", "PV", 7000), ("V1_L5", "SST", 5000), ("V1_L5", "VIP", 1000),
    ("HVA_L2/3", "PV", 3000), ("HVA_L2/3", "SST", 1500), ("HVA_L2/3", "VIP", 600),
    ("HVA_L4", "PV", 2500), ("HVA_L4", "SST", 1000),
    ("HVA_L5", "PV", 2000), ("HVA_L5", "SST", 1200),
    ("PV", "V1_L2/3", 12000), ("PV", "V1_L4", 14000), ("PV", "V1_L5", 8000),
    ("PV", "HVA_L2/3", 4000), ("PV", "HVA_L4", 3000), ("PV", "HVA_L5", 2000),
    ("SST", "V1_L2/3", 5000), ("SST", "V1_L4", 3000), ("SST", "V1_L5", 4000),
    ("SST", "HVA_L2/3", 1500), ("SST", "HVA_L4", 1000), ("SST", "HVA_L5", 1200),
    ("SST", "PV", 3000), ("VIP", "SST", 4000), ("VIP", "PV", 1000),
]


def mod_to_izh(mod):
    if mod == "PV":
        return "PV"
    if mod == "SST":
        return "SST"
    if mod == "VIP":
        return "VIP"
    return "pyramidal"


def mod_sign(mod):
    return -1 if mod in ("PV", "SST", "VIP") else 1


def izhikevich_module_sim(W, drive, all_modules, n_steps=200, dt=1.0, noise=0.5):
    """Fast module-level Izhikevich simulation."""
    N = W.shape[0]
    v = np.full(N, -65.0)
    u = np.zeros(N)

    a_arr = np.array([IZH_PARAMS[mod_to_izh(m)]["a"] for m in all_modules])
    b_arr = np.array([IZH_PARAMS[mod_to_izh(m)]["b"] for m in all_modules])
    c_arr = np.array([IZH_PARAMS[mod_to_izh(m)]["c"] for m in all_modules])
    d_arr = np.array([IZH_PARAMS[mod_to_izh(m)]["d"] for m in all_modules])
    sign_arr = np.array([mod_sign(m) for m in all_modules], dtype=float)

    spike_count = np.zeros(N)
    rng = np.random.default_rng(42)

    for _ in range(n_steps):
        firing = (v >= 30.0).astype(float)
        spike_count += firing
        v = np.where(firing > 0, c_arr, v)
        u = np.where(firing > 0, u + d_arr, u)

        syn_I = W.T @ (firing * sign_arr) * 15.0
        I_total = drive + syn_I + rng.normal(0, noise, N)

        v_new = v + dt * (0.04 * v ** 2 + 5 * v + 140 - u + I_total)
        u_new = u + dt * a_arr * (b_arr * v - u)
        v = np.clip(v_new, -90.0, 35.0)
        u = u_new

    return spike_count / n_steps


def main():
    parser = argparse.ArgumentParser(description="Mouse cortex full pipeline (MICrONS)")
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    parser.add_argument("--microns-dir", default=MICRONS_DIR,
                        help="Directory with MICrONS cached data")
    args = parser.parse_args()

    microns_dir = args.microns_dir

    logger.info("=" * 70)
    logger.info("FULL SYNTHETIC NEUROSCIENCE PIPELINE -- MOUSE CORTEX")
    logger.info("=" * 70)

    # Load data
    node_pkl = os.path.join(microns_dir, "node_data_v1.pkl")
    edge_pkl = os.path.join(microns_dir, "edge_data_v1.pkl")

    if not (os.path.exists(node_pkl) and os.path.exists(edge_pkl)):
        logger.error("MICrONS cached data not found at %s. Run exp5_microns.py first.", microns_dir)
        return

    nodes_df = pickle.load(open(node_pkl, "rb"))
    edges_df = pickle.load(open(edge_pkl, "rb"))
    logger.info("Loaded %d neurons, %d synapses", len(nodes_df), len(edges_df))

    nodes_df = nodes_df.copy()
    nodes_df["cell_type"] = (
        nodes_df["hva"].astype(str).str.strip() + "_" + nodes_df["layer"].astype(str).str.strip()
    )

    n_exc = len(nodes_df)
    n_PV = int(n_exc * 0.20 / 0.67)
    n_SST = int(n_exc * 0.08 / 0.67)
    n_VIP = int(n_exc * 0.05 / 0.67)

    exc_modules = sorted(nodes_df["cell_type"].unique())
    inh_modules = ["PV", "SST", "VIP"]
    all_modules = exc_modules + inh_modules
    mod_idx = {m: i for i, m in enumerate(all_modules)}
    N_MOD = len(all_modules)

    # Build module connectivity
    mod_syn_count = defaultdict(int)
    for _, row in edges_df.iterrows():
        pre_m = f"{str(row.get('pre_hva', '')).strip()}_{str(row.get('pre_layer', '')).strip()}"
        post_m = f"{str(row.get('post_hva', '')).strip()}_{str(row.get('post_layer', '')).strip()}"
        if pre_m in mod_idx and post_m in mod_idx:
            mod_syn_count[(pre_m, post_m)] += row.get("n_synapses", 1)

    for pre, post, cnt in INHIB_RULES:
        if pre in mod_idx and post in mod_idx:
            mod_syn_count[(pre, post)] += cnt

    W_base = np.zeros((N_MOD, N_MOD))
    for (pre, post), cnt in mod_syn_count.items():
        W_base[mod_idx[pre], mod_idx[post]] = np.log1p(cnt)
    W_max = W_base.max() if W_base.max() > 0 else 1.0
    W_base /= W_max

    # Module counts
    mod_counts = {}
    for m in exc_modules:
        mod_counts[m] = int((nodes_df["cell_type"] == m).sum())
    mod_counts["PV"] = n_PV
    mod_counts["SST"] = n_SST
    mod_counts["VIP"] = n_VIP

    # Orientation selectivity fitness
    has_ori = "pref_ori_cvt_monet_full" in nodes_df.columns
    drive_A = np.zeros(N_MOD)
    drive_B = np.zeros(N_MOD)

    if has_ori:
        ori_data = nodes_df[["nucleus_id", "cell_type", "pref_ori_cvt_monet_full"]].dropna()
        for _, row in ori_data[ori_data["pref_ori_cvt_monet_full"].between(0, 45)].iterrows():
            if row["cell_type"] in mod_idx:
                drive_A[mod_idx[row["cell_type"]]] += 1
        for _, row in ori_data[ori_data["pref_ori_cvt_monet_full"].between(67.5, 112.5)].iterrows():
            if row["cell_type"] in mod_idx:
                drive_B[mod_idx[row["cell_type"]]] += 1
        total = max(drive_A.sum(), drive_B.sum(), 1)
        drive_A = drive_A / total * 20.0
        drive_B = drive_B / total * 20.0
    else:
        if "V1_L4" in mod_idx:
            drive_A[mod_idx["V1_L4"]] = 15.0
        if "HVA_L4" in mod_idx:
            drive_B[mod_idx["HVA_L4"]] = 15.0

    output_modules = ["V1_L2/3", "HVA_L2/3", "V1_L5"]
    output_indices = [mod_idx[m] for m in output_modules if m in mod_idx]

    def compute_fitness(W):
        rate_A = izhikevich_module_sim(W, drive_A, all_modules)
        rate_B = izhikevich_module_sim(W, drive_B, all_modules)
        return abs(rate_A[output_indices].mean() - rate_B[output_indices].mean())

    baseline_fit = compute_fitness(W_base)
    logger.info("Baseline fitness: %.4f", baseline_fit)

    # Evolution
    N_GEN, N_MUT = 25, 10
    rng = np.random.default_rng(1234)
    edge_delta = defaultdict(list)
    W_current = W_base.copy()
    current_fit = baseline_fit
    best_fit = baseline_fit
    accepted_mutations = []

    for gen in range(N_GEN):
        gen_accepted = 0
        for _ in range(N_MUT):
            candidates = [(i, j) for i in range(N_MOD) for j in range(N_MOD)
                          if W_current[i, j] > 0 or W_base[i, j] > 0.01]
            if not candidates:
                candidates = [(i, j) for i in range(N_MOD) for j in range(N_MOD)]
            i_mut, j_mut = candidates[rng.integers(len(candidates))]

            W_trial = W_current.copy()
            delta_w = rng.normal(0, 0.1)
            W_trial[i_mut, j_mut] = np.clip(W_current[i_mut, j_mut] + delta_w, 0, 2.0)
            trial_fit = compute_fitness(W_trial)
            fit_delta = trial_fit - current_fit

            edge_delta[(all_modules[i_mut], all_modules[j_mut])].append(fit_delta)

            if trial_fit > current_fit:
                W_current = W_trial
                current_fit = trial_fit
                gen_accepted += 1
                accepted_mutations.append({
                    "gen": gen, "edge": (all_modules[i_mut], all_modules[j_mut]),
                    "fit_delta": float(fit_delta),
                })

        if current_fit > best_fit:
            best_fit = current_fit
        if gen % 5 == 0 or gen == N_GEN - 1:
            logger.info("Gen %d: fitness=%.4f accepted=%d/%d", gen, current_fit, gen_accepted, N_MUT)

    logger.info("Evolution: %.4f -> %.4f", baseline_fit, best_fit)

    # Classify edges
    edge_classification = {}
    for edge_key, deltas in edge_delta.items():
        mean_delta = np.mean(deltas)
        if mean_delta > 0.01:
            cls = "evolvable"
        elif mean_delta < -0.005:
            cls = "frozen"
        else:
            cls = "irrelevant"
        edge_classification[edge_key] = {"classification": cls, "mean_delta": float(mean_delta)}

    n_evolvable = sum(1 for v in edge_classification.values() if v["classification"] == "evolvable")
    n_frozen = sum(1 for v in edge_classification.values() if v["classification"] == "frozen")
    n_total = len(edge_classification)
    logger.info("Edges: %d evolvable, %d frozen, %d total", n_evolvable, n_frozen, n_total)

    # Lesion test
    lesion_results = {}
    for mod in all_modules:
        W_lesion = W_current.copy()
        i_mod = mod_idx[mod]
        W_lesion[i_mod, :] = 0
        W_lesion[:, i_mod] = 0
        lesion_fit = compute_fitness(W_lesion)
        fit_drop = best_fit - lesion_fit
        lesion_results[mod] = {
            "fitness": float(lesion_fit),
            "pct_drop": float(fit_drop / max(best_fit, 1e-6) * 100),
            "is_critical": fit_drop > 0.5 * best_fit,
        }

    critical_modules = [m for m in all_modules if lesion_results[m]["is_critical"]]
    logger.info("Critical modules: %s", critical_modules)

    # Cross-species comparison
    logger.info("=" * 70)
    logger.info("CROSS-SPECIES COMPARISON")
    mouse_pct_frozen = n_frozen / max(n_total, 1) * 100
    mouse_pct_evolvable = n_evolvable / max(n_total, 1) * 100
    logger.info("Mouse: %.1f%% frozen, %.1f%% evolvable", mouse_pct_frozen, mouse_pct_evolvable)
    logger.info("Fly:   ~79%% frozen, ~21%% evolvable")

    # Save
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    results = {
        "experiment": "mouse_full_pipeline",
        "n_modules": N_MOD,
        "baseline_fitness": float(baseline_fit),
        "final_fitness": float(best_fit),
        "n_evolvable": n_evolvable,
        "n_frozen": n_frozen,
        "critical_modules": critical_modules,
        "lesion_results": lesion_results,
        "n_accepted": len(accepted_mutations),
    }
    with open(outdir / "mouse_full_pipeline.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info("Saved to %s", outdir / "mouse_full_pipeline.json")
    logger.info("PIPELINE COMPLETE.")


if __name__ == "__main__":
    main()
