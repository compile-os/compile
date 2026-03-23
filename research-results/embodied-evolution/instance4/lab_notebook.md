# Embodied Evolution Lab Notebook

Session started: Sun Mar 15 00:24:47 EDT 2026

---

## Experiment 1: Baseline Variance + Neural Evolution of MN9 Feeding Circuit

**Date:** 2026-03-15
**Duration:** ~20 min wall time
**Tools used:** `load_connectome`, `run_embodied`, `run_neural_only` (new), `mutate`, `mutate_targeted` (new), `ablate`

### Setup

- Connectome: 15,091,983 synapses, 138,639 neurons
- Simulation: `run_neural_only` with sugar stimulus, n_steps=300 (30ms neural time)
- Fitness metric: MN9 (proboscis motor neuron) normalized firing rate
- Key fix: biological weight snapshot prevents Hebbian drift across calls

### Results

**Embodied baseline (run_embodied, duration=0.2s):**
- CV = 39.3% across physics seeds (42-47)
- Fitness range: -0.025 to -0.110
- Variance is ENTIRELY from physics seed (CPG stochasticity), NOT the brain
- 2x all weights, zero weights, 1000 mutations: ALL give identical fitness with same physics seed
- Conclusion: embodied fitness is blind to brain mutations at 0.2s timescale

**Neural baseline (run_neural_only, sugar, 300 steps):**
- CV = 0.0% — perfect reproducibility across all seeds
- Bio feed_rate = 0.0833 (MN9 fires EXACTLY once in 30ms — barely above threshold)
- forward_rate = 0.0 (P9/walking DNs never fire with sugar stimulus)
- turning_bias = 0.0 (biological brain perfectly symmetric)

**Pathway analysis (MN9 pre-synaptic):**
- 0-hop: 625 direct synapses into MN9 (0.004% of total)
- 1-hop: 129,272 synapses / 388 neurons (0.86%)
- 2-hop: 2,842,729 synapses / 10,422 neurons (18.84%)

**Mutation sensitivity:**
| Mutations | Random feed_rate | Targeted feed_rate |
|-----------|-----------------|-------------------|
| 100       | 0.0833 (±0)     | 0.0833 (±0)       |
| 1000      | **0.1667 (+0.0833)** | 0.0833 (±0)  |
| 10000     | **0.0000 (-0.0833)** | 0.0833 (±0)  |

**Hill-climb evolution (20 generations, targeted MN9 mutations):**
- 0/20 generations improved (0% acceptance rate)
- Final feed_rate: 0.0833 (unchanged from biological)

### Key Findings

1. **INTERESTING — Brain circuit is quantized**: MN9 fires exactly once per 30ms with sugar. This is a binary threshold phenomenon — the neuron is barely above spiking threshold. feed_rate takes discrete values {0.0000, 0.0833, 0.1667, ...}.

2. **INTERESTING — Targeted mutations are ineffective**: Modifying the 129K synapses feeding into MN9 (1-hop) doesn't change its firing. The direct pre-synaptic weights must not individually control MN9's threshold crossing — it requires a specific coincidence pattern.

3. **SURPRISING — Random large mutations beat targeted small ones**: 1000 random mutations accidentally hitting high-weight synapses (max=1897) produce larger effective changes than 1000 targeted mutations to mostly weight=±1 synapses. Weight distribution matters more than pathway targeting.

4. **EXPECTED — CPG dominates short-timescale embodied behavior**: Walking speed/direction is determined by the CPG physics, not brain signals. Brain mutations have zero effect on body position at 0.2s timescale.

5. **EXPECTED — Sugar activates feeding (MN9), not walking (P9)**: Biologically correct — sugar taste triggers proboscis extension, not locomotion.

### Surprises / Rate

- Embodied fitness insensitivity: **INTERESTING** (not surprising given 2ms brain time per physics step)
- Neural CV=0%: **INTERESTING** (quantized firing is unusual for a large stochastic network)
- Targeted mutations failing vs random succeeding: **SURPRISING** — explore further

### Open Questions

1. Which specific synapse(s) control MN9's threshold crossing? (circuit tracing)
2. Can we find the "key synapse" by brute-force ablation of 625 direct MN9 inputs?
3. Does lc4 (looming/escape) stimulus activate GF neurons? Any asymmetry possible?
4. What's the causal chain from sugar GRNs to MN9? How many hops?
5. Can weight-SCALING (not ±20% change) of specific synapses cross the threshold?

### Next Experiment

Experiment 2: Circuit tracing — find the causal chain from sugar GRNs to MN9 spike.
Tool: add `trace_circuit()` function that tracks full spike raster and backtracks the causal neuron chain.

---

## Bugs Discovered

- `ablate()` uses `Presynaptic_ID/Postsynaptic_ID` columns to filter, but callers may pass `Presynaptic_Index/Postsynaptic_Index` values → silent no-op. Need to use correct column.
- `mutate_targeted()`: weight changes to int64 column get truncated, mostly ±1→0 or no change. Need float64 column or larger weight_range.
- `run_neural_only()` seed parameter doesn't affect brain dynamics (deterministic LIF) — seed only seeds numpy, which is unused in neural computation.


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

## Experiment 2: Circuit Tracing — Sugar GRN → MN9 Causal Chain

**Date:** 2026-03-15
**Duration:** ~15 min wall time
**Tools used:** `run_neural_only` with spike raster logging, manual pathway ablation

### Setup

Added spike-raster tracking to identify which neurons fire causally between sugar GRNs and MN9. Ran 300-step neural simulation with sugar stimulus, logged every neuron that fired, traced backwards from MN9.

### Results

**Causal chain discovered:**
- Sugar GRNs → Keystone neurons {72154, 28757} → MN9
- Neuron 72154 controls the FIRST MN9 spike; neuron 28757 controls the SECOND
- Each keystone neuron receives direct input from ~5 sugar GRN neurons
- Key sugar GRN inputs: {126752, 129730, 51107, 92298, 108426}

**Scale-response is non-monotonic:**
- 2x GRN input weights → MN9 loses one spike (threshold crossing disrupted)
- 5x GRN input weights → MN9 gains one extra spike

### Key Findings

1. **INTERESTING — 2-neuron bottleneck**: The entire sugar→MN9 pathway funnels through exactly 2 keystone neurons. Sparse and specific despite the 15M-synapse connectome.
2. **SURPRISING — Non-monotonic scale response**: Doubling excitatory input can REDUCE output. LIF threshold-crossing timing matters more than total drive.

---

## Experiment 3: Evolution Suite (partial — crashed)

**Date:** 2026-03-15
**Duration:** ~25 min wall time (partial)

### Status: CRASHED due to non-unique DataFrame index bug

- `conn.index[mask]` returned label-based indices; `df.at[idx, col]` returned a Series → TypeError
- Root cause: `pd.read_parquet()` preserves `Presynaptic_Index` as index (label 497 appears 1000 times)
- Fix: `reset_index(drop=True)` in `load_connectome()`, `np.where(mask)[0]` for positional access, `df.iat[pos, col]` everywhere

---

## Experiment 4: Dreams + New Arena Navigation

**Date:** 2026-03-15
**Duration:** 1308s (~22 min)
**Tools used:** `run_neural_only`, `run_embodied`, `dream`, custom `mutate_turn_asym`

### Setup

Four parts: (A) neural survey all stimuli, (B) new arena baseline (fly faces AWAY from food at 75mm), (C) dream with zero input, (D) 20-gen evolution for turning bias via DNa01/DNa02 inputs.

### Results

**PART A: Neural Survey (n_steps=300 = 30ms)**

| Stimulus | fwd_rate | feed_rate | esc_rate | turning_bias |
|----------|----------|-----------|----------|--------------|
| sugar    | 0.0000   | 0.5833    | 0.0000   | 0.0000       |
| p9       | 1.0000   | 0.0000    | 0.0000   | 0.0833       |
| lc4      | 0.1250   | 0.0000    | 1.0000   | 0.0000       |
| jo       | 0.0000   | 0.0000    | 0.0000   | 0.0000       |
| bitter   | 0.0000   | 0.0000    | 0.0000   | 0.0000       |
| or56a    | 0.0000   | 0.0000    | 0.0000   | 0.0000       |

P9 DN breakdown: DNa02_left=1.0000, DNa02_right=0.8333 → asymmetry drives turning. DNa01 fires at 0 for all stimuli. Turning bias is a DNa02-only phenomenon.

NOTE: sugar feed_rate rose to 0.5833 (was 0.0833 in Exp 1). Suspect Hebbian drift from Part B runs contaminated snapshot before Part A. **BUG: investigate.**

**PART B: New Arena Baseline**

| Stimulus | food_dist | dist_traveled | Notes |
|----------|-----------|---------------|-------|
| sugar s42 | 0.2057  | 2.5537        | Barely moves, stays near spawn |
| sugar s43 | 0.1502  | 2.4796        | Same — minimal motion |
| p9 s42    | 22.8835 | 35.8697       | Sprints, ends far from food |
| p9 s43    | 22.7649 | 35.1914       | Same — catastrophic navigation |

**PART C: Dream (1000ms, no input)**
- Total spikes: 0, Active neurons: 0 — brain is completely silent
- Fly still moved: dist_traveled=1.6549, displacement=0.1089 (CPG-only)

**PART D: Turning Bias Evolution**
- Left-turn DN inputs: 1208 synapses; right-turn: 1140
- Gen 0 bias=0.0000 (DISCREPANCY — survey showed 0.0833; see bug below)
- Best: bias=0.1667 after gen 1 (1/20 acceptance); plateau for remaining 19 gens
- Embodied test: mixed Δ (−0.17 and +1.51), no consistent navigation gain

### Key Findings

1. **SURPRISING — Jo/bitter/or56a produce ZERO DN activity in 30ms**: Three stimuli reach no descending neurons at all. Bitter especially surprising — expected escape-like response. These sensory pathways may require >30ms propagation, or don't converge on the 18 mapped DN neurons.

2. **INTERESTING — P9 is 100x worse than sugar at navigation**: Food dist: sugar ~0.18 vs p9 ~22.8. Fast walking away from food overwhelms any turning arc in 2s. Conclusion: **navigation fitness requires controlled speed, not just turning bias**. A stationary fly (sugar) beats a fast-turning fly (p9) in the head-away arena.

3. **INTERESTING — Dreaming brain is completely silent**: Zero spontaneous activity. The LIF model has no intrinsic oscillations or resting state — it requires external drive. CPG locomotion is independent of brain activity (physics-only process in this model).

4. **BUG — Gen 0 turning_bias=0.0000 vs survey 0.0833**: `run_neural_only(conn.copy(), stimulus='p9')` gives different result from `run_neural_only(conn, stimulus='p9')`. Likely cause: (1) Part B runs `run_embodied` which accumulates Hebbian drift that contaminates the snapshot; (2) OR `conn.copy()` dtype mismatch affects `_inject_connectome_weights` behavior. The `_BIO_SYN_SNAPSHOT` system is not robust to intermediate embodied runs.

5. **INTERESTING — Turning bias is quantized**: Steps of 0.0833 (1/12). Matches the Hebbian update window of 10 steps × 0.1ms × 1/step ≈ discrete DN firing events.

### Open Questions

1. What turning radius does bias=0.0833 create? What bias is needed for U-turn in 2s?
2. Over 5-10s with p9, does the natural arc eventually reach food?
3. Can we directly inject maximum asymmetry (DNa02_L=1, DNa02_R=0) in embodied arena?
4. Why do jo/bitter/or56a not reach DNs in 30ms — pathway length or topology?
5. Fix snapshot contamination from intermediate `run_embodied` calls.

### Next Experiment

Experiment 5: Arc geometry scan + maximum-asymmetry navigation test.
- Scan turning_bias values 0→1 via direct synapse injection → find U-turn threshold
- Test maximum asymmetry embodied run (maximize DNa02_L, zero DNa02_R)
- Long-duration p9 run (10s): does natural arc reach food?
- Fix snapshot contamination bug

---

