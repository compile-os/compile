#!/usr/bin/env python3
"""
Experiment 5: MICrONS mouse visual cortex.

Load the MICrONS dataset (mouse V1, ~70K neurons), build module
structure, and run an edge-sweep to compare evolvable surface topology
against the fly's.

If same bimodal modifiability -> design principles transfer.
If same topological motifs -> universal circuit design.

Falls back to synthetic data if MICrONS is unavailable.
"""

import argparse
import json
import logging
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from compile.constants import DT, POISSON_RATE, POISSON_WEIGHT, W_SCALE
from compile.simulate import izh_step

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MICRONS_DIR = os.environ.get("MICRONS_DATA_DIR", "data/microns")
GAIN_MOUSE = 20.0
POISSON_RATE_MOUSE = 300.0
POISSON_WEIGHT_MOUSE = 20.0
W_SCALE_MOUSE = 0.3


def load_microns_data():
    """Load MICrONS data from cache, CAVEclient, or generate synthetic."""
    node_pkl = os.path.join(MICRONS_DIR, "node_data_v1.pkl")
    edge_pkl = os.path.join(MICRONS_DIR, "edge_data_v1.pkl")

    syn = ct = None

    # Try cached files
    if os.path.exists(node_pkl) and os.path.exists(edge_pkl):
        logger.info("Found cached MICrONS data -- loading from disk...")
        try:
            import pickle
            nodes_df = pickle.load(open(node_pkl, "rb"))
            edges_df = pickle.load(open(edge_pkl, "rb"))
            syn = edges_df[["pre_nucleus_id", "post_nucleus_id", "mean_synapse_size"]].copy()
            syn.columns = ["pre_pt_root_id", "post_pt_root_id", "size"]
            syn = syn.dropna(subset=["pre_pt_root_id", "post_pt_root_id"]).reset_index(drop=True)

            nodes_df = nodes_df.copy()
            nodes_df["cell_type"] = (
                nodes_df["hva"].astype(str).fillna("unknown") + "_"
                + nodes_df["layer"].astype(str).fillna("unknown")
            )
            ct = nodes_df[["nucleus_id", "cell_type"]].rename(columns={"nucleus_id": "pt_root_id"})
            logger.info("Cached data: %d synapses, %d neurons", len(syn), len(ct))
        except Exception as e:
            logger.warning("Cached load failed: %s", e)
            syn = ct = None

    # Try CAVEclient
    if syn is None:
        try:
            from caveclient import CAVEclient
            client = CAVEclient("minnie65_public")
            ct_raw = client.materialize.query_table("aibs_metamodel_celltypes_v661")
            typed_ids = ct_raw["pt_root_id"].tolist() if "pt_root_id" in ct_raw.columns else []
            if typed_ids:
                syn = client.materialize.query_table(
                    "synapses_pni_2",
                    filter_in_dict={"pre_pt_root_id": typed_ids[:5000]},
                    select_columns=["pre_pt_root_id", "post_pt_root_id", "size"],
                )
                ct = ct_raw
                logger.info("CAVEclient: %d synapses", len(syn))
        except Exception as e:
            logger.info("CAVEclient unavailable: %s", e)

    # Fallback: synthetic
    if syn is None:
        logger.info("Generating synthetic MICrONS-scale graph...")
        rng = np.random.default_rng(42)
        N_SYN, N_CELLS = 50_000, 3_000
        syn = pd.DataFrame({
            "pre_pt_root_id": rng.integers(0, N_CELLS, N_SYN),
            "post_pt_root_id": rng.integers(0, N_CELLS, N_SYN),
            "size": rng.exponential(scale=500, size=N_SYN).astype(np.float32),
        })
        cell_types = ["V1_L2/3", "V1_L4", "V1_L5", "HVA_L2/3", "HVA_L4", "HVA_L5"]
        ct = pd.DataFrame({
            "pt_root_id": np.arange(N_CELLS),
            "cell_type": rng.choice(cell_types, size=N_CELLS),
        })

    return syn, ct


def run_mouse_sim(syn_vals_local, pre_idx, post_idx, n_neurons, stim_idx,
                  readout_neurons, n_steps=500):
    """Izhikevich simulation for mouse cortex."""
    a_t = torch.full((n_neurons,), 0.02)
    b_t = torch.full((n_neurons,), 0.2)
    c_t = torch.full((n_neurons,), -65.0)
    d_t = torch.full((n_neurons,), 8.0)

    W = torch.sparse_coo_tensor(
        torch.stack([torch.tensor(post_idx, dtype=torch.long),
                     torch.tensor(pre_idx, dtype=torch.long)]),
        syn_vals_local, (n_neurons, n_neurons), dtype=torch.float32,
    ).to_sparse_csr()

    v = torch.full((1, n_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_neurons)
    rates = torch.zeros(1, n_neurons)
    for idx in stim_idx:
        rates[0, idx] = POISSON_RATE_MOUSE

    readout_total = 0
    for _ in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        I = poisson * POISSON_WEIGHT_MOUSE + torch.mm(spikes, W.t()) * W_SCALE_MOUSE
        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=DT)
        spk = spikes.squeeze(0)
        readout_total += sum(int(spk[r].item()) for r in readout_neurons)

    return readout_total


def main():
    parser = argparse.ArgumentParser(description="MICrONS mouse visual cortex experiment")
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    parser.add_argument("--microns-dir", default=MICRONS_DIR,
                        help="Directory with MICrONS cached data")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MICrONS MOUSE VISUAL CORTEX")
    logger.info("=" * 60)

    syn, ct = load_microns_data()

    if syn is None or len(syn) == 0:
        logger.error("No synapse data available.")
        return

    pre_col, post_col = "pre_pt_root_id", "post_pt_root_id"
    unique_neurons = sorted(set(syn[pre_col].tolist() + syn[post_col].tolist()))
    n_neurons = len(unique_neurons)
    n_synapses = len(syn)
    nid_to_idx = {nid: i for i, nid in enumerate(unique_neurons)}
    logger.info("Neurons: %d, Synapses: %d", n_neurons, n_synapses)

    # Module assignment from cell type
    if ct is not None and "cell_type" in ct.columns:
        id_col = "pt_root_id" if "pt_root_id" in ct.columns else ct.columns[0]
        nid_to_type = dict(zip(ct[id_col], ct["cell_type"]))
        type_to_mod = {}
        mod_counter = 0
        labels_mouse = np.full(n_neurons, -1, dtype=int)
        for i, nid in enumerate(unique_neurons):
            ctype = nid_to_type.get(nid, "unknown")
            if ctype not in type_to_mod:
                type_to_mod[ctype] = mod_counter
                mod_counter += 1
            labels_mouse[i] = type_to_mod[ctype]
        n_modules = mod_counter
    else:
        labels_mouse = np.zeros(n_neurons, dtype=int)
        n_modules = 1

    logger.info("Modules (cell types): %d", n_modules)

    pre_idx = np.array([nid_to_idx[nid] for nid in syn[pre_col]])
    post_idx = np.array([nid_to_idx[nid] for nid in syn[post_col]])
    weights = syn["size"].values.astype(np.float32) if "size" in syn.columns else np.ones(len(syn), dtype=np.float32)
    weights = weights / max(weights.max(), 1.0)
    syn_vals = torch.tensor(weights * GAIN_MOUSE, dtype=torch.float32)

    # Build edge index
    pre_mods = labels_mouse[pre_idx]
    post_mods = labels_mouse[post_idx]
    edge_syn_idx = defaultdict(list)
    for i in range(len(syn)):
        edge_syn_idx[(int(pre_mods[i]), int(post_mods[i]))].append(i)
    inter_edges = sorted([e for e in edge_syn_idx if e[0] != e[1] and e[0] >= 0 and e[1] >= 0])

    n_stim = min(200, n_neurons // 5)
    stim_step = max(1, n_neurons // n_stim)
    stim_neurons = list(range(0, n_neurons, stim_step))[:n_stim]
    readout_neurons = stim_neurons[:]

    logger.info("Baseline measurement...")
    baseline = run_mouse_sim(syn_vals, pre_idx, post_idx, n_neurons, stim_neurons, readout_neurons)
    logger.info("Baseline readout: %d", baseline)

    # Edge sweep
    n_test = min(200, len(inter_edges))
    test_edges = inter_edges[:n_test]
    logger.info("Sweeping %d inter-module edges...", n_test)

    results = {"frozen": 0, "evolvable": 0, "irrelevant": 0}
    for i, edge in enumerate(test_edges):
        syns = edge_syn_idx[edge]
        test_vals = syn_vals.clone()
        test_vals[syns] *= 2.0
        fit_amp = run_mouse_sim(test_vals, pre_idx, post_idx, n_neurons, stim_neurons, readout_neurons)

        test_vals2 = syn_vals.clone()
        test_vals2[syns] *= 0.5
        fit_att = run_mouse_sim(test_vals2, pre_idx, post_idx, n_neurons, stim_neurons, readout_neurons)

        if (fit_amp - baseline) > 0 or (fit_att - baseline) > 0:
            results["evolvable"] += 1
        elif (fit_amp - baseline) < 0 and (fit_att - baseline) < 0:
            results["frozen"] += 1
        else:
            results["irrelevant"] += 1

        if (i + 1) % 50 == 0:
            logger.info("  [%d/%d] %s", i + 1, n_test, results)

    total = sum(results.values())
    logger.info("MOUSE CORTEX MODIFIABILITY:")
    for cls, count in results.items():
        logger.info("  %s: %d (%.1f%%)", cls, count, 100 * count / max(total, 1))

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(outdir / "microns_mouse.json", "w") as f:
        json.dump({
            "species": "mouse", "n_neurons": n_neurons, "n_synapses": n_synapses,
            "n_modules": n_modules, "n_edges_tested": n_test,
            "baseline": baseline, "results": results,
        }, f, indent=2, default=str)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
