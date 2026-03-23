"""Tests for compile.simulate."""

import numpy as np
import torch
import pytest

from compile.simulate import assign_neuron_types, build_weight_matrix, IzhikevichModel
from compile.constants import NEURON_TYPES


class TestAssignNeuronTypes:
    def test_returns_dict_with_abcd_keys(self):
        result = assign_neuron_types(5, ["1", "2", "3", "4", "5"], {}, {})
        assert set(result.keys()) == {"a", "b", "c", "d"}

    def test_arrays_have_correct_shape(self):
        n = 10
        result = assign_neuron_types(n, [str(i) for i in range(n)], {}, {})
        for key in ("a", "b", "c", "d"):
            assert result[key].shape == (n,)
            assert result[key].dtype == np.float32

    def test_defaults_to_regular_spiking(self):
        rs = NEURON_TYPES["RS"]
        result = assign_neuron_types(3, ["1", "2", "3"], {}, {})
        np.testing.assert_allclose(result["a"], rs["a"])
        np.testing.assert_allclose(result["b"], rs["b"])
        np.testing.assert_allclose(result["c"], rs["c"])
        np.testing.assert_allclose(result["d"], rs["d"])

    def test_gaba_neurons_get_fast_spiking(self):
        fs = NEURON_TYPES["FS"]
        rid_to_nt = {"0": "gaba", "1": "", "2": ""}
        result = assign_neuron_types(3, ["0", "1", "2"], rid_to_nt, {})
        assert result["a"][0] == pytest.approx(fs["a"])
        assert result["c"][0] == pytest.approx(fs["c"])

    def test_central_complex_neurons_get_ib(self):
        ib = NEURON_TYPES["IB"]
        rid_to_class = {"0": "CX_neuron", "1": "visual", "2": "EB_ring"}
        result = assign_neuron_types(3, ["0", "1", "2"], {}, rid_to_class)
        # neuron 0 (CX) and 2 (EB) should be IB
        assert result["c"][0] == pytest.approx(ib["c"])
        assert result["c"][2] == pytest.approx(ib["c"])
        # neuron 1 should remain RS
        rs = NEURON_TYPES["RS"]
        assert result["c"][1] == pytest.approx(rs["c"])


class TestBuildWeightMatrix:
    def test_returns_sparse_tensor(self, small_connectome):
        sc = small_connectome
        W = build_weight_matrix(sc["pre"], sc["post"], sc["vals"], sc["num_neurons"])
        assert W.is_sparse_csr
        assert W.shape == (sc["num_neurons"], sc["num_neurons"])

    def test_correct_device(self, small_connectome):
        sc = small_connectome
        W = build_weight_matrix(sc["pre"], sc["post"], sc["vals"], sc["num_neurons"], device="cpu")
        assert str(W.device) == "cpu"

    def test_dtype_is_float32(self, small_connectome):
        sc = small_connectome
        W = build_weight_matrix(sc["pre"], sc["post"], sc["vals"], sc["num_neurons"])
        assert W.dtype == torch.float32


class TestIzhikevichModel:
    @pytest.fixture
    def model(self, small_connectome):
        sc = small_connectome
        W = build_weight_matrix(sc["pre"], sc["post"], sc["vals"], sc["num_neurons"])
        return IzhikevichModel(
            num_neurons=sc["num_neurons"],
            weights=W,
            neuron_params=sc["neuron_params"],
        )

    def test_state_init_shapes(self, model, small_connectome):
        n = small_connectome["num_neurons"]
        v, u, spikes = model.state_init()
        assert v.shape == (1, n)
        assert u.shape == (1, n)
        assert spikes.shape == (1, n)

    def test_state_init_values(self, model):
        v, u, spikes = model.state_init()
        # v should be initialized to v_init (-65.0)
        assert torch.allclose(v, torch.full_like(v, -65.0))
        # spikes should be all zeros
        assert torch.all(spikes == 0)

    def test_forward_output_shapes(self, model, small_connectome):
        n = small_connectome["num_neurons"]
        state = model.state_init()
        synaptic_input = torch.zeros(1, n)
        v_new, u_new, spikes = model(state, synaptic_input)
        assert v_new.shape == (1, n)
        assert u_new.shape == (1, n)
        assert spikes.shape == (1, n)

    def test_forward_voltage_in_range(self, model, small_connectome):
        n = small_connectome["num_neurons"]
        state = model.state_init()
        # Run a few steps with some input
        for _ in range(10):
            synaptic_input = torch.randn(1, n) * 5.0
            state = model(state, synaptic_input)
        v, u, spikes = state
        # Voltage should be clamped between -100 and v_peak (30)
        assert v.min().item() >= -100.0
        assert v.max().item() <= 30.0

    def test_spikes_are_binary(self, model, small_connectome):
        n = small_connectome["num_neurons"]
        state = model.state_init()
        # Drive hard to produce some spikes
        synaptic_input = torch.ones(1, n) * 100.0
        _, _, spikes = model(state, synaptic_input)
        # Spikes should be 0 or 1
        assert torch.all((spikes == 0) | (spikes == 1))
