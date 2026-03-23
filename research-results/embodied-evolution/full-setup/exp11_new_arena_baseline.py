"""
Experiment 11: New Arena Baseline

The arena was fixed: fly spawns at (0,0,0.3) facing AWAY (orientation=π),
food is at [0.075, 0, 0] = 75mm away. This is a genuine navigation challenge.

Prior food-distance measurements are INVALIDATED. This experiment re-establishes
the reference point for all future evolution experiments.

Expected results:
- Biological brain: negative food_dist (fly walks away from food)
- Zero brain / CPG-only: similar (walks straight away)
- A "good" brain should be near 0 (turns and finds food)

Tools: run_embodied (food_distance metric with new arena)
"""

import sys, json, os
import numpy as np
sys.path.insert(0, '/home/ubuntu/autoresearch')
from capabilities import load_connectome, run_embodied, scale_brain

os.makedirs('results', exist_ok=True)

print("=" * 60)
print("EXPERIMENT 11: NEW ARENA BASELINE")
print("Arena: fly at (0,0,0.3), facing π (away from food)")
print("Food: [0.075, 0, 0] = 75mm away")
print("=" * 60)

connectome = load_connectome()
SEEDS = [42, 123, 456, 789, 1337]
DURATION = 2.0

# ── 1. Biological brain baseline ──────────────────────────────────────────────
print("\n1. Biological brain baseline (5 seeds × 2s each)")
print("   Stimulus: lc4 (escape locomotion — most powerful signal)")
bio_results = {}
for seed in SEEDS:
    r = run_embodied(connectome, seed=seed, duration_sec=DURATION, stimulus='lc4')
    bio_results[seed] = {
        'food_dist': float(r['food_distance']),
        'dist_traveled': float(r.get('distance_traveled', 0)),
    }
    print(f"   seed={seed}: food_dist={bio_results[seed]['food_dist']:.4f}m  "
          f"traveled={bio_results[seed]['dist_traveled']:.4f}m")

bio_food_dists = [v['food_dist'] for v in bio_results.values()]
bio_mean = float(np.mean(bio_food_dists))
bio_std  = float(np.std(bio_food_dists))
print(f"   Mean food_dist: {bio_mean:.4f}m ± {bio_std:.4f}m")

# ── 2. Sugar stimulus (should be ~zero locomotion → stays near start) ─────────
print("\n2. Biological brain + sugar stimulus (5 seeds)")
sugar_results = {}
for seed in SEEDS:
    r = run_embodied(connectome, seed=seed, duration_sec=DURATION, stimulus='sugar')
    sugar_results[seed] = {
        'food_dist': float(r['food_distance']),
        'dist_traveled': float(r.get('distance_traveled', 0)),
    }
    print(f"   seed={seed}: food_dist={sugar_results[seed]['food_dist']:.4f}m  "
          f"traveled={sugar_results[seed]['dist_traveled']:.4f}m")

sugar_food_dists = [v['food_dist'] for v in sugar_results.values()]
sugar_mean = float(np.mean(sugar_food_dists))
sugar_std  = float(np.std(sugar_food_dists))
print(f"   Mean food_dist: {sugar_mean:.4f}m ± {sugar_std:.4f}m")

# ── 3. P9 stimulus ────────────────────────────────────────────────────────────
print("\n3. Biological brain + p9 stimulus (5 seeds)")
p9_results = {}
for seed in SEEDS:
    r = run_embodied(connectome, seed=seed, duration_sec=DURATION, stimulus='p9')
    p9_results[seed] = {
        'food_dist': float(r['food_distance']),
        'dist_traveled': float(r.get('distance_traveled', 0)),
    }
    print(f"   seed={seed}: food_dist={p9_results[seed]['food_dist']:.4f}m  "
          f"traveled={p9_results[seed]['dist_traveled']:.4f}m")

p9_food_dists = [v['food_dist'] for v in p9_results.values()]
p9_mean = float(np.mean(p9_food_dists))
p9_std  = float(np.std(p9_food_dists))
print(f"   Mean food_dist: {p9_mean:.4f}m ± {p9_std:.4f}m")

# ── 4. Half-brain baseline (best from Exp 9) ──────────────────────────────────
print("\n4. Half-brain (50% neurons, seed=42) + lc4 (2 seeds)")
half_brain = scale_brain(connectome, 0.5, seed=42)
half_results = {}
for seed in [42, 789]:
    r = run_embodied(half_brain, seed=seed, duration_sec=DURATION, stimulus='lc4')
    half_results[seed] = {
        'food_dist': float(r['food_distance']),
        'dist_traveled': float(r.get('distance_traveled', 0)),
    }
    print(f"   seed={seed}: food_dist={half_results[seed]['food_dist']:.4f}m  "
          f"traveled={half_results[seed]['dist_traveled']:.4f}m")

half_food_dists = [v['food_dist'] for v in half_results.values()]
half_mean = float(np.mean(half_food_dists))

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("NEW ARENA BASELINE SUMMARY")
print("=" * 60)
print(f"{'Brain':>20} {'Stimulus':>8} {'Mean food_dist':>15} {'Interpretation'}")
print(f"{'Full bio':>20} {'lc4':>8} {bio_mean:>14.4f}m  ", end='')
if bio_mean < -0.05:
    print("walks AWAY from food (expected)")
elif bio_mean < 0.01:
    print("stays near start")
else:
    print("approaches food (SURPRISING)")

print(f"{'Full bio':>20} {'sugar':>8} {sugar_mean:>14.4f}m")
print(f"{'Full bio':>20} {'p9':>8} {p9_mean:>14.4f}m")
print(f"{'Half bio':>20} {'lc4':>8} {half_mean:>14.4f}m")
print(f"\nFood starts 75mm = 0.075m away.")
print(f"Random walk towards food: ~0.0 (50/50 chance)")
print(f"LC4 escape: should walk AWAY → negative food_dist")

output = {
    'experiment': 'new_arena_baseline',
    'arena': {
        'spawn_pos': [0.0, 0.0, 0.3],
        'spawn_orientation_rad': 3.14159,
        'food_pos': [0.075, 0.0, 0.0],
        'food_dist_initial': 0.075,
    },
    'duration_sec': DURATION,
    'seeds': SEEDS,
    'biological_lc4': {
        'per_seed': bio_results,
        'mean_food_dist': bio_mean,
        'std_food_dist': bio_std,
    },
    'biological_sugar': {
        'per_seed': sugar_results,
        'mean_food_dist': sugar_mean,
        'std_food_dist': sugar_std,
    },
    'biological_p9': {
        'per_seed': p9_results,
        'mean_food_dist': p9_mean,
        'std_food_dist': p9_std,
    },
    'half_brain_lc4': {
        'per_seed': half_results,
        'mean_food_dist': half_mean,
    },
}

with open('results/exp11_new_arena_baseline.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\nSaved: results/exp11_new_arena_baseline.json")
print("=" * 60)
