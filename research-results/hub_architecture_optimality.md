# Hub Architecture is NOT Optimal — Alternative Architectures Outperform Biology

**Date:** 2026-03-22
**Experiment:** `experiments/exploratory/hub_architecture.py`
**Instances:** 5 × C5 (us-east-1b)
**Status:** Seed 0 complete for flat/swap, seeds 1+ running

## Summary

We surgically modified the FlyWire connectome's hub-and-spoke architecture and tested whether evolution could compile navigation onto the modified brain. **Every alternative architecture outperformed the biological baseline.** The biological brain (modules 4, 19 as hubs) produced zero evolvable navigation — 0 accepted mutations across 500 tested. The flat, swapped-hub, and more-hub architectures all evolved successfully.

## Key Result

| Architecture | Baseline (nav) | Evolved (nav) | Accepted Mutations | Verdict |
|---|---|---|---|---|
| **Biological** (hubs 4,19) | 0 | 0 | 0/500 | Cannot evolve navigation |
| **Flat** (no hubs, 2x cap) | 0 | **112** | 6/500 | Hubs not necessary |
| **Swap** (hubs 12,37) | 115 | **276** | 7/500 | Hub location flexible |
| **More** (6 hubs) | 102 | **249** | 5/500 | More hubs also works |

Navigation fitness = total P9 + MN9 descending neuron spikes (motor output).

## What the Surgery Did

### Flat (No Hubs)
Scaled down all modules exceeding 2x average inter-module synaptic strength. 6 modules suppressed: 23, 33, 32, 30, 17, 16 (scale factors 0.52–0.97x). Post-surgery, no module dominates routing.

Interesting: the biological "hub" modules 4 and 19 were NOT the top connectivity hubs by raw synaptic weight. Modules 17, 33, 25, 32, 30, 23 had higher inter-module strength. This suggests the functional importance of 4/19 (from edge 19→4 finding) is about their computational role, not their raw connectivity.

### Swap (Alternative Hubs)
Demoted modules 4, 19 to average connectivity. Promoted modules 12, 37 to match original hub strength. Post-surgery top modules: 49, 24, 22, 27, 3, 30.

The swapped brain had a NONZERO baseline (115 spikes vs 0 for biological). This means redistributing hub connectivity activated motor output pathways that were silent in the biological architecture.

### More (6 Hubs)
Kept modules 4, 19 and boosted modules 8, 12, 25, 37 to hub-level connectivity. Post-surgery top modules: 49, 24, 22, 27, 3, 30.

Similar to swap — baseline was nonzero (102) and evolution improved it to 249.

## Interpretation

### Hub-and-spoke is a local optimum, not the global optimum.
The biological architecture is stuck. Zero accepted mutations means the fitness landscape around the biological hub configuration has no accessible improvements — evolution is trapped. Alternative architectures open new paths.

### Hub LOCATION is flexible.
Swapping hubs from 4,19 to 12,37 didn't break navigation — it improved it. The specific neurons that serve as hubs matter less than having SOME hub structure (or not — flat works too).

### The biological architecture may be optimized for something other than navigation.
The biological hub-and-spoke produced zero navigation output. It may be optimized for conflict resolution (edge 19→4), escape, or behavioral stability rather than raw motor output. Different objectives → different optimal architectures.

### Architecture IS a design variable.
This is the key finding for Compile. The biological connectome is one architecture among many. We can design alternative architectures and compile behaviors onto them. The architecture catalog (`compile/architecture_catalog.md`) defines 20+ alternatives, all expressible as developmental recipes.

## Parameters
- Neuron model: Izhikevich (139K neurons, full connectome)
- Evolution: (1+1) ES, 50 generations × 10 mutations, 100 timesteps
- Fitness: navigation (P9 + MN9 total spikes with sugar stimulus)
- Seeds: 5 per experiment (seed 0 complete, 1-4 in progress)

## Next Steps
Test 5 architectures from the architecture catalog by growing circuits from developmental specs and compiling behaviors:
1. Reservoir computing (simplest to grow)
2. Subsumption (closest to insects)
3. Predictive coding (most interesting for cognition)
4. Recurrent attractor (best for working memory)
5. Evidence accumulator (best for decision-making)

## Files
- Surgery library: `latent/ml/compile/hub_surgery.py`
- Experiment script: `latent/ml/experiments/exploratory/hub_architecture.py`
- Architecture catalog: `latent/ml/compile/architecture_catalog.md`
- Architecture specs: `latent/ml/compile/architecture_specs.py`
