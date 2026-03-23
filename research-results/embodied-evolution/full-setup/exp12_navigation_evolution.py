"""
Experiment 12: Navigation Evolution — New Arena

With the fixed arena (fly faces away from food 75mm away), we now have a real
navigation task. Can we evolve a brain that turns around and reaches the food?

Hypothesis: The biological brain with LC4 (escape) walks AWAY from food
(negative food_dist). We want to evolve toward food_dist → 0 (reaches food).
The trick: the fly must turn 180° and walk 75mm.

KEY INSIGHT from Exp 11 (new arena):
- LC4 stimulus: food_dist = 31.7m (escape run = very far from food)
- Sugar stimulus: food_dist = 0.18m (barely moves, stays ~75mm from food)
- Sugar gives the most tractable starting point for navigation evolution!

Strategy:
- Use run_embodied (food_distance metric) with stimulus='sugar'
- Fitness = MINIMIZE food_dist (0.0 = reached food, starting at 0.075m)
- Bio sugar baseline = 0.18m (fly moved slightly AWAY from food)
- Evolution target: drive food_dist below 0.075m (approach food)
- Run 3 generations × 4 candidates × 3 seeds
- N_MUT = 2000 (aggressive — need to activate gustatory navigation circuits)

Note: Seeds chosen carefully:
- Seeds 42, 456, 789 as used in Exp 11

Tools: mutate + run_embodied + compete
"""

import sys, json, os
import numpy as np
sys.path.insert(0, '/home/ubuntu/autoresearch')
from capabilities import load_connectome, mutate, run_embodied

os.makedirs('results', exist_ok=True)

print("=" * 60)
print("EXPERIMENT 12: NAVIGATION EVOLUTION (NEW ARENA)")
print("Goal: evolve brain that navigates toward food 75mm away (sugar stimulus)")
print("Key insight: sugar baseline food_dist=0.18m — much more tractable than LC4 (31.7m)")
print("=" * 60)

connectome = load_connectome()
STIM = 'sugar'
SEEDS = [42, 456, 789]
DURATION = 2.0
N_GEN = 3
N_CANDS = 4
N_MUT = 2000


def eval_nav(df, seeds=SEEDS):
    """
    Fitness = -mean(food_distance) over seeds.
    food_distance = final Euclidean distance to food (0 = reached food, 0.075 = start).
    We MAXIMIZE fitness = MINIMIZE food_distance.
    """
    dists = []
    for s in seeds:
        r = run_embodied(df, seed=s, duration_sec=DURATION, stimulus=STIM)
        dists.append(float(r['food_distance']))
    return -float(np.mean(dists))  # negate: higher = better (closer to food)


# ── Baseline ──────────────────────────────────────────────────────────────────
print(f"\nBaseline (biological brain, {len(SEEDS)} seeds):")
bio_food_dists = []
for s in SEEDS:
    r = run_embodied(connectome, seed=s, duration_sec=DURATION, stimulus=STIM)
    fd = float(r['food_distance'])
    dt = float(r.get('distance_traveled', 0))
    bio_food_dists.append(fd)
    print(f"  seed={s}: food_dist={fd:.4f}m  traveled={dt:.4f}m")

bio_mean_dist = float(np.mean(bio_food_dists))
bio_fitness = -bio_mean_dist  # for evolution: higher = better
print(f"  Mean food_dist: {bio_mean_dist:.4f}m  (fitness={bio_fitness:.4f})")
print(f"  (Food starts 0.075m away. Higher food_dist = further from food)")

# ── Evolution ─────────────────────────────────────────────────────────────────
print(f"\nEvolution: {N_GEN} gen × {N_CANDS} cands × {len(SEEDS)} seeds, "
      f"N_MUT={N_MUT}")
print(f"Maximizing food_distance (less negative = closer to food)")

best_brain = connectome.copy()
best_fitness = bio_fitness  # = -bio_mean_dist
best_food_dist = bio_mean_dist
evolution_log = [{'gen': 0, 'food_dist': bio_mean_dist, 'fitness': bio_fitness,
                  'improved': False, 'candidates': [bio_fitness]}]

for gen in range(1, N_GEN + 1):
    print(f"\n  Gen {gen}/{N_GEN}:")
    gen_scores = []
    gen_brains = []
    for i in range(N_CANDS):
        cand, _ = mutate(best_brain, n_mutations=N_MUT, seed=gen * 100 + i)
        score = eval_nav(cand)
        gen_scores.append(score)
        gen_brains.append(cand)
        print(f"    Cand {i+1}: food_dist={score:.4f}m")

    best_idx = int(np.argmax(gen_scores))
    gen_best_score = gen_scores[best_idx]
    improved = gen_best_score > best_fitness
    if improved:
        best_brain = gen_brains[best_idx]
        best_fitness = gen_best_score
        best_food_dist = -gen_best_score
        print(f"  >> NEW BEST: food_dist={best_food_dist:.4f}m "
              f"(Δ={best_food_dist - bio_mean_dist:+.4f}m from bio)")
    else:
        print(f"  >> No improvement (best this gen food_dist={-gen_best_score:.4f}m, "
              f"prev best={best_food_dist:.4f}m)")

    evolution_log.append({
        'gen': gen,
        'food_dist': float(-gen_best_score),
        'fitness': float(gen_best_score),
        'improved': bool(improved),
        'candidates_fitness': [float(s) for s in gen_scores],
        'candidates_food_dist': [float(-s) for s in gen_scores],
    })

# ── Final evaluation of best brain ───────────────────────────────────────────
print(f"\nFinal best brain evaluation ({len(SEEDS)} seeds × 2s):")
final_food_dists = []
for s in SEEDS:
    r = run_embodied(best_brain, seed=s, duration_sec=DURATION, stimulus=STIM)
    fd = float(r['food_distance'])
    dt = float(r.get('distance_traveled', 0))
    final_food_dists.append(fd)
    print(f"  seed={s}: food_dist={fd:.4f}m  traveled={dt:.4f}m")
final_mean_dist = float(np.mean(final_food_dists))
final_fitness = -final_mean_dist

# ── Summary ───────────────────────────────────────────────────────────────────
delta = bio_mean_dist - final_mean_dist  # positive = closer to food (improvement)
improvement_mm = delta * 1000
food_start = 0.075  # meters
approach_pct = delta / food_start * 100

print("\n" + "=" * 60)
print("NAVIGATION EVOLUTION RESULTS")
print("=" * 60)
print(f"  Biological brain: food_dist={bio_mean_dist:.4f}m")
print(f"  Evolved brain:    food_dist={final_mean_dist:.4f}m")
print(f"  Delta:           {delta:+.4f}m ({improvement_mm:+.1f}mm closer to food)")
print(f"  Food start dist:  0.075m (75mm)")
print(f"  Approach:        {approach_pct:+.1f}% of initial distance closed")

if approach_pct > 10:
    surprise = "SURPRISING — meaningful navigation improvement!"
elif approach_pct > 2:
    surprise = "INTERESTING — small but measurable navigation improvement"
else:
    surprise = "EXPECTED — evolution on flat landscape, no navigation"

print(f"\n  Surprise: {surprise}")

output = {
    'experiment': 'navigation_evolution',
    'arena': 'new (fly faces away, food 75mm)',
    'stimulus': STIM,
    'seeds': SEEDS,
    'duration': DURATION,
    'n_gen': N_GEN,
    'n_cands': N_CANDS,
    'n_mut': N_MUT,
    'bio_mean_food_dist': bio_mean_dist,
    'bio_per_seed': {str(s): float(sc) for s, sc in zip(SEEDS, bio_food_dists)},
    'evolved_mean_food_dist': final_mean_dist,
    'evolved_per_seed': {str(s): float(sc) for s, sc in zip(SEEDS, final_food_dists)},
    'delta_meters_closer': float(delta),
    'approach_pct': float(approach_pct),
    'evolution_log': evolution_log,
}

with open('results/exp12_navigation_evolution.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\nSaved: results/exp12_navigation_evolution.json")
print("=" * 60)
