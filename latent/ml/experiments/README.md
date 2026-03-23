# Experiments

All experiment scripts from the research sprint. Each imports from the shared `compile` library (`pip install -e .` from `latent/ml/`).

## Structure

```
experiments/
├── core/           8 scripts producing headline results
├── controls/       3 validation and robustness checks
├── growth/         4 growth program experiments
├── cross_species/  2 mouse cortex pipeline scripts
├── exploratory/    9 non-core experiments
└── legacy/         13 superseded or failed approaches
```

## Setup

```bash
cd latent/ml
pip install -e ".[dev]"
export COMPILE_DATA_DIR=/path/to/flywire/data
```

## Neuron models

Two spiking neuron models are used:

- **LIF (BrainEngine)**: Eon Systems' leaky integrate-and-fire model via `brain_body_bridge`. Used for reactive behaviors. Requires the Eon `fly-brain-embodied` codebase.
- **Izhikevich**: Richer dynamics supporting persistent activity and attractor states. Used for cognitive capability experiments. Implemented in `compile.simulate`.

Key result: edge 19→4 appears in BOTH models — the finding is model-independent.

## External dependencies

The LIF model (`--model lif` flag) requires [Eon Systems' fly-brain-embodied](https://eon.systems) codebase, which provides `brain_body_bridge.BrainEngine`. This is NOT included in the compile package and is not required for any core result — all headline findings are replicated on the Izhikevich model.

To run LIF experiments:
1. Clone the [fly-brain-embodied](https://eon.systems) repository
2. Add it to your Python path: `export PYTHONPATH=/path/to/fly-brain-embodied/code:$PYTHONPATH`

All experiments default to Izhikevich if BrainEngine is not available.

## Core scripts

| Script | Model | Result | Key finding |
|--------|-------|--------|-------------|
| `edge_sweep.py` | LIF | Behavior-dependent modifiability | Turning: 91% frozen; Escape: 89% evolvable |
| `bulletproof_evolution.py` | LIF | Compiled behaviors | 8 reactive behaviors, 5 seeds each |
| `izhikevich_brain.py` | Izh | Neuron model validation | Drop-in replacement for LIF with persistent activity |
| `izh_strategy_switching.py` | Izh | Conflict resolution | +153% improvement, edge 19→4 model-independent |
| `exp6_gene_guided.py` | Izh | Gene-guided extraction | 8,158 neurons, 19 hemilineages, 19x more active |
| `exp6_developmental_compiler.py` | Izh | Growth program | 19 cell types, 30 connection rules |
| `interference_matrix.py` | Izh | Processor specification | 9/10 behavior pairs compatible |
| `expA_prediction.py` | Izh | Prediction validation | 9/10 confirmed, +58% untargeted escape |

## Controls

| Script | Tests | Result |
|--------|-------|--------|
| `critical_controls.py` | Random baseline + scale sensitivity | Gene-guided 834 vs random 0/0/0/0/0. Scale: 44% agreement at 1.5x |
| `distraction_control.py` | Distraction resistance claim | **RETRACTED** — uncompiled brain shows same bias (4.7x vs 4.9x) |
| `izh_persistence_test.py` | CX persistent activity | PASSED — 11-14 spikes/step for 500+ steps after stimulus removal |

## Growth

| Script | Approach | Result |
|--------|----------|--------|
| `growth_simulation.py` | Bundle growth model | Hybrid 96.6% of real brain performance; implementable features predict 7-9% of connections |
| `growth_behavioral_test.py` | Sequential activity-dependent growth | Nav score 851 vs FlyWire 577 vs random 459 at 1.45% density; growth order critical (sequential works, random order dead) |
| `trajectory_growth.py` | Axon trajectory fitting | F1=0.93% — too simple |
| `axon_trajectory_model.py` | Agent-based axon growth | Iterated on parameters |

## Cross-species

| Script | Species | Result |
|--------|---------|--------|
| `exp5_microns.py` | Mouse (MICrONS) | Data loading and cortical module extraction |
| `mouse_full_pipeline.py` | Mouse (MICrONS) | Full compile pipeline on V1 cortex |

## Data requirements

All scripts load data via `compile.data.load_connectome()`. Set `COMPILE_DATA_DIR` to your data directory, or place files in `./data/`:

- `2025_Connectivity_783.parquet`
- `2025_Completeness_783.csv`
- `flywire_annotations.tsv`
- `module_labels_v2.npy` (set `COMPILE_MODULE_LABELS` or place in `./data/`)

Mouse scripts require MICrONS data via [caveclient](https://github.com/CAVEconnectome/CAVEclient).

## Gain parameter

All scripts use `GAIN = 8.0` (synaptic weight multiplier), imported from `compile.constants`. Validated at 4x-8x — both cognitive capabilities compile at every gain level tested. 7x is optimal. See `controls/critical_controls.py`.

## Evolution method

All evolution experiments use a (1+1) evolutionary strategy via `compile.evolve.run_evolution()`. See the root README for justification of this method choice and its limitations.
