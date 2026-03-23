# compile — ML

Neural circuit design via directed evolution on biological connectomes.

## Installation

```bash
cd latent/ml
pip install -e ".[dev]"
```

## Structure

```
ml/
├── compile/               # Shared Python library
│   ├── constants.py       # DN neurons, stimuli, simulation parameters
│   ├── data.py            # Connectome data loading (configurable paths)
│   ├── fitness.py         # Behavioral fitness functions
│   ├── simulate.py        # Izhikevich neuron model and simulation
│   ├── evolve.py          # (1+1) ES evolution loop
│   └── stats.py           # Bootstrap CI, permutation tests
├── experiments/           # All experiment scripts
│   ├── core/              # 8 headline results
│   ├── controls/          # 3 validation scripts
│   ├── growth/            # 4 growth program experiments
│   ├── cross_species/     # 2 mouse cortex scripts
│   ├── exploratory/       # 9 non-core experiments
│   └── legacy/            # Superseded approaches
├── models/                # Backward-compatible model re-exports
├── tests/                 # pytest test suite
├── scripts/               # Utility scripts
├── autoresearch/          # Autonomous research tools
└── autoresearch_connectome/  # Connectome-specific research tools
```

## Data requirements

Set `COMPILE_DATA_DIR` to your data directory, or place files in `./data/`:

- `2025_Connectivity_783.parquet` — FlyWire v783 connectivity
- `2025_Completeness_783.csv` — neuron completeness scores
- `flywire_annotations.tsv` — cell type, hemilineage, neurotransmitter

Download from [flywire.ai](https://flywire.ai). Mouse experiments require MICrONS data via [caveclient](https://github.com/CAVEconnectome/CAVEclient).

## Quick start

```bash
# Run tests (no connectome data needed)
make test

# Verify neuron index derivation
python scripts/derive_neuron_indices.py

# Run core experiments
python experiments/core/edge_sweep.py --fitness navigation
python experiments/core/izh_strategy_switching.py
python experiments/core/exp6_gene_guided.py

# Run all core experiments
make reproduce-core
```

## Using the library

```python
from compile.constants import DN_NEURONS, GAIN, STIM_SUGAR
from compile.data import load_connectome, load_module_labels, build_edge_synapse_index
from compile.fitness import get_fitness
from compile.simulate import IzhikevichBrainEngine, evaluate_brain
from compile.evolve import run_evolution
from compile.stats import bootstrap_ci, improvement_with_ci
```
