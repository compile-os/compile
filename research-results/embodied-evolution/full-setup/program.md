# Compile Autonomous Research Agent — Embodied Evolution

## The Change

Previous experiments used bare LIF with invented fitness functions. Every finding either collapsed or was textbook network science. This session uses **EMBODIED simulation** — the fly brain connected to a MuJoCo physics body via NeuroMechFly. Fitness is REAL BEHAVIOR: did the fly walk to food? How fast? How far?


## CRITICAL BUG FIX — APPLIED 2026-03-15

### The Problem: Brain Activity Never Reached Motor Neurons

Previous experiments showed "brain is a passenger" — mutations didn't affect behavior. This was a **BUG**, not a discovery.

**Root cause:** Brian2's PoissonInput adds 68.75 mV directly to voltage (`target_var='v'`), bypassing the synapse. But the PyTorch implementation put ALL input through the synapse (18-step delay + decay), attenuating the signal to near-zero by the time it reached descending neurons.

### The Fix: Direct Voltage Injection

Modified `brain_body_bridge.py` to inject stimulus spikes directly to voltage (matching Brian2):

```python
# In BrainEngine.step():
POISSON_WEIGHT = 68.75  # mV per spike (w_syn * f_poi = 0.275 * 250)
stim_mask = self.rates[0] > 0
if stim_mask.any():
    prob = (self.rates[0, stim_mask] * 0.1 / 1000.0).clamp(0, 1)
    stim_spikes = torch.bernoulli(prob)
    v[0, stim_mask] = v[0, stim_mask] + stim_spikes * POISSON_WEIGHT
```

### Verification

**Before fix:** Sugar stimulus → 0 DN spikes (signal dies in multi-hop pathway)
**After fix:** Sugar stimulus → 4-13 DN spikes depending on rate (signal propagates!)

| Rate | DN Spikes (500 steps) |
|------|-----------------------|
| 200 Hz | 4 |
| 500 Hz | 6 |
| 1000 Hz | 8 |
| 2000 Hz | 10 |
| 5000 Hz | 13 |

### What This Means

- **All previous "brain is a passenger" findings were artifacts of this bug**
- **Mutations CAN now affect behavior** through the proper signal pathway
- The sugar → gustatory → central processing → DN pathway now works
- Experiments should now show meaningful brain-behavior coupling



## Your tools

## CRITICAL BUGS FOUND AND FIXED (2026-03-15)

### Bug 1: Stimulus Rate Too Low
**Problem:** The Poisson spike generator used `rate * prob_scale` where `prob_scale = 0.0001`. At 200 Hz, this gave only 2% probability per timestep, resulting in 64% of timesteps having ZERO input spikes. The network never built enough activity to propagate signals.

**Fix:** Increased stimulus rates from 200 Hz to 5000 Hz in `brain_body_bridge.py`. This gives ~50% spike probability per timestep, matching Brian2's effective input strength.

### Bug 2: Signal Attenuation Through Multi-Hop Pathways
**Problem:** The path from gustatory neurons (sugar stimulus) to descending neurons (motor output) requires 2-7 synaptic hops. Each hop attenuates the signal, so by the time activity reaches DNs, voltage is still below threshold.

**Status:** Partially addressed. P9 stimulus (which directly activates P9 DN neurons) now works correctly. Sugar stimulus pathway still needs investigation.

**Workaround:** For evolution experiments, prefer P9 stimulus over sugar, OR use multi-seed evaluation that includes "brain-sensitive" seeds where small voltage differences matter.

### Bug 3: Previous Mutation Injection Bugs (FIXED EARLIER)
**Problem:** Two bugs in `capabilities.py` prevented mutations from affecting behavior:
1. `_ORIG_DF_CACHE` was initialized from mutant df instead of biological
2. Int64 truncation in weight column lost fractional mutations

**Fix:** Already fixed in capabilities.py - biological weights now always loaded from parquet file, and weights column cast to float64.

### What This Means For Experiments
- **All previous experiments showing "brain is a passenger"** were artifacts of bug #1
- **P9 stimulus experiments are valid** - DN neurons now fire
- **Sugar stimulus experiments may need higher rates** or longer simulation times
- **Mutations CAN affect behavior** now that bugs #1-3 are fixed


```python
from capabilities import (
    # Evolution tools
    load_connectome, mutate, run_embodied,
    merge_brains, scale_brain, compete,
    crossover, add_plasticity, ablate, transplant,
    # Memory forensics tools
    read_memory, read_all_memories, erase_memory,
    implant_memory, compare_memories, get_mushroom_body_neurons,
)
```

You **CAN and SHOULD** add new functions to `capabilities.py` when you need something that doesn't exist. The toolbox grows with your research.

## What the tools do

| Tool | What it does |
|------|-------------|
| `load_connectome()` | Load FlyWire connectome as DataFrame |
| `mutate(df)` | Modify connectome weights/wiring |
| `run_embodied(df)` | Run brain in physics body, return fitness |
| `merge_brains(orig, a, b)` | Combine mutations from two evolved brains |
| `scale_brain(df, factor)` | Change brain size (0.25x to 2x) |
| `compete(df_a, df_b)` | Run two brains in same arena, compare |
| `crossover(orig, a, b)` | Sexual reproduction — child gets half of each parent |
| `add_plasticity(df, spikes)` | Hebbian learning — synapses change based on activity |
| `ablate(df, neurons)` | Remove specific neurons |
| `transplant(src, tgt, indices)` | Copy specific mutations between brains |
| `read_memory(df, odor)` | Stimulate odor → read MBON response → memory type |
| `read_all_memories(df)` | Complete memory map for all odor channels |
| `erase_memory(df, odor)` | Zero KC→MBON weights for specific odor |
| `implant_memory(df, src, tgt)` | Copy memory pattern between odors |
| `compare_memories(df_a, df_b)` | Diff memory maps between brains |

**Combine them freely. Chain them into pipelines. The more tools per experiment, the more novel the result.**

## Example pipelines

```python
# Evolve → Crossover → Compete
brain_a = evolve_for_navigation(connectome)
brain_b = evolve_for_speed(connectome)
child = crossover(connectome, brain_a, brain_b)
result = compete(child, brain_a)

# Scale → Plasticity → Test recovery
small_brain = scale_brain(connectome, 0.5)
for i in range(10):
    result = run_embodied(small_brain)
    small_brain = add_plasticity(small_brain, result)

# Ablate hubs → Plasticity → Does brain recover?
damaged = ablate(connectome, [720575940640978048])  # Hub neuron
for i in range(10):
    result = run_embodied(damaged)
    damaged = add_plasticity(damaged, result)
```

## Previous findings (do not re-discover)

- 16.7% variance in bare LIF — embodied variance may differ, **measure it FIRST**
- ~8% improvement from LIF evolution — embodied may be different
- Weakening mutations dominated in LIF — check if this holds with behavioral fitness
- Hub structure exists — known network science
- Pruning improves signal-to-noise — known
- Brain is modular — known since 1800s

## Methodology

1. **Measure embodied fitness variance FIRST** (run same brain 5x, compute std)
2. Use 3x averaged fitness unless variance is already low
3. Each experiment must complete in < 30 minutes
4. Save all results as JSON in `results/`
5. Update `lab_notebook.md` after every experiment
6. If surprising, verify with different random seed

## Artifact Detection Rules (CRITICAL)

**1. IDENTICAL RESULTS = BUG.** If 2+ different brains produce the exact same fitness (to 3+ decimal places), something is wrong. Different connectomes MUST produce different behavior. If you see this, the mutation isn't being injected properly.

**2. ATTRACTOR STATES.** The embodied simulation has discrete behavioral modes (walk forward, turn left, groom, stop). Mutations can flip BETWEEN modes rather than improve WITHIN a mode. Always check: did the fly's TRAJECTORY change shape, or did it just switch to a different fixed behavior?

**3. SEED DEPENDENCY.** If a result only appears with one random seed, it's the seed not the mutation. Test every finding with at least 3 different seeds. The biological brain with seed 123 reaches food perfectly — that's the seed, not a mutation.

**4. COMPARE TRAJECTORIES, NOT JUST FITNESS.** Two flies can have the same final distance to food via completely different paths. Save and compare full (x,y) trajectories. Plot them. Use `detect_attractor()` to check for convergence.

**5. BASELINE MUST MATCH.** Before claiming improvement, verify your baseline matches other instances' baselines for the same seed. If your baseline = -1.72 but another instance's baseline for same seed = -0.10, your code has a bug (likely the old deterministic code).

**6. CHECK FOR KNOWN VALUES.** The fitness -0.1004 appears with seed 42 on the biological brain. If your "improved" mutant gets exactly -0.1004, it might just be expressing the seed-42 behavior, not a genuine mutation effect.

```python
# Use this to verify results are real
from capabilities import detect_attractor, verify_result_is_real

# After getting mutation results:
check = verify_result_is_real(mutant_fitness, baseline_fitnesses_all_seeds)
if check['is_suspicious']:
    print(f"WARNING: {check['reason']}")
```

## Data Collection (CRITICAL)

For every experiment, save to JSON:
- **mutation_details**: list of (connection_index, old_weight, new_weight) for each mutation
- **behavioral_trajectory**: fly (x, y) position at each timestep
- **final_fitness**: distance to food
- **spike_summary**: number of active neurons, total spikes, per-region spike counts if available
- **generation**: which generation this was
- **parent_fitness**: fitness before this mutation

**We will do geometric analysis on this data later.** The richer the data per experiment, the more we can extract. A single fitness number is almost worthless. The full trajectory and mutation details are gold.

Example JSON structure:
```json
{
  "experiment": "evolution_gen_5",
  "generation": 5,
  "parent_fitness": -0.15,
  "mutations": [
    {"index": 12345, "old_weight": 0.5, "new_weight": 0.8},
    {"index": 67890, "old_weight": -0.3, "new_weight": -0.1}
  ],
  "trajectory": [[0.0, 0.0], [0.1, 0.02], [0.2, 0.05], ...],
  "final_fitness": -0.12,
  "spike_summary": {
    "total_spikes": 15420,
    "active_neurons": 8234,
    "per_region": {"visual": 2340, "motor": 5120, ...}
  }
}
```

## Your metric: SURPRISE

Rate each experiment:
- **EXPECTED** — move on
- **INTERESTING** — explore adjacent
- **SURPRISING** — verify, then go deep
- **BREAKTHROUGH** — stop everything, characterize fully

## What NOT to do

- Don't measure spike counts. You have real behavior now.
- Don't rediscover network science (hubs, rich clubs, Metcalfe's law)
- Don't run single-tool experiments if you can chain two tools instead
- Don't optimize a single metric endlessly. Explore breadth.

## What to explore

Questions that can ONLY be answered with embodied simulation:

1. Does a fly evolved for walking also get better at turning? (behavioral transfer)
2. Can two separately evolved brains be merged into one that does both tasks?
3. Does a half-size evolved brain outperform a full-size biological brain?
4. Can a damaged brain (hub neurons ablated) recover through Hebbian plasticity?
5. Does adversarial evolution (two flies competing) produce different behaviors?
6. Is crossover offspring more behaviorally robust across different arenas?
7. What's the minimum brain that can still walk?
8. Does the evolved fly LOOK different when it walks? (trajectory shape, speed, turning)
9. Can you evolve a fly that's better at one behavior without losing another?

**But these are starting points. Follow your own curiosity.**

## Memory Forensics — Read This Fly's Life History

The FlyWire connectome is from **ONE specific fly** that lived a specific life. Its memories are encoded in the KC→MBON synaptic weights of the mushroom body. You can READ them.

**New tools:**
```python
from capabilities import (
    read_memory,        # Stimulate one odor → read MBON response → appetitive/aversive/none
    read_all_memories,  # Complete memory map for all ~20 odor channels
    erase_memory,       # Zero KC→MBON weights for specific odor
    implant_memory,     # Copy weight pattern from one odor to another
    compare_memories,   # Diff memory maps between two brains
    get_mushroom_body_neurons,  # Find KC, MBON, DAN indices
)
```

**What you can discover:**
- What odors did this fly learn to like? To avoid? To ignore?
- Are the memories structured (clustered by valence) or random?
- Do evolution/plasticity overwrite existing memories?
- Does crossover inheritance include memories? Which parent's?
- Can you erase a fear memory and change behavior?
- Can you implant a fake memory and observe navigation change?

**Memory + Evolution pipelines:**
```python
# Read memories before and after evolution
mem_before = read_all_memories(connectome)
evolved, _ = mutate(connectome, n_mutations=1000)
mem_after = read_all_memories(evolved)
diff = compare_memories(connectome, evolved)
# → Which memories survived evolution?

# Erase a memory and test behavior
erased, details = erase_memory(connectome, 'DL5')  # CO2 avoidance
result_erased = run_embodied(erased)
result_original = run_embodied(connectome)
# → Does the fly now approach what it avoided?

# Compare parent and offspring memories
child = crossover(connectome, parent_a, parent_b)
diff_a = compare_memories(parent_a, child)
diff_b = compare_memories(parent_b, child)
# → Which parent's memories dominate in the child?

# Does Hebbian plasticity CREATE memories?
mem_before = read_all_memories(connectome)
plastic = add_plasticity(connectome, spike_data, rule='hebbian')
mem_after = read_all_memories(plastic)
# → New memories formed during simulation?
```

**The company angle:** If you can demonstrate reading a fly's memories from its connectome, the implications cascade: forensic neuroscience, drug development (did this drug erase the memory?), brain-computer interfaces, AI interpretability.

**This is not optimization. This is FORENSICS. Reading the life history of a dead brain.**

## Dreams — Spontaneous Activity Without Input

Run the brain with **ZERO sensory input**. No food, no odor, no light, no touch.
The spontaneous activity that emerges is the connectome dreaming.

**New tools:**
```python
from capabilities import (
    dream,                    # Run brain in darkness, record all spontaneous activity
    compare_dream_to_waking,  # Which waking neurons replay during dreams?
    dream_memory_replay,      # Which memories replay during dreams?
    sleep_between_generations,# Does dreaming between evolution gens help?
)
```

**What you can discover:**
- Does the fly's body MOVE during dreaming? Which motor programs fire spontaneously?
- Do MBONs activate during dreams? Which memories replay?
- Compare dream activity to waking — does the brain replay navigation sequences?
- Do evolved brains dream DIFFERENTLY than biological?
- Erase a memory → dream → does the erased memory stop replaying?
- Does dreaming between evolution generations speed up improvement?

**Dream experiments:**
```python
# Basic dream
dream_result = dream(connectome, duration_ms=2000)
print(f"Body moved: {dream_result['body_moved']}")
print(f"Active neurons: {dream_result['active_neurons']}")

# Compare dream to waking
waking = run_embodied(connectome, stimulus='sugar')
dream_result = dream(connectome)
overlap = compare_dream_to_waking(dream_result, waking)
# → High overlap = memory consolidation

# Which memories replay?
replay = dream_memory_replay(connectome)
print(f"Dominant replay: {replay['mbon_replay']['dominant_type']}")
# → Does it dream about food it liked or things it avoided?

# Does sleep help evolution?
result = sleep_between_generations(connectome, my_evolve_fn, n_generations=5)
print(f"Sleep advantage: {result['sleep_advantage']}")
# → If positive, dreaming serves a computational function
```

**The insight:** Drosophila DO sleep in real life. Sleep is when memories consolidate.
If dream activity patterns correlate with stored memories, that's evidence the connectome
encodes not just what the fly learned, but how it REHEARSES what it learned.

## The loop

1. Read `lab_notebook.md`
2. Design experiment using 1+ tools
3. Write `experiment.py`
4. Run it (< 30 min)
5. Analyze — check for artifacts, compare to baseline
6. Update `lab_notebook.md` with findings and surprise rating
7. If you need a new tool, add it to `capabilities.py`
8. Follow surprises deeper or change direction
9. **NEVER STOP**

## Starting direction

Your first experiment: run the **BIOLOGICAL (unmodified)** fly in the embodied simulation. Measure baseline behavioral fitness. Run it 5 times. Compute mean and std. This is your reference point for everything that follows.

Then pick any two tools and combine them.

## Files

```
/home/ubuntu/autoresearch/
├── program.md          # This file
├── capabilities.py     # Your tools (add more!)
├── experiment.py       # Current experiment
├── lab_notebook.md     # Results log
└── results/            # JSON outputs

/home/ubuntu/fly-brain-embodied/
├── fly_embodied.py     # Full embodied simulation
├── brain_body_bridge.py # DN → motor commands
├── data/               # Connectome data
└── ...                 # Other modules
```

## Running experiments

```python
# experiment.py
import sys
sys.path.insert(0, '/home/ubuntu/autoresearch')
from capabilities import load_connectome, run_embodied, mutate

# Load biological brain
connectome = load_connectome()
print(f"Loaded {len(connectome)} synapses")

# Baseline
baseline = run_embodied(connectome)
print(f"Baseline fitness: {baseline['fitness']:.4f}")

# Mutate and test
mutated, indices = mutate(connectome, n_mutations=5)
result = run_embodied(mutated)
print(f"Mutated fitness: {result['fitness']:.4f}")
```

Run with: `python3 experiment.py`

## ARENA FIX — DEPLOYED 2026-03-15

### The Problem: Food Too Close to Start
The original arena placed food at 10mm from the fly's starting position. The fly started 
near the food, so "doing nothing" got high fitness. The sugar stimulus correctly triggers 
"freeze to eat" behavior — which was being rewarded because the fly was already at the food.

**This tested "does the brain suppress locomotion?" not "can the brain navigate?"**

### The Fix
1. **Food position**: [10, 0, 0]mm → **[75, 0, 0]mm** (75mm from origin)
2. **Fly orientation**: spawn_orientation = (0, 0, π) — **fly faces AWAY from food**
3. **Required behavior**: fly must TURN 180° and WALK 75mm to reach food

### Expected Behavior
- **Zero brain** (CPG only): walks forward (away from food), ends ~150-200mm from food
- **Good brain**: turns toward food, walks to it, fitness → 0
- **Bad brain**: walks away from food, fitness → -0.2 or worse

### Fitness Metric (unchanged)
```python
fitness = -food_distance  # Higher = better (closer to food)
```

### Implications for Evolution
- Sugar stimulus "freeze" behavior now HURTS fitness (fly stays far from food)
- P9 left-turn bias might help or hurt depending on turn direction
- Evolution can optimize for turning + navigation, not just locomotion suppression

