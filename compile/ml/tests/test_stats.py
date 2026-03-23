"""Tests for compile.stats."""

import numpy as np
import pytest

from compile.stats import bootstrap_ci, cohens_d, improvement_with_ci, permutation_test


class TestBootstrapCI:
    def test_returns_three_floats(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        point, lower, upper = bootstrap_ci(data, seed=42)
        assert isinstance(point, float)
        assert isinstance(lower, float)
        assert isinstance(upper, float)

    def test_lower_le_point_le_upper(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        point, lower, upper = bootstrap_ci(data, seed=42)
        assert lower <= point <= upper

    def test_point_estimate_is_mean(self):
        data = np.array([10.0, 20.0, 30.0])
        point, _, _ = bootstrap_ci(data, seed=42)
        assert point == pytest.approx(20.0)

    def test_constant_data_gives_tight_ci(self):
        data = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
        point, lower, upper = bootstrap_ci(data, seed=42)
        assert point == pytest.approx(5.0)
        assert lower == pytest.approx(5.0)
        assert upper == pytest.approx(5.0)

    def test_reproducible_with_seed(self):
        data = np.random.RandomState(0).randn(50)
        r1 = bootstrap_ci(data, seed=123)
        r2 = bootstrap_ci(data, seed=123)
        assert r1 == r2

    def test_bootstrap_ci_with_known_distribution(self):
        """Draw from N(5, 1); the 95% CI should contain the true mean."""
        rng = np.random.RandomState(7)
        data = rng.normal(loc=5.0, scale=1.0, size=200)
        point, lower, upper = bootstrap_ci(data, ci=0.95, seed=42)
        assert lower <= 5.0 <= upper
        assert point == pytest.approx(np.mean(data))

    def test_bootstrap_ci_seed_reproducibility(self):
        """Same data + same seed must yield bit-identical results."""
        data = np.random.RandomState(10).exponential(2.0, size=80)
        r1 = bootstrap_ci(data, seed=999)
        r2 = bootstrap_ci(data, seed=999)
        assert r1[0] == r2[0]
        assert r1[1] == r2[1]
        assert r1[2] == r2[2]

    def test_bootstrap_ci_wider_at_lower_confidence(self):
        """A 99% CI should be wider than an 80% CI on the same data."""
        data = np.random.RandomState(3).randn(100)
        _, lo80, hi80 = bootstrap_ci(data, ci=0.80, seed=42)
        _, lo99, hi99 = bootstrap_ci(data, ci=0.99, seed=42)
        width80 = hi80 - lo80
        width99 = hi99 - lo99
        assert width99 > width80


class TestPermutationTest:
    def test_returns_stat_and_pvalue(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])
        stat, p = permutation_test(a, b, seed=42, n_permutations=999)
        assert isinstance(stat, float)
        assert isinstance(p, float)

    def test_pvalue_between_0_and_1(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])
        _, p = permutation_test(a, b, seed=42, n_permutations=999)
        assert 0.0 <= p <= 1.0

    def test_identical_groups_high_pvalue(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        _, p = permutation_test(data, data.copy(), seed=42, n_permutations=999)
        # Identical groups should have a high p-value (not significant)
        assert p > 0.05

    def test_very_different_groups_low_pvalue(self):
        a = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        b = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        _, p = permutation_test(a, b, seed=42, n_permutations=999)
        assert p < 0.05

    def test_permutation_test_identical_groups_p_near_one(self):
        """Two copies of the same data -> observed diff ~ 0 -> p near 1."""
        data = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        stat, p = permutation_test(data, data.copy(), seed=7, n_permutations=5000)
        assert stat == pytest.approx(0.0)
        assert p > 0.9

    def test_permutation_test_very_different_groups_significant(self):
        """Clearly separated distributions should give p < 0.05."""
        rng = np.random.RandomState(0)
        a = rng.normal(loc=100.0, scale=1.0, size=30)
        b = rng.normal(loc=0.0, scale=1.0, size=30)
        _, p = permutation_test(a, b, seed=42, n_permutations=5000)
        assert p < 0.05

    def test_permutation_test_seed_reproducibility(self):
        """Same inputs + same seed must give the same p-value."""
        a = np.array([1.0, 3.0, 5.0, 7.0])
        b = np.array([2.0, 4.0, 6.0, 8.0])
        _, p1 = permutation_test(a, b, seed=123, n_permutations=2000)
        _, p2 = permutation_test(a, b, seed=123, n_permutations=2000)
        assert p1 == p2


class TestCohensD:
    def test_identical_groups_return_zero(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        assert cohens_d(data, data.copy()) == 0.0

    def test_returns_float(self):
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([4.0, 5.0, 6.0])
        result = cohens_d(a, b)
        assert isinstance(result, float)

    def test_sign_indicates_direction(self):
        a = np.array([10.0, 11.0, 12.0])
        b = np.array([1.0, 2.0, 3.0])
        # a > b so d should be positive
        assert cohens_d(a, b) > 0
        # Flip -> negative
        assert cohens_d(b, a) < 0

    def test_large_effect(self):
        a = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        b = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        d = cohens_d(a, b)
        assert abs(d) > 0.8  # Large effect

    def test_cohens_d_large_effect_with_small_std(self):
        """Means 0 and 10, small std -> |d| should be very large."""
        rng = np.random.RandomState(0)
        a = rng.normal(loc=0.0, scale=0.1, size=50)
        b = rng.normal(loc=10.0, scale=0.1, size=50)
        d = cohens_d(a, b)
        # With means 10 apart and std ~ 0.1, d should be roughly -100
        assert abs(d) > 10.0

    def test_cohens_d_no_effect(self):
        """Same distribution -> d should be approximately 0."""
        rng = np.random.RandomState(42)
        data = rng.normal(loc=5.0, scale=2.0, size=500)
        # Split into two halves
        a = data[:250]
        b = data[250:]
        d = cohens_d(a, b)
        assert abs(d) < 0.2  # Should be near zero


class TestImprovementWithCI:
    def test_returns_dict_with_expected_keys(self):
        result = improvement_with_ci(10.0, np.array([15.0, 16.0, 14.0]), seed=42)
        expected_keys = {
            "baseline", "mean_evolved", "mean_improvement",
            "ci_lower", "ci_upper", "pct_improvement",
            "pct_ci_lower", "pct_ci_upper", "n_seeds",
        }
        assert set(result.keys()) == expected_keys

    def test_n_seeds_matches_input(self):
        evolved = np.array([15.0, 16.0, 14.0, 17.0])
        result = improvement_with_ci(10.0, evolved, seed=42)
        assert result["n_seeds"] == 4

    def test_baseline_preserved(self):
        result = improvement_with_ci(10.0, np.array([15.0, 16.0]), seed=42)
        assert result["baseline"] == 10.0

    def test_improvement_is_positive_when_evolved_is_better(self):
        result = improvement_with_ci(10.0, np.array([20.0, 21.0, 19.0]), seed=42)
        assert result["mean_improvement"] > 0
        assert result["pct_improvement"] > 0

    def test_improvement_with_ci_all_keys(self):
        """Verify every expected key is present and is a numeric type."""
        result = improvement_with_ci(
            5.0, np.array([6.0, 7.0, 8.0, 9.0, 10.0]), seed=0
        )
        expected_keys = {
            "baseline", "mean_evolved", "mean_improvement",
            "ci_lower", "ci_upper", "pct_improvement",
            "pct_ci_lower", "pct_ci_upper", "n_seeds",
        }
        assert set(result.keys()) == expected_keys
        for key in expected_keys:
            assert isinstance(result[key], (int, float)), f"{key} is not numeric"

    def test_improvement_with_ci_positive_improvement(self):
        """All evolved values > baseline -> CI should be entirely positive."""
        result = improvement_with_ci(
            1.0, np.array([5.0, 6.0, 7.0, 8.0, 9.0]), seed=42
        )
        assert result["mean_improvement"] > 0
        assert result["ci_lower"] > 0
        assert result["pct_improvement"] > 0

    def test_improvement_with_ci_zero_baseline(self):
        """Baseline = 0 should not cause division errors."""
        result = improvement_with_ci(
            0.0, np.array([1.0, 2.0, 3.0]), seed=42
        )
        # Should complete without error
        assert result["baseline"] == 0.0
        assert result["mean_improvement"] > 0
        # Percentage is computed relative to max(|baseline|, 1e-10)
        assert np.isfinite(result["pct_improvement"])
