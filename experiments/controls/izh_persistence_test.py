#!/usr/bin/env python3
"""
IZHIKEVICH PERSISTENCE TEST
Gate experiment: does the central complex sustain activity after input removal?
"""
import sys, os, time
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd

# ============================================================================
# Izhikevich neuron types
# ============================================================================
NEURON_TYPES = {
    'RS':  {'a': 0.02,  'b': 0.2,  'c': -65.0, 'd': 8.0},
    'IB':  {'a': 0.02,  'b': 0.2,  'c': -55.0, 'd': 4.0},
    'FS':  {'a': 0.1,   'b': 0.2,  'c': -65.0, 'd': 2.0},
}

print("=" * 60)
print("IZHIKEVICH PERSISTENCE TEST")
print("=" * 60)

# Load connectome
print("Loading connectome...")
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)
print(f"Neurons: {num_neurons}")

# Load annotations for neuron type assignment
ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

# Assign neuron types
a = np.full(num_neurons, 0.02, dtype=np.float32)  # RS default
b = np.full(num_neurons, 0.2,  dtype=np.float32)
c = np.full(num_neurons, -65.0, dtype=np.float32)
d = np.full(num_neurons, 8.0, dtype=np.float32)

n_ib, n_fs = 0, 0
for idx, nid in enumerate(neuron_ids):
    cell_class = rid_to_class.get(nid, '')
    nt = rid_to_nt.get(nid, '')
    if isinstance(cell_class, str) and 'CX' in cell_class:
        a[idx], b[idx], c[idx], d[idx] = 0.02, 0.2, -55.0, 4.0  # IB
        n_ib += 1
    elif nt == 'gaba' or nt == 'GABA':
        a[idx], b[idx], c[idx], d[idx] = 0.1, 0.2, -65.0, 2.0   # FS
        n_fs += 1

print(f"Types: {n_ib} IB (CX), {n_fs} FS (GABA), {num_neurons-n_ib-n_fs} RS")

# Convert to tensors
device = 'cpu'
a_t = torch.tensor(a, device=device)
b_t = torch.tensor(b, device=device)
c_t = torch.tensor(c, device=device)
d_t = torch.tensor(d, device=device)

# Build sparse weight matrix
print("Building weight matrix...")
pre = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

GAIN = 8.0
vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32, device=device)

weight_coo = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long),
                torch.tensor(pre, dtype=torch.long)]),
    vals_tensor,
    (num_neurons, num_neurons), dtype=torch.float32
)
W = weight_coo.to_sparse_csr()

# DN and stimulus indices (from BrainEngine)
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

STIM = {
    'sugar': [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584, 129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842, 90589, 92298, 12494],
    'lc4': [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646, 45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424, 100901, 124935],
    'jo': [133917, 23290, 40779, 42646, 43215, 100833, 108537, 114244, 1828, 4290, 6375, 24322, 43314, 51816, 54541, 59929, 74572, 82120, 96822, 107107, 107820, 116136],
}

# Find CX neuron indices for monitoring
cx_neurons = []
for idx, nid in enumerate(neuron_ids):
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        cx_neurons.append(idx)
print(f"CX neurons for monitoring: {len(cx_neurons)}")

# Simulation parameters
DT = 0.5  # ms
W_SCALE = 0.275
POISSON_WEIGHT = 15.0
POISSON_RATE = 150.0  # Hz

def run_simulation(stim_name, stim_steps, post_steps):
    """Run stimulus then silence, return per-step activity."""
    v = torch.full((1, num_neurons), -65.0, device=device)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons, device=device)
    
    rates = torch.zeros(1, num_neurons, device=device)
    if stim_name in STIM:
        rates[0, STIM[stim_name]] = POISSON_RATE
    
    cx_activity = []
    dn_activity = []
    total_activity = []
    
    total_steps = stim_steps + post_steps
    
    for step in range(total_steps):
        # Remove stimulus at transition
        if step == stim_steps:
            rates.zero_()
        
        # Poisson input
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT
        
        # Recurrent input
        recurrent = torch.mm(spikes, W.t()) * W_SCALE
        
        # Total input
        I = poisson_current + recurrent
        
        # Izhikevich dynamics (half-step)
        v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new = u + DT * a_t * (b_t * v_new - u)
        
        # Spike detection
        fired = (v_new >= 30.0).float()
        v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new = torch.clamp(v_new, -100.0, 30.0)
        
        v, u, spikes = v_new, u_new, fired
        
        # Record
        spk = spikes.squeeze(0)
        cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
        dn_spk = sum(int(spk[DN[name]].item()) for name in DN)
        total_spk = int(spk.sum().item())
        
        cx_activity.append(cx_spk)
        dn_activity.append(dn_spk)
        total_activity.append(total_spk)
    
    return cx_activity, dn_activity, total_activity


# Run for each stimulus
for stim_name in ['lc4', 'sugar', 'jo']:
    print(f"\n{'='*60}")
    print(f"STIMULUS: {stim_name}")
    print(f"{'='*60}")
    
    t0 = time.time()
    cx, dn, total = run_simulation(stim_name, stim_steps=200, post_steps=500)
    elapsed = time.time() - t0
    
    # Stim phase stats
    stim_cx = cx[:200]
    stim_dn = dn[:200]
    stim_total = total[:200]
    print(f"  Stim phase (200 steps, {elapsed:.1f}s):")
    print(f"    CX: {sum(stim_cx)} total, {np.mean(stim_cx):.2f}/step")
    print(f"    DN: {sum(stim_dn)} total")
    print(f"    All: {sum(stim_total)} total, {np.mean(stim_total):.1f}/step")
    
    # Post-stimulus analysis (50-step windows)
    post_cx = cx[200:]
    post_dn = dn[200:]
    post_total = total[200:]
    
    print(f"  Post-stimulus activity (50-step windows):")
    for w in range(10):
        w_cx = post_cx[w*50:(w+1)*50]
        w_dn = post_dn[w*50:(w+1)*50]
        w_total = post_total[w*50:(w+1)*50]
        cx_mean = np.mean(w_cx)
        status = "ACTIVE" if cx_mean > 0.5 else "silent"
        print(f"    Steps {w*50}-{(w+1)*50}: CX={sum(w_cx):>4}, DN={sum(w_dn):>3}, "
              f"Total={sum(w_total):>5}, CX/step={cx_mean:.2f} [{status}]")
    
    # Persistence verdict
    last_window_cx = np.mean(post_cx[-50:])
    mid_window_cx = np.mean(post_cx[200:250])
    
    if last_window_cx > 1.0:
        print(f"  >>> PERSISTENT ACTIVITY! CX={last_window_cx:.2f}/step after 500 steps")
        print(f"  >>> ATTRACTOR DYNAMICS CONFIRMED")
    elif mid_window_cx > 0.5:
        print(f"  >>> PARTIAL PERSISTENCE: CX active at 200 steps ({mid_window_cx:.2f}), decayed by 500 ({last_window_cx:.2f})")
    else:
        print(f"  >>> NO PERSISTENCE: CX died quickly ({last_window_cx:.2f}/step at end)")

print(f"\n{'='*60}")
print("PERSISTENCE TEST COMPLETE")
print("="*60)
