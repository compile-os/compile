# Embodied Evolution Lab Notebook

## Session 1 — First Embodied Run

**Context:** Switching from bare LIF to embodied simulation (NeuroMechFly + MuJoCo).
Previous LIF findings: 16.7% baseline variance, ~8% fitness improvement from evolution,
weakening mutations dominated. None of that carries over automatically — must re-measure.

**Fitness metric:** `-food_distance` (closer to food = higher fitness). Food at [0.01, 0, 0].

---

---

## Experiment 01 — Embodied Baseline Variance
**Date:** 2026-03-15
**Tools:** `load_connectome`, `run_embodied` x5

**Setup:** Biological (unmodified) brain, 5 seeds, 2s simulation, sugar stimulus.

**Results:**
| Metric | Mean | Std | CV |
|--------|------|-----|-----|
| fitness (-food_dist) | -0.0543 | 0.0319 | **58.7%** |
| distance_traveled | 2.697 | 0.387 | **14.3%** |

Per-seed fitnesses: -0.1004, -0.0138, -0.0421, -0.0338, -0.0816

**Surprise rating: INTERESTING**

**Interpretation:**
- `fitness` (food proximity) has 58.7% CV — extremely noisy. Food is at [0.01, 0, 0]
  (essentially straight ahead at 1cm), yet the fly rarely reaches it. Direction is stochastic.
- `distance_traveled` has only 14.3% CV — locomotion quality is stable and consistent.
- **Key implication:** Cannot trust single-run fitness comparisons. But locomotion can be
  measured reliably with 1-2 runs.
- **Methodology change:** Use `distance_traveled` as primary evolutionary metric (stable).
  Only use food_distance fitness when averaging 5 runs.
- Seed 42 was a bad run (fitness -0.1004, only 1.93m traveled vs ~2.8m for others).
  This seed should be excluded from first-run comparisons.

**Follow-up:** Evolve for locomotion distance (stable signal), then check if better locomotors
also happen to find food better (behavioral transfer question).

---

## Experiment 02 — Evolve Two Lineages + Crossover (partial)
**Date:** 2026-03-15
**Tools:** `mutate` × 18, `crossover`, `compete`
**Status:** Timed out at ~36 min (exceeded 40 min limit)

**Partial results (3 gens × 2 candidates per lineage, n_mut=2000, weight_range=0.4):**

| | dist | vs bio |
|-|------|--------|
| Biological | 2.6093 | — |
| Lineage A (best) | 2.6120 | +0.1% |
| Lineage B (best) | 2.6093 | 0.0% |

**Key observation:** Most mutations produce one of only 3 distinct distances: 2.5367, 2.6093, 2.6120.
The CPG-driven locomotor has **discrete attractor states**. Small weight changes rarely shift the
brain's output enough to change which attractor the fly lands in.

**Surprise rating: INTERESTING**

**Interpretation:**
- Random weight mutations are too weak vs CPG dynamics (signal/noise ratio too low)
- Evolution IS possible (+0.1% found) but very slow
- The 3-valued attractor pattern suggests brain drive modulates CPG discretely
- Structural changes (ablate/scale) will produce larger, cleaner effects

**Pivot:** Drop weight evolution for now. Use `ablate()` and `scale_brain()` which trigger
full CSR rebuilds and produce large, guaranteed behavioral differences.

---

## Debug Session — Pipeline Verification
**Date:** 2026-03-15
**Finding: 3 sequential bugs were hiding the mutation signal**

### Bug 1: Non-unique DataFrame index
The parquet file has only ~26K unique labels across 15M rows. `df.at[label, col]`
updates ALL rows with that label (~1000 rows per label). Fixed with `df.iat[pos, col_pos]`.

### Bug 2: Incorrect weight reset (DataFrame order ≠ CSR order)
My weight-reset code did `brain._syn_vals.copy_(tensor_of_df_order_values)`.
`_syn_vals` is CSR-ordered; DataFrame is row-ordered. Copying the wrong order
scrambled the entire weight matrix → zero brain activity.
Fixed by saving `_ORIG_CSR_VALS = brain._syn_vals.clone()` at initialization.

### Bug 3: Brain never active during simulation
Sugar stimulus takes **415 brain steps** (~41ms brain time) before first DN spike.
The 2s embodied simulation only runs 200 brain steps (20ms brain time) total.
**DNs never fire → drive=[0,0] → pure CPG autopilot → all mutations identical.**
Fixed with warmup_steps=500 (pre-runs brain before physics to establish steady-state).

### Verified behavior:
- Bio × 2 with same seed = identical (warmup is deterministic)
- 10× DN inputs: -3.2% distance
- n_mutations sweep: 50→-11%, 200→0%, 1000→-9%, 5000→+13%
- Effect is real but noisy: same mutation set can be + or - depending on which synapses

---



## Experiment 04 — Does Small-Brain Superiority Hold Across Ablation Seeds?
**Date:** 2026-03-15
**Tools:** `scale_brain` × 5, `run_embodied` × 18
**Status:** COMPLETE

**Setup:** Test if Exp 03's +9.3% small-brain benefit was a lucky draw (seed=42)
or universal. 0.25x scale with 5 ablation seeds (42, 7, 13, 99, 200), each evaluated
with 3 sim seeds (7, 13, 99). warmup_steps=500.

**Results:**
| Abl seed | Synapses | Dist mean | vs bio |
|----------|----------|-----------|--------|
| 42 | 940,209 | 2.5333 | +1.0% |
| 7 | 930,509 | 2.5333 | +1.0% |
| 13 | 960,739 | 2.5333 | +1.0% |
| 99 | 935,660 | 2.5333 | +1.0% |
| 200 | 958,345 | 2.5333 | +1.0% |

Bio baseline: 2.5083 ± 0.3818 (seeds 7/13/99: 1.9788, 2.6817, 2.8643)
All 0.25x: IDENTICAL results per sim seed (2.3030 / 2.7991 / 2.4977), std=0.0000

**Surprise rating: VERY SURPRISING → deeper investigation reveals EXPECTED**

**Critical insight:**
- All 5 ablation seeds (different neuron sets) produce EXACTLY IDENTICAL behavior
- This can ONLY happen if the ablated brain produces zero neural drive to the CPG
- **The 0.25x ablation breaks the sugar→DN signal propagation path** (random ablation
  removes intermediate neurons needed for multi-hop signal routing to DNs)
- With drive=[0,0], locomotion is pure CPG, determined entirely by sim_seed → identical
- Bio brain DOES produce variable drive (bio distances ≠ 0.25x distances for same sim seed)

**Revised interpretation of Exp 03's "9.3% improvement":**
- Exp 03 used only 3 sim seeds and found 0.25x==0.50x (same results) — now explained
- Both ablated brains have zero drive → same pure CPG behavior
- The "improvement" over bio is just: bio brain sometimes steers in ways that reduce
  total path length (brain turns the fly), while pure CPG walks more "straight"
- The effect is NOT a genuine neural improvement — it's signal-path disruption

**Bio brain vs pure CPG (drive=0):**
| Sim seed | Bio dist | 0.25x (pure CPG) | Brain effect |
|----------|----------|------------------|--------------|
| 7 | 1.9788 | 2.3030 | **-14.5%** (brain steers, reducing raw distance) |
| 13 | 2.6817 | 2.7991 | **-4.4%** |
| 99 | 2.8643 | 2.4977 | **+14.7%** |

The brain effect on distance is mixed: +/-15%. Brain changes trajectory (sometimes more
efficient, sometimes less). The key measurement should be FOOD PROXIMITY (fitness),
not distance.

**Fitness comparison (bio vs 0.25x pure CPG):**
- sim_seed=7: bio=-0.1256, 0.25x=-0.0609 → 0.25x CLOSER to food
- sim_seed=13: bio=-0.1048, 0.25x=-0.1046 → tie
- sim_seed=99: bio=-0.1266, 0.25x=-0.1238 → tie

So with food at 75mm behind fly: the 0.25x pure CPG gets within 6cm of food (seed=7),
while bio brain (supposedly steering toward food) only reaches 12.5cm. This suggests
the brain is NOT successfully navigating to food in this 2s window.

**Root question:** Is 2s enough for the bio brain to perform successful food navigation?
With food 75mm behind and fly needs to turn 180°, 2s may be too short.

**Follow-up:** Experiment 05 — find minimal locomotor kernel:
Keep only neurons within N hops of DNs and ablate the rest. Test if DN-adjacent
neurons are sufficient for full locomotor performance vs full bio.

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

## Experiment 03 — Brain Scaling: Minimum Viable Brain
**Date:** 2026-03-15
**Tools:** `scale_brain` × 4, `run_embodied` × 15
**Status:** COMPLETE

**Setup:** Scale brain by randomly removing neurons (0.10x, 0.25x, 0.50x, 0.75x, 1.0x biological).
Each scale tested with 3 seeds (7, 13, 99). warmup_steps=500.
scale_brain(seed=42) for all sub-biological brains.

**Results:**
| Scale | Synapses | Dist (mean±std) | vs bio | Fitness |
|-------|----------|-----------------|--------|---------|
| 0.10x | 151,310 | 2.6465 ± 0.1100 | -0.2% | -0.0413 |
| 0.25x | 940,209 | 2.8978 ± 0.0778 | **+9.3%** | -0.0299 |
| 0.50x | 3,760,856 | 2.8978 ± 0.0778 | **+9.3%** | -0.0299 |
| 0.75x | 8,489,773 | 2.7011 ± 0.2688 | +1.9% | -0.0491 |
| 1.00x | 15,091,983 | 2.6508 ± 0.1156 | 0.0% | -0.0419 |

Note: 0.25x and 0.50x returned IDENTICAL results (same mean, std, fitness) — likely same
random sample was preserved due to scale_brain(seed=42) interaction.

**Surprise rating: SURPRISING**

**Key findings:**
1. **A 0.25x brain outperforms the full biological brain by +9.3%**
   - Only 940K of 15M synapses retained, yet locomotion improves
   - The full brain may contain inhibitory interneurons that suppress locomotion
2. **Minimum viable scale is ≤0.10x** (151K synapses still achieves near-bio performance)
   - Even 1% of the brain sustains locomotion (CPG is robust)
3. **0.25x == 0.50x**: identical results suggest the kept-neuron set is the same
   - scale_brain with seed=42 at 25% and 50% may overlap completely at some attractor
   - OR the `_inject_connectome_weights` structural path produces identical CSR at these sizes

**Open questions:**
- Is the 0.25x superiority consistent across different ablation seeds, or lucky?
- Does removing INHIBITORY neurons specifically explain the improvement?
- What is the "minimal locomotor kernel" — the smallest connected subgraph that achieves full performance?

**Follow-up:** Experiment 04 — Test 0.25x with multiple ablation seeds (7, 13, 99, 200, 42) to determine
if outperformance is a general property of 25%-brain or specific to seed=42's neuron selection.

---


