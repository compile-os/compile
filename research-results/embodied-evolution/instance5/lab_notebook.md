# Embodied Evolution Lab Notebook

Session started: Sun Mar 15 00:24:55 EDT 2026

---

## Experiment 1: Embodied Baseline Variance
**Date**: 2026-03-15
**File**: `results/exp01_baseline_variance.json`
**Tools**: `load_connectome`, `run_embodied`

### Setup
- Run biological (unmodified) connectome 5× with seeds [42, 123, 777, 1337, 9999]
- Measure fitness variance to calibrate averaging requirements

### Results
| Metric | Mean | Std | CV |
|--------|------|-----|-----|
| Fitness (−food_dist) | −1.7180 | 0.0000 | 0.0% |
| Distance traveled | 8.7279 m | 0.0 | 0.0% |
| Food distance | 1.7180 m | 0.0 | 0.0% |
| Displacement | 1.7231 m | 0.0 | 0.0% |

**Trajectory**: Start ≈ [0.015, 0.007, 1.78] → End ≈ [−1.708, −0.010, −0.287]
Food at [0.01, 0.0, 0.0]. The fly walks AWAY from food in the −x direction.

### Rating: **SURPRISING**

**Surprise**: CV = 0% — the simulation is PERFECTLY deterministic regardless of seed. All 5 runs produced IDENTICAL results (including identical floating point values). The `seed` parameter passed to `run_embodied` has zero effect on outcomes.

**Implication for methodology**:
- Single runs are completely reliable — no averaging needed
- Any fitness difference observed between brains is a real signal, not noise
- Can run ≈3× more experiments per session

**Implication for biology**: The biological fly brain, driven by sugar stimulus, produces a stereotyped walking trajectory. The fly walks persistently in one direction but happens to move AWAY from the food source. This is the baseline we must beat.

---

## Experiment 2: Evolutionary Search + Merge (RUNNING)
**Date**: 2026-03-15
**Tools**: `mutate`, `run_embodied`, `merge_brains`, `crossover`

### Hypothesis
With zero noise, even tiny fitness improvements are real. Can random mutations improve food-approach behavior? Do two independently improved brains, merged, produce additive gains?

### Design
1. Generate 5 mutant brains (n_mutations=100, seeds 0−4)
2. Test all 5
3. Merge best 2 → test
4. Crossover best 2 → test

### Expected
- Some mutations hurt, some help, ~8% improvement from best single mutant (LIF prior)
- Merge: may show additive improvement or conflict
- Crossover: may show similar or different pattern from merge

---


---

## ⚠️ ARENA FIX DEPLOYED — READ THIS ⚠️
**Timestamp:** 2026-03-15 08:30 UTC

The experimental arena has been fixed. Your `capabilities.py` has been updated:
- **Food position**: now at [75, 0, 0]mm (was [10, 0, 0]mm)
- **Fly orientation**: now faces AWAY from food (spawn_orientation = (0, 0, π))

**Implications:**
1. All previous fitness measurements are invalidated (they tested "freeze near food" not "navigate to food")
2. Re-run your experiments with the new arena
3. Zero brain (CPG only) should now score ~-0.15 to -0.20 (walks away from food)
4. A good brain should turn and walk to food, scoring close to 0

**Your tools still work — just re-run with the fixed arena.**

---


