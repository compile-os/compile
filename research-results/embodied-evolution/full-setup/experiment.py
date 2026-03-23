"""
Experiment 10: Evolve Compressed Brain → Transplant to Full Brain

The 50% brain already outperforms full brain (18.99m vs 18.69m).
Can we evolve it further? And do those mutations benefit the full brain?

Pipeline: scale_brain(0.5) → mutate → eval → transplant → compare

Tools: scale_brain + mutate + run_embodied_locomotion + transplant + compete
"""

import sys, json, os, time
import numpy as np
sys.path.insert(0, '/home/ubuntu/autoresearch')
from capabilities import (load_connectome, scale_brain, mutate,
                           run_embodied_locomotion, transplant, run_embodied)

os.makedirs('results', exist_ok=True)

print("=" * 60)
print("EXPERIMENT 10: EVOLVE COMPRESSED BRAIN → TRANSPLANT")
print("=" * 60)

connectome = load_connectome()
STIM = 'lc4'
SEEDS = [42, 789]
DURATION = 1.0

# Create compressed (50% neurons) brain
print("\nCreating 50%-neuron brain...")
half_brain = scale_brain(connectome, 0.5, seed=42)
print(f"  Synapses: {len(half_brain):,} ({len(half_brain)/len(connectome)*100:.1f}%)")

def eval_loco(df, seeds=SEEDS):
    dists = [run_embodied_locomotion(df, seed=s, duration_sec=DURATION, stimulus=STIM)
             ['distance_traveled'] for s in seeds]
    return float(np.mean(dists))

# Baselines
print("\nBaselines:")
full_baseline = eval_loco(connectome)
half_baseline = eval_loco(half_brain)
print(f"  Full brain: {full_baseline:.4f}m")
print(f"  Half brain: {half_baseline:.4f}m  (+{(half_baseline-full_baseline)/full_baseline*100:+.1f}%)")

# Evolve half brain for 2 generations
print(f"\nEvolving half brain (2 gen × 3 cands × {len(SEEDS)} seeds)...")
N_GEN = 2
N_CANDS = 3
N_MUT = 500

best_half = half_brain.copy()
best_score = half_baseline
evolution_log = [{'gen': 0, 'score': half_baseline, 'improved': False}]

for gen in range(1, N_GEN + 1):
    print(f"\n  Gen {gen}/{N_GEN}:")
    gen_best = None
    gen_score = -999
    for i in range(N_CANDS):
        cand, idxs = mutate(best_half, n_mutations=N_MUT, seed=gen*100+i)
        score = eval_loco(cand)
        print(f"    Cand {i+1}: {score:.4f}m")
        if score > gen_score:
            gen_score = score
            gen_best = cand
            gen_idxs = idxs
    improved = gen_score > best_score
    if improved:
        best_half = gen_best
        best_score = gen_score
        print(f"  >> NEW BEST: {best_score:.4f}m")
    else:
        print(f"  >> No improvement (best={gen_score:.4f}m, was={best_score:.4f}m)")
    evolution_log.append({'gen': gen, 'score': float(gen_score), 'improved': bool(improved)})

print(f"\nEvolution result: {half_baseline:.4f} → {best_score:.4f}m "
      f"({(best_score-half_baseline)/half_baseline*100:+.1f}%)")

# Transplant mutations from best compressed brain back to full brain
print(f"\nTransplanting evolved mutations to full brain...")
weight_col = 'Excitatory x Connectivity'
half_orig = scale_brain(connectome, 0.5, seed=42)  # Fresh half brain (same random seed)

# Find which synapses changed in best_half vs half_orig
orig_w = half_orig[weight_col].values
best_w = best_half[weight_col].values
changed_mask = orig_w != best_w
changed_idxs = np.where(changed_mask)[0].tolist()
print(f"  Changed synapses in evolved half: {len(changed_idxs)}")

if len(changed_idxs) > 0:
    # Map changed indices to full connectome: find matching rows
    # The half brain's rows are a subset of the full brain's rows
    # We need to find which rows in the full connectome correspond to changed rows in half brain
    # Note: scale_brain keeps rows where both pre AND post are in 'keep' set
    # The order may differ, so we need to match by Presynaptic_ID and Postsynaptic_ID

    # Approach: get pre/post IDs from half_brain changed rows
    pre_col = 'Presynaptic_ID'
    post_col = 'Postsynaptic_ID'

    changed_rows_half = best_half.iloc[changed_idxs]
    changed_pre = set(zip(changed_rows_half[pre_col].values,
                           changed_rows_half[post_col].values))

    # Find matching rows in full connectome
    full_pre_post = set(zip(connectome[pre_col].values, connectome[post_col].values))
    match_count = len(changed_pre & full_pre_post)
    print(f"  Matching rows in full brain: {match_count}/{len(changed_idxs)}")

    if match_count > 0:
        # Build a mapping: (pre_id, post_id) → new weight
        weight_map = {}
        for i in changed_idxs:
            row = best_half.iloc[i]
            weight_map[(row[pre_col], row[post_col])] = row[weight_col]

        # Apply to full brain
        full_evolved = connectome.copy()
        for idx, row in connectome.iterrows():
            key = (row[pre_col], row[post_col])
            if key in weight_map:
                full_evolved.at[idx, weight_col] = weight_map[key]

        print(f"  Applied {len(weight_map)} mutations to full brain")
        full_evolved_score = eval_loco(full_evolved)
        transplant_improvement = (full_evolved_score - full_baseline) / full_baseline * 100
        print(f"  Full evolved score: {full_evolved_score:.4f}m ({transplant_improvement:+.1f}%)")
    else:
        full_evolved_score = None
        transplant_improvement = None
        print("  No matching rows found — transplant not applicable")
else:
    full_evolved_score = None
    transplant_improvement = None
    print("  No evolved mutations to transplant")

# Final competition summary
print("\n" + "=" * 60)
print("FINAL COMPETITION RESULTS")
print("=" * 60)
print(f"{'Brain':>20} {'LC4 Dist':>10} {'vs Full':>10}")
print(f"{'Full biological':>20} {full_baseline:>10.4f} {'(baseline)':>10}")
print(f"{'Half biological':>20} {half_baseline:>10.4f} {(half_baseline-full_baseline)/full_baseline*100:>+9.1f}%")
print(f"{'Half evolved':>20} {best_score:>10.4f} {(best_score-full_baseline)/full_baseline*100:>+9.1f}%")
if full_evolved_score is not None:
    print(f"{'Full + transplant':>20} {full_evolved_score:>10.4f} {transplant_improvement:>+9.1f}%")

import json as _json
class SafeEncoder(_json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.floating, np.integer)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, bool):
            return int(obj)
        return super().default(obj)

output = {
    'experiment': 'evolve_compressed_transplant',
    'stimulus': STIM, 'seeds': SEEDS, 'duration': DURATION,
    'full_baseline': float(full_baseline),
    'half_baseline': float(half_baseline),
    'half_evolved': float(best_score),
    'half_evolution_log': evolution_log,
    'transplant': {
        'changed_synapses': len(changed_idxs),
        'full_evolved_score': float(full_evolved_score) if full_evolved_score else None,
        'improvement_pct': float(transplant_improvement) if transplant_improvement else None,
    },
}

with open('results/exp10_compressed_evolution.json', 'w') as f:
    _json.dump(output, f, indent=2, cls=SafeEncoder)

print("\nSaved: results/exp10_compressed_evolution.json")
print("=" * 60)
