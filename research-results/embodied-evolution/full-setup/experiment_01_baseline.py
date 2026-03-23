"""
Experiment 01: Baseline Embodied Fitness Variance
==================================================
Run the UNMODIFIED biological fly brain 5× with different seeds.
Measure mean ± std of embodied fitness (food-seeking behavior).
This is the reference point for all subsequent experiments.
"""
import sys, os, json, time
sys.path.insert(0, '/home/ubuntu/autoresearch')
sys.path.insert(0, '/home/ubuntu/fly-brain-embodied')
os.environ['MUJOCO_GL'] = 'osmesa'
os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

import numpy as np
from capabilities import load_connectome, run_embodied

os.makedirs('/home/ubuntu/autoresearch/results', exist_ok=True)

print("=" * 60)
print("EXPERIMENT 01: Baseline Embodied Fitness Variance")
print("=" * 60)

connectome = load_connectome()
print(f"Loaded connectome: {len(connectome):,} synapses")

seeds = [42, 123, 777, 1234, 9999]
results = []

for i, seed in enumerate(seeds):
    print(f"\nRun {i+1}/5 (seed={seed})...")
    t0 = time.time()
    r = run_embodied(connectome, duration_sec=2.0, seed=seed, stimulus='sugar',
                     use_df_weights=False)  # Bio brain - skip weight injection
    elapsed = time.time() - t0
    r['seed'] = seed
    r['elapsed_sec'] = elapsed
    results.append(r)
    print(f"  fitness={r['fitness']:.5f}  dist={r['distance_traveled']:.5f}m  "
          f"displacement={r['displacement']:.5f}m  elapsed={elapsed:.1f}s")

# Statistics
fitnesses = [r['fitness'] for r in results]
distances = [r['distance_traveled'] for r in results]
displacements = [r['displacement'] for r in results]

print("\n" + "=" * 60)
print("BASELINE STATISTICS")
print("=" * 60)
print(f"Fitness:      mean={np.mean(fitnesses):.5f}  std={np.std(fitnesses):.5f}  "
      f"cv={np.std(fitnesses)/max(abs(np.mean(fitnesses)),1e-9):.3f}")
print(f"Dist traveled: mean={np.mean(distances):.5f}  std={np.std(distances):.5f}")
print(f"Displacement:  mean={np.mean(displacements):.5f}  std={np.std(displacements):.5f}")

# Check if fly is moving at all
if np.mean(distances) < 1e-5:
    print("\nWARNING: Fly is barely moving! Drive might not be reaching controller.")
elif np.std(fitnesses) / (abs(np.mean(fitnesses)) + 1e-9) < 0.05:
    print(f"\nLOW VARIANCE: CV={np.std(fitnesses)/abs(np.mean(fitnesses)):.3f} "
          f"— single-run fitness is reliable")
else:
    print(f"\nHIGH VARIANCE: CV={np.std(fitnesses)/abs(np.mean(fitnesses)):.3f} "
          f"— use 3x averaged fitness for experiments")

# Save
output = {
    'experiment': 'baseline_variance',
    'n_runs': len(seeds),
    'seeds': seeds,
    'results': results,
    'stats': {
        'fitness_mean': float(np.mean(fitnesses)),
        'fitness_std': float(np.std(fitnesses)),
        'fitness_cv': float(np.std(fitnesses) / max(abs(np.mean(fitnesses)), 1e-9)),
        'distance_mean': float(np.mean(distances)),
        'displacement_mean': float(np.mean(displacements)),
    }
}

with open('/home/ubuntu/autoresearch/results/exp01_baseline.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nSaved to results/exp01_baseline.json")
