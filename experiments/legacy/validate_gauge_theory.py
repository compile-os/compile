#!/usr/bin/env python3
"""
Validate Gauge Theory Hypothesis:
Do beneficial mutations preferentially occur in connections involving critical modules?
"""

import numpy as np
import pandas as pd
from scipy import stats
import json
import sys
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")

print("=" * 60)
print("GAUGE THEORY VALIDATION EXPERIMENT")
print("=" * 60)

# Load gauge theory results
print("\n1. Loading gauge theory results...")
module_labels = np.load("/home/ubuntu/module_labels_v2.npy")
critical_score = np.load("/home/ubuntu/critical_score_v2.npy") if __import__("os").path.exists("/home/ubuntu/critical_score_v2.npy") else np.load("/home/ubuntu/critical_score.npy")
module_holonomy = np.load("/home/ubuntu/module_holonomy_v2.npy")

n_modules = len(critical_score)
print(f"   Modules: {n_modules}")
print(f"   Critical scores: min={critical_score.min():.4f}, max={critical_score.max():.4f}")

# Identify critical modules (top 20%)
threshold = np.percentile(critical_score, 80)
critical_modules = set(np.where(critical_score >= threshold)[0])
print(f"   Critical modules (top 20%): {sorted(critical_modules)}")

# Load connectome
print("\n2. Loading FlyWire connectome...")
df = pd.read_parquet("/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet")
print(f"   Connections: {len(df):,}")

# Map neurons to modules
print("\n3. Mapping connections to modules...")
n_neurons = len(module_labels)
pre_idx = df["Presynaptic_Index"].values
post_idx = df["Postsynaptic_Index"].values

# Filter valid indices
valid_mask = (pre_idx < n_neurons) & (post_idx < n_neurons)
pre_idx = pre_idx[valid_mask]
post_idx = post_idx[valid_mask]
valid_indices = np.where(valid_mask)[0]

pre_modules = module_labels[pre_idx]
post_modules = module_labels[post_idx]

# Classify connections
is_inter_module = pre_modules != post_modules
is_critical_connection = np.array([
    (pre_modules[i] in critical_modules or post_modules[i] in critical_modules)
    for i in range(len(pre_modules))
])

n_inter = is_inter_module.sum()
n_critical = (is_inter_module & is_critical_connection).sum()
n_non_critical = (is_inter_module & ~is_critical_connection).sum()

print(f"   Inter-module connections: {n_inter:,}")
print(f"   Critical module connections: {n_critical:,} ({100*n_critical/n_inter:.1f}%)")
print(f"   Non-critical connections: {n_non_critical:,} ({100*n_non_critical/n_inter:.1f}%)")

# Expected proportion if random
p_critical_expected = n_critical / n_inter
print(f"   Expected critical proportion (null): {p_critical_expected:.4f}")

# Simulate evolution: run multiple trials of mutation
print("\n4. Running evolution simulation...")
print("   (Testing if beneficial mutations cluster in critical connections)")

np.random.seed(42)
N_MUTATIONS = 100  # Per trial
N_TRIALS = 100     # Number of evolution trials
N_GENERATIONS = 10

# For each trial: mutate, evaluate, track which connections were in beneficial mutations
# Simplified: we test if randomly selected "beneficial" mutations cluster in critical connections

inter_module_indices = valid_indices[is_inter_module]
critical_flags = is_critical_connection[is_inter_module]

results = {
    "trials": [],
    "critical_mutation_counts": [],
    "total_mutations": []
}

for trial in range(N_TRIALS):
    # Simulate hill-climbing evolution
    beneficial_in_critical = 0
    beneficial_total = 0
    
    for gen in range(N_GENERATIONS):
        # Random mutations
        mutation_indices = np.random.choice(len(inter_module_indices), N_MUTATIONS, replace=False)
        
        # Simulate: ~30% of mutations are "beneficial" (matching observed 31% improvement)
        # In reality this depends on fitness evaluation
        n_beneficial = int(N_MUTATIONS * 0.05)  # ~5% beneficial per generation
        beneficial_mask = np.zeros(N_MUTATIONS, dtype=bool)
        beneficial_mask[:n_beneficial] = True
        np.random.shuffle(beneficial_mask)
        
        # Count how many beneficial mutations were in critical connections
        for i, is_beneficial in enumerate(beneficial_mask):
            if is_beneficial:
                beneficial_total += 1
                if critical_flags[mutation_indices[i]]:
                    beneficial_in_critical += 1
    
    results["trials"].append(trial)
    results["critical_mutation_counts"].append(beneficial_in_critical)
    results["total_mutations"].append(beneficial_total)

# Statistical analysis
print("\n5. Statistical Analysis...")
observed_critical_rate = np.mean(results["critical_mutation_counts"]) / np.mean(results["total_mutations"])
expected_critical_rate = p_critical_expected

print(f"   Observed critical mutation rate: {observed_critical_rate:.4f}")
print(f"   Expected (null hypothesis): {expected_critical_rate:.4f}")

# Binomial test for each trial
p_values = []
for i in range(N_TRIALS):
    k = results["critical_mutation_counts"][i]
    n = results["total_mutations"][i]
    # One-sided test: are critical mutations MORE common than expected?
    p_val = 1 - stats.binom.cdf(k-1, n, expected_critical_rate)
    p_values.append(p_val)

mean_p = np.mean(p_values)
significant_trials = sum(1 for p in p_values if p < 0.05)

print(f"   Mean p-value: {mean_p:.4f}")
print(f"   Significant trials (p < 0.05): {significant_trials}/{N_TRIALS}")

# The key test: chi-squared
print("\n6. Chi-Squared Test (Aggregate)...")
total_beneficial = sum(results["total_mutations"])
total_in_critical = sum(results["critical_mutation_counts"])
total_in_non_critical = total_beneficial - total_in_critical

expected_in_critical = total_beneficial * expected_critical_rate
expected_in_non_critical = total_beneficial * (1 - expected_critical_rate)

chi2, p_chi = stats.chisquare(
    [total_in_critical, total_in_non_critical],
    [expected_in_critical, expected_in_non_critical]
)

print(f"   Chi-squared: {chi2:.2f}")
print(f"   P-value: {p_chi:.6f}")
print(f"   Significant: {YES if p_chi < 0.05 else NO}")

# Key insight
print("\n" + "=" * 60)
print("INTERPRETATION")
print("=" * 60)

if abs(observed_critical_rate - expected_critical_rate) < 0.01:
    print("""
Under RANDOM mutation selection, mutations occur in critical
and non-critical connections at the EXPECTED rate.

This is the NULL HYPOTHESIS baseline.

To validate gauge theory: we need ACTUAL evolution results
where beneficial mutations are SELECTED by fitness, not random.

If beneficial mutations cluster in critical modules MORE than
expected under random selection, gauge theory is supported.
""")
else:
    direction = "MORE" if observed_critical_rate > expected_critical_rate else "LESS"
    print(f"""
Mutations occur in critical connections {direction} than expected.
Observed: {observed_critical_rate:.4f} vs Expected: {expected_critical_rate:.4f}
""")

# Save results
results_summary = {
    "n_modules": int(n_modules),
    "critical_modules": list(map(int, sorted(critical_modules))),
    "n_connections": int(len(df)),
    "n_inter_module": int(n_inter),
    "n_critical_connections": int(n_critical),
    "p_critical_expected": float(expected_critical_rate),
    "observed_critical_rate": float(observed_critical_rate),
    "chi2": float(chi2),
    "p_value": float(p_chi),
    "interpretation": "NULL_BASELINE - random mutations show expected distribution"
}

with open("/home/ubuntu/gauge_validation_results.json", "w") as f:
    json.dump(results_summary, f, indent=2)

print("\nResults saved to /home/ubuntu/gauge_validation_results.json")
print("=" * 60)
