"""
compile — shared library for connectome evolution experiments.

Provides reusable constants, data loaders, fitness functions, simulation
utilities, and evolution routines used across all experiment scripts.

Install with: pip install -e latent/ml
"""

from compile.constants import (
    DN_NEURONS,
    DN_FLYIDS,
    STIM_SUGAR,
    STIM_LC4,
    STIM_LC4_EXTENDED,
    STIM_JO,
    STIM_JO_EXTENDED,
    STIMULUS_MAP,
    SIGNATURE_HEMIS,
    DEFAULT_SIM_PARAMS,
    NEURON_TYPES,
)
from compile.data import load_connectome, load_annotations, load_module_labels
from compile.fitness import FITNESS_FUNCTIONS, get_fitness
from compile.simulate import IzhikevichModel, IzhikevichBrainEngine, izh_step, run_simulation
from compile.evolve import run_evolution

__version__ = "0.1.0"
