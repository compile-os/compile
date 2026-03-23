#!/usr/bin/env python3
"""
Connectome Autoresearch Orchestrator
====================================

Runs the analysis loop: propose hypothesis → run analysis → evaluate → keep/discard.
For use with an LLM agent that modifies analysis.py.

This script is a helper that can be run manually to test the setup.
The actual autoresearch loop is driven by the LLM agent following program.md.

Usage: python autoresearch_connectome.py [--baseline]
"""

import os
import sys
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

RESULTS_FILE = Path("results.tsv")
TIMEOUT = 600  # 10 minutes max per analysis


def run_analysis():
    """Run analysis.py and capture output."""
    try:
        result = subprocess.run(
            ["python3", "analysis.py"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", -1
    except Exception as e:
        return str(e), -1


def parse_results(output: str) -> dict:
    """Parse the structured output from analysis.py."""
    results = {}

    patterns = {
        'hypothesis': r'^hypothesis:\s*(.+)$',
        'metric_real': r'^metric_real:\s*([\d.]+)',
        'metric_null': r'^metric_null:\s*([\d.]+)',
        'z_score': r'^z_score:\s*([-\d.]+)',
        'p_value': r'^p_value:\s*([\d.]+)',
        'is_significant': r'^is_significant:\s*(True|False)',
        'is_novel': r'^is_novel:\s*(True|False)',
        'conclusion': r'^conclusion:\s*(.+)$',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, output, re.MULTILINE)
        if match:
            val = match.group(1)
            if key in ['is_significant', 'is_novel']:
                results[key] = val == 'True'
            elif key in ['metric_real', 'metric_null', 'z_score', 'p_value']:
                results[key] = float(val)
            else:
                results[key] = val

    return results


def log_result(commit: str, results: dict, status: str):
    """Log result to TSV file."""
    if not RESULTS_FILE.exists():
        with open(RESULTS_FILE, "w") as f:
            f.write("commit\tp_value\tis_significant\tis_novel\tstatus\thypothesis\ttimestamp\n")

    with open(RESULTS_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        p_val = results.get('p_value', 0.0)
        is_sig = results.get('is_significant', False)
        is_nov = results.get('is_novel', False)
        hyp = results.get('hypothesis', 'unknown')[:50]
        f.write(f"{commit}\t{p_val:.4f}\t{is_sig}\t{is_nov}\t{status}\t{hyp}\t{timestamp}\n")


def get_git_commit():
    """Get current short commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return "unknown"


def main():
    print("=" * 60)
    print("CONNECTOME AUTORESEARCH")
    print("=" * 60)
    print()

    # Check data exists
    data_dir = Path.home() / "neurodata" / "flywire" / "FAFB_v783"
    cell_types = data_dir / "consolidated_cell_types.csv.gz"
    connections = data_dir / "connections_princeton_no_threshold.csv.gz"

    if not cell_types.exists() or not connections.exists():
        print(f"ERROR: Data not found at {data_dir}")
        print("Required files:")
        print(f"  - {cell_types}")
        print(f"  - {connections}")
        sys.exit(1)

    print(f"Data directory: {data_dir}")
    print(f"Cell types: {cell_types.stat().st_size / 1024:.1f} KB")
    print(f"Connections: {connections.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    # Run analysis
    print("Running analysis...")
    start_time = time.time()
    output, returncode = run_analysis()
    elapsed = time.time() - start_time

    print(f"Completed in {elapsed:.1f}s")
    print()

    if returncode != 0 or "TIMEOUT" in output:
        print("CRASHED or TIMEOUT")
        print(output[-2000:] if len(output) > 2000 else output)
        log_result(get_git_commit(), {}, "crash")
        return

    # Parse results
    results = parse_results(output)

    if not results:
        print("Could not parse results. Output:")
        print(output[-2000:] if len(output) > 2000 else output)
        return

    print("Results:")
    for k, v in results.items():
        print(f"  {k}: {v}")
    print()

    # Determine status
    if results.get('is_significant') and results.get('is_novel'):
        status = "keep"
        print("STATUS: KEEP (significant + novel)")
    elif results.get('is_significant') and not results.get('is_novel'):
        status = "known"
        print("STATUS: KNOWN (significant but already published)")
    else:
        status = "discard"
        print("STATUS: DISCARD (not significant)")

    # Log
    log_result(get_git_commit(), results, status)
    print(f"\nLogged to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
