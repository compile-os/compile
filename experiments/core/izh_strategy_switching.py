#!/usr/bin/env python3
"""
IZHIKEVICH STRATEGY SWITCHING — Step 2

With persistent activity confirmed, test whether the brain can resolve
conflicting internal representations when stimulus changes.

Phase 1 (steps 0-500): Sugar stimulus → navigation behavior
Phase 2 (steps 500-1000): Switch to LC4 stimulus → escape behavior
  NO STATE RESET — neural activity carries over

Key measurement: the CONFLICT PERIOD (steps 500-550) where persistent
"navigate" representation competes with new "escape" stimulus.

Records full DN vector at every timestep to capture the transition dynamics.
"""
import sys, os, time, json
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================================
# Setup (same as persistence test)
# ============================================================================
print("=" * 60)
print("IZHIKEVICH STRATEGY SWITCHING")
print("=" * 60)

df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)

ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

# Assign neuron types
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

# Weight matrix
pre = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)
# Synaptic gain multiplier. Validated at 4x-8x (see gain_sensitivity experiment). 7x is optimal.
GAIN = 8.0
vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32, device=device)
_syn_vals = vals_tensor.clone()

weight_coo = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long),
                torch.tensor(pre, dtype=torch.long)]),
    vals_tensor, (num_neurons, num_neurons), dtype=torch.float32
)
W = weight_coo.to_sparse_csr()

# Module labels for edge-level evolution
labels = np.load('/home/ubuntu/module_labels_v2.npy')
pre_mods = labels[pre].astype(int)
post_mods = labels[post].astype(int)
edge_syn_idx = {}
for i in range(len(df_conn)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)
inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]
print(f"Inter-module edges: {len(inter_module_edges)}")

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

STIM = {
    'sugar': [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
              129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842,
              90589, 92298, 12494],
    'lc4': [1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
            45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424,
            100901, 124935, 264, 9350, 13067, 13728, 13909, 14284, 14345, 15883,
            17935, 18045, 20770, 20810, 22455, 22751, 23130, 24281, 25985, 28213,
            29383, 30533, 33149, 34245, 34246, 34402, 34409, 34445, 34603, 36093,
            36239, 36310, 38907, 42880, 42886, 45196, 46146, 47583, 49698, 51100,
            54455, 55583, 57783, 64467, 68119, 68461, 73496, 73522, 73846, 73964,
            77031, 79150, 82937, 86033, 86146, 88184, 88693, 89165, 89200, 89699,
            90786, 95107, 96243, 97190, 98862, 101707, 101892, 103513, 108651,
            109680, 109955, 110942, 111699, 112907, 115387, 118928, 121451,
            124829, 127954, 129665, 130519, 134682, 136520, 137218],
}

DT = 0.5
W_SCALE = 0.275
POISSON_WEIGHT = 15.0
POISSON_RATE = 150.0

PHASE1_STEPS = 500   # sugar (navigation)
PHASE2_STEPS = 500   # lc4 (escape)
CONFLICT_START = PHASE1_STEPS
CONFLICT_END = PHASE1_STEPS + 50
TOTAL_STEPS = PHASE1_STEPS + PHASE2_STEPS

# ============================================================================
# Simulation function
# ============================================================================
def run_switching(syn_vals_override=None, record_every=1):
    """Run two-phase switching simulation. Returns per-step DN vectors + CX activity."""
    # Build weight matrix
    if syn_vals_override is not None:
        wc = torch.sparse_coo_tensor(
            torch.stack([torch.tensor(post, dtype=torch.long),
                        torch.tensor(pre, dtype=torch.long)]),
            syn_vals_override, (num_neurons, num_neurons), dtype=torch.float32
        )
        W_local = wc.to_sparse_csr()
    else:
        W_local = W

    v = torch.full((1, num_neurons), -65.0, device=device)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons, device=device)
    rates = torch.zeros(1, num_neurons, device=device)

    # Phase 1: sugar
    rates[0, STIM['sugar']] = POISSON_RATE

    dn_timeseries = []  # (steps, 18) DN activity per step
    cx_timeseries = []
    total_timeseries = []

    for step in range(TOTAL_STEPS):
        # Switch stimulus at phase boundary
        if step == PHASE1_STEPS:
            rates.zero_()
            rates[0, STIM['lc4']] = POISSON_RATE

        # Poisson input
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT

        # Recurrent
        recurrent = torch.mm(spikes, W_local.t()) * W_SCALE

        I = poisson_current + recurrent

        # Izhikevich step
        v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new = u + DT * a_t * (b_t * v_new - u)

        fired = (v_new >= 30.0).float()
        v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new = torch.clamp(v_new, -100.0, 30.0)

        v, u, spikes = v_new, u_new, fired

        if step % record_every == 0:
            spk = spikes.squeeze(0)
            dn_vec = [int(spk[dn_idx[j]].item()) for j in range(len(dn_names))]
            cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
            dn_timeseries.append(dn_vec)
            cx_timeseries.append(cx_spk)
            total_timeseries.append(int(spk.sum().item()))

    return np.array(dn_timeseries), np.array(cx_timeseries), np.array(total_timeseries)


# ============================================================================
# Fitness functions
# ============================================================================
def fitness_nav(dn_ts, start, end):
    """Navigation score: P9 + MN9 during [start:end]."""
    p9_idx = [i for i, n in enumerate(dn_names) if 'P9' in n or 'MN9' in n]
    return float(dn_ts[start:end, p9_idx].sum())

def fitness_escape(dn_ts, start, end):
    """Escape score: GF + MDN during [start:end]."""
    gf_idx = [i for i, n in enumerate(dn_names) if 'GF' in n or 'MDN' in n]
    return float(dn_ts[start:end, gf_idx].sum())

def fitness_switching(dn_ts):
    """
    Strategy switching fitness:
    Phase 1 (0-500): navigation score
    Phase 2 (500-1000): escape score
    Conflict period (500-550): bonus for fast transition
    Fitness = min(nav, escape) + conflict_bonus
    """
    nav = fitness_nav(dn_ts, 0, PHASE1_STEPS)
    esc = fitness_escape(dn_ts, PHASE1_STEPS, TOTAL_STEPS)

    # Conflict bonus: reward if escape DNs activate quickly after switch
    conflict_escape = fitness_escape(dn_ts, CONFLICT_START, CONFLICT_END)
    # Penalty if nav DNs PERSIST during conflict (should be suppressed)
    conflict_nav = fitness_nav(dn_ts, CONFLICT_START, CONFLICT_END)

    conflict_bonus = conflict_escape - 0.5 * conflict_nav  # reward fast switching

    return {
        'fitness': min(nav, esc) + max(0, conflict_bonus),
        'nav': nav,
        'escape': esc,
        'conflict_escape': conflict_escape,
        'conflict_nav': conflict_nav,
        'conflict_bonus': conflict_bonus,
    }

# ============================================================================
# Step 2a: Baseline measurement
# ============================================================================
print(f"\n{'='*60}")
print("BASELINE MEASUREMENT")
print("="*60)

t0 = time.time()
dn_ts, cx_ts, total_ts = run_switching()
t1 = time.time()
bl = fitness_switching(dn_ts)

print(f"Simulation time: {t1-t0:.1f}s")
print(f"Phase 1 (nav):     {bl['nav']:.1f}")
print(f"Phase 2 (escape):  {bl['escape']:.1f}")
print(f"Conflict escape:   {bl['conflict_escape']:.1f}")
print(f"Conflict nav:      {bl['conflict_nav']:.1f}")
print(f"Conflict bonus:    {bl['conflict_bonus']:.1f}")
print(f"FITNESS:           {bl['fitness']:.1f}")

# Analyze the transition
print(f"\n--- TRANSITION DYNAMICS (around step 500) ---")
window = 25  # 25-step windows
for w_start in range(400, 600, window):
    w_end = min(w_start + window, TOTAL_STEPS)
    nav_w = fitness_nav(dn_ts, w_start, w_end)
    esc_w = fitness_escape(dn_ts, w_start, w_end)
    cx_w = cx_ts[w_start:w_end].sum()
    phase = "NAV" if w_start < 500 else "ESC"
    marker = " <<<SWITCH" if w_start == 500 else ""
    print(f"  Steps {w_start}-{w_end}: nav={nav_w:>5.0f} esc={esc_w:>5.0f} CX={cx_w:>5} [{phase}]{marker}")

# ============================================================================
# Step 2b: Evolution
# ============================================================================
print(f"\n{'='*60}")
print("EVOLUTION: Strategy Switching")
print("="*60)

N_GENERATIONS = 25
N_MUTATIONS = 10
baseline_fitness = bl['fitness']
current_fitness = baseline_fitness
best_syn_vals = _syn_vals.clone()

np.random.seed(42)
torch.manual_seed(42)

all_mutations = []
accepted = 0
t_start = time.time()

for gen in range(N_GENERATIONS):
    ga = 0
    for mi in range(N_MUTATIONS):
        edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
        syns = edge_syn_idx[edge]
        old = best_syn_vals[syns].clone()
        scale = np.random.uniform(0.5, 4.0)
        test_vals = best_syn_vals.clone()
        test_vals[syns] = old * scale

        dn_ts, cx_ts, total_ts = run_switching(syn_vals_override=test_vals, record_every=1)
        result = fitness_switching(dn_ts)
        new_fitness = result['fitness']

        delta = new_fitness - current_fitness
        acc = new_fitness > current_fitness

        mutation = {
            'gen': gen, 'mi': mi,
            'edge': [int(edge[0]), int(edge[1])],
            'scale': float(scale),
            'fitness': float(new_fitness),
            'delta': float(delta),
            'accepted': acc,
            'nav': result['nav'],
            'escape': result['escape'],
            'conflict_escape': result['conflict_escape'],
            'conflict_nav': result['conflict_nav'],
        }
        all_mutations.append(mutation)

        if acc:
            current_fitness = new_fitness
            best_syn_vals[syns] = old * scale
            ga += 1
            accepted += 1
            print(f"  G{gen} M{mi}: {edge[0]}->{edge[1]} s={scale:.2f} "
                  f"fit={new_fitness:.1f} nav={result['nav']:.0f} esc={result['escape']:.0f} "
                  f"conflict_esc={result['conflict_escape']:.0f} Δ={delta:+.1f} ACCEPTED")
        else:
            pass  # revert implicit — we use test_vals

    elapsed = time.time() - t_start
    remaining = elapsed / (gen + 1) * (N_GENERATIONS - gen - 1)
    if gen % 5 == 4 or gen == N_GENERATIONS - 1:
        print(f"  Gen {gen}: fit={current_fitness:.1f} acc={ga}/{N_MUTATIONS} "
              f"total_acc={accepted} [{elapsed:.0f}s elapsed, {remaining:.0f}s remaining]")

# ============================================================================
# Step 2c: Analysis
# ============================================================================
print(f"\n{'='*60}")
print("RESULTS")
print("="*60)

# Run final evolved brain
dn_ts_final, cx_ts_final, total_ts_final = run_switching(syn_vals_override=best_syn_vals)
final = fitness_switching(dn_ts_final)

print(f"Baseline: nav={bl['nav']:.1f}, escape={bl['escape']:.1f}, fitness={bl['fitness']:.1f}")
print(f"Final:    nav={final['nav']:.1f}, escape={final['escape']:.1f}, fitness={final['fitness']:.1f}")
print(f"Accepted: {accepted}/{len(all_mutations)}")

# Accepted edges
acc_edges = sorted(set(tuple(m['edge']) for m in all_mutations if m['accepted']))
print(f"Evolvable edges: {len(acc_edges)}: {acc_edges}")

# Transition dynamics comparison
print(f"\n--- TRANSITION COMPARISON (baseline vs evolved) ---")
print(f"{'Window':<15} {'BL_nav':>7} {'BL_esc':>7} {'EV_nav':>7} {'EV_esc':>7} {'Δnav':>7} {'Δesc':>7}")
for w_start in range(400, 600, 25):
    w_end = min(w_start + 25, TOTAL_STEPS)
    bl_nav = fitness_nav(dn_ts, w_start, w_end)
    bl_esc = fitness_escape(dn_ts, w_start, w_end)
    ev_nav = fitness_nav(dn_ts_final, w_start, w_end)
    ev_esc = fitness_escape(dn_ts_final, w_start, w_end)
    marker = " <<<" if w_start == 500 else ""
    print(f"  {w_start}-{w_end}{marker:<10} {bl_nav:>7.0f} {bl_esc:>7.0f} {ev_nav:>7.0f} {ev_esc:>7.0f} "
          f"{ev_nav-bl_nav:>+7.0f} {ev_esc-bl_esc:>+7.0f}")

# Check for conflict signature
print(f"\n--- CONFLICT ANALYSIS ---")
# In the conflict period, are BOTH nav and escape DNs active simultaneously?
conflict_dn = dn_ts_final[CONFLICT_START:CONFLICT_END]
nav_active = (conflict_dn[:, [i for i, n in enumerate(dn_names) if 'P9' in n or 'MN9' in n]].sum(axis=1) > 0)
esc_active = (conflict_dn[:, [i for i, n in enumerate(dn_names) if 'GF' in n or 'MDN' in n]].sum(axis=1) > 0)
both_active = nav_active & esc_active
print(f"Conflict period (steps {CONFLICT_START}-{CONFLICT_END}):")
print(f"  Nav DNs active: {nav_active.sum()}/{len(nav_active)} steps")
print(f"  Escape DNs active: {esc_active.sum()}/{len(esc_active)} steps")
print(f"  BOTH active simultaneously: {both_active.sum()}/{len(both_active)} steps")
if both_active.sum() > 5:
    print(f"  >>> CONFLICT SIGNATURE DETECTED: competing representations coexist")
else:
    print(f"  >>> No conflict: transition is instant (stimulus-dominated)")

# Save
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
output = {
    'experiment': 'izhikevich_strategy_switching',
    'baseline': bl,
    'final': final,
    'accepted_edges': acc_edges,
    'total_accepted': accepted,
    'total_mutations': len(all_mutations),
    'mutations': all_mutations,
    'dn_names': dn_names,
    'conflict_both_active_steps': int(both_active.sum()),
}
with open(f'{outdir}/izh_strategy_switching.json', 'w') as f:
    json.dump(output, f)

print(f"\nSaved to {outdir}/izh_strategy_switching.json")
print(f"Total time: {time.time() - t_start:.0f}s")
print("DONE.")
