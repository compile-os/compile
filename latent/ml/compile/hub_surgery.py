"""
Hub architecture surgery for connectome experiments.

Provides functions to reshape the hub-and-spoke architecture of the
FlyWire connectome by manipulating inter-module synaptic weights.

Three surgical operations:

1. **flatten_hubs** — Suppress hub modules so no module has more than
   `max_ratio` × average inter-module connectivity. Tests whether
   hub-and-spoke is NECESSARY.

2. **swap_hubs** — Demote existing hubs and promote new modules to hub
   status by redistributing inter-module synaptic weight. Tests whether
   hub LOCATION matters.

3. **add_hubs** — Scale up additional modules to hub-level connectivity
   without touching existing hubs. Tests whether MORE hubs = better.

All operations work on the IzhikevichBrainEngine's `_syn_vals` tensor,
modifying synaptic weights in-place. They return a surgery report dict
for logging.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)


def _compute_module_edge_strength(
    syn_vals: torch.Tensor,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
) -> dict[int, float]:
    """
    Compute total absolute synaptic weight for each module's inter-module edges.

    Returns dict mapping module_id -> total |weight| of all inter-module
    synapses involving that module (as source or target).
    """
    module_strength: dict[int, float] = {}
    for edge in inter_module_edges:
        pre_mod, post_mod = edge
        syns = edge_syn_idx[edge]
        strength = float(syn_vals[syns].abs().sum())
        module_strength[pre_mod] = module_strength.get(pre_mod, 0) + strength
        module_strength[post_mod] = module_strength.get(post_mod, 0) + strength
    return module_strength


def identify_hubs(
    syn_vals: torch.Tensor,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
    top_n: int = 2,
) -> tuple[list[int], dict[int, float]]:
    """
    Identify the top-N hub modules by inter-module synaptic strength.

    Returns:
        (hub_module_ids, module_strength_dict)
    """
    strengths = _compute_module_edge_strength(syn_vals, edge_syn_idx, inter_module_edges)
    sorted_mods = sorted(strengths.keys(), key=lambda m: strengths[m], reverse=True)
    hubs = sorted_mods[:top_n]
    logger.info(
        "Identified hub modules: %s (strengths: %s)",
        hubs, {m: f"{strengths[m]:.0f}" for m in hubs},
    )
    return hubs, strengths


def flatten_hubs(
    syn_vals: torch.Tensor,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
    max_ratio: float = 2.0,
) -> dict:
    """
    Suppress hub connectivity so no module exceeds max_ratio × average.

    For each module whose inter-module synaptic strength exceeds the
    threshold, scales down ALL synapses on edges involving that module
    so its total strength equals max_ratio × mean.

    Args:
        syn_vals: synaptic weight tensor (modified in-place)
        edge_syn_idx: (pre_mod, post_mod) -> synapse indices
        inter_module_edges: list of inter-module edge tuples
        max_ratio: maximum allowed ratio over mean strength

    Returns:
        dict with surgery report (modules_suppressed, scale_factors, etc.)
    """
    strengths = _compute_module_edge_strength(syn_vals, edge_syn_idx, inter_module_edges)
    mean_strength = np.mean(list(strengths.values()))
    threshold = max_ratio * mean_strength

    suppressed = {}
    for mod, strength in strengths.items():
        if strength > threshold:
            scale = threshold / strength
            suppressed[mod] = {"original_strength": strength, "scale_factor": float(scale)}

            # Scale down all synapses on edges involving this module
            for edge in inter_module_edges:
                if mod in edge:
                    syns = edge_syn_idx[edge]
                    syn_vals[syns] *= scale

    logger.info(
        "Flattened %d hub modules (threshold=%.0f, mean=%.0f, max_ratio=%.1f)",
        len(suppressed), threshold, mean_strength, max_ratio,
    )
    for mod, info in suppressed.items():
        logger.info(
            "  Module %d: %.0f -> %.0f (scale=%.3f)",
            mod, info["original_strength"],
            info["original_strength"] * info["scale_factor"],
            info["scale_factor"],
        )

    return {
        "operation": "flatten_hubs",
        "max_ratio": max_ratio,
        "mean_strength": float(mean_strength),
        "threshold": float(threshold),
        "modules_suppressed": {str(k): v for k, v in suppressed.items()},
    }


def swap_hubs(
    syn_vals: torch.Tensor,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
    old_hubs: list[int],
    new_hubs: list[int],
) -> dict:
    """
    Demote old hub modules and promote new ones.

    1. Measure the average strength of old hubs.
    2. Scale old hubs DOWN to average module strength.
    3. Scale new hubs UP to match the old hub strength.

    Args:
        syn_vals: synaptic weight tensor (modified in-place)
        edge_syn_idx: (pre_mod, post_mod) -> synapse indices
        inter_module_edges: list of inter-module edge tuples
        old_hubs: module IDs to demote (e.g., [4, 19])
        new_hubs: module IDs to promote (e.g., [12, 37])

    Returns:
        dict with surgery report
    """
    strengths = _compute_module_edge_strength(syn_vals, edge_syn_idx, inter_module_edges)
    all_strengths = list(strengths.values())
    mean_strength = np.mean(all_strengths)

    old_hub_strengths = {m: strengths.get(m, mean_strength) for m in old_hubs}
    new_hub_strengths = {m: strengths.get(m, mean_strength) for m in new_hubs}
    target_strength = np.mean(list(old_hub_strengths.values()))

    demotions = {}
    promotions = {}

    # Demote old hubs to average
    for mod in old_hubs:
        current = old_hub_strengths[mod]
        if current > 0:
            scale = mean_strength / current
            demotions[mod] = {"from": current, "to": mean_strength, "scale": float(scale)}
            for edge in inter_module_edges:
                if mod in edge:
                    syns = edge_syn_idx[edge]
                    syn_vals[syns] *= scale

    # Promote new hubs to old hub level
    for mod in new_hubs:
        current = new_hub_strengths[mod]
        if current > 0:
            scale = target_strength / current
            promotions[mod] = {"from": current, "to": target_strength, "scale": float(scale)}
            for edge in inter_module_edges:
                if mod in edge:
                    syns = edge_syn_idx[edge]
                    syn_vals[syns] *= scale

    logger.info(
        "Swapped hubs: %s (demoted) -> %s (promoted)",
        old_hubs, new_hubs,
    )
    return {
        "operation": "swap_hubs",
        "old_hubs": old_hubs,
        "new_hubs": new_hubs,
        "target_strength": float(target_strength),
        "mean_strength": float(mean_strength),
        "demotions": {str(k): v for k, v in demotions.items()},
        "promotions": {str(k): v for k, v in promotions.items()},
    }


def add_hubs(
    syn_vals: torch.Tensor,
    edge_syn_idx: dict[tuple[int, int], list[int]],
    inter_module_edges: list[tuple[int, int]],
    existing_hubs: list[int],
    new_hubs: list[int],
) -> dict:
    """
    Scale up additional modules to match existing hub connectivity.

    Does NOT modify existing hubs — only boosts the new ones.

    Args:
        syn_vals: synaptic weight tensor (modified in-place)
        edge_syn_idx: (pre_mod, post_mod) -> synapse indices
        inter_module_edges: list of inter-module edge tuples
        existing_hubs: current hub module IDs (e.g., [4, 19])
        new_hubs: additional modules to promote (e.g., [8, 12, 25, 37])

    Returns:
        dict with surgery report
    """
    strengths = _compute_module_edge_strength(syn_vals, edge_syn_idx, inter_module_edges)

    hub_target = np.mean([strengths.get(m, 0) for m in existing_hubs])
    promotions = {}

    for mod in new_hubs:
        current = strengths.get(mod, 0)
        if current > 0:
            scale = hub_target / current
            promotions[mod] = {"from": current, "to": hub_target, "scale": float(scale)}
            for edge in inter_module_edges:
                if mod in edge:
                    syns = edge_syn_idx[edge]
                    syn_vals[syns] *= scale

    logger.info(
        "Added %d hubs: %s (existing: %s, target_strength=%.0f)",
        len(new_hubs), new_hubs, existing_hubs, hub_target,
    )
    return {
        "operation": "add_hubs",
        "existing_hubs": existing_hubs,
        "new_hubs": new_hubs,
        "target_strength": float(hub_target),
        "promotions": {str(k): v for k, v in promotions.items()},
    }
