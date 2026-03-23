#!/usr/bin/env python3
"""Autoresearch SSL - 30 minute time limit"""

import os, sys, re, random, subprocess, time
from datetime import datetime
from pathlib import Path

TIME_LIMIT = 1800  # 30 minutes
TIME_PER_EXP = 120

SEARCH_SPACE = {
    "mask_n_bands": [1, 2, 3],
    "d_model": [128, 192, 256, 384],
    "n_layers": [4, 6, 8],
    "n_heads": [4, 8],
    "dropout": [0.1, 0.15, 0.2, 0.3],
    "use_contrastive": [True, False],
    "contrastive_temp": [0.05, 0.07, 0.1, 0.15],
    "contrastive_weight": [0.1, 0.3, 0.5],
    "batch_size": [16, 24, 32],
    "lr": [1e-4, 3e-4, 5e-4, 1e-3],
    "weight_decay": [0.01, 0.05, 0.1],
}

best_accuracy = 0.0
results_file = Path("results_ssl.tsv")

def read_config():
    with open("train_ssl.py", "r") as f:
        content = f.read()
    config = {}
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
    try:
        result = subprocess.run(["python3", "train_ssl.py"], capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        match = re.search(r'probe_accuracy:\s*([\d.]+)', output)
        if match:
            return float(match.group(1)), output
        return None, output
    except Exception as e:
        return None, str(e)

def log_result(exp_num, param, value, accuracy, status, desc):
    if not results_file.exists():
        with open(results_file, "w") as f:
            f.write("exp\tparam\tvalue\tacc\tstatus\tdesc\n")
    with open(results_file, "a") as f:
        f.write(f"{exp_num}\t{param}\t{value}\t{accuracy:.4f}\t{status}\t{desc}\n")

def main():
    global best_accuracy
    start_time = time.time()
    
    print("=" * 50)
    print("AUTORESEARCH SSL (30 min limit)")
    print("=" * 50)
    
    baseline_config = read_config()
    print("Baseline:", baseline_config)
    
    print("\nRunning baseline...")
    accuracy, _ = run_experiment()
    if accuracy is None:
        print("Baseline failed!")
        return
    
    best_accuracy = accuracy
    print(f"Baseline: {best_accuracy:.4f}")
    log_result(0, "baseline", "-", best_accuracy, "keep", "baseline")
    
    exp_num = 0
    while time.time() - start_time < TIME_LIMIT:
        exp_num += 1
        elapsed = (time.time() - start_time) / 60
        print(f"\n[{elapsed:.1f}m] Exp {exp_num} | Best: {best_accuracy:.4f}")
        
        param = random.choice(list(SEARCH_SPACE.keys()))
        current = baseline_config.get(param)
        options = [v for v in SEARCH_SPACE[param] if v != current]
        if not options:
            options = SEARCH_SPACE[param]
        new_value = random.choice(options)
        
        print(f"  {param}: {current} -> {new_value}")
        modify_config(param, new_value)
        
        accuracy, _ = run_experiment()
        if accuracy is None:
            print("  CRASH - reverting")
            modify_config(param, current)
            log_result(exp_num, param, new_value, 0, "crash", "crashed")
            continue
        
        if accuracy > best_accuracy:
            print(f"  IMPROVED: {accuracy:.4f} (+{accuracy-best_accuracy:.4f})")
            best_accuracy = accuracy
            baseline_config[param] = new_value
            log_result(exp_num, param, new_value, accuracy, "keep", "improved")
        else:
            print(f"  No gain: {accuracy:.4f}")
            modify_config(param, current)
            log_result(exp_num, param, new_value, accuracy, "discard", "no improvement")
    
    print("\n" + "=" * 50)
    print(f"DONE! Best accuracy: {best_accuracy:.4f}")
    print(f"Experiments run: {exp_num}")
    print("=" * 50)

if __name__ == "__main__":
    main()
