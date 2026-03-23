#!/usr/bin/env python3
"""
Auto-calibrate all architecture specs using FlyWire biological operating ranges.

Maps each connection type (inferred from role, NT, and rule type) to the
real probability and weight ranges observed in the FlyWire v783 connectome.

Operating ranges (from subsumption functional group analysis):
  sensory → processing:  prob 0.002-0.02,  weight 3-5
  processing → motor:    prob 0.08-0.24,   weight 9-16
  inhibition/gating:     prob 0.04-0.10,   weight 7-10
  recurrent/lateral:     prob 0.015-0.035,  weight 6-8
  cross-module:          prob 0.005-0.015,  weight 5-7
  E → I:                 prob 0.04-0.08,   weight 8-9
  I → E:                 prob 0.06-0.09,   weight 10-11
  broadcast/modulatory:  prob 0.003-0.01,  weight 2-4

Usage:
    python scripts/calibrate_all_architectures.py
    python scripts/calibrate_all_architectures.py --dry-run  # print without modifying
"""

import json
import re
import sys
from copy import deepcopy

from compile.architecture_specs import ARCHITECTURES

# FlyWire operating ranges by connection semantic type
CALIBRATION_MAP = {
    # Sensory input pathways (sparse)
    "input": {"prob": 0.012, "mean_weight": 5.0},
    "sensory_input": {"prob": 0.016, "mean_weight": 5.0},
    "evidence_input": {"prob": 0.012, "mean_weight": 5.0},
    "threat_detection": {"prob": 0.057, "mean_weight": 1.2},
    "direct_sensorimotor": {"prob": 0.022, "mean_weight": 7.0},

    # Output pathways (dense)
    "output": {"prob": 0.15, "mean_weight": 14.0},
    "direct_output": {"prob": 0.12, "mean_weight": 12.0},

    # Recurrent connections
    "recurrent": {"prob": 0.025, "mean_weight": 7.0},
    "strong_recurrent": {"prob": 0.035, "mean_weight": 8.0},
    "self_excitation": {"prob": 0.03, "mean_weight": 8.0},
    "local_recurrent": {"prob": 0.02, "mean_weight": 6.0},
    "plastic_recurrent": {"prob": 0.02, "mean_weight": 6.0},

    # E/I balance
    "E_to_I": {"prob": 0.06, "mean_weight": 8.5},
    "I_to_E": {"prob": 0.08, "mean_weight": 10.0},
    "EI": {"prob": 0.06, "mean_weight": 8.5},
    "IE": {"prob": 0.08, "mean_weight": 10.0},
    "fast_EI": {"prob": 0.06, "mean_weight": 8.5},
    "fast_IE": {"prob": 0.08, "mean_weight": 10.0},
    "slow_EI": {"prob": 0.06, "mean_weight": 8.5},
    "slow_IE": {"prob": 0.08, "mean_weight": 10.0},
    "homeostatic_IE": {"prob": 0.08, "mean_weight": 10.0},
    "global_I_to_E": {"prob": 0.09, "mean_weight": 10.5},

    # Inhibition/suppression
    "gating": {"prob": 0.06, "mean_weight": 8.0},
    "suppress": {"prob": 0.08, "mean_weight": 10.0},
    "suppress_lower": {"prob": 0.06, "mean_weight": 7.5},
    "drive_suppression": {"prob": 0.05, "mean_weight": 8.5},
    "inhibitory": {"prob": 0.06, "mean_weight": 8.0},
    "global_inhibition": {"prob": 0.04, "mean_weight": 7.0},
    "lateral_inhibition": {"prob": 0.04, "mean_weight": 7.0},
    "local_inhibition": {"prob": 0.04, "mean_weight": 7.0},
    "sparsity_enforcement": {"prob": 0.04, "mean_weight": 6.0},
    "arbitration": {"prob": 0.06, "mean_weight": 8.0},
    "drive_inhibition": {"prob": 0.06, "mean_weight": 8.5},

    # Feedforward/convergent
    "feedforward": {"prob": 0.03, "mean_weight": 7.0},
    "convergent": {"prob": 0.06, "mean_weight": 9.0},
    "hub_relay": {"prob": 0.08, "mean_weight": 11.0},
    "tier_relay": {"prob": 0.06, "mean_weight": 10.0},
    "reservoir_to_readout": {"prob": 0.10, "mean_weight": 12.0},
    "parallel_fiber": {"prob": 0.008, "mean_weight": 4.0},
    "divergent_sparse": {"prob": 0.005, "mean_weight": 3.0},

    # Feedback/cross-layer
    "feedback": {"prob": 0.02, "mean_weight": 6.0},
    "cross_layer": {"prob": 0.015, "mean_weight": 7.0},
    "cross_frequency": {"prob": 0.015, "mean_weight": 6.0},
    "phase_feedback": {"prob": 0.01, "mean_weight": 5.0},
    "top_down_prediction": {"prob": 0.025, "mean_weight": 7.0},
    "error_ascending": {"prob": 0.03, "mean_weight": 7.0},
    "prediction": {"prob": 0.06, "mean_weight": 8.5},
    "subtract_prediction": {"prob": 0.07, "mean_weight": 10.0},

    # Broadcast/modulatory (very sparse)
    "broadcast": {"prob": 0.005, "mean_weight": 2.5},
    "token_broadcast": {"prob": 0.008, "mean_weight": 3.0},
    "token_update": {"prob": 0.008, "mean_weight": 3.0},
    "reward_broadcast": {"prob": 0.005, "mean_weight": 2.5},
    "urgency_broadcast": {"prob": 0.005, "mean_weight": 2.5},
    "gain_modulation": {"prob": 0.005, "mean_weight": 2.5},

    # Specialized
    "ring_forward": {"prob": 0.04, "mean_weight": 8.0},
    "ring_backward": {"prob": 0.015, "mean_weight": 5.0},
    "threshold_check": {"prob": 0.10, "mean_weight": 12.0},
    "state_vector": {"prob": 0.04, "mean_weight": 7.0},
    "long_range_shortcut": {"prob": 0.003, "mean_weight": 5.0},
    "distributed_output": {"prob": 0.008, "mean_weight": 6.0},
    "write": {"prob": 0.02, "mean_weight": 6.0},
    "read": {"prob": 0.02, "mean_weight": 6.0},
    "emergency_override": {"prob": 0.045, "mean_weight": 3.0},
    "emergency_suppression": {"prob": 0.045, "mean_weight": 5.5},
    "direct_reflex": {"prob": 0.016, "mean_weight": 3.0},
    "three_factor": {"prob": 0.02, "mean_weight": 6.0},

    # Defaults for unknown types
    "default_excitatory": {"prob": 0.02, "mean_weight": 6.0},
    "default_inhibitory": {"prob": 0.06, "mean_weight": 8.0},
}


def calibrate_rule(rule: dict, cell_types: list) -> dict:
    """Calibrate a single connection rule."""
    rule = dict(rule)
    rule_type = rule.get("type", "")

    # Look up calibration by type
    if rule_type in CALIBRATION_MAP:
        cal = CALIBRATION_MAP[rule_type]
    else:
        # Infer from the rule type string
        matched = False
        for key in CALIBRATION_MAP:
            if key in rule_type.lower():
                cal = CALIBRATION_MAP[key]
                matched = True
                break
        if not matched:
            # Check if source is inhibitory
            from_id = rule.get("from", "")
            from_spec = next((ct for ct in cell_types if ct["id"] == from_id), {})
            if from_spec.get("nt") == "GABA":
                cal = CALIBRATION_MAP["default_inhibitory"]
            else:
                cal = CALIBRATION_MAP["default_excitatory"]

    rule["prob"] = cal["prob"]
    rule["mean_weight"] = cal["mean_weight"]
    return rule


def calibrate_architecture(name: str, spec: dict) -> dict:
    """Calibrate an architecture spec."""
    spec = deepcopy(spec)
    spec["calibrated"] = True
    spec["calibration_source"] = "FlyWire v783 — biological operating ranges from functional group analysis"

    # Calibrate connection rules
    spec["connection_rules"] = [
        calibrate_rule(rule, spec["cell_types"])
        for rule in spec["connection_rules"]
    ]

    # Reduce neuron count to biological subcircuit scale
    if spec["total_neurons"] > 3500:
        spec["total_neurons"] = 3000

    # Fix proportions: sensory and motor should be small (biological)
    props = spec["proportions"]
    for key in props:
        ct_spec = next((ct for ct in spec["cell_types"] if ct["id"] == key), {})
        role = ct_spec.get("role", "")
        if "sensory" in role or "sensory" in key:
            props[key] = 0.022
        elif "motor" in role or "motor" in key:
            props[key] = 0.006

    # Normalize proportions to sum to ~1
    total = sum(props.values())
    if abs(total - 1.0) > 0.01:
        for key in props:
            props[key] = round(props[key] / total, 4)

    # Fix growth order: sensory should come first
    go = spec["growth_order"]
    sensory_entries = [g for g in go if "sensory" in g.lower() or "input" in g.lower()]
    motor_entries = [g for g in go if "motor" in g.lower()]
    other_entries = [g for g in go if g not in sensory_entries and g not in motor_entries]
    spec["growth_order"] = sensory_entries + other_entries + motor_entries

    return spec


def main():
    dry_run = "--dry-run" in sys.argv

    calibrated = {}
    already = []
    for name, spec in ARCHITECTURES.items():
        if spec.get("calibrated"):
            already.append(name)
            continue
        cal = calibrate_architecture(name, spec)
        calibrated[name] = cal

    print(f"Already calibrated: {len(already)}")
    for n in already:
        print(f"  [OK] {n}")

    print(f"\nNewly calibrated: {len(calibrated)}")
    for name, spec in calibrated.items():
        n_rules = len(spec["connection_rules"])
        n_cal = sum(1 for r in spec["connection_rules"] if "mean_weight" in r)
        print(f"  {name:30s}: {n_rules} rules, {n_cal} with mean_weight, {spec['total_neurons']} neurons")

    if dry_run:
        print("\n[DRY RUN] No files modified.")
        return

    # Output calibrated specs as JSON for review
    output = {}
    for name, spec in calibrated.items():
        output[name] = {
            "total_neurons": spec["total_neurons"],
            "proportions": spec["proportions"],
            "connection_rules": spec["connection_rules"],
            "growth_order": spec["growth_order"],
        }

    with open("results/calibrated_all.json", "w") as f:
        json.dump(output, f, indent=2, default=lambda x: float(x) if hasattr(x, 'item') else str(x))
    print(f"\nSaved calibrated specs to results/calibrated_all.json")
    print("Apply with: python scripts/apply_calibrations.py")


if __name__ == "__main__":
    main()
