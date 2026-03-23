# Next Experiments

Concrete experiments to run, prioritized. These directly feed product features.

## Priority 1: Pairwise Interference Matrix on Generated Architectures

The original interference matrix (Result 10) was only on hub-and-spoke. We know circular locomotion + escape conflict on the fly brain. We DON'T know which behavior pairs conflict on cellular automaton, WTA, or reservoir.

**Experiment:** Run the full pairwise interference matrix on the top 3 architectures (cellular_automaton, spiking_state_machine, winner_take_all). For each pair of behaviors, compile both onto the same circuit and measure whether the second degrades the first.

**Why it matters:** The composite recommendation engine assumes behaviors can be combined freely. If specific pairs interfere on specific architectures, the engine needs conflict rules.

**Estimate:** 3 architectures × 10 behavior pairs × 3 seeds = 90 runs. ~2 hours on one instance.

## Priority 2: Multi-Behavior-Per-Region Composites

The 10-region composite scaled without degradation — but that was one behavior (navigation) evaluated across all regions. The real question: does compiling DIFFERENT behaviors onto DIFFERENT regions of the same composite degrade any of them?

**Experiment:** CA region (navigation + WM) + WTA region (conflict) + reservoir region (self-prediction). Compile all simultaneously. Measure each behavior's score vs the single-architecture baseline.

**Why it matters:** This validates the composite recommendation engine's core assumption: that regions don't interfere through interface connections when running different behaviors.

**Estimate:** 1 composite × 4 behaviors × 3 seeds = 12 runs. ~30 min.

## Priority 3: 3-Tier with More Seeds and Generations

Current 3-tier data: 10 seeds, 200 gen. Tier 3 mean = 12.3%, 7/10 seeds > 5%, peak 40%.

**Experiment:** Run 20 seeds at 500 generations. Does Tier 3 improve with more evolution? Is 12.3% a ceiling or still climbing?

**Why it matters:** Determines whether recursive self-monitoring is a reliable capability or requires specific lucky seeds.

## Priority 4: Oscillatory with Izhikevich

Oscillatory architecture scored 0 across all tasks. The architecture is correct but LIF neurons can't produce oscillations — they need the richer dynamics of Izhikevich (persistent activity, bursting, resonance).

**Experiment:** Run oscillatory on rhythm_alt with Izhikevich neuron parameters (already in the simulator). If it works, the architecture catalog gets its first rhythm-specialized entry with real data.

## Priority 5: Embodied Validation

Run the top 3 architectures through Eon's embodied simulation (MuJoCo + NeuroMechFly). The current fitness functions measure DN spike counts. Embodied validation measures actual behavioral performance — does the fly walk to food?

**Why it matters:** The gap between spike counts and real behavior. A circuit could score high on spikes without producing coherent locomotion.

## Completed Experiments (Reference)

All results in `latent/ml/results/`:
- 26 architectures × 5 tasks (130 results)
- Hub architecture optimality (flat/swap/more vs biological)
- Depression/tau/duration sweeps (partial)
- Exp 6: Structured vs random growth (no difference)
- Exp 7: CA+WTA composite (matches or exceeds either alone)
- Exp 8: Scale sensitivity (3K minimum viable)
- Exp 9: Adaptation (reservoir 3.4x novelty, reward-modulated 6x)
- Rhythm validation (CA 5.44, ring 0.41)
- Multi-behavior (CA 84.68 combined)
- Self-prediction (reservoir 85%)
- 2-tier (31-70% prediction)
- 3-tier 10 seeds (Tier 3 mean 12.3%)
- Composite scaling (2-10 regions, 28K neurons, no degradation)
- Composite pairs (CA+reservoir, WTA+reservoir)
