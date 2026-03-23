"""
Connectome Analysis Script (AGENT MODIFIES THIS FILE)
=====================================================

This is the file the autoresearch agent modifies.
Each experiment should:
1. State a hypothesis
2. Run analysis on the real connectome
3. Compare against a null model
4. Report whether the finding is significant

Usage: python analysis.py
"""

import numpy as np
import pandas as pd
import networkx as nx
from collections import Counter
from scipy import stats
import random

from prepare_connectome import (
    build_graph,
    load_cell_types,
    load_connections,
    random_graph_preserve_degree,
    shuffle_node_attributes,
    get_neurons_by_type,
    get_neurons_by_nt,
    find_hub_neurons,
    count_motifs_3node,
)

# =============================================================================
# EXPERIMENT CONFIGURATION
# =============================================================================

HYPOTHESIS = """
Hub neurons (high betweenness centrality) are more likely to be inhibitory (GABAergic)
than expected by chance. This would suggest that the brain uses inhibition as a
control mechanism at critical routing points.
"""

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# =============================================================================
# ANALYSIS
# =============================================================================

def run_analysis():
    """
    Main analysis function. Modify this to test different hypotheses.
    """
    print("=" * 60)
    print("HYPOTHESIS:")
    print(HYPOTHESIS.strip())
    print("=" * 60)
    print()

    # Load graph (min 5 synapses for cleaner signal)
    G = build_graph(min_synapses=5)

    # --- REAL DATA ANALYSIS ---
    print("Analyzing real connectome...")

    # Find hub neurons by betweenness centrality
    hubs = find_hub_neurons(G, top_k=500, metric='betweenness')

    # Get neurotransmitter for hubs
    hub_nt = [G.nodes[n].get('nt_type') for n in hubs if G.nodes[n].get('nt_type')]
    hub_nt_counts = Counter(hub_nt)

    # Get baseline NT distribution (all neurons)
    all_nt = [G.nodes[n].get('nt_type') for n in G.nodes() if G.nodes[n].get('nt_type')]
    all_nt_counts = Counter(all_nt)

    # Calculate proportions
    total_hubs = sum(hub_nt_counts.values())
    total_all = sum(all_nt_counts.values())

    hub_gaba_frac = hub_nt_counts.get('GABA', 0) / total_hubs if total_hubs > 0 else 0
    all_gaba_frac = all_nt_counts.get('GABA', 0) / total_all if total_all > 0 else 0

    print(f"\nHub neurons (top 500 by betweenness):")
    print(f"  GABA fraction: {hub_gaba_frac:.3f} ({hub_nt_counts.get('GABA', 0)}/{total_hubs})")
    print(f"\nAll neurons:")
    print(f"  GABA fraction: {all_gaba_frac:.3f} ({all_nt_counts.get('GABA', 0)}/{total_all})")

    # --- NULL MODEL COMPARISON ---
    print("\nComparing to null model (shuffled NT labels)...")

    null_gaba_fracs = []
    n_permutations = 100

    for i in range(n_permutations):
        G_shuffled = shuffle_node_attributes(G, 'nt_type', seed=RANDOM_SEED + i)
        shuffled_nt = [G_shuffled.nodes[n].get('nt_type') for n in hubs
                       if G_shuffled.nodes[n].get('nt_type')]
        shuffled_counts = Counter(shuffled_nt)
        total_shuffled = sum(shuffled_counts.values())
        if total_shuffled > 0:
            null_gaba_fracs.append(shuffled_counts.get('GABA', 0) / total_shuffled)

    null_mean = np.mean(null_gaba_fracs)
    null_std = np.std(null_gaba_fracs)

    # Z-score
    if null_std > 0:
        z_score = (hub_gaba_frac - null_mean) / null_std
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # two-tailed
    else:
        z_score = 0
        p_value = 1.0

    print(f"\nNull model (shuffled, n={n_permutations}):")
    print(f"  Mean GABA fraction: {null_mean:.3f} +/- {null_std:.3f}")
    print(f"\nStatistical test:")
    print(f"  Z-score: {z_score:.2f}")
    print(f"  P-value: {p_value:.4f}")

    # --- CONCLUSION ---
    print("\n" + "=" * 60)
    print("RESULT:")

    if p_value < 0.05:
        if hub_gaba_frac > null_mean:
            conclusion = "SIGNIFICANT: Hub neurons ARE enriched for GABA"
            is_significant = True
            is_novel = True  # This is a real finding
        else:
            conclusion = "SIGNIFICANT: Hub neurons are DEPLETED for GABA"
            is_significant = True
            is_novel = True
    else:
        conclusion = "NOT SIGNIFICANT: No enrichment detected"
        is_significant = False
        is_novel = False

    print(conclusion)
    print("=" * 60)

    # --- OUTPUT FOR LOGGING ---
    print()
    print("---")
    print(f"hypothesis: Hub neurons enriched for inhibitory NT")
    print(f"metric_real: {hub_gaba_frac:.4f}")
    print(f"metric_null: {null_mean:.4f}")
    print(f"z_score: {z_score:.2f}")
    print(f"p_value: {p_value:.4f}")
    print(f"is_significant: {is_significant}")
    print(f"is_novel: {is_novel}")
    print(f"conclusion: {conclusion}")


if __name__ == "__main__":
    run_analysis()
