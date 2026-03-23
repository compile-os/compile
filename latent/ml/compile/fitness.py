"""
Fitness functions for connectome evolution.

Each function scores a brain's behavioral output. Two interfaces are provided:

1. **Array-based** (``fitness_*``): Takes the output dict from ``evaluate_brain()``
   with keys ``dn_names``, ``total``, ``windowed``, ``n_windows``.
   Used by evolution loops that call the full simulation.

2. **Dict-based** (``f_*``): Takes a ``{dn_name: spike_count}`` dict.
   Used by inline simulation loops (e.g., gene-guided experiments).

Both return a float score (higher = better).
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Array-based fitness functions (for evaluate_brain output)
# ---------------------------------------------------------------------------

def fitness_navigation(data: dict) -> float:
    """Forward locomotion: P9 + MN9 total spikes."""
    names = data["dn_names"]
    p9_idx = [i for i, n in enumerate(names) if "P9" in n or "MN9" in n]
    return float(sum(data["total"][i] for i in p9_idx))


def fitness_escape(data: dict) -> float:
    """Escape response: GF + MDN total spikes."""
    names = data["dn_names"]
    gf_idx = [i for i, n in enumerate(names) if "GF" in n]
    mdn_idx = [i for i, n in enumerate(names) if "MDN" in n]
    return float(
        sum(data["total"][i] for i in gf_idx)
        + sum(data["total"][i] for i in mdn_idx)
    )


def fitness_turning(data: dict) -> float:
    """Turning: left-right asymmetry of DNa01 + DNa02, plus baseline activity."""
    names = data["dn_names"]
    da01_l = names.index("DNa01_left") if "DNa01_left" in names else -1
    da01_r = names.index("DNa01_right") if "DNa01_right" in names else -1
    da02_l = names.index("DNa02_left") if "DNa02_left" in names else -1
    da02_r = names.index("DNa02_right") if "DNa02_right" in names else -1

    left = data["total"][da01_l] + (data["total"][da02_l] if da02_l >= 0 else 0)
    right = data["total"][da01_r] + (data["total"][da02_r] if da02_r >= 0 else 0)
    # 0.1 baseline weight: small reward for any turning activity even if symmetric,
    # preventing the optimizer from silencing all turning neurons to minimize asymmetry.
    return float(abs(left - right) + (left + right) * 0.1)


def fitness_arousal(data: dict) -> float:
    """General arousal: total spikes across all DN neurons."""
    return float(data["total"].sum())


def fitness_circles(data: dict) -> float:
    """Circling: sustained asymmetric turning + weak forward drive."""
    names = data["dn_names"]
    da01_l = names.index("DNa01_left") if "DNa01_left" in names else -1
    da01_r = names.index("DNa01_right") if "DNa01_right" in names else -1
    da02_l = names.index("DNa02_left") if "DNa02_left" in names else -1
    da02_r = names.index("DNa02_right") if "DNa02_right" in names else -1

    windowed = data["windowed"]
    turn_per_window = np.zeros(data["n_windows"])
    for w in range(data["n_windows"]):
        l = windowed[w, da01_l] + (windowed[w, da02_l] if da02_l >= 0 else 0)
        r = windowed[w, da01_r] + (windowed[w, da02_r] if da02_r >= 0 else 0)
        turn_per_window[w] = l - r

    cumulative = np.cumsum(turn_per_window)
    displacement = abs(cumulative[-1]) if len(cumulative) > 0 else 0
    consistency = (
        abs(np.mean(np.sign(turn_per_window + 1e-10)))
        if len(turn_per_window) > 0
        else 0
    )
    p9_idx = [i for i, n in enumerate(names) if "P9" in n or "MN9" in n]
    fwd = sum(data["total"][i] for i in p9_idx) if p9_idx else 0
    # 0.1 forward weight: weak forward drive keeps the fly moving while circling,
    # preventing stationary rotation.
    return float(displacement + consistency * 5.0 + fwd * 0.1)


def fitness_rhythm(data: dict) -> float:
    """Rhythmic activity: on/off alternation in windowed spike counts."""
    windowed = data["windowed"]
    n_windows = data["n_windows"]
    if n_windows < 4:
        return 0.0
    activity = windowed.sum(axis=1)
    on = np.mean(activity[0::2])
    off = np.mean(activity[1::2])
    # 0.05 baseline: small reward for overall activity to prevent silent solutions.
    return float(max(0, on - off) + activity.mean() * 0.05)


# ---------------------------------------------------------------------------
# Dict-based fitness functions (for inline simulation loops)
# ---------------------------------------------------------------------------

def f_nav(dn: dict) -> float:
    """Forward locomotion from DN spike dict."""
    return float(sum(
        dn.get(n, 0) for n in
        ["P9_left", "P9_right", "MN9_left", "MN9_right", "P9_oDN1_left", "P9_oDN1_right"]
    ))


def f_esc(dn: dict) -> float:
    """Escape from DN spike dict."""
    return float(sum(
        dn.get(n, 0) for n in
        ["GF_1", "GF_2", "MDN_1", "MDN_2", "MDN_3", "MDN_4"]
    ))


def f_turn(dn: dict) -> float:
    """Turning from DN spike dict."""
    l = sum(dn.get(n, 0) for n in ["DNa01_left", "DNa02_left"])
    r = sum(dn.get(n, 0) for n in ["DNa01_right", "DNa02_right"])
    return float(abs(l - r) + (l + r) * 0.1)


def f_arousal(dn: dict) -> float:
    """Arousal from DN spike dict."""
    return float(sum(dn.values()))


def f_circles(dn: dict) -> float:
    """Circling (simplified) from DN spike dict."""
    return float(f_turn(dn) + f_nav(dn) * 0.1)


def f_rhythm(dn: dict) -> float:
    """Rhythm (simplified) from DN spike dict."""
    return float(f_arousal(dn) * 0.05)


def f_rhythm_alternation(bins: list[float]) -> float:
    """Proper rhythm metric: measures alternation between consecutive bins.

    Args:
        bins: list of activity values per time bin (e.g., 10-step windows)

    Score = number of sign changes in consecutive bin differences.
    Pure sustained activity: 0 (no alternation)
    Pure silence: 0 (nothing to alternate)
    Perfect on-off-on-off: maximum score

    Also rewards higher amplitude oscillations — weak flicker scores less
    than strong on-off swings.
    """
    if len(bins) < 4:
        return 0.0

    # Count sign changes (alternations)
    diffs = [bins[i+1] - bins[i] for i in range(len(bins) - 1)]
    alternations = 0
    for i in range(len(diffs) - 1):
        if diffs[i] * diffs[i+1] < 0:  # Sign change
            alternations += 1

    max_alternations = len(diffs) - 1
    if max_alternations == 0:
        return 0.0

    alternation_score = alternations / max_alternations

    # Amplitude: mean absolute difference between consecutive bins
    amplitude = np.mean([abs(d) for d in diffs]) if diffs else 0.0

    # Combined: alternation regularity × amplitude
    # Both must be nonzero for a good score
    return float(alternation_score * amplitude)


def f_multibehavior(dn: dict) -> float:
    """Simultaneous multi-behavior fitness: nav + conflict + working memory.

    Rewards circuits that can navigate AND resolve conflicts AND show
    activity across diverse DN groups simultaneously. Each component
    contributes equally (normalized by typical scale).
    """
    nav = f_nav(dn)
    conflict_score = f_conflict(dn, dn)  # Same dn for both args
    arousal = f_arousal(dn)

    # Normalize each to ~0-1 range based on typical scales, then sum
    nav_norm = min(nav / 100.0, 1.0)
    conflict_norm = min(conflict_score / 15.0, 1.0)
    arousal_norm = min(arousal / 50.0, 1.0)

    # All three must be nonzero — geometric mean penalizes zeros
    if nav_norm <= 0 or conflict_norm <= 0 or arousal_norm <= 0:
        return float(nav_norm + conflict_norm + arousal_norm)  # Fallback to sum

    return float((nav_norm * conflict_norm * arousal_norm) ** (1/3) * 100)


def f_self_prediction(predicted: list[float], actual: list[float]) -> float:
    """Self-prediction: correlation between predicted and actual DN activity.

    The circuit receives its own previous-timestep DN output as input.
    Score = Pearson correlation between what the circuit "predicted"
    (its output at t-1) and what actually happened (its output at t).

    High correlation = the circuit is modeling its own dynamics.
    Zero correlation = output is uncorrelated with previous output.
    This is the minimal form of self-modeling.
    """
    if len(predicted) < 10 or len(actual) < 10:
        return 0.0
    pred = np.array(predicted)
    act = np.array(actual)
    if pred.std() == 0 or act.std() == 0:
        return 0.0
    corr = float(np.corrcoef(pred, act)[0, 1])
    # Scale to 0-100 range, penalize negative correlation
    return float(max(0, corr) * 100)


def f_working_memory(dn_during: dict, dn_after: dict) -> float:
    """Working memory: sustained DN activity AFTER stimulus stops.

    Args:
        dn_during: DN spikes while stimulus is on (first half)
        dn_after: DN spikes after stimulus stops (second half)

    Score = activity in the "after" period. Higher = better memory retention.
    Penalty if no activity during stimulus (circuit is dead, not remembering).
    """
    during = sum(dn_during.values())
    after = sum(dn_after.values())
    if during == 0:
        return 0.0  # Dead circuit, not memory
    return float(after)


def f_conflict(dn_nav: dict, dn_esc: dict) -> float:
    """Conflict resolution: choose between navigation and escape.

    Args:
        dn_nav: DN spikes from navigation pathway
        dn_esc: DN spikes from escape pathway

    Score = asymmetry between the two responses. The circuit should
    DECIDE — activate one pathway and suppress the other. Equal
    activation of both = no decision = score 0.
    """
    nav = f_nav(dn_nav)
    esc = f_esc(dn_esc)
    total = nav + esc
    if total == 0:
        return 0.0
    # Asymmetry: max when one pathway dominates completely
    asymmetry = abs(nav - esc) / total
    return float(asymmetry * total)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Maps behavior name -> (stimulus_name, array_fitness_fn, dict_fitness_fn)
FITNESS_FUNCTIONS = {
    "navigation": ("sugar", fitness_navigation, f_nav),
    "escape":     ("lc4",   fitness_escape,     f_esc),
    "turning":    ("jo",    fitness_turning,     f_turn),
    "arousal":    ("sugar", fitness_arousal,     f_arousal),
    "circles":    ("sugar", fitness_circles,     f_circles),
    "rhythm":     ("sugar", fitness_rhythm,      f_rhythm),
}


def get_fitness(name: str):
    """
    Look up a fitness function by name.

    Returns:
        (stimulus_name, array_fitness_fn, dict_fitness_fn)

    Raises:
        KeyError: if name not in FITNESS_FUNCTIONS
    """
    if name not in FITNESS_FUNCTIONS:
        available = ", ".join(sorted(FITNESS_FUNCTIONS.keys()))
        raise KeyError(f"Unknown fitness function '{name}'. Available: {available}")
    return FITNESS_FUNCTIONS[name]
