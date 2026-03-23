#!/usr/bin/env python3
"""
EXPERIMENT 2: Plasticity Training

Can the 20,626-neuron processor LEARN through Hebbian plasticity?

Protocol: Present training pairs (stimulus + desired DN output).
Then present stimulus alone. Does the circuit produce the trained output?

If yes: the processor is TRAINABLE. Program organoids like training a dog.
If no: need precision weight control. Harder implementation path.
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path

print("=" * 60)
print("PLASTICITY TRAINING EXPERIMENT")
print("=" * 60)

# Load connectome
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons_full = len(df_comp)
labels = np.load('/home/ubuntu/module_labels_v2.npy')
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

DN = {
    'P9_left': 83620, 'P9_right': 119032,
    'P9_oDN1_left': 78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431,
    'DNa02_left': 904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1': 57246, 'GF_2': 108748,
    'aDN1_left': 65709, 'aDN1_right': 26421,
    'MN9_left': 138332, 'MN9_right': 34268,
}
dn_names = sorted(DN.keys())

STIM_SUGAR = [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
              129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842,
              90589, 92298, 12494]

# Processor modules
_conflict_mods = set([40, 28, 23, 32, 31, 37, 4, 45, 35, 30, 24, 46, 17, 19, 5, 12, 36, 41])
_dn_mods = set(int(labels[DN[n]]) for n in DN)
_stim_mods = set(int(labels[i]) for i in STIM_SUGAR)
ALL_MODS = sorted(_conflict_mods | _dn_mods | _stim_mods)

DT, W_SCALE, GAIN = 0.5, 0.275, 8.0
POISSON_WEIGHT, POISSON_RATE = 15.0, 150.0

# Build subcircuit at 20% fraction
pre_full = df_conn['Presynaptic_Index'].values
post_full = df_conn['Postsynaptic_Index'].values
vals_full = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

rng = np.random.RandomState(42)
essential_set = set(DN.values()) | set(STIM_SUGAR)
keep_neurons = []
for mod in ALL_MODS:
    neurons = np.where(labels == mod)[0]
    n_keep = max(1, int(len(neurons) * 0.2))
    mod_essential = [n for n in neurons if n in essential_set]
    non_essential = [n for n in neurons if n not in essential_set]
    rng.shuffle(non_essential)
    keep = sorted(set(mod_essential) | set(non_essential[:max(0, n_keep - len(mod_essential))]))
    keep_neurons.extend(keep)

keep_set = set(keep_neurons)
keep_neurons = sorted(keep_set)
n_sub = len(keep_neurons)
old_to_new = {old: new for new, old in enumerate(keep_neurons)}
print(f"Subcircuit: {n_sub} neurons")

# Filter synapses
mask = np.array([pre_full[i] in keep_set and post_full[i] in keep_set for i in range(len(df_conn))])
pre_sub = np.array([old_to_new[pre_full[i]] for i in range(len(df_conn)) if mask[i]])
post_sub = np.array([old_to_new[post_full[i]] for i in range(len(df_conn)) if mask[i]])
vals_sub = vals_full[mask] * GAIN
n_synapses = len(pre_sub)
print(f"Synapses: {n_synapses}")

# Neuron types (Izhikevich)
a = np.full(n_sub, 0.02, dtype=np.float32)
b_arr = np.full(n_sub, 0.2, dtype=np.float32)
c = np.full(n_sub, -65.0, dtype=np.float32)
d_arr = np.full(n_sub, 8.0, dtype=np.float32)
for new_idx, old_idx in enumerate(keep_neurons):
    nid = neuron_ids[old_idx]
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        a[new_idx], b_arr[new_idx], c[new_idx], d_arr[new_idx] = 0.02, 0.2, -55.0, 4.0
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        a[new_idx], b_arr[new_idx], c[new_idx], d_arr[new_idx] = 0.1, 0.2, -65.0, 2.0

a_t = torch.tensor(a)
b_t = torch.tensor(b_arr)
c_t = torch.tensor(c)
d_t = torch.tensor(d_arr)

# Remap DN and stim
dn_new = {name: old_to_new[idx] for name, idx in DN.items() if idx in old_to_new}
stim_sugar_new = [old_to_new[i] for i in STIM_SUGAR if i in old_to_new]

# Navigation DN indices
nav_dn = [dn_new[n] for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'] if n in dn_new]
print(f"Nav DN neurons: {len(nav_dn)}")
print(f"Sugar stim neurons: {len(stim_sugar_new)}")

# Hebbian plasticity parameters
HEBB_LR = 0.001  # learning rate
HEBB_MAX = 3.0   # max weight multiplier

def run_with_plasticity(syn_vals, stim_indices, reinforce_indices, n_steps, plasticity=True):
    """Run simulation with optional Hebbian plasticity."""
    W_vals = syn_vals.clone()

    v = torch.full((1, n_sub), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, n_sub)
    rates = torch.zeros(1, n_sub)
    for idx in stim_indices:
        rates[0, idx] = POISSON_RATE

    # Also stimulate reinforcement neurons during training
    reinforce_rates = torch.zeros(1, n_sub)
    if reinforce_indices:
        for idx in reinforce_indices:
            reinforce_rates[0, idx] = POISSON_RATE * 2  # stronger reinforcement

    dn_total = {n: 0 for n in dn_names}
    dn_idx_list = [dn_new.get(n, -1) for n in dn_names]

    pre_t = torch.tensor(pre_sub, dtype=torch.long)
    post_t = torch.tensor(post_sub, dtype=torch.long)
    orig_abs = W_vals.abs().clamp(min=0.01)

    for step in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        reinforce = (torch.rand_like(reinforce_rates) < reinforce_rates * DT / 1000.0).float()

        # Build weight matrix
        W = torch.sparse_coo_tensor(
            torch.stack([post_t, pre_t]),
            W_vals, (n_sub, n_sub), dtype=torch.float32
        ).to_sparse_csr()

        I = (poisson + reinforce) * POISSON_WEIGHT + torch.mm(spikes, W.t()) * W_SCALE

        v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new = u + DT * a_t * (b_t * v_new - u)
        fired = (v_new >= 30.0).float()
        v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new = torch.clamp(v_new, -100.0, 30.0)

        # Hebbian plasticity: strengthen connections where pre and post fire together
        if plasticity and step % 10 == 0:  # every 10 steps for efficiency
            spk_flat = fired.squeeze(0)
            pre_fired = spk_flat[pre_sub] > 0
            post_fired = spk_flat[post_sub] > 0
            both = pre_fired & post_fired
            pre_only = pre_fired & ~post_fired

            # Hebbian: both fire → strengthen
            W_vals[both] += HEBB_LR * orig_abs[both]
            # Anti-Hebbian: pre fires, post doesn't → weaken
            W_vals[pre_only] -= HEBB_LR * 0.5 * orig_abs[pre_only]
            # Clamp
            W_vals = torch.clamp(W_vals, -HEBB_MAX * orig_abs, HEBB_MAX * orig_abs)

        v, u, spikes = v_new, u_new, fired

        spk = spikes.squeeze(0)
        for j in range(len(dn_names)):
            if dn_idx_list[j] >= 0:
                dn_total[dn_names[j]] += int(spk[dn_idx_list[j]].item())

    return dn_total, W_vals


def nav_score(dn):
    return sum(dn.get(n, 0) for n in ['P9_left', 'P9_right', 'MN9_left', 'MN9_right', 'P9_oDN1_left', 'P9_oDN1_right'])


# ============================================================
# Phase 1: Baseline (no training)
# ============================================================
print(f"\n{'='*60}")
print("PHASE 1: Baseline (no training)")
print("="*60)

syn_vals_base = torch.tensor(vals_sub, dtype=torch.float32)
t0 = time.time()
dn_baseline, _ = run_with_plasticity(syn_vals_base.clone(), stim_sugar_new, [], 500, plasticity=False)
baseline_nav = nav_score(dn_baseline)
print(f"Baseline nav score: {baseline_nav} ({time.time()-t0:.1f}s)")
print(f"Active DNs: {dict(sorted([(k,v) for k,v in dn_baseline.items() if v > 0]))}")

# ============================================================
# Phase 2: Training with reinforcement
# ============================================================
print(f"\n{'='*60}")
print("PHASE 2: Hebbian training (sugar + nav DN reinforcement)")
print("="*60)

TRAINING_PROTOCOLS = [
    {'name': 'light', 'reps': 10, 'steps_per_rep': 100},
    {'name': 'medium', 'reps': 50, 'steps_per_rep': 100},
    {'name': 'heavy', 'reps': 200, 'steps_per_rep': 100},
    {'name': 'intensive', 'reps': 500, 'steps_per_rep': 100},
]

results = []
for protocol in TRAINING_PROTOCOLS:
    print(f"\n--- Protocol: {protocol['name']} ({protocol['reps']} reps x {protocol['steps_per_rep']} steps) ---")

    syn_vals = syn_vals_base.clone()
    t0 = time.time()

    # Training: present sugar + reinforce nav DNs
    for rep in range(protocol['reps']):
        _, syn_vals = run_with_plasticity(
            syn_vals, stim_sugar_new, nav_dn,
            protocol['steps_per_rep'], plasticity=True
        )
        if (rep + 1) % max(1, protocol['reps'] // 5) == 0:
            # Quick test
            dn_test, _ = run_with_plasticity(syn_vals.clone(), stim_sugar_new, [], 200, plasticity=False)
            test_nav = nav_score(dn_test)
            print(f"  Rep {rep+1}: nav={test_nav}")

    train_time = time.time() - t0

    # Test: sugar stimulus ONLY (no reinforcement)
    print(f"  Testing (no reinforcement)...")
    dn_trained, _ = run_with_plasticity(syn_vals.clone(), stim_sugar_new, [], 500, plasticity=False)
    trained_nav = nav_score(dn_trained)

    improvement = (trained_nav - baseline_nav) / max(abs(baseline_nav), 1) * 100
    learned = trained_nav > baseline_nav * 1.1  # >10% improvement = learned

    # Weight change analysis
    weight_delta = (syn_vals - syn_vals_base).abs()
    n_changed = (weight_delta > 0.01).sum().item()
    max_change = weight_delta.max().item()

    result = {
        'protocol': protocol['name'],
        'reps': protocol['reps'],
        'baseline_nav': baseline_nav,
        'trained_nav': trained_nav,
        'improvement_pct': improvement,
        'learned': learned,
        'n_weights_changed': n_changed,
        'max_weight_change': max_change,
        'train_time': train_time,
    }
    results.append(result)

    status = "LEARNED" if learned else "no change"
    print(f"  Result: baseline={baseline_nav} → trained={trained_nav} ({improvement:+.1f}%) [{status}]")
    print(f"  Weights changed: {n_changed}/{n_synapses} ({100*n_changed/n_synapses:.1f}%)")
    print(f"  Training time: {train_time:.1f}s")

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*60}")
print("PLASTICITY TRAINING RESULTS")
print("="*60)

any_learned = any(r['learned'] for r in results)
print(f"\n{'Protocol':>12} {'Reps':>6} {'Baseline':>10} {'Trained':>10} {'Improve':>10} {'Status':>10}")
print("-" * 65)
for r in results:
    status = "LEARNED" if r['learned'] else "no change"
    print(f"{r['protocol']:>12} {r['reps']:>6} {r['baseline_nav']:>10} {r['trained_nav']:>10} "
          f"{r['improvement_pct']:>+9.1f}% {status:>10}")

if any_learned:
    print(f"\n>>> THE PROCESSOR IS TRAINABLE. Hebbian plasticity programs the evolvable surface.")
    print(f">>> Programming model: present input + reinforce desired output. Like training a dog.")
else:
    print(f"\n>>> The processor did NOT learn through Hebbian plasticity alone.")
    print(f">>> Need precision weight control or different plasticity rule.")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
with open(f'{outdir}/plasticity_training.json', 'w') as f:
    json.dump({'results': results, 'any_learned': any_learned}, f, indent=2)
print(f"\nSaved to {outdir}/plasticity_training.json")
print("DONE.")
