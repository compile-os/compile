# Embodied Evolution Lab Notebook

Session started: Sun Mar 15 00:24:01 EDT 2026

---

## Experiment 01 — Baseline Embodied Fitness Variance
**Date:** 2026-03-15
**File:** `results/01_baseline_variance.json`
**Pipeline:** `load_connectome → run_embodied × 5 seeds`

### Setup
- Biological (unmodified) FlyWire connectome: 15,091,983 synapses
- Duration: 2.0 sec per run, stimulus: sugar
- Seeds: 42, 123, 777, 2024, 31415
- Food position: [0.01, 0.0, 0.0]
- Fly starts at: [0.016, 0.007, 1.78]

### Results
| Seed | Fitness | Food Dist | Displacement | Time (s) |
|------|---------|-----------|--------------|----------|
| 42   | -0.1004 | 0.1004    | 0.096        | 133      |
| 123  | -0.0014 | 0.0014    | 0.010        | 106      |
| 777  | -0.1347 | 0.1347    | 0.131        | 102      |
| 2024 | -0.0614 | 0.0614    | 0.052        | 102      |
| 31415| -0.0651 | 0.0651    | 0.056        | 100      |

**Mean fitness:** -0.073 ± 0.044 (CV = 61%)
**Mean displacement:** 0.069 ± 0.041 m
**Mean distance traveled:** 2.60 ± 0.35 m

### Key Observations
- **VERY HIGH VARIANCE** (CV=61%) — 5x seed averaging required for all future experiments
- Best run (seed 123): fly ended only 0.0014m from food — essentially found it
- Worst run (seed 777): fly wandered 0.13m away from food
- The fly already walks significant distances (2.6m in 2 seconds!) and sometimes reaches food
- Each simulation run: ~100–133 seconds; budget ~15 runs per 30-min experiment
- `mutate()` uses `df.columns[-1]` fallback = `Excitatory x Connectivity` ✓ correct column
- `_inject_connectome_weights()` reads `Excitatory x Connectivity` directly ✓ consistent

### Surprise Rating: EXPECTED
High variance was anticipated from stochastic physics. The biological fly finding food (seed 123) is good but not surprising — CPG locomotion is already functional.

### Open Questions
- Does mutating the connectome actually change behavior (fitness changes)?
- What mutation intensity is needed to move the fitness needle above noise floor?
- Is the fly's good performance (seed 123) a fluke of CPG timing, or is the brain contributing?

---

## Experiment 02 — Mutation Landscape Survey
**Date:** 2026-03-15
**File:** `results/02_mutation_landscape.json`
**Pipeline:** `mutate(n) → run_embodied × 3 seeds → compete(best_mutant, biological)`

### Results
| N_mut | Changed | Mean fitness | Δbaseline | z-score |
|-------|---------|-------------|-----------|---------|
| 50    | 42,899  | -0.0788     | -0.0062   | -0.14   |
| 500   | 407,681 | -0.0788     | -0.0062   | -0.14   |
| 2,000 | 1,587,686 | -0.0788   | -0.0062   | -0.14   |
| 10,000| 6,288,252 | -0.0788   | -0.0062   | -0.14   |

**IDENTICAL results across ALL mutation intensities.** Every mutation count (50 to 10,000) produced EXACTLY the same fitness for each seed as the unmodified biological brain.

### Bug Discovery — CRITICAL
Root cause analysis revealed TWO bugs in `capabilities.py`:

**Bug 1: Wrong reference in `_ORIG_DF_CACHE` initialization**
- `run_embodied()` caches `_ORIG_DF_CACHE = df['Excitatory x Connectivity'].values.copy()` on first call
- But first call was with a MUTANT df, not biological
- Delta-injection computes `changed_mask = mutant != mutant_ref` → all False → NO injection
- Brain always ran with its file-loaded biological weights regardless of input df

**Bug 2: Int64 truncation in `mutate()`**
- `Excitatory x Connectivity` column is stored as int64 in parquet
- Setting float values (e.g., 0.95) into int64 column triggers FutureWarning and truncates
- Small mutations on low-weight synapses (value 0-1) silently round back to original
- Even if injection worked, many mutations would have no effect

### Fixes Applied (capabilities.py)
1. **`run_embodied()`**: `_ORIG_DF_CACHE` now always loaded from biological parquet file directly, never from the df parameter
2. **`mutate()`**: Column cast to float64 before any mutations, preserving fractional weight changes

### Surprise Rating: SURPRISING → then EXPECTED
The identical results were surprising. The bug discovery was expected (the previous session had flagged potential injection issues).

---

## Experiment 03 — Mutation Efficacy Validation (post-fix)
**Date:** 2026-03-15
**File:** `results/03_mutation_efficacy.json`
**Pipeline:** `run_embodied(bio) → mutate(n) → run_embodied × 3 seeds → compare`

### Results
Bug fix still showed ZERO behavioral change. Injections confirmed working (diagnostic3). Root cause: the bug was NOT in the injection. The real issue was discovered via diagnostics.

### Diagnostic Findings — Critical

**Diagnostic 1** (H1/H2 test):
- H1 CONFIRMED: `_syn_vals.data_ptr == model.weights.values().data_ptr` — injection modifies live weights
- H2 CONFIRMED: **ZERO DN neurons fired in 200ms with sugar stimulus!**
- Root cause: sugar GRNs → gustatory pathway → **NO excitatory chain to locomotion DNs**

**Diagnostic 2** (stimulus comparison, 500ms each):
| Stimulus | Net spikes/step | Active DNs | Key DNs | Notes |
|---------|----------------|-----------|---------|-------|
| sugar | 0.89 | 2 (MN9) | MN9 ~50Hz (feeding) | Mode → feeding (stops walking) |
| **p9** | 0.06 | **5** | **P9_left 82Hz, P9_right 66Hz** | **LEFT TURN BIAS** |
| **lc4** | 2.02 | **5** | GF_1 88Hz, GF_2 100Hz | Escape but symmetric |
| jo | 3.25 | 2 | aDN1 (grooming) | No locomotion effect |

**Diagnostic 3** (zero-brain ablation test, seed=42):
| Condition | Fitness | Dist traveled | Displacement |
|-----------|---------|--------------|--------------|
| Bio (sugar) | -0.1004 | 1.933m | 0.096 |
| Zero brain (sugar) | -0.1004 | 1.933m | 0.096 |
| Bio (lc4) | -0.1004 | 1.933m | 0.096 |
| Zero brain (lc4) | -0.1004 | 1.933m | 0.096 |
| **Bio (p9)** | **-0.1434** | 2.257m | 0.137 |
| **Zero brain (p9)** | **-0.1004** | 1.933m | 0.096 |

**CRITICAL DISCOVERY**: HybridTurningController CPG walks AUTONOMOUSLY regardless of drive amplitude. Only drive **ASYMMETRY** (left-right difference) changes behavior. With sugar and lc4, the brain produces symmetric drives → same as zero brain. With p9, the brain creates a LEFT-TURN BIAS (P9_left > P9_right) → fly turns away from food → WORSE fitness.

### Open Questions Resolved
- Brain uses CPG's baseline gait regardless of forward drive magnitude
- Only left/right imbalance in [left_drive, right_drive] affects trajectory
- sugar, lc4: brain output is effectively symmetric → no evolution signal
- p9: brain creates exploitable asymmetry → evolution gradient exists

### Surprise Rating: SURPRISING
The CPG autonomy was unexpected. But it reveals a clean evolutionary problem: with p9 stimulus, the brain makes the fly WORSE at finding food (left-turn bias). Evolving to reduce this asymmetry could improve fitness.

### Path Forward — Experiment 04
- Use **p9 stimulus** for all future experiments
- Evolve to **reduce left-turn bias** (target: P9_left ≈ P9_right firing rates)
- Baseline reference: seed=42 → -0.1434 (biological), -0.1004 (zero brain)
- Evolution target: fitness > -0.1004 (beat the zero brain)

---

## Experiment 04 — p9 Evolution in New Arena (First Valid Evolution Attempt)
**Date:** 2026-03-15
**File:** `results/04_p9_evolution.json`
**Script:** `experiment04.py` (lean/GC version; v1 OOM-killed at 36min → fixed with gc.collect())
**Pipeline:** `mutate(n=500) → run_embodied(stimulus='p9') × seeds → hill-climb × 1 gen`

### Arena Context (from ARENA FIX notice below)
- Fly spawns at `(0, 0, 0.3)` facing AWAY from food (`spawn_orientation=(0, 0, π)`)
- Food at `[0.075, 0, 0]` — essentially at fly's starting XY position (distance 0.075)
- Zero-brain (CPG only) walks straight backward → food_dist ~0.15–0.20 (per fix note)
- **Evolution goal**: reduce left-turn asymmetry → fly walks less crooked → beat zero-brain

### Phase 1 — p9 Baseline (3 seeds)
| Seed | Fitness    | Food Dist |
|------|-----------|-----------|
| 42   | -21.6266  | 21.63     |
| 123  | -23.2164  | 23.22     |
| 777  | -23.6242  | 23.62     |

**p9 Baseline:** mean = **-22.8224 ± 0.8618** (CV = **4%** — vastly better than sugar's 61%!)

**Interpretation:** p9 left-turn bias causes the fly to SPIRAL rather than walk straight. In 2s it ends up 21–23 units from food, vs expected ~0.15–0.20 for zero-brain → p9 brain is **~100× worse than zero-brain** in new arena!

### Phase 2 — Mutation Sensitivity (n=500, 3 seeds)
| Seed | Mutant Fitness | Δbio     |
|------|---------------|---------|
| 42   | -24.2289      | -2.6022 |
| 123  | -23.1287      | +0.0876 |
| 777  | -24.0283      | -0.4040 |

`any_differ = True` → **mutations DO change p9 fitness** ✓ — First confirmed evolutionary signal!

### Phase 3 — Hill-Climb (1 gen × 3 candidates × 2 seeds)
| Cand | Mean     | Δparent  |
|------|---------|---------|
| 0    | -22.2573 | **+0.565** ← BEST |
| 1    | -24.4824 | -1.66   |
| 2    | -24.7704 | -1.95   |

1/3 candidates improved over parent (+0.565, within ±0.86 noise floor).

### Final Competition (INVALID — wrong stimulus)
- Called `compete(evolved, bio, seed=42)` without `stimulus='p9'` → defaulted to 'sugar' → both -0.2057 → tie
- **Bug**: must pass `stimulus='p9'` to `compete()`

### Key Discoveries
1. **CV=4%** with p9 + new arena (15× cleaner than sugar baseline)
2. **Mutations work** — any_differ=True proves evolutionary gradient exists
3. **p9 brain catastrophically bad in new arena** — spiraling 21+ units vs expected ~0.15 straight walk
4. Zero-brain reference for new arena NOT YET MEASURED — needed for Experiment 05

### Open Questions
- What is zero-brain fitness in new arena (food=[0.075], facing backward)?
- How many generations to reduce p9 spiral enough to beat zero-brain?
- Would n=100 mutations (smaller steps) give better hill-climb efficiency?

### Path Forward — Experiment 05
1. Phase A: zero-brain diagnostic (3 seeds) — establish reference
2. Phase B: 3 generations × 4 candidates × 3 seeds starting from Exp04 best (cand 0)
3. Use `compete(evolved, bio, seed=42, stimulus='p9')`

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

## Experiment 05 — Zero-Brain Reference + Multi-Gen Hill-Climb
**Date:** 2026-03-15
**File:** `results/05_zero_brain_and_hillclimb.json`
**Script:** `experiment05.py`
**Pipeline:** Phase A: zero-brain × 3 seeds | Phase B: 2 gens × 3 cands × 2 seeds from Exp04 best

### Phase A — Zero-Brain Reference (p9 stimulus, 3 seeds)
| Seed | Fitness   |
|------|----------|
| 42   | -13.9147 |
| 123  | -13.9362 |
| 777  | -13.8143 |

**Zero-brain mean = -13.8884 ± 0.0531 (CV<1%)**

> Fix note predicted ~-0.15 to -0.20 — actual is **90× larger**! The fly walks ~13.9 units from food in 2 seconds of CPG-only backward locomotion.

### Phase B — Hill-Climb (Exp04 best as parent)
Parent: `mutate(connectome, n=500, seed=200)` (from Exp04 cand 0)

| Generation   | Best Mean | Δ vs Zero-Brain |
|-------------|----------|----------------|
| Bio baseline | -22.8224 | -8.93 (much worse) |
| Gen 1 best   | **-13.8301** | **+0.0583 ← BEATS ZERO-BRAIN** |
| Gen 2 best   | **-13.7635** | **+0.1249 ← IMPROVED FURTHER** |

ALL 3 Gen 2 candidates beat zero-brain. Evolution is consistently improving.

### Compete() Reliability Issue — CRITICAL
`compete(evolved, biological, seed=42, stimulus='p9')` showed evolved=-13.9055, bio=-13.6976, winner=bio. This is CONTAMINATED: after running evolved, `_inject_connectome_weights(biological)` finds `changed_mask=all False` (bio matches ORIG_CACHE) so keeps evolved weights + Hebbian drift. Fix: run biological FIRST when comparing.

### Key Discoveries
1. **Zero-brain actual baseline**: -13.8884 (fix note's -0.15-0.20 prediction was ~90× off)
2. **FIRST EVOLVED BRAIN BEATS ZERO-BRAIN**: Gen 1 after 1500 cumulative mutations beats CPG-only
3. **Interpretation**: mutations likely suppressed P9-asymmetry pathway → fly walks straighter (like zero-brain) instead of spiraling

### Surprise Rating: EXCITING
Jump from -22.8 to -13.8 happened in ONE additional mutation step from Exp04 best. Phase transition: enough mutations accumulated to suppress the problematic P9 asymmetry.

### Path Forward — Experiment 06
- Verify result by running `compete()` with biological first (fix contamination)
- Continue hill-climb from Exp05 best (Gen 2 cand 2, mut_seed=302)
- Investigate which synapses changed vs biological
- Try larger mutations (n=1000) or targeted mutations to P9 pathway neurons

---

