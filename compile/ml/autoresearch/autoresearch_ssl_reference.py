#!/usr/bin/env python3
"""
Autoresearch for SSL Pre-training
=================================

Autonomous overnight research loop. Modifies train_ssl.py hyperparameters,
runs experiments, keeps improvements, discards regressions.

Run: python autoresearch_ssl.py
"""

import os
import sys
import re
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Configuration
TIME_BUDGET_PER_EXPERIMENT = 120  # 2 minutes per experiment
MAX_EXPERIMENTS = 200  # Stop after this many

# Hyperparameter search space
SEARCH_SPACE = {
    # Cross-view prediction
    "mask_n_bands": [1, 2, 3],

    # Architecture
    "d_model": [128, 192, 256, 384],
    "n_layers": [4, 6, 8],
    "n_heads": [4, 8],
    "dropout": [0.1, 0.15, 0.2, 0.3],

    # Contrastive
    "use_contrastive": [True, False],
    "contrastive_temp": [0.05, 0.07, 0.1, 0.15],
    "contrastive_weight": [0.1, 0.3, 0.5, 0.7],

    # Training
    "batch_size": [16, 24, 32, 48],
    "lr": [1e-4, 3e-4, 5e-4, 1e-3],
    "weight_decay": [0.01, 0.05, 0.1],
    "warmup_ratio": [0.1, 0.15, 0.2],
}

# Track best result
best_accuracy = 0.0
results_file = Path("results_ssl.tsv")


def read_current_config():
    """Read current config values from train_ssl.py."""
    with open("train_ssl.py", "r") as f:
        content = f.read()

    config = {}
    # Extract values using regex
    patterns = {
        "d_model": r'd_model:\s*int\s*=\s*(\d+)',
        "n_layers": r'n_layers:\s*int\s*=\s*(\d+)',
        "n_heads": r'n_heads:\s*int\s*=\s*(\d+)',
        "dropout": r'dropout:\s*float\s*=\s*([\d.]+)',
        "mask_n_bands": r'mask_n_bands:\s*int\s*=\s*(\d+)',
        "use_contrastive": r'use_contrastive:\s*bool\s*=\s*(True|False)',
        "contrastive_temp": r'contrastive_temp:\s*float\s*=\s*([\d.]+)',
        "contrastive_weight": r'contrastive_weight:\s*float\s*=\s*([\d.]+)',
        "batch_size": r'batch_size:\s*int\s*=\s*(\d+)',
        "lr": r'lr:\s*float\s*=\s*([\d.e-]+)',
        "weight_decay": r'weight_decay:\s*float\s*=\s*([\d.]+)',
        "warmup_ratio": r'warmup_ratio:\s*float\s*=\s*([\d.]+)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            val = match.group(1)
            if key == "use_contrastive":
                config[key] = val == "True"
            elif key in ["d_model", "n_layers", "n_heads", "mask_n_bands", "batch_size"]:
                config[key] = int(val)
            else:
                config[key] = float(val)

    return config


def modify_config(param, value):
    """Modify a single parameter in train_ssl.py."""
    with open("train_ssl.py", "r") as f:
        content = f.read()

    if param == "use_contrastive":
        pattern = r'(use_contrastive:\s*bool\s*=\s*)(True|False)'
        replacement = f'\\g<1>{value}'
    elif param in ["d_model", "n_layers", "n_heads", "mask_n_bands", "batch_size"]:
        pattern = rf'({param}:\s*int\s*=\s*)\d+'
        replacement = f'\\g<1>{value}'
    else:
        pattern = rf'({param}:\s*float\s*=\s*)[\d.e-]+'
        replacement = f'\\g<1>{value}'

    new_content = re.sub(pattern, replacement, content)

    with open("train_ssl.py", "w") as f:
        f.write(new_content)


def run_experiment():
    """Run a single experiment and return probe_accuracy."""
    try:
        result = subprocess.run(
            ["python3", "train_ssl.py"],
            capture_output=True,
            text=True,
            timeout=TIME_BUDGET_PER_EXPERIMENT + 120  # Extra time for eval
        )

        output = result.stdout + result.stderr

        # Extract probe_accuracy
        match = re.search(r'probe_accuracy:\s*([\d.]+)', output)
        if match:
            return float(match.group(1)), output
        else:
            return None, output

    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except Exception as e:
        return None, str(e)


def log_result(experiment_num, param, value, accuracy, status, description):
    """Log result to TSV file."""
    if not results_file.exists():
        with open(results_file, "w") as f:
            f.write("exp_num\tparam\tvalue\tprobe_acc\tstatus\tdescription\ttimestamp\n")

    with open(results_file, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{experiment_num}\t{param}\t{value}\t{accuracy:.6f}\t{status}\t{description}\t{timestamp}\n")


def main():
    global best_accuracy

    print("=" * 60)
    print("AUTORESEARCH: SSL Pre-training for Neural Signals")
    print("=" * 60)
    print(f"Time budget per experiment: {TIME_BUDGET_PER_EXPERIMENT}s")
    print(f"Max experiments: {MAX_EXPERIMENTS}")
    print()

    # Read baseline config
    baseline_config = read_current_config()
    print("Baseline config:")
    for k, v in baseline_config.items():
        print(f"  {k}: {v}")
    print()

    # Run baseline
    print("Running baseline experiment...")
    accuracy, output = run_experiment()

    if accuracy is None:
        print("Baseline failed! Output:")
        print(output[-2000:] if len(output) > 2000 else output)
        return

    best_accuracy = accuracy
    print(f"Baseline accuracy: {best_accuracy:.4f}")
    log_result(0, "baseline", "-", best_accuracy, "keep", "baseline cross-view SSL")

    # Main loop
    for exp_num in range(1, MAX_EXPERIMENTS + 1):
        print()
        print(f"=" * 60)
        print(f"Experiment {exp_num}/{MAX_EXPERIMENTS}")
        print(f"Current best: {best_accuracy:.4f}")
        print(f"=" * 60)

        # Pick a random parameter to modify
        param = random.choice(list(SEARCH_SPACE.keys()))
        current_value = baseline_config.get(param)

        # Pick a new value different from current
        options = [v for v in SEARCH_SPACE[param] if v != current_value]
        if not options:
            options = SEARCH_SPACE[param]
        new_value = random.choice(options)

        print(f"Trying: {param} = {new_value} (was {current_value})")

        # Modify and run
        modify_config(param, new_value)
        accuracy, output = run_experiment()

        if accuracy is None:
            print(f"CRASHED! Reverting...")
            modify_config(param, current_value)
            log_result(exp_num, param, new_value, 0.0, "crash", f"{param}={new_value} crashed")
            continue

        print(f"Result: {accuracy:.4f}")

        if accuracy > best_accuracy:
            improvement = accuracy - best_accuracy
            print(f"IMPROVEMENT! +{improvement:.4f}")
            best_accuracy = accuracy
            baseline_config[param] = new_value
            log_result(exp_num, param, new_value, accuracy, "keep", f"{param}={new_value} improved")
        else:
            print(f"No improvement. Reverting.")
            modify_config(param, current_value)
            log_result(exp_num, param, new_value, accuracy, "discard", f"{param}={new_value} no improvement")

    print()
    print("=" * 60)
    print("AUTORESEARCH COMPLETE")
    print(f"Final best accuracy: {best_accuracy:.4f}")
    print(f"Results logged to: {results_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
