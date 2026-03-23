"""Tests for compile.evolve."""

import numpy as np
import pytest
import torch
import torch.nn as nn

from compile.evolve import _classify_edges, run_evolution
from compile.simulate import (
    IzhikevichModel,
    build_weight_matrix,
    evaluate_brain,
)


# ---------------------------------------------------------------------------
# Minimal mock brain that satisfies IzhikevichBrainEngine's public interface
# without needing real connectome data.
# ---------------------------------------------------------------------------

class _MiniBrain:
    """
    A tiny brain-like object (N neurons) that can be used with
    ``evaluate_brain`` and ``run_evolution``.
    """

    def __init__(self, num_neurons: int = 8, n_synapses: int = 16, seed: int = 0):
        rng = np.random.RandomState(seed)
        self.num_neurons = num_neurons
        self.device = "cpu"

        # Random synapses
        pre = rng.randint(0, num_neurons, size=n_synapses).astype(np.int64)
        post = rng.randint(0, num_neurons, size=n_synapses).astype(np.int64)
        self._syn_vals = torch.tensor(
            rng.uniform(0.5, 2.0, size=n_synapses), dtype=torch.float32
        )

        # Regular Spiking neuron params
        neuron_params = {
            "a": np.full(num_neurons, 0.02, dtype=np.float32),
            "b": np.full(num_neurons, 0.2, dtype=np.float32),
            "c": np.full(num_neurons, -65.0, dtype=np.float32),
            "d": np.full(num_neurons, 8.0, dtype=np.float32),
        }

        weights = build_weight_matrix(pre, post, self._syn_vals, num_neurons)
        self.model = IzhikevichModel(
            num_neurons, weights, neuron_params, device="cpu",
        )

        # State
        self.state = self.model.state_init()
        self.rates = torch.zeros(1, num_neurons)
        self._spike_acc = torch.zeros(1, num_neurons)
        self._hebb_count = 0

        # DN indices — pick first few neurons
        self.dn_indices = {
            "DN_a": 0,
            "DN_b": 1,
            "DN_c": 2,
        }

        # Stimulus lookup
        self.stim_indices = {
            "test": [3, 4],
        }

        self._pre_idx = torch.tensor(pre, dtype=torch.long)
        self._post_idx = torch.tensor(post, dtype=torch.long)
        self._neuron_params = neuron_params

    def set_stimulus(self, name: str, rate: float | None = None):
        if rate is None:
            rate = 100.0
        self.rates.zero_()
        indices = self.stim_indices.get(name, [])
        if indices:
            self.rates[0, indices] = rate

    def step(self):
        with torch.no_grad():
            v, u, spikes = self.state
            poisson_spikes = (
                torch.rand_like(self.rates) < self.rates * 0.5 / 1000.0
            ).float()
            poisson_current = poisson_spikes * 20.0
            recurrent = torch.mm(spikes, self.model.weights.t()) * 0.002
            total_input = poisson_current + recurrent
            self.state = self.model(self.state, total_input)
            self._spike_acc += self.state[2]

    def _rebuild_weight_matrix(self):
        self.model.weights = build_weight_matrix(
            self._pre_idx.numpy(),
            self._post_idx.numpy(),
            self._syn_vals,
            self.num_neurons,
        )


# ---------------------------------------------------------------------------
# Helper: build synthetic inter-module edge structures for the mini brain
# ---------------------------------------------------------------------------

def _make_edge_structures(brain: _MiniBrain):
    """
    Create ``edge_syn_idx`` and ``inter_module_edges`` from the brain's
    synapse arrays. We treat each (pre, post) pair as its own module edge.
    """
    edge_syn_idx: dict[tuple[int, int], list[int]] = {}
    for i in range(len(brain._pre_idx)):
        key = (int(brain._pre_idx[i].item()), int(brain._post_idx[i].item()))
        edge_syn_idx.setdefault(key, []).append(i)
    inter_module_edges = list(edge_syn_idx.keys())
    return edge_syn_idx, inter_module_edges


# ===========================================================================
# Tests for _classify_edges
# ===========================================================================


class TestClassifyEdges:
    def test_evolvable_category(self):
        """An edge that had at least one accepted mutation is 'evolvable'."""
        mutations = [
            {"pre_module": 0, "post_module": 1, "accepted": True, "delta": 0.5},
            {"pre_module": 0, "post_module": 1, "accepted": False, "delta": -0.1},
        ]
        result = _classify_edges(mutations)
        assert "0->1" in result
        assert result["0->1"]["category"] == "evolvable"
        assert result["0->1"]["accepted"] == 1
        assert result["0->1"]["total_tests"] == 2

    def test_frozen_category(self):
        """An edge where >50% of mutations decrease fitness is 'frozen'."""
        mutations = [
            {"pre_module": 2, "post_module": 3, "accepted": False, "delta": -0.3},
            {"pre_module": 2, "post_module": 3, "accepted": False, "delta": -0.2},
            {"pre_module": 2, "post_module": 3, "accepted": False, "delta": 0.0},
        ]
        result = _classify_edges(mutations)
        assert "2->3" in result
        # 2 out of 3 decreased -> 66% > 50% -> frozen
        assert result["2->3"]["category"] == "frozen"

    def test_irrelevant_category(self):
        """An edge with no accepted and <=50% decreased is 'irrelevant'."""
        mutations = [
            {"pre_module": 5, "post_module": 6, "accepted": False, "delta": 0.0},
            {"pre_module": 5, "post_module": 6, "accepted": False, "delta": 0.0},
            {"pre_module": 5, "post_module": 6, "accepted": False, "delta": -0.01},
        ]
        result = _classify_edges(mutations)
        assert "5->6" in result
        # 1 out of 3 decreased -> 33% <= 50% -> irrelevant
        assert result["5->6"]["category"] == "irrelevant"

    def test_multiple_edges(self):
        """Multiple edges are classified independently."""
        mutations = [
            {"pre_module": 0, "post_module": 1, "accepted": True, "delta": 0.5},
            {"pre_module": 2, "post_module": 3, "accepted": False, "delta": -0.3},
            {"pre_module": 2, "post_module": 3, "accepted": False, "delta": -0.4},
        ]
        result = _classify_edges(mutations)
        assert result["0->1"]["category"] == "evolvable"
        assert result["2->3"]["category"] == "frozen"

    def test_empty_mutations(self):
        assert _classify_edges([]) == {}

    def test_mean_delta_computed(self):
        mutations = [
            {"pre_module": 0, "post_module": 1, "accepted": True, "delta": 1.0},
            {"pre_module": 0, "post_module": 1, "accepted": False, "delta": -1.0},
        ]
        result = _classify_edges(mutations)
        assert result["0->1"]["mean_delta"] == pytest.approx(0.0)


# ===========================================================================
# Tests for run_evolution
# ===========================================================================


class TestRunEvolution:
    @pytest.fixture
    def mini_setup(self):
        brain = _MiniBrain(num_neurons=8, n_synapses=16, seed=0)
        edge_syn_idx, inter_module_edges = _make_edge_structures(brain)

        def fitness_fn(data):
            return float(data["total"].sum())

        return {
            "brain": brain,
            "fitness_fn": fitness_fn,
            "edge_syn_idx": edge_syn_idx,
            "inter_module_edges": inter_module_edges,
        }

    def test_run_evolution_returns_expected_keys(self, mini_setup):
        result = run_evolution(
            brain=mini_setup["brain"],
            fitness_name="test_behavior",
            fitness_fn=mini_setup["fitness_fn"],
            stimulus="test",
            edge_syn_idx=mini_setup["edge_syn_idx"],
            inter_module_edges=mini_setup["inter_module_edges"],
            seed=0,
            n_generations=2,
            n_mutations=3,
            n_steps=10,
        )
        expected_keys = {
            "fitness_name",
            "seed",
            "baseline",
            "final_fitness",
            "improvement",
            "improvement_pct",
            "accepted",
            "total_mutations",
            "edges_tested",
            "n_generations",
            "n_mutations_per_gen",
            "mutations",
            "edge_classification",
        }
        assert set(result.keys()) == expected_keys
        assert result["fitness_name"] == "test_behavior"
        assert result["seed"] == 0
        assert result["n_generations"] == 2
        assert result["n_mutations_per_gen"] == 3
        assert result["total_mutations"] == 6  # 2 gens * 3 mutations

    def test_evolution_improves_fitness(self, mini_setup):
        """Evolution should not make fitness worse (greedy acceptance)."""
        result = run_evolution(
            brain=mini_setup["brain"],
            fitness_name="test_behavior",
            fitness_fn=mini_setup["fitness_fn"],
            stimulus="test",
            edge_syn_idx=mini_setup["edge_syn_idx"],
            inter_module_edges=mini_setup["inter_module_edges"],
            seed=42,
            n_generations=5,
            n_mutations=5,
            n_steps=20,
        )
        # Greedy (1+1) ES never accepts worse solutions
        assert result["final_fitness"] >= result["baseline"]

    def test_evolution_respects_seed(self, mini_setup):
        """Running twice with the same seed should give identical results."""
        kwargs = dict(
            fitness_name="test_behavior",
            fitness_fn=mini_setup["fitness_fn"],
            stimulus="test",
            edge_syn_idx=mini_setup["edge_syn_idx"],
            inter_module_edges=mini_setup["inter_module_edges"],
            seed=99,
            n_generations=3,
            n_mutations=4,
            n_steps=10,
        )

        # First run
        brain1 = _MiniBrain(num_neurons=8, n_synapses=16, seed=0)
        edge_syn_idx1, inter_module_edges1 = _make_edge_structures(brain1)
        r1 = run_evolution(
            brain=brain1,
            edge_syn_idx=edge_syn_idx1,
            inter_module_edges=inter_module_edges1,
            **{k: v for k, v in kwargs.items()
               if k not in ("edge_syn_idx", "inter_module_edges")},
        )

        # Second run — fresh brain with same construction seed
        brain2 = _MiniBrain(num_neurons=8, n_synapses=16, seed=0)
        edge_syn_idx2, inter_module_edges2 = _make_edge_structures(brain2)
        r2 = run_evolution(
            brain=brain2,
            edge_syn_idx=edge_syn_idx2,
            inter_module_edges=inter_module_edges2,
            **{k: v for k, v in kwargs.items()
               if k not in ("edge_syn_idx", "inter_module_edges")},
        )

        assert r1["baseline"] == r2["baseline"]
        assert r1["final_fitness"] == r2["final_fitness"]
        assert r1["accepted"] == r2["accepted"]
        assert len(r1["mutations"]) == len(r2["mutations"])
        for m1, m2 in zip(r1["mutations"], r2["mutations"]):
            assert m1["delta"] == pytest.approx(m2["delta"])
            assert m1["accepted"] == m2["accepted"]

    def test_evolution_different_seeds_differ(self, mini_setup):
        """Different seeds should produce different mutation sequences."""
        kwargs = dict(
            fitness_name="test_behavior",
            fitness_fn=mini_setup["fitness_fn"],
            stimulus="test",
            n_generations=3,
            n_mutations=5,
            n_steps=10,
        )

        brain1 = _MiniBrain(num_neurons=8, n_synapses=16, seed=0)
        esidx1, ime1 = _make_edge_structures(brain1)
        r1 = run_evolution(
            brain=brain1, seed=1,
            edge_syn_idx=esidx1, inter_module_edges=ime1,
            **kwargs,
        )

        brain2 = _MiniBrain(num_neurons=8, n_synapses=16, seed=0)
        esidx2, ime2 = _make_edge_structures(brain2)
        r2 = run_evolution(
            brain=brain2, seed=2,
            edge_syn_idx=esidx2, inter_module_edges=ime2,
            **kwargs,
        )

        # The mutation sequences should differ (different edges picked,
        # different scales). Check that at least one mutation differs.
        any_different = False
        for m1, m2 in zip(r1["mutations"], r2["mutations"]):
            if (m1["pre_module"] != m2["pre_module"]
                    or m1["post_module"] != m2["post_module"]
                    or m1["scale"] != pytest.approx(m2["scale"])):
                any_different = True
                break
        assert any_different, "Two different seeds produced identical mutation sequences"
