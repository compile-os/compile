# Curvature Predicts Evolvability in the Fly Brain
## Compile Definitive Experiment — Results

### Hypothesis
Beneficial mutations in fly brain evolution preferentially occur on high-curvature edges of the module graph.

### Result: CONFIRMED (p = 2.16 × 10⁻²¹)

### Data
- 75 beneficial mutations across 4 independent evolution runs
- 50 functional modules, 2,500 inter-module edges with Ollivier-Ricci curvature
- FlyWire connectome: 138,639 neurons, 15,091,983 synapses

### Key Findings

| Dataset | N mutations | Fitness gain | Mean κ (mutation) | Mean κ (all) | p-value | Q4 % |
|---|---|---|---|---|---|---|
| nav_seed42 | 30 | +11.1% | 0.9006 | 0.7514 | 5.86e-09 | 70% |
| nav_seed123 | 15 | +8.0% | 0.9266 | 0.7514 | 6.50e-07 | 87% |
| layer1_universal | 5 | — | 0.9075 | 0.7514 | 1.09e-02 | 80% |
| layer2_specific | 25 | — | 0.8992 | 0.7514 | 1.54e-07 | 68% |
| **COMBINED** | **75** | — | **0.9058** | **0.7514** | **2.16e-21** | **73%** |

- **Effect size (Cohen's d): 1.018** (large)
- **Spearman ρ = 0.118, p = 3.28e-09** (curvature correlates with mutation frequency)
- **0% of mutations on lowest-curvature edges** (Q1)
- **73% of mutations on highest-curvature edges** (Q4)
- Expected if random: 25% per quartile

### Interpretation

Evolution preferentially modifies HIGH-curvature (redundant) inter-module connections.

Positive curvature (κ → 1) means module neighborhoods overlap heavily — many parallel pathways exist. Evolution acts here because:
1. **Safety**: Redundant connections can be modified without catastrophic failure (backup pathways exist)
2. **Leverage**: Dense inter-module connections have more "surface area" for beneficial tweaks
3. **Evolvability**: The biological brain is structured to be evolvable at specific geometric locations

Low-curvature edges (bottlenecks/bridges) are NEVER modified by evolution — they're too critical. Changing a bridge connection risks disconnecting modules entirely.

### Implications for Compile

The brain's "programming language" is geometric:
- **Primitives** = functional modules (evolution doesn't touch them)
- **Syntax** = inter-module connection topology
- **Semantics** = curvature of connections predicts computational role
- **Evolvability** = curvature predicts WHERE the brain can be safely modified

This validates the GU-inspired hypothesis: computation is curvature of connections.

### Prior Results This Builds On
1. Evolution improved fly brain fitness 31% by changing ONLY inter-module wiring (23 mutations, 0 core circuits)
2. Local node features predict nothing about function (R² ≈ 0)
3. Module graph: 50 modules, 14.4M inter-module connections

### Methods
- Module assignment: 50 functional modules from FlyWire cell type annotations
- Curvature: Ollivier-Ricci curvature using Wasserstein-1 distance (POT library)
- Evolution: Single-synapse mutations with embodied fitness evaluation
- Statistical tests: Mann-Whitney U (non-parametric), Spearman rank correlation
