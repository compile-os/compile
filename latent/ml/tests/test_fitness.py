"""Tests for compile.fitness."""

import numpy as np
import pytest

from compile.fitness import (
    FITNESS_FUNCTIONS,
    f_arousal,
    f_esc,
    f_nav,
    f_turn,
    fitness_arousal,
    fitness_escape,
    fitness_navigation,
    fitness_turning,
    get_fitness,
)


class TestRegistry:
    def test_fitness_functions_has_6_entries(self):
        assert len(FITNESS_FUNCTIONS) == 6

    def test_all_expected_behaviors_present(self):
        expected = {"navigation", "escape", "turning", "arousal", "circles", "rhythm"}
        assert set(FITNESS_FUNCTIONS.keys()) == expected

    def test_each_entry_is_3_tuple(self):
        for name, entry in FITNESS_FUNCTIONS.items():
            assert len(entry) == 3, f"{name} entry has {len(entry)} elements, expected 3"
            stim_name, array_fn, dict_fn = entry
            assert isinstance(stim_name, str)
            assert callable(array_fn)
            assert callable(dict_fn)

    def test_get_fitness_returns_valid_entry(self):
        stim, arr_fn, dict_fn = get_fitness("navigation")
        assert stim == "sugar"
        assert callable(arr_fn)
        assert callable(dict_fn)

    def test_get_fitness_raises_keyerror_for_unknown(self):
        with pytest.raises(KeyError, match="Unknown fitness function"):
            get_fitness("nonexistent_behavior")


class TestArrayBasedFitness:
    """Test array-based fitness functions with synthetic data."""

    @pytest.fixture
    def mock_eval_data(self):
        """Synthetic evaluate_brain output for 5 DN neurons."""
        names = ["DNa01_left", "DNa01_right", "GF_1", "MN9_left", "P9_left"]
        n_windows = 10
        total = np.array([5.0, 3.0, 8.0, 4.0, 6.0])
        windowed = np.random.RandomState(0).rand(n_windows, len(names))
        return {
            "dn_names": names,
            "total": total,
            "windowed": windowed,
            "n_windows": n_windows,
        }

    def test_fitness_navigation_returns_float(self, mock_eval_data):
        result = fitness_navigation(mock_eval_data)
        assert isinstance(result, float)

    def test_fitness_escape_returns_float(self, mock_eval_data):
        result = fitness_escape(mock_eval_data)
        assert isinstance(result, float)

    def test_fitness_turning_returns_float(self, mock_eval_data):
        result = fitness_turning(mock_eval_data)
        assert isinstance(result, float)

    def test_fitness_arousal_returns_float(self, mock_eval_data):
        result = fitness_arousal(mock_eval_data)
        assert isinstance(result, float)

    def test_fitness_navigation_sums_p9_mn9(self, mock_eval_data):
        # P9_left (6.0) + MN9_left (4.0) = 10.0
        result = fitness_navigation(mock_eval_data)
        assert result == 10.0

    def test_fitness_escape_sums_gf(self, mock_eval_data):
        # GF_1 (8.0), no MDN in this dataset
        result = fitness_escape(mock_eval_data)
        assert result == 8.0

    def test_fitness_arousal_sums_all(self, mock_eval_data):
        result = fitness_arousal(mock_eval_data)
        assert result == pytest.approx(26.0)


class TestDictBasedFitness:
    """Test dict-based fitness functions with known inputs."""

    def test_f_nav_known_input(self):
        dn = {"P9_left": 10, "P9_right": 5, "MN9_left": 3}
        assert f_nav(dn) == 18.0

    def test_f_nav_empty_dict(self):
        assert f_nav({}) == 0.0

    def test_f_esc_known_input(self):
        dn = {"GF_1": 10, "GF_2": 5}
        assert f_esc(dn) == 15.0

    def test_f_esc_with_mdn(self):
        dn = {"GF_1": 10, "GF_2": 5, "MDN_1": 3, "MDN_2": 2, "MDN_3": 1, "MDN_4": 4}
        assert f_esc(dn) == 25.0

    def test_f_turn_symmetric_input(self):
        dn = {"DNa01_left": 10, "DNa01_right": 10, "DNa02_left": 5, "DNa02_right": 5}
        # abs(15 - 15) + (15 + 15) * 0.1 = 0 + 3.0 = 3.0
        assert f_turn(dn) == pytest.approx(3.0)

    def test_f_turn_asymmetric_input(self):
        dn = {"DNa01_left": 10, "DNa01_right": 0}
        # abs(10 - 0) + (10 + 0) * 0.1 = 10 + 1.0 = 11.0
        assert f_turn(dn) == pytest.approx(11.0)

    def test_f_arousal_sums_all_values(self):
        dn = {"A": 1, "B": 2, "C": 3}
        assert f_arousal(dn) == 6.0

    def test_all_dict_functions_return_float(self):
        dn = {"P9_left": 5, "GF_1": 3, "DNa01_left": 2}
        for fn in [f_nav, f_esc, f_turn, f_arousal]:
            result = fn(dn)
            assert isinstance(result, float), f"{fn.__name__} did not return float"
