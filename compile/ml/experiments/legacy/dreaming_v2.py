#!/usr/bin/env python3
"""
DREAMING TEST v2: Brief wake, then darkness.

100 steps of random Poisson noise to ALL neurons (simulating spontaneous
ion channel fluctuations). Then 5000 steps of pure darkness.

If the brain sustains structured activity after the noise seed,
that's spontaneous attractor dynamics — dreaming.
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")
import torch, numpy as np, pandas as pd
from pathlib import Path
from collections import Counter

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
a_t, b_t = torch.tensor(a, device=device), torch.tensor(b, device=device)
c_t, d_t = torch.tensor(c, device=device), torch.tensor(d, device=device)

pre = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
GAIN = 8.0
W = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long), torch.tensor(pre, dtype=torch.long)]),
    torch.tensor(vals * GAIN, dtype=torch.float32, device=device),
    (num_neurons, num_neurons), dtype=torch.float32
).to_sparse_csr()

DN = {
    'P9_left': 83620, 'P9_right': 119032, 'P9_oDN1_left': 78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431, 'DNa02_left': 904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1': 57246, 'GF_2': 108748, 'aDN1_left': 65709, 'aDN1_right': 26421,
    'MN9_left': 138332, 'MN9_right': 34268,
}
dn_names = sorted(DN.keys())
dn_idx = [DN[n] for n in dn_names]

DT, W_SCALE = 0.5, 0.275
WAKE_STEPS = 100
DREAM_STEPS = 5000
NOISE_RATE = 20.0  # Hz — low background noise, simulates spontaneous channel openings
NOISE_WEIGHT = 10.0

print("=" * 60)
print("DREAMING TEST v2: Brief wake, then darkness")
print(f"  Wake: {WAKE_STEPS} steps of {NOISE_RATE}Hz noise to all neurons")
print(f"  Dream: {DREAM_STEPS} steps of pure silence")
print("=" * 60)

v = torch.full((1, num_neurons), -65.0, device=device)
u = b_t.unsqueeze(0) * v
spikes = torch.zeros(1, num_neurons, device=device)

dn_ts = np.zeros((WAKE_STEPS + DREAM_STEPS, len(dn_names)), dtype=np.int8)
cx_ts = np.zeros(WAKE_STEPS + DREAM_STEPS, dtype=np.int32)
total_ts = np.zeros(WAKE_STEPS + DREAM_STEPS, dtype=np.int32)

t0 = time.time()
for step in range(WAKE_STEPS + DREAM_STEPS):
    # Background noise during wake phase only
    if step < WAKE_STEPS:
        noise = (torch.rand(1, num_neurons, device=device) < NOISE_RATE * DT / 1000.0).float()
        I_ext = noise * NOISE_WEIGHT
    else:
        I_ext = torch.zeros(1, num_neurons, device=device)

    recurrent = torch.mm(spikes, W.t()) * W_SCALE
    I = I_ext + recurrent

    v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
    v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
    u_new = u + DT * a_t * (b_t * v_new - u)
    fired = (v_new >= 30.0).float()
    v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
    u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
    v_new = torch.clamp(v_new, -100.0, 30.0)
    v, u, spikes = v_new, u_new, fired

    spk = spikes.squeeze(0)
    for j in range(len(dn_names)):
        dn_ts[step, j] = int(spk[dn_idx[j]].item())
    cx_ts[step] = sum(int(spk[n].item()) for n in cx_neurons[:500])
    total_ts[step] = int(spk.sum().item())

    if (step + 1) % 500 == 0:
        phase = "WAKE" if step < WAKE_STEPS else "DREAM"
        elapsed = time.time() - t0
        print(f"  Step {step+1} [{phase}] ({elapsed:.1f}s) — "
              f"total={total_ts[step]}, CX={cx_ts[step]}, DN={dn_ts[step].sum()}")

elapsed = time.time() - t0
print(f"\nDone in {elapsed:.1f}s")

# Analysis — dream phase only
dream_dn = dn_ts[WAKE_STEPS:]
dream_cx = cx_ts[WAKE_STEPS:]
dream_total = total_ts[WAKE_STEPS:]

print(f"\n{'='*60}")
print("DREAM PHASE ANALYSIS")
print("="*60)
print(f"Total spikes/step: mean={dream_total.mean():.0f}, std={dream_total.std():.0f}")
print(f"CX spikes/step: mean={dream_cx.mean():.1f}, std={dream_cx.std():.1f}")

if dream_total.mean() < 1:
    print("\n>>> Brain died after wake phase. No spontaneous activity.")
    print(">>> Need stronger initial kick or ongoing background noise.")
else:
    print(f"\n>>> BRAIN IS ACTIVE IN THE DARK! {dream_total.mean():.0f} spikes/step")

    # Behavioral signatures in dream
    nav_i = [i for i, n in enumerate(dn_names) if 'P9' in n or 'MN9' in n]
    esc_i = [i for i, n in enumerate(dn_names) if 'GF' in n or 'MDN' in n]
    turn_i = [i for i, n in enumerate(dn_names) if 'DNa01' in n or 'DNa02' in n]

    window = 50
    n_win = DREAM_STEPS // window
    states = []
    for w in range(n_win):
        chunk = dream_dn[w*window:(w+1)*window]
        nav = chunk[:, nav_i].sum()
        esc = chunk[:, esc_i].sum()
        turn = chunk[:, turn_i].sum()
        scores = {'nav': nav, 'esc': esc, 'turn': turn}
        active = {k: v for k, v in scores.items() if v > 0}
        if not active:
            states.append('silent')
        else:
            states.append(max(active, key=active.get))

    counts = Counter(states)
    print(f"\nSpontaneous behavioral states ({window}-step windows):")
    for state, count in counts.most_common():
        pct = 100 * count / n_win
        print(f"  {state:>8}: {count}/{n_win} ({pct:.1f}%)")

    # Transitions
    transitions = Counter()
    for i in range(len(states) - 1):
        if states[i] != states[i+1]:
            transitions[(states[i], states[i+1])] += 1
    print(f"\nState transitions: {sum(transitions.values())} total")
    for (s1, s2), count in transitions.most_common(10):
        print(f"  {s1:>8} → {s2:<8}: {count}")

    # Timeline (first 40 windows)
    print(f"\nDream timeline (first {min(40, n_win)} windows of {window} steps):")
    for i in range(min(40, n_win)):
        chunk = dream_dn[i*window:(i+1)*window]
        nav = chunk[:, nav_i].sum()
        esc = chunk[:, esc_i].sum()
        turn = chunk[:, turn_i].sum()
        bar_nav = '#' * min(nav, 20)
        bar_esc = '*' * min(esc, 20)
        bar_turn = '~' * min(turn, 20)
        print(f"  {i*window:>5}-{(i+1)*window:<5} {states[i]:>8} | nav:{bar_nav} esc:{bar_esc} turn:{bar_turn}")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'experiment': 'dreaming_v2',
    'wake_steps': WAKE_STEPS, 'dream_steps': DREAM_STEPS,
    'noise_rate': NOISE_RATE, 'noise_weight': NOISE_WEIGHT,
    'dn_names': dn_names,
    'dream_total_mean': float(dream_total.mean()),
    'dream_cx_mean': float(dream_cx.mean()),
    'dn_timeseries': dn_ts.tolist(),
}
with open(f'{outdir}/dreaming_v2.json', 'w') as f:
    json.dump(output, f)
print(f"\nSaved to {outdir}/dreaming_v2.json")
