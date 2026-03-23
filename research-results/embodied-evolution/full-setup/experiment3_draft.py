"""
Experiment 3: Evolutionary Search to Reduce Variance + Increase Mean Fitness

Motivation: Exp 1 showed CV=52.6% (huge noise). Seed 123 reaches food nearly
perfectly — suggesting the brain HAS this capacity but doesn't reliably express it.

Question: Can we evolve a brain that CONSISTENTLY reaches food (low variance + high mean)?

Pipeline: mutate -> run_embodied (3x avg) -> keep best -> repeat 5 generations
Then: crossover(best_walker, best_directed) to test if combined brain is more robust

Tools used: mutate + run_embodied + crossover + compete
"""

import sys, json, os, time
import numpy as np
sys.path.insert(0, '/home/ubuntu/autoresearch')
from capabilities import load_connectome, run_embodied, mutate, crossover, compete

os.makedirs('results', exist_ok=True)

SEEDS_EVAL = [42, 789]   # 2 seeds for fast evaluation (skip 123 as it's outlier)
DURATION = 1.0
N_CANDIDATES = 5          # mutations per generation
N_GENERATIONS = 5
N_MUTATIONS = 50          # mutations per candidate (more = bigger steps)

print("=" * 60)
print("EXPERIMENT 3: EVOLUTIONARY VARIANCE REDUCTION")
print("=" * 60)

connectome = load_connectome()

def avg_fitness(df, seeds=SEEDS_EVAL, duration=DURATION, stimulus='sugar'):
    """Evaluate brain as average over multiple seeds."""
    fitnesses = []
    for s in seeds:
        r = run_embodied(df, duration_sec=duration, seed=s, stimulus=stimulus)
        fitnesses.append(r['fitness'])
    return float(np.mean(fitnesses)), float(np.std(fitnesses))

# Baseline
print("\nBaseline (2 seeds, 1s):")
base_mean, base_std = avg_fitness(connectome)
print(f"  mean={base_mean:.4f} std={base_std:.4f}")

# Evolutionary loop
current_best = connectome.copy()
current_best_fitness = base_mean
history = [{'gen': 0, 'mean': base_mean, 'std': base_std}]

print(f"\nStarting evolution: {N_GENERATIONS} generations, {N_CANDIDATES} candidates each")
print(f"N_mutations={N_MUTATIONS}, {len(SEEDS_EVAL)} seeds per eval")

for gen in range(1, N_GENERATIONS + 1):
    print(f"\n--- Generation {gen}/{N_GENERATIONS} ---")
    candidates = []
    for i in range(N_CANDIDATES):
        mutated, idxs = mutate(current_best, n_mutations=N_MUTATIONS,
                               seed=gen * 100 + i)
        m, s = avg_fitness(mutated)
        candidates.append({'df': mutated, 'mean': m, 'std': s, 'idx': i})
        print(f"  Cand {i+1}: mean={m:.4f} std={s:.4f}")

    # Select best
    best = max(candidates, key=lambda c: c['mean'])
    if best['mean'] > current_best_fitness:
        current_best = best['df']
        current_best_fitness = best['mean']
        print(f"  >> New best: {best['mean']:.4f} (gen {gen}, cand {best['idx']+1})")
    else:
        print(f"  >> No improvement. Best this gen: {best['mean']:.4f}")

    history.append({'gen': gen, 'mean': best['mean'], 'std': best['std'],
                    'improved': best['mean'] > history[-1]['mean']})

# Save intermediate candidates for crossover
print("\n--- Running crossover of diversity ---")
# Take two independent evolved lines from gen 1 + last gen
line_a, _ = mutate(connectome, n_mutations=N_MUTATIONS, seed=100)
line_b, _ = mutate(connectome, n_mutations=N_MUTATIONS, seed=200)
for _ in range(3):  # 3 more generations of each line independently
    line_a_cands = [mutate(line_a, n_mutations=N_MUTATIONS, seed=300+i) for i in range(3)]
    line_b_cands = [mutate(line_b, n_mutations=N_MUTATIONS, seed=400+i) for i in range(3)]
    line_a_scores = [(avg_fitness(df)[0], df) for df, _ in line_a_cands]
    line_b_scores = [(avg_fitness(df)[0], df) for df, _ in line_b_cands]
    line_a = max(line_a_scores, key=lambda x: x[0])[1]
    line_b = max(line_b_scores, key=lambda x: x[0])[1]

# Crossover
child = crossover(connectome, line_a, line_b, ratio=0.5, seed=42)
child_mean, child_std = avg_fitness(child)
line_a_mean, _ = avg_fitness(line_a)
line_b_mean, _ = avg_fitness(line_b)
print(f"  Line A mean: {line_a_mean:.4f}")
print(f"  Line B mean: {line_b_mean:.4f}")
print(f"  Crossover child mean: {child_mean:.4f}")

# Head-to-head: evolved best vs biological
print("\n--- COMPETITION: Evolved vs Biological ---")
comp = compete(current_best, connectome, seed=42, stimulus='sugar')
print(f"  Evolved: {comp['a']['fitness']:.4f}")
print(f"  Biological: {comp['b']['fitness']:.4f}")
print(f"  Winner: {comp['winner']}")

# Summary
print("\n=== EVOLUTION SUMMARY ===")
print(f"{'Gen':>4} {'Mean':>8} {'Std':>8} {'Improved':>9}")
for h in history:
    imp = '<<' if h.get('improved', False) else ''
    print(f"  {h['gen']:>2}  {h['mean']:>8.4f}  {h['std']:>8.4f}  {imp}")

print(f"\nEvolution: {base_mean:.4f} -> {current_best_fitness:.4f} "
      f"({(current_best_fitness - base_mean)/abs(base_mean)*100:+.1f}%)")

output = {
    'experiment': 'evolutionary_variance_reduction',
    'n_generations': N_GENERATIONS,
    'n_candidates': N_CANDIDATES,
    'n_mutations': N_MUTATIONS,
    'eval_seeds': SEEDS_EVAL,
    'baseline_mean': base_mean,
    'baseline_std': base_std,
    'best_evolved_mean': current_best_fitness,
    'history': history,
    'crossover': {'line_a_mean': line_a_mean, 'line_b_mean': line_b_mean, 'child_mean': child_mean},
    'competition': comp,
}

with open('results/exp3_evolution.json', 'w') as f:
    json.dump(output, f, indent=2)

print("Saved: results/exp3_evolution.json")
