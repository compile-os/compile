"""
Statistical analysis utilities for evolution experiments.

Provides bootstrap confidence intervals, permutation tests, and effect
sizes for reporting results with proper quantification of uncertainty.
"""

from __future__ import annotations

import numpy as np
from typing import Optional


def bootstrap_ci(
    data: np.ndarray,
    statistic: callable = np.mean,
    n_bootstrap: int = 10000,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> tuple[float, float, float]:
    """
    Compute bootstrap confidence interval for a statistic.

    Args:
        data: 1D array of observations
        statistic: function to compute (default: np.mean)
        n_bootstrap: number of bootstrap resamples
        ci: confidence level (default: 0.95)
        seed: random seed for reproducibility

    Returns:
        (point_estimate, ci_lower, ci_upper)
    """
    rng = np.random.RandomState(seed)
    data = np.asarray(data)
    point = float(statistic(data))

    boot_stats = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(data, size=len(data), replace=True)
        boot_stats[i] = statistic(sample)

    alpha = 1 - ci
    lower = float(np.percentile(boot_stats, 100 * alpha / 2))
    upper = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))

    return point, lower, upper


def permutation_test(
    group_a: np.ndarray,
    group_b: np.ndarray,
    statistic: callable = lambda a, b: np.mean(a) - np.mean(b),
    n_permutations: int = 10000,
    seed: Optional[int] = None,
) -> tuple[float, float]:
    """
    Two-sample permutation test.

    Args:
        group_a, group_b: 1D arrays of observations
        statistic: function(a, b) -> float (default: difference in means)
        n_permutations: number of permutations
        seed: random seed

    Returns:
        (observed_statistic, p_value)
    """
    rng = np.random.RandomState(seed)
    a = np.asarray(group_a)
    b = np.asarray(group_b)
    observed = float(statistic(a, b))

    combined = np.concatenate([a, b])
    n_a = len(a)
    count = 0

    for _ in range(n_permutations):
        rng.shuffle(combined)
        perm_stat = statistic(combined[:n_a], combined[n_a:])
        if abs(perm_stat) >= abs(observed):
            count += 1

    p_value = (count + 1) / (n_permutations + 1)
    return observed, p_value


def cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """
    Cohen's d effect size (pooled standard deviation).

    Interpretation: |d| < 0.2 small, 0.5 medium, 0.8 large.
    """
    a = np.asarray(group_a, dtype=float)
    b = np.asarray(group_b, dtype=float)
    n_a, n_b = len(a), len(b)
    pooled_std = np.sqrt(
        ((n_a - 1) * np.var(a, ddof=1) + (n_b - 1) * np.var(b, ddof=1))
        / (n_a + n_b - 2)
    )
    if pooled_std == 0:
        return 0.0
    return float((np.mean(a) - np.mean(b)) / pooled_std)


def improvement_with_ci(
    baseline: float,
    evolved_values: np.ndarray,
    ci: float = 0.95,
    seed: Optional[int] = None,
) -> dict:
    """
    Report an evolution improvement with confidence interval.

    Args:
        baseline: scalar baseline fitness
        evolved_values: array of evolved fitness values (e.g., across seeds)
        ci: confidence level

    Returns:
        dict with mean_improvement, pct_improvement, ci_lower, ci_upper, n_seeds
    """
    evolved = np.asarray(evolved_values)
    improvements = evolved - baseline
    pct_improvements = improvements / max(abs(baseline), 1e-10) * 100

    mean_imp, ci_lo, ci_hi = bootstrap_ci(improvements, ci=ci, seed=seed)
    mean_pct, pct_lo, pct_hi = bootstrap_ci(pct_improvements, ci=ci, seed=seed)

    return {
        "baseline": float(baseline),
        "mean_evolved": float(np.mean(evolved)),
        "mean_improvement": mean_imp,
        "ci_lower": ci_lo,
        "ci_upper": ci_hi,
        "pct_improvement": mean_pct,
        "pct_ci_lower": pct_lo,
        "pct_ci_upper": pct_hi,
        "n_seeds": len(evolved),
    }
