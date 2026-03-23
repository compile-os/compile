"""
FlyWire Connectome Data & Utilities (READ-ONLY)
================================================

DO NOT MODIFY THIS FILE. It contains:
1. Data loading for FlyWire connectome (neurons + connections)
2. Graph construction with NetworkX
3. Null model generation for statistical comparison
4. Utility functions for common analyses

The autoresearch agent only modifies analysis.py.
"""

import os
import pandas as pd
import networkx as nx
import numpy as np
from pathlib import Path
from collections import Counter
import random

# =============================================================================
# CONSTANTS - DO NOT MODIFY
# =============================================================================

DATA_DIR = Path(os.environ.get('CONNECTOME_DATA_DIR',
    Path.home() / 'neurodata' / 'flywire' / 'FAFB_v783'))

CELL_TYPES_FILE = DATA_DIR / 'consolidated_cell_types.csv.gz'
CLASSIFICATION_FILE = DATA_DIR / 'classification.csv.gz'
NEURONS_FILE = DATA_DIR / 'neurons.csv.gz'
CONNECTIONS_FILE = DATA_DIR / 'connections_princeton_no_threshold.csv.gz'

# =============================================================================
# DATA LOADING
# =============================================================================

_cache = {}

def load_cell_types() -> pd.DataFrame:
    """
    Load neuron metadata by merging multiple source files.

    Merged columns:
    - root_id: unique neuron identifier
    - primary_type: cell type (e.g., 'T4b', 'LC10', 'DNa02')
    - super_class: broad category ('optic', 'central', 'sensory', etc.)
    - cell_class: intermediate category
    - sub_class: detailed category
    - nt_type: neurotransmitter ('GABA', 'ACH', 'GLUT', etc.)
    - side: 'left', 'right', 'center'
    - flow: 'intrinsic', 'input', 'output'
    """
    if 'cell_types' not in _cache:
        print(f"Loading cell types...")

        # Load consolidated cell types (primary_type)
        types_df = pd.read_csv(CELL_TYPES_FILE)
        print(f"  Cell types: {len(types_df)} neurons")

        # Load classification (super_class, class, sub_class, side, flow)
        if CLASSIFICATION_FILE.exists():
            class_df = pd.read_csv(CLASSIFICATION_FILE)
            class_df = class_df.rename(columns={'class': 'cell_class'})
            types_df = types_df.merge(class_df, on='root_id', how='left')
            print(f"  + Classification: {len(class_df)} entries")

        # Load neurons (nt_type, neurotransmitter scores)
        if NEURONS_FILE.exists():
            neurons_df = pd.read_csv(NEURONS_FILE)
            # Keep only key columns
            nt_cols = ['root_id', 'nt_type', 'nt_type_score', 'group']
            neurons_df = neurons_df[[c for c in nt_cols if c in neurons_df.columns]]
            types_df = types_df.merge(neurons_df, on='root_id', how='left')
            print(f"  + Neurons: {len(neurons_df)} entries")

        print(f"  Final merged: {len(types_df)} neurons, {len(types_df.columns)} columns")
        _cache['cell_types'] = types_df

    return _cache['cell_types']


def load_connections() -> pd.DataFrame:
    """
    Load synaptic connections.

    Columns:
    - pre_root_id: presynaptic (source) neuron
    - post_root_id: postsynaptic (target) neuron
    - syn_count: number of synapses
    - neuropil: brain region where connection occurs
    - nt_type: neurotransmitter type
    """
    if 'connections' not in _cache:
        print(f"Loading connections from {CONNECTIONS_FILE}...")
        _cache['connections'] = pd.read_csv(CONNECTIONS_FILE)
        print(f"  Loaded {len(_cache['connections'])} connections")
    return _cache['connections']


def build_graph(min_synapses: int = 1) -> nx.DiGraph:
    """
    Build directed graph from connectome data.

    Args:
        min_synapses: minimum synapse count to include edge (default 1)

    Returns:
        NetworkX DiGraph with:
        - Node attributes: primary_type, super_class, nt_type, side, cell_class, etc.
        - Edge attributes: syn_count, neuropil, nt_type
    """
    cache_key = f'graph_{min_synapses}'
    if cache_key not in _cache:
        print(f"Building graph (min_synapses={min_synapses})...")

        types_df = load_cell_types()
        conns_df = load_connections()

        # Filter by synapse count
        if min_synapses > 1:
            conns_df = conns_df[conns_df['syn_count'] >= min_synapses]

        G = nx.DiGraph()

        # Add nodes with attributes
        type_cols = ['root_id', 'primary_type', 'super_class', 'cell_class',
                     'sub_class', 'nt_type', 'side', 'flow', 'group']
        available_cols = [c for c in type_cols if c in types_df.columns]

        for _, row in types_df[available_cols].iterrows():
            attrs = {k: row[k] for k in available_cols if k != 'root_id' and pd.notna(row[k])}
            G.add_node(row['root_id'], **attrs)

        # Add edges with attributes
        edge_cols = ['pre_root_id', 'post_root_id', 'syn_count', 'neuropil', 'nt_type']
        available_edge_cols = [c for c in edge_cols if c in conns_df.columns]

        for _, row in conns_df[available_edge_cols].iterrows():
            attrs = {k: row[k] for k in available_edge_cols
                    if k not in ['pre_root_id', 'post_root_id'] and pd.notna(row[k])}
            G.add_edge(row['pre_root_id'], row['post_root_id'], **attrs)

        print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        _cache[cache_key] = G

    return _cache[cache_key]


# =============================================================================
# NULL MODELS FOR STATISTICAL COMPARISON
# =============================================================================

def random_graph_preserve_degree(G: nx.DiGraph, seed: int = 42) -> nx.DiGraph:
    """
    Generate random graph with same degree sequence.

    Useful null model: if a pattern exists in real graph but not in
    degree-matched random graph, the pattern is meaningful.
    """
    return nx.directed_configuration_model(
        list(d for n, d in G.in_degree()),
        list(d for n, d in G.out_degree()),
        seed=seed,
        create_using=nx.DiGraph()
    )


def random_graph_erdos_renyi(G: nx.DiGraph, seed: int = 42) -> nx.DiGraph:
    """
    Generate Erdos-Renyi random graph with same density.
    """
    n = G.number_of_nodes()
    p = G.number_of_edges() / (n * (n - 1))
    return nx.erdos_renyi_graph(n, p, directed=True, seed=seed)


def shuffle_node_attributes(G: nx.DiGraph, attr: str, seed: int = 42) -> nx.DiGraph:
    """
    Create copy of graph with shuffled node attribute.

    Useful null model: if cell_type predicts connectivity, shuffling
    cell_type should destroy the pattern.
    """
    random.seed(seed)
    G_shuffled = G.copy()

    values = [G.nodes[n].get(attr) for n in G.nodes()]
    random.shuffle(values)

    for i, n in enumerate(G_shuffled.nodes()):
        G_shuffled.nodes[n][attr] = values[i]

    return G_shuffled


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_neurons_by_type(G: nx.DiGraph, cell_type: str) -> list:
    """Get all neuron IDs of a specific cell type (primary_type)."""
    return [n for n in G.nodes() if G.nodes[n].get('primary_type') == cell_type]


def get_neurons_by_superclass(G: nx.DiGraph, super_class: str) -> list:
    """Get all neuron IDs of a specific super_class."""
    return [n for n in G.nodes() if G.nodes[n].get('super_class') == super_class]


def get_neurons_by_region(G: nx.DiGraph, group: str) -> list:
    """Get all neuron IDs in a specific brain region (group)."""
    return [n for n in G.nodes() if G.nodes[n].get('group') == group]


def get_neurons_by_nt(G: nx.DiGraph, nt_type: str) -> list:
    """Get all neurons using a specific neurotransmitter."""
    return [n for n in G.nodes() if G.nodes[n].get('nt_type') == nt_type]


def subgraph_by_region(G: nx.DiGraph, neuropil: str) -> nx.DiGraph:
    """Extract subgraph of neurons in a specific brain region."""
    nodes = get_neurons_by_region(G, neuropil)
    return G.subgraph(nodes).copy()


def count_motifs_3node(G: nx.DiGraph, sample_size: int = 10000) -> dict:
    """
    Count 3-node motifs in graph (sampled for speed).

    Returns dict mapping motif pattern to count.
    Motif patterns: 'chain', 'mutual', 'fan_in', 'fan_out', 'cycle', etc.
    """
    motifs = Counter()
    nodes = list(G.nodes())

    for _ in range(sample_size):
        # Sample 3 random nodes
        if len(nodes) < 3:
            break
        sample = random.sample(nodes, 3)
        a, b, c = sample

        # Check all possible edges
        edges = (
            G.has_edge(a, b), G.has_edge(b, a),
            G.has_edge(b, c), G.has_edge(c, b),
            G.has_edge(a, c), G.has_edge(c, a)
        )

        # Classify pattern
        edge_count = sum(edges)
        if edge_count == 0:
            motifs['empty'] += 1
        elif edge_count == 1:
            motifs['single'] += 1
        elif edge_count == 2:
            if edges[0] and edges[1]:  # a <-> b
                motifs['mutual_pair'] += 1
            elif (edges[0] and edges[2]) or (edges[1] and edges[4]):  # chain
                motifs['chain'] += 1
            elif (edges[0] and edges[4]) or (edges[2] and edges[4]):  # fan out
                motifs['fan_out'] += 1
            elif (edges[1] and edges[5]) or (edges[3] and edges[5]):  # fan in
                motifs['fan_in'] += 1
            else:
                motifs['other_2'] += 1
        elif edge_count == 3:
            if edges[0] and edges[2] and edges[4]:  # a->b->c->a would be cycle but this is a->b, b->c, a->c
                motifs['feedforward'] += 1
            else:
                motifs['3_edges'] += 1
        else:
            motifs[f'{edge_count}_edges'] += 1

    return dict(motifs)


def compute_centrality_metrics(G: nx.DiGraph) -> pd.DataFrame:
    """
    Compute various centrality metrics for all nodes.

    Returns DataFrame with columns: node, in_degree, out_degree,
    betweenness, pagerank, etc.
    """
    print("Computing centrality metrics...")

    metrics = {
        'node': list(G.nodes()),
        'in_degree': [d for n, d in G.in_degree()],
        'out_degree': [d for n, d in G.out_degree()],
    }

    # PageRank (fast)
    pr = nx.pagerank(G, max_iter=100)
    metrics['pagerank'] = [pr.get(n, 0) for n in G.nodes()]

    # Betweenness (slow - sample for large graphs)
    if G.number_of_nodes() > 5000:
        bc = nx.betweenness_centrality(G, k=1000)
    else:
        bc = nx.betweenness_centrality(G)
    metrics['betweenness'] = [bc.get(n, 0) for n in G.nodes()]

    return pd.DataFrame(metrics)


def find_hub_neurons(G: nx.DiGraph, top_k: int = 100, metric: str = 'pagerank') -> list:
    """
    Find the top hub neurons by specified metric.

    Args:
        G: graph
        top_k: number of hubs to return
        metric: 'pagerank', 'betweenness', 'in_degree', 'out_degree'
    """
    if metric == 'pagerank':
        scores = nx.pagerank(G, max_iter=100)
    elif metric == 'betweenness':
        scores = nx.betweenness_centrality(G, k=min(1000, G.number_of_nodes()))
    elif metric == 'in_degree':
        scores = dict(G.in_degree())
    elif metric == 'out_degree':
        scores = dict(G.out_degree())
    else:
        raise ValueError(f"Unknown metric: {metric}")

    sorted_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [n for n, s in sorted_nodes[:top_k]]


def path_analysis(G: nx.DiGraph, source_type: str, target_type: str,
                  sample_size: int = 100) -> dict:
    """
    Analyze paths between neurons of different types.

    Returns statistics about path lengths between source and target cell types.
    """
    sources = get_neurons_by_type(G, source_type)
    targets = get_neurons_by_type(G, target_type)

    if not sources or not targets:
        return {'error': 'No neurons found for specified types'}

    # Sample for speed
    if len(sources) > sample_size:
        sources = random.sample(sources, sample_size)
    if len(targets) > sample_size:
        targets = random.sample(targets, sample_size)

    path_lengths = []
    for s in sources[:10]:  # Limit computation
        for t in targets[:10]:
            try:
                length = nx.shortest_path_length(G, s, t)
                path_lengths.append(length)
            except nx.NetworkXNoPath:
                pass

    if not path_lengths:
        return {'reachable': False}

    return {
        'reachable': True,
        'mean_path_length': np.mean(path_lengths),
        'min_path_length': min(path_lengths),
        'max_path_length': max(path_lengths),
        'n_paths_found': len(path_lengths)
    }


# =============================================================================
# MAIN - Test data loading
# =============================================================================

if __name__ == "__main__":
    print("Testing connectome data loading...\n")

    types_df = load_cell_types()
    print(f"\nCell types shape: {types_df.shape}")
    print(f"Columns: {list(types_df.columns)}")

    conns_df = load_connections()
    print(f"\nConnections shape: {conns_df.shape}")
    print(f"Columns: {list(conns_df.columns)}")

    G = build_graph(min_synapses=5)
    print(f"\nGraph (min 5 synapses): {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Quick stats
    print(f"\nNeurotransmitter distribution (nodes):")
    nt_counts = Counter(nx.get_node_attributes(G, 'nt_type').values())
    for nt, count in nt_counts.most_common(10):
        print(f"  {nt}: {count}")

    print(f"\nSuper class distribution:")
    sc_counts = Counter(nx.get_node_attributes(G, 'super_class').values())
    for sc, count in sc_counts.most_common(10):
        print(f"  {sc}: {count}")

    print(f"\nSide distribution:")
    side_counts = Counter(nx.get_node_attributes(G, 'side').values())
    for side, count in side_counts.most_common():
        print(f"  {side}: {count}")

    print("\nReady for autoresearch!")
