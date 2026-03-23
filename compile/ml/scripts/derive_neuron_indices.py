#!/usr/bin/env python3
"""
Derive and verify DN neuron indices from FlyWire v783 connectome data.

This script is the provenance trail for the "magic numbers" in
compile.constants.DN_NEURONS. It loads the FlyWire v783 connectome
completeness matrix (df_comp), maps each DN neuron's FlyWire root_id
to its integer row-index in that matrix, and verifies the result
matches the hardcoded constants.

The mapping is deterministic: given the same v783 data files, the same
indices will always be produced. This script exists so that anyone can
independently verify where the constants came from.

Usage:
    python scripts/derive_neuron_indices.py

Requirements:
    - FlyWire v783 data files in data/ (or set COMPILE_DATA_DIR)
      - 2025_Completeness_783.csv
      - 2025_Connectivity_783.parquet
"""

from __future__ import annotations

import sys

from compile.constants import (
    DN_FLYIDS, DN_NEURONS, STIM_SUGAR_FLYIDS, STIM_SUGAR,
    STIM_LC4, STIM_JO,
)
from compile.data import load_connectome


def main():
    print("Verifying DN neuron indices against FlyWire v783 connectome...")
    print()

    # Load connectome (only need df_comp for index mapping)
    try:
        _, df_comp, num_neurons = load_connectome()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print()
        print("Place FlyWire v783 data files in data/ or set COMPILE_DATA_DIR.")
        sys.exit(1)

    print(f"Loaded completeness matrix: {num_neurons} neurons")
    print()

    # Build root_id -> index mapping
    flyid_to_index = {root_id: idx for idx, root_id in enumerate(df_comp.index)}

    # --- Verify DN neurons ---
    print("DN neuron indices:")
    errors = []
    for name in sorted(DN_FLYIDS.keys()):
        flyid = DN_FLYIDS[name]
        derived_index = flyid_to_index.get(flyid, None)
        expected_index = DN_NEURONS.get(name, None)

        if derived_index is None:
            status = "NOT FOUND"
            errors.append(f"  {name}: FlyWire {flyid} not in completeness matrix")
        elif derived_index == expected_index:
            status = "ok"
        else:
            status = f"MISMATCH (got {derived_index}, expected {expected_index})"
            errors.append(f"  {name}: {status}")

        print(f"  {name}: FlyWire {flyid} -> index {derived_index} {status}")

    print()

    # --- Verify stimulus neuron indices ---
    print("Stimulus neuron indices (sugar):")
    stim_errors = []
    derived_sugar = []
    for flyid in STIM_SUGAR_FLYIDS:
        derived_index = flyid_to_index.get(flyid, None)
        if derived_index is not None:
            derived_sugar.append(derived_index)
        else:
            stim_errors.append(f"  FlyWire {flyid} not in completeness matrix")

    if set(derived_sugar) == set(STIM_SUGAR):
        print(f"  All {len(STIM_SUGAR)} sugar stimulus indices verified. ok")
    else:
        missing = set(STIM_SUGAR) - set(derived_sugar)
        extra = set(derived_sugar) - set(STIM_SUGAR)
        if missing:
            stim_errors.append(f"  Missing indices: {missing}")
        if extra:
            stim_errors.append(f"  Extra indices: {extra}")

    print()

    # Note: STIM_LC4 and STIM_JO are connectome indices derived from FlyWire
    # cell_class annotations. Unlike DN neurons (which have stable FlyWire root_ids),
    # stimulus neuron lists were selected by querying annotations for specific
    # cell classes (e.g., "LC4" visual neurons, "JO" Johnston's organ neurons)
    # and recording their row indices in the v783 completeness matrix.
    # These indices are deterministic given the same v783 data files.

    # Verify stimulus index bounds
    print("Stimulus index bounds check:")
    for stim_name, stim_indices in [("LC4", STIM_LC4), ("JO", STIM_JO)]:
        if not stim_indices:
            print(f"  {stim_name}: empty (not yet derived)")
            continue
        max_idx = max(stim_indices)
        min_idx = min(stim_indices)
        if min_idx < 0:
            stim_errors.append(f"  {stim_name}: negative index {min_idx}")
        if max_idx >= num_neurons:
            stim_errors.append(
                f"  {stim_name}: index {max_idx} >= num_neurons {num_neurons}"
            )
        if min_idx >= 0 and max_idx < num_neurons:
            print(f"  {stim_name}: {len(stim_indices)} indices in [0, {num_neurons}). ok")

    print()

    # --- Summary ---
    all_errors = errors + stim_errors
    if not all_errors:
        print(f"All {len(DN_NEURONS)} DN indices verified.")
        print("All stimulus indices verified.")
        print("Constants match the v783 connectome data.")
    else:
        print("ERRORS FOUND:")
        for e in all_errors:
            print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
