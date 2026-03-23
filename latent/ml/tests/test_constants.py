"""Tests for compile.constants."""

from compile.constants import (
    DEFAULT_SIM_PARAMS,
    DN_NAMES,
    DN_NEURONS,
    NEURON_TYPES,
    SIGNATURE_HEMIS,
    STIM_JO,
    STIM_JO_EXTENDED,
    STIM_LC4,
    STIM_LC4_EXTENDED,
    STIM_SUGAR,
)


class TestDNNeurons:
    def test_dn_neurons_has_18_entries(self):
        assert len(DN_NEURONS) == 18

    def test_all_dn_indices_are_nonnegative_ints(self):
        for name, idx in DN_NEURONS.items():
            assert isinstance(idx, int), f"{name} index is not int: {type(idx)}"
            assert idx >= 0, f"{name} index is negative: {idx}"

    def test_dn_names_is_sorted(self):
        assert DN_NAMES == sorted(DN_NAMES)


class TestStimulusLists:
    def test_stim_sugar_nonnegative_ints(self):
        for idx in STIM_SUGAR:
            assert isinstance(idx, int) and idx >= 0

    def test_stim_lc4_nonnegative_ints(self):
        for idx in STIM_LC4:
            assert isinstance(idx, int) and idx >= 0

    def test_stim_lc4_extended_nonnegative_ints(self):
        for idx in STIM_LC4_EXTENDED:
            assert isinstance(idx, int) and idx >= 0

    def test_stim_jo_nonnegative_ints(self):
        for idx in STIM_JO:
            assert isinstance(idx, int) and idx >= 0

    def test_stim_jo_extended_nonnegative_ints(self):
        for idx in STIM_JO_EXTENDED:
            assert isinstance(idx, int) and idx >= 0

    def test_extended_lists_are_supersets(self):
        assert set(STIM_LC4).issubset(set(STIM_LC4_EXTENDED))
        assert set(STIM_JO).issubset(set(STIM_JO_EXTENDED))


class TestSignatureHemis:
    def test_signature_hemis_has_19_entries(self):
        assert len(SIGNATURE_HEMIS) == 19

    def test_all_entries_are_strings(self):
        for h in SIGNATURE_HEMIS:
            assert isinstance(h, str)


class TestSimParams:
    def test_default_sim_params_has_expected_keys(self):
        expected_keys = {
            "dt", "v_peak", "v_init", "u_init_scale",
            "poisson_rate", "poisson_weight", "w_scale", "gain",
        }
        assert set(DEFAULT_SIM_PARAMS.keys()) == expected_keys

    def test_all_values_are_numeric(self):
        for key, val in DEFAULT_SIM_PARAMS.items():
            assert isinstance(val, (int, float)), f"{key} is not numeric: {type(val)}"


class TestNeuronTypes:
    def test_neuron_types_has_expected_entries(self):
        expected = {"RS", "IB", "CH", "FS", "LTS"}
        assert set(NEURON_TYPES.keys()) == expected

    def test_each_type_has_abcd(self):
        for name, params in NEURON_TYPES.items():
            assert set(params.keys()) == {"a", "b", "c", "d"}, f"{name} missing keys"

    def test_all_params_are_floats(self):
        for name, params in NEURON_TYPES.items():
            for key, val in params.items():
                assert isinstance(val, float), f"{name}.{key} is not float"
