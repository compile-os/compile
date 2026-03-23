"""Shared pytest fixtures for compile tests."""

import numpy as np
import pytest
import torch


@pytest.fixture
def small_connectome():
    """A minimal synthetic connectome with 10 neurons for unit tests.

    Returns a dict with:
        num_neurons: 10
        pre: presynaptic indices
        post: postsynaptic indices
        vals: synapse weight tensor
        neuron_params: dict with a, b, c, d arrays (all Regular Spiking)
    """
    num_neurons = 10
    # Create a small set of synapses (20 random connections)
    rng = np.random.RandomState(42)
    n_synapses = 20
    pre = rng.randint(0, num_neurons, size=n_synapses).astype(np.int64)
    post = rng.randint(0, num_neurons, size=n_synapses).astype(np.int64)
    vals = torch.tensor(rng.uniform(0.1, 1.0, size=n_synapses), dtype=torch.float32)

    # All Regular Spiking parameters
    neuron_params = {
        "a": np.full(num_neurons, 0.02, dtype=np.float32),
        "b": np.full(num_neurons, 0.2, dtype=np.float32),
        "c": np.full(num_neurons, -65.0, dtype=np.float32),
        "d": np.full(num_neurons, 8.0, dtype=np.float32),
    }

    return {
        "num_neurons": num_neurons,
        "pre": pre,
        "post": post,
        "vals": vals,
        "neuron_params": neuron_params,
    }


@pytest.fixture
def mock_dn_indices():
    """Mock DN indices mapping into a 10-neuron network."""
    return {
        "DNa01_left": 0,
        "DNa01_right": 1,
        "DNa02_left": 2,
        "DNa02_right": 3,
        "GF_1": 4,
        "GF_2": 5,
        "P9_left": 6,
        "P9_right": 7,
        "MN9_left": 8,
        "MDN_1": 9,
    }
