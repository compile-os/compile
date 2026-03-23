#!/usr/bin/env python3
"""
Apply calibrations to architecture_specs.py by modifying the ARCHITECTURES dict in-place.

This reads the current specs, applies the calibration function from
calibrate_all_architectures.py, and writes the updated Python source.

Usage:
    python -m scripts.apply_calibrations
"""

import ast
import json
import sys
from pathlib import Path

from compile.architecture_specs import ARCHITECTURES
from scripts.calibrate_all_architectures import calibrate_architecture


def main():
    specs_path = Path("compile/architecture_specs.py")
    source = specs_path.read_text()

    # Apply calibration to all uncalibrated specs
    updates = {}
    for name, spec in ARCHITECTURES.items():
        if spec.get("calibrated"):
            continue
        cal = calibrate_architecture(name, spec)
        updates[name] = cal

    if not updates:
        print("All architectures already calibrated.")
        return

    # Generate the calibrated specs as Python source
    # We'll write a JSON file and a summary, then the user can review
    out = {}
    for name, spec in updates.items():
        out[name] = {
            "calibrated": True,
            "calibration_source": spec["calibration_source"],
            "total_neurons": spec["total_neurons"],
            "proportions": spec["proportions"],
            "connection_rules": spec["connection_rules"],
            "growth_order": spec["growth_order"],
        }

    outpath = Path("results/calibrations_to_apply.json")
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(out, f, indent=2, default=lambda x: float(x) if hasattr(x, 'item') else str(x))

    print(f"Wrote {len(updates)} calibrations to {outpath}")
    print("\nTo apply: manually update architecture_specs.py with these values,")
    print("or use the auto-apply function below.")

    # Auto-apply: modify the Python source directly
    for name, cal_spec in updates.items():
        old_spec = ARCHITECTURES[name]

        # Update the in-memory dict
        old_spec["calibrated"] = True
        old_spec["calibration_source"] = cal_spec["calibration_source"]
        old_spec["total_neurons"] = cal_spec["total_neurons"]
        old_spec["proportions"] = cal_spec["proportions"]
        old_spec["connection_rules"] = cal_spec["connection_rules"]
        old_spec["growth_order"] = cal_spec["growth_order"]

    # Write the entire ARCHITECTURES dict back
    # This is hacky but works: serialize each spec
    lines = ['# Architecture Developmental Specifications\n']
    lines.append('# Each spec is executable by the sequential activity-dependent growth model\n')
    lines.append('# Format: cell_types, proportions, connection_rules, spatial_layout, growth_order\n')
    lines.append('# AUTO-CALIBRATED against FlyWire v783 biological operating ranges\n\n')
    lines.append('import json\n\n')
    lines.append('ARCHITECTURES = {\n')

    for name, spec in ARCHITECTURES.items():
        lines.append(f'\n    "{name}": {json.dumps(spec, indent=8, default=str)},\n')

    lines.append('}\n')

    # Don't overwrite — too risky. Write to a new file for review.
    review_path = Path("compile/architecture_specs_calibrated.py")
    with open(review_path, "w") as f:
        f.writelines(lines)

    print(f"\nWrote calibrated specs to {review_path}")
    print("Review and rename to architecture_specs.py when satisfied.")


if __name__ == "__main__":
    main()
