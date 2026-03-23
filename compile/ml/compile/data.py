"""
Connectome data loading utilities.

All file paths are resolved through a configurable DATA_DIR, defaulting
to ``data/`` relative to the working directory.  Override with::

    export COMPILE_DATA_DIR=/path/to/flywire/data

This replaces the hardcoded ``/home/ubuntu/fly-brain-embodied/data/``
paths that were previously scattered across every experiment script.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data directory resolution
# ---------------------------------------------------------------------------

_DATA_DIR_CANDIDATES = [
    os.environ.get("COMPILE_DATA_DIR", ""),
    "data",
    "latent/ml/data",
]


def get_data_dir() -> Path:
    """Return the first existing data directory from candidates."""
    for candidate in _DATA_DIR_CANDIDATES:
        if candidate and Path(candidate).is_dir():
            return Path(candidate)
    raise FileNotFoundError(
        "Cannot find connectome data directory. Set COMPILE_DATA_DIR environment "
        "variable or place data files in ./data/. Required files:\n"
        "  - 2025_Connectivity_783.parquet\n"
        "  - 2025_Completeness_783.csv\n"
        "  - flywire_annotations.tsv\n"
        "Download from https://flywire.ai"
    )


def _resolve_path(filename: str, data_dir: Optional[Path] = None) -> Path:
    """Resolve a data filename to its full path."""
    if data_dir is None:
        data_dir = get_data_dir()
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Core loaders
# ---------------------------------------------------------------------------

def load_connectome(data_dir: Optional[Path] = None):
    """
    Load the FlyWire v783 connectome.

    Returns:
        df_conn: DataFrame with columns Presynaptic_Index, Postsynaptic_Index,
                 Excitatory x Connectivity
        df_comp: DataFrame indexed by root_id with completeness scores
        num_neurons: int, total number of neurons
    """
    data_dir = Path(data_dir) if data_dir else get_data_dir()

    conn_path = _resolve_path("2025_Connectivity_783.parquet", data_dir)
    comp_path = _resolve_path("2025_Completeness_783.csv", data_dir)

    logger.info("Loading connectome from %s", data_dir)
    df_conn = pd.read_parquet(conn_path)
    df_comp = pd.read_csv(comp_path, index_col=0)
    num_neurons = len(df_comp)

    # Validate index bounds
    pre = df_conn["Presynaptic_Index"].values
    post = df_conn["Postsynaptic_Index"].values
    if pre.max() >= num_neurons or post.max() >= num_neurons:
        raise ValueError(
            f"Connectivity indices out of bounds: max pre={pre.max()}, "
            f"max post={post.max()}, but only {num_neurons} neurons in "
            f"completeness matrix. Data files may be version-mismatched."
        )
    if pre.min() < 0 or post.min() < 0:
        raise ValueError(
            f"Negative connectivity indices found: min pre={pre.min()}, "
            f"min post={post.min()}. Data may be corrupted."
        )

    logger.info("Loaded %d neurons, %d synapses", num_neurons, len(df_conn))

    return df_conn, df_comp, num_neurons


def load_annotations(data_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Load FlyWire neuron annotations (cell class, neurotransmitter, hemilineage).

    Returns:
        DataFrame with columns: root_id, cell_class, top_nt,
        ito_lee_hemilineage, super_class, ...
    """
    data_dir = Path(data_dir) if data_dir else get_data_dir()
    ann_path = _resolve_path("flywire_annotations.tsv", data_dir)
    logger.info("Loading annotations from %s", ann_path)
    return pd.read_csv(ann_path, sep="\t", low_memory=False)


def load_module_labels(path: Optional[str] = None) -> np.ndarray:
    """
    Load module label assignments for each neuron.

    Returns:
        1D array of shape (num_neurons,) with integer module labels.
    """
    if path is None:
        # Try standard locations, including COMPILE_DATA_DIR
        data_dir = os.environ.get("COMPILE_DATA_DIR", "")
        candidates = [
            os.environ.get("COMPILE_MODULE_LABELS", ""),
            os.path.join(data_dir, "module_labels_v2.npy") if data_dir else "",
            "data/module_labels_v2.npy",
            "module_labels_v2.npy",
        ]
        for c in candidates:
            if c and Path(c).exists():
                path = c
                break
        else:
            raise FileNotFoundError(
                "Cannot find module_labels_v2.npy. This file contains spectral "
                "clustering module assignments for each neuron in the v783 connectome.\n"
                "Set COMPILE_MODULE_LABELS=/path/to/module_labels_v2.npy or place "
                "in ./data/\n"
                "See DATA.md for details on how to obtain or regenerate this file."
            )

    logger.info("Loading module labels from %s", path)
    return np.load(path)


# ---------------------------------------------------------------------------
# Annotation mappings (convenience)
# ---------------------------------------------------------------------------

def build_annotation_maps(ann: pd.DataFrame) -> dict:
    """
    Build lookup dictionaries from annotation DataFrame.

    Returns:
        dict with keys: rid_to_hemi, rid_to_class, rid_to_nt, rid_to_super
    """
    rid = ann["root_id"].astype(str)
    return {
        "rid_to_hemi": dict(zip(rid, ann["ito_lee_hemilineage"].fillna("unknown"))),
        "rid_to_class": dict(zip(rid, ann["cell_class"].fillna("unknown"))),
        "rid_to_nt": dict(zip(rid, ann["top_nt"].fillna("unknown"))),
        "rid_to_super": dict(zip(rid, ann["super_class"].fillna("unknown"))),
    }


# ---------------------------------------------------------------------------
# Edge-synapse index (for evolution)
# ---------------------------------------------------------------------------

def build_edge_synapse_index(df_conn: pd.DataFrame, labels: np.ndarray):
    """
    Build mapping from inter-module edges to synapse indices.

    Args:
        df_conn: connectivity DataFrame
        labels: per-neuron module labels

    Returns:
        edge_syn_idx: dict mapping (pre_module, post_module) -> list of synapse indices
        inter_module_edges: list of (pre_module, post_module) tuples where pre != post
    """
    pre_mods = labels[df_conn["Presynaptic_Index"].values].astype(int)
    post_mods = labels[df_conn["Postsynaptic_Index"].values].astype(int)

    edge_syn_idx: dict[tuple[int, int], list[int]] = {}
    for i in range(len(df_conn)):
        edge = (int(pre_mods[i]), int(post_mods[i]))
        if edge not in edge_syn_idx:
            edge_syn_idx[edge] = []
        edge_syn_idx[edge].append(i)

    inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]
    logger.info("Built edge index: %d inter-module edges", len(inter_module_edges))

    return edge_syn_idx, inter_module_edges
