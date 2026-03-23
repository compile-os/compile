#!/usr/bin/env python3
"""
DREAMING TEST: What does a fly brain do with zero input?

Record full DN output vector every timestep for 5000 steps.
No stimulus. No body. Just the brain in the dark.

If DN vectors cycle through behavioral signatures spontaneously,
the brain is dreaming — replaying behavioral states from attractor dynamics.
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
print("DREAMING TEST: Fly brain in the dark")
print("=" * 60)

# Setup (same as persistence test)
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)

ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

a = np.full(num_neurons, 0.02, dtype=np.float32)
b = np.full(num_neurons, 0.2,  dtype=np.float32)
c = np.full(num_neurons, -65.0, dtype=np.float32)
d = np.full(num_neurons, 8.0, dtype=np.float32)

cx_neurons = []
for idx, nid in enumerate(neuron_ids):
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        a[idx], b[idx], c[idx], d[idx] = 0.02, 0.2, -55.0, 4.0
        cx_neurons.append(idx)
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        a[idx], b[idx], c[idx], d[idx] = 0.1, 0.2, -65.0, 2.0

device = 'cpu'
a_t = torch.tensor(a, device=device)
b_t = torch.tensor(b, device=device)
c_t = torch.tensor(c, device=device)
d_t = torch.tensor(d, device=device)

pre = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
GAIN = 8.0

weight_coo = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long),
                torch.tensor(pre, dtype=torch.long)]),
    torch.tensor(vals * GAIN, dtype=torch.float32, device=device),
    (num_neurons, num_neurons), dtype=torch.float32
)
W = weight_coo.to_sparse_csr()

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
dn_idx = [DN[n] for n in dn_names]

DT = 0.5
W_SCALE = 0.275
N_STEPS = 5000

# ============================================================
# Run: brain in the dark
# ============================================================
print(f"\nRunning {N_STEPS} steps with ZERO input...")

v = torch.full((1, num_neurons), -65.0, device=device)
u = b_t.unsqueeze(0) * v
spikes = torch.zeros(1, num_neurons, device=device)

dn_timeseries = np.zeros((N_STEPS, len(dn_names)), dtype=np.int8)
cx_timeseries = np.zeros(N_STEPS, dtype=np.int32)
total_timeseries = np.zeros(N_STEPS, dtype=np.int32)

t0 = time.time()
for step in range(N_STEPS):
    # NO INPUT — just recurrent dynamics
    recurrent = torch.mm(spikes, W.t()) * W_SCALE

    v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + recurrent)
    v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + recurrent)
    u_new = u + DT * a_t * (b_t * v_new - u)

    fired = (v_new >= 30.0).float()
    v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
    u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
    v_new = torch.clamp(v_new, -100.0, 30.0)

    v, u, spikes = v_new, u_new, fired

    spk = spikes.squeeze(0)
    for j in range(len(dn_names)):
        dn_timeseries[step, j] = int(spk[dn_idx[j]].item())
    cx_timeseries[step] = sum(int(spk[n].item()) for n in cx_neurons[:500])
    total_timeseries[step] = int(spk.sum().item())

    if (step + 1) % 1000 == 0:
        elapsed = time.time() - t0
        print(f"  Step {step+1}/{N_STEPS} ({elapsed:.1f}s) — "
              f"total spikes={total_timeseries[step]}, CX={cx_timeseries[step]}, "
              f"DN={dn_timeseries[step].sum()}")

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.1f}s")

# ============================================================
# Analysis
# ============================================================
print(f"\n{'='*60}")
print("SPONTANEOUS ACTIVITY ANALYSIS")
print("="*60)

# Overall stats
print(f"\nTotal spikes/step: mean={total_timeseries.mean():.0f}, std={total_timeseries.std():.0f}")
print(f"CX spikes/step: mean={cx_timeseries.mean():.1f}, std={cx_timeseries.std():.1f}")
print(f"DN spikes/step: mean={dn_timeseries.sum(axis=1).mean():.2f}")

# Per-DN activity
print(f"\nPer-DN neuron firing rates (spikes per 100 steps):")
for j, name in enumerate(dn_names):
    total = dn_timeseries[:, j].sum()
    rate = total / (N_STEPS / 100)
    print(f"  {name:>15}: {total:>5} total, {rate:>6.1f}/100steps")

# Behavioral signature detection
# Define signatures based on which DN groups are active
nav_idx = [i for i, n in enumerate(dn_names) if 'P9' in n or 'MN9' in n]
esc_idx = [i for i, n in enumerate(dn_names) if 'GF' in n or 'MDN' in n]
turn_idx = [i for i, n in enumerate(dn_names) if 'DNa01' in n or 'DNa02' in n]
adn_idx = [i for i, n in enumerate(dn_names) if 'aDN1' in n]

# Compute behavioral scores in 25-step windows
window = 25
n_windows = N_STEPS // window
nav_score = np.zeros(n_windows)
esc_score = np.zeros(n_windows)
turn_score = np.zeros(n_windows)
adn_score = np.zeros(n_windows)

for w in range(n_windows):
    chunk = dn_timeseries[w*window:(w+1)*window]
    nav_score[w] = chunk[:, nav_idx].sum()
    esc_score[w] = chunk[:, esc_idx].sum()
    turn_score[w] = chunk[:, turn_idx].sum()
    adn_score[w] = chunk[:, adn_idx].sum()

print(f"\nBehavioral signatures (25-step windows, {n_windows} windows):")
print(f"  Navigation (P9/MN9):  mean={nav_score.mean():.2f}, std={nav_score.std():.2f}, "
      f"max={nav_score.max():.0f}, nonzero={np.count_nonzero(nav_score)}/{n_windows}")
print(f"  Escape (GF/MDN):      mean={esc_score.mean():.2f}, std={esc_score.std():.2f}, "
      f"max={esc_score.max():.0f}, nonzero={np.count_nonzero(esc_score)}/{n_windows}")
print(f"  Turning (DNa01/02):   mean={turn_score.mean():.2f}, std={turn_score.std():.2f}, "
      f"max={turn_score.max():.0f}, nonzero={np.count_nonzero(turn_score)}/{n_windows}")
print(f"  Angular (aDN1):       mean={adn_score.mean():.2f}, std={adn_score.std():.2f}, "
      f"max={adn_score.max():.0f}, nonzero={np.count_nonzero(adn_score)}/{n_windows}")

# State classification per window
print(f"\nSpontaneous behavioral state sequence (first 100 windows):")
state_sequence = []
for w in range(min(100, n_windows)):
    scores = {'nav': nav_score[w], 'esc': esc_score[w], 'turn': turn_score[w], 'adn': adn_score[w]}
    active = {k: v for k, v in scores.items() if v > 0}
    if not active:
        state = 'silent'
    elif len(active) > 1:
        dominant = max(active, key=active.get)
        state = f'mixed({dominant})'
    else:
        state = list(active.keys())[0]
    state_sequence.append(state)

# Count state transitions
from collections import Counter
state_counts = Counter(state_sequence)
print(f"  State counts: {dict(state_counts)}")

transitions = Counter()
for i in range(len(state_sequence) - 1):
    if state_sequence[i] != state_sequence[i+1]:
        transitions[(state_sequence[i], state_sequence[i+1])] += 1

print(f"  Transitions: {len(transitions)} unique")
for (s1, s2), count in transitions.most_common(10):
    print(f"    {s1} → {s2}: {count}")

# Is there temporal structure? Autocorrelation of DN activity
print(f"\nTemporal structure (autocorrelation of total DN activity):")
dn_total = dn_timeseries.sum(axis=1).astype(float)
if dn_total.std() > 0:
    for lag in [1, 5, 10, 25, 50, 100]:
        if lag < len(dn_total):
            r = np.corrcoef(dn_total[:-lag], dn_total[lag:])[0, 1]
            print(f"  Lag {lag:>3}: r = {r:.4f}")
else:
    print("  No variance in DN activity")

# Check for oscillations via FFT
print(f"\nFrequency analysis (FFT of CX activity):")
if cx_timeseries.std() > 0:
    from scipy import fft
    cx_fft = np.abs(fft.rfft(cx_timeseries - cx_timeseries.mean()))
    freqs = fft.rfftfreq(N_STEPS, d=DT/1000)  # Hz
    top_freqs = np.argsort(cx_fft[1:])[-5:] + 1  # skip DC
    print(f"  Top 5 frequencies:")
    for fi in reversed(top_freqs):
        print(f"    {freqs[fi]:.1f} Hz: amplitude={cx_fft[fi]:.1f}")

# Save full timeseries
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'experiment': 'dreaming_test',
    'n_steps': N_STEPS,
    'dt_ms': DT,
    'dn_names': dn_names,
    'dn_timeseries': dn_timeseries.tolist(),
    'cx_mean': float(cx_timeseries.mean()),
    'total_mean': float(total_timeseries.mean()),
    'state_sequence_100': state_sequence,
    'nav_score_windows': nav_score.tolist(),
    'esc_score_windows': esc_score.tolist(),
    'turn_score_windows': turn_score.tolist(),
}
with open(f'{outdir}/dreaming_test.json', 'w') as f:
    json.dump(output, f)
print(f"\nSaved to {outdir}/dreaming_test.json")
print("DONE.")
