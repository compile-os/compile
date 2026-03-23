#!/usr/bin/env python3
"""
Behavior manifold (fast version).

Map the space of possible behaviors by perturbing inter-module edges
and measuring DN output vectors.  Includes PCA/UMAP embedding.

Uses BrainEngine (LIF) if available, otherwise IzhikevichBrainEngine.
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path

import numpy as np
import torch

from compile.constants import GAIN
from compile.data import build_edge_synapse_index, load_connectome, load_module_labels

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

N_STEPS = 300
STIMULI = ["sugar", "lc4", "jo"]


def _get_brain_engine():
    try:
        from brain_body_bridge import BrainEngine
        brain = BrainEngine(device="cpu")
        logger.info("Using LIF BrainEngine")
        return brain
    except ImportError:
        from compile.simulate import IzhikevichBrainEngine
        brain = IzhikevichBrainEngine(device="cpu")
        logger.info("Using IzhikevichBrainEngine")
        return brain


def get_dn_vector(brain, stimulus):
    """Run brain and return DN spike dict."""
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)
    dn_spikes = {name: 0 for name in brain.dn_indices}
    for _ in range(N_STEPS):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for name, idx in brain.dn_indices.items():
            dn_spikes[name] += int(spk[idx].item())
    return dn_spikes


def main():
    parser = argparse.ArgumentParser(description="Behavior manifold mapping")
    parser.add_argument("--output", default=os.environ.get("COMPILE_OUTPUT_DIR", "results"),
                        help="Output directory")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BEHAVIOR MANIFOLD (FAST)")
    logger.info("=" * 60)

    brain = _get_brain_engine()
    brain._syn_vals.mul_(GAIN)
    baseline_weights = brain._syn_vals.clone()
    dn_names = sorted(brain.dn_indices.keys())

    labels = load_module_labels()
    df_conn = load_connectome()[0]
    edge_syn_idx, inter_module_edges_set = build_edge_synapse_index(df_conn, labels)
    inter_module_edges = sorted(inter_module_edges_set)

    # Also need module-level perturbation indices
    pre_mods = labels[df_conn["Presynaptic_Index"].values].astype(int)
    post_mods = labels[df_conn["Postsynaptic_Index"].values].astype(int)

    results = []
    t0_global = time.time()

    def record(stim, perturbation, edge, scale, dn, label):
        vec = [dn.get(n, 0) for n in dn_names]
        results.append({
            "stimulus": stim, "perturbation": perturbation,
            "edge": edge, "scale": scale,
            "dn_vector": vec, "total_spikes": sum(vec), "label": label,
        })

    # Phase 1: Baselines
    logger.info("Phase 1: Baselines")
    for stim in STIMULI:
        brain._syn_vals.copy_(baseline_weights)
        dn = get_dn_vector(brain, stim)
        record(stim, "baseline", None, 1.0, dn, f"baseline_{stim}")

    # Phase 2: 100 random edge perturbations
    logger.info("Phase 2: 100 random edge perturbations")
    rng = np.random.RandomState(42)
    random_edges = rng.choice(len(inter_module_edges), 100, replace=False)
    for pi, eidx in enumerate(random_edges):
        edge = inter_module_edges[eidx]
        syns = edge_syn_idx[edge]
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[syns] *= 2.0
        for stim in STIMULI:
            dn = get_dn_vector(brain, stim)
            record(stim, "single_edge", list(edge), 2.0, dn, f"e{edge[0]}_{edge[1]}_{stim}")
        if (pi + 1) % 20 == 0:
            logger.info("  [%d/100] %d points", pi + 1, len(results))

    # Phase 3: Module-level perturbations
    logger.info("Phase 3: Module-level perturbations")
    n_modules = int(labels.max()) + 1
    for mod in range(n_modules):
        mod_syns = [i for i in range(len(df_conn)) if pre_mods[i] == mod or post_mods[i] == mod]
        if not mod_syns:
            continue
        brain._syn_vals.copy_(baseline_weights)
        brain._syn_vals[mod_syns] *= 2.0
        for stim in STIMULI:
            dn = get_dn_vector(brain, stim)
            record(stim, "module_scale", mod, 2.0, dn, f"mod{mod}_{stim}")

    # Phase 4: Multi-edge combos
    logger.info("Phase 4: 30 multi-edge combos")
    for ci in range(30):
        combo = rng.choice(len(inter_module_edges), 5, replace=False)
        brain._syn_vals.copy_(baseline_weights)
        edges_used = []
        for eidx in combo:
            edge = inter_module_edges[eidx]
            brain._syn_vals[edge_syn_idx[edge]] *= 2.0
            edges_used.append(list(edge))
        for stim in STIMULI:
            dn = get_dn_vector(brain, stim)
            record(stim, "multi_edge", edges_used, 2.0, dn, f"combo{ci}_{stim}")

    # Phase 5: Embedding
    logger.info("Phase 5: Embedding %d points", len(results))
    vectors = np.array([r["dn_vector"] for r in results], dtype=float)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vectors_norm = vectors / norms

    from sklearn.decomposition import PCA
    pca = PCA(n_components=min(10, vectors.shape[1]))
    pca_coords = pca.fit_transform(vectors_norm)
    logger.info("PCA variance: %s", pca.explained_variance_ratio_[:5].round(4))

    try:
        import umap
        umap_coords = umap.UMAP(n_components=2, random_state=42).fit_transform(vectors_norm)
        has_umap = True
    except ImportError:
        umap_coords = pca_coords[:, :2]
        has_umap = False

    for i, r in enumerate(results):
        r["pca"] = pca_coords[i, :3].tolist()
        r["umap"] = umap_coords[i].tolist()

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    output = {
        "metadata": {
            "dn_names": dn_names, "n_points": len(results),
            "pca_explained_variance": pca.explained_variance_ratio_.tolist(),
            "has_umap": has_umap, "total_time": time.time() - t0_global,
        },
        "points": results,
    }
    with open(outdir / "behavior_manifold.json", "w") as f:
        json.dump(output, f)
    logger.info("Saved %d points. Total time: %.0fs", len(results), time.time() - t0_global)
    logger.info("DONE.")


if __name__ == "__main__":
    main()
