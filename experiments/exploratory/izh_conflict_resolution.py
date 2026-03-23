#!/usr/bin/env python3
"""
IZHIKEVICH CONFLICT RESOLUTION — Step 3

The Izhikevich strategy switching run (Step 2) confirmed:
  - CONFLICT SIGNATURE: both nav AND escape DNs active 48/50 steps during steps 500-550
  - Evolution improved overall escape (+152%) but did NOT resolve the conflict period
  - Nav DNs still fire 100% of conflict steps in evolved brain

This script evolves specifically for CONFLICT RESOLUTION:
  fitness = escape_activation(500-550) - nav_activation(500-550)

Goal: find edges that either suppress nav quickly or activate escape fast
after the stimulus switch. The transition window is the target.

Hypothesis: need inhibitory edges FROM escape circuits TO nav circuits,
or excitatory shortcuts that drive GF/MDN within the first 50 steps.
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
print("IZHIKEVICH CONFLICT RESOLUTION — Step 3")
print("=" * 60)

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
d = np.full(num_neurons, 8.0,  dtype=np.float32)

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
vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32, device=device)
_syn_vals = vals_tensor.clone()

weight_coo = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long),
                torch.tensor(pre, dtype=torch.long)]),
    vals_tensor, (num_neurons, num_neurons), dtype=torch.float32
)
W = weight_coo.to_sparse_csr()

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

PHASE1_STEPS = 500
PHASE2_STEPS = 500
CONFLICT_START = PHASE1_STEPS        # 500
CONFLICT_END   = PHASE1_STEPS + 50   # 550
TOTAL_STEPS = PHASE1_STEPS + PHASE2_STEPS

nav_dn_idx  = [i for i, n in enumerate(dn_names) if 'P9' in n or 'MN9' in n]
esc_dn_idx  = [i for i, n in enumerate(dn_names) if 'GF' in n or 'MDN' in n]

# ============================================================================
# Simulation — runs only 550 steps (phase 1 + conflict window only)
# Much faster per evaluation: ~10s vs ~21s for full 1000-step run
# ============================================================================
EVAL_STEPS = CONFLICT_END  # 550 — only simulate up to end of conflict window

def run_conflict_only(syn_vals_override=None):
    """Run simulation through end of conflict window (550 steps). Returns DN timeseries."""
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

    rates[0, STIM['sugar']] = POISSON_RATE

    dn_timeseries = []

    for step in range(EVAL_STEPS):
        if step == PHASE1_STEPS:
            rates.zero_()
            rates[0, STIM['lc4']] = POISSON_RATE

        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT
        recurrent = torch.mm(spikes, W_local.t()) * W_SCALE
        I = poisson_current + recurrent

        v_new = v + 0.5 * DT * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
        v_new = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new = u + DT * a_t * (b_t * v_new - u)

        fired = (v_new >= 30.0).float()
        v_new = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new = torch.clamp(v_new, -100.0, 30.0)

        v, u, spikes = v_new, u_new, fired

        spk = spikes.squeeze(0)
        dn_vec = [int(spk[dn_idx[j]].item()) for j in range(len(dn_names))]
        dn_timeseries.append(dn_vec)

    return np.array(dn_timeseries)


def fitness_conflict_resolution(dn_ts):
    """
    PRIMARY fitness: escape activation MINUS nav activation during steps 500-550.
    We want escape DNs to fire and nav DNs to be suppressed in the conflict window.

    Secondary: phase 1 nav score (don't break navigation behavior).
    """
    conflict_esc = float(dn_ts[CONFLICT_START:CONFLICT_END, esc_dn_idx].sum())
    conflict_nav = float(dn_ts[CONFLICT_START:CONFLICT_END, nav_dn_idx].sum())
    phase1_nav   = float(dn_ts[0:PHASE1_STEPS, nav_dn_idx].sum())

    # Primary: conflict resolution score
    resolution = conflict_esc - conflict_nav

    # Penalty if phase 1 navigation collapses (don't break the first phase)
    nav_penalty = max(0, 500.0 - phase1_nav) * 0.1  # soft floor

    fitness = resolution - nav_penalty

    return {
        'fitness': fitness,
        'resolution': resolution,
        'conflict_esc': conflict_esc,
        'conflict_nav': conflict_nav,
        'phase1_nav': phase1_nav,
        'nav_penalty': nav_penalty,
    }


# ============================================================================
# Baseline
# ============================================================================
print(f"\n{'='*60}")
print("BASELINE — Conflict Resolution Score")
print("="*60)

t0 = time.time()
dn_ts_bl = run_conflict_only()
t1 = time.time()
bl = fitness_conflict_resolution(dn_ts_bl)

print(f"Eval time: {t1-t0:.1f}s (550-step run)")
print(f"Phase 1 nav (0-500):      {bl['phase1_nav']:.1f}")
print(f"Conflict escape (500-550): {bl['conflict_esc']:.1f}")
print(f"Conflict nav (500-550):    {bl['conflict_nav']:.1f}")
print(f"Resolution score:          {bl['resolution']:.1f}  (escape - nav)")
print(f"Nav penalty:               {bl['nav_penalty']:.1f}")
print(f"FITNESS:                   {bl['fitness']:.1f}")

# Per-step conflict detail
print(f"\n--- CONFLICT WINDOW DETAIL (baseline) ---")
conflict_dn = dn_ts_bl[CONFLICT_START:CONFLICT_END]
nav_per_step = conflict_dn[:, nav_dn_idx].sum(axis=1)
esc_per_step = conflict_dn[:, esc_dn_idx].sum(axis=1)
nav_active = (nav_per_step > 0)
esc_active = (esc_per_step > 0)
both = nav_active & esc_active
print(f"Nav active:  {nav_active.sum()}/50 steps, mean {nav_per_step.mean():.2f} spikes/step")
print(f"Esc active:  {esc_active.sum()}/50 steps, mean {esc_per_step.mean():.2f} spikes/step")
print(f"Both active: {both.sum()}/50 steps  ← conflict score")

# ============================================================================
# Evolution targeting conflict window
# ============================================================================
print(f"\n{'='*60}")
print("EVOLUTION: Conflict Resolution (steps 500-550)")
print("="*60)
print("Fitness = escape_DNs(500-550) - nav_DNs(500-550)")
print("Each eval runs only 550 steps — roughly 2× faster than full run")
print()

N_GENERATIONS = 30
N_MUTATIONS   = 12
baseline_fitness = bl['fitness']
current_fitness  = baseline_fitness
best_syn_vals    = _syn_vals.clone()

np.random.seed(123)
torch.manual_seed(123)

all_mutations = []
accepted = 0
t_start = time.time()

for gen in range(N_GENERATIONS):
    ga = 0
    for mi in range(N_MUTATIONS):
        edge = inter_module_edges[np.random.randint(len(inter_module_edges))]
        syns = edge_syn_idx[edge]
        old = best_syn_vals[syns].clone()

        # Allow scaling DOWN (inhibition reduction) and UP (excitation boost)
        scale = np.random.choice([
            np.random.uniform(0.1, 0.9),   # reduce — may suppress nav
            np.random.uniform(1.1, 5.0),   # amplify — may boost escape
        ])
        test_vals = best_syn_vals.clone()
        test_vals[syns] = old * scale

        dn_ts = run_conflict_only(syn_vals_override=test_vals)
        result = fitness_conflict_resolution(dn_ts)
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
            'resolution': result['resolution'],
            'conflict_esc': result['conflict_esc'],
            'conflict_nav': result['conflict_nav'],
            'phase1_nav': result['phase1_nav'],
        }
        all_mutations.append(mutation)

        if acc:
            current_fitness = new_fitness
            best_syn_vals[syns] = old * scale
            ga += 1
            accepted += 1
            direction = "↑ESC" if scale > 1.0 else "↓INH"
            print(f"  G{gen:02d} M{mi:02d}: {edge[0]:>2}->{edge[1]:<2} s={scale:.2f} [{direction}] "
                  f"fit={new_fitness:.1f} esc={result['conflict_esc']:.0f} "
                  f"nav={result['conflict_nav']:.0f} "
                  f"res={result['resolution']:.1f} Δ={delta:+.1f} ACCEPTED")

    elapsed = time.time() - t_start
    remaining = elapsed / (gen + 1) * (N_GENERATIONS - gen - 1)
    if gen % 5 == 4 or gen == N_GENERATIONS - 1:
        print(f"  Gen {gen:02d}: fit={current_fitness:.1f} acc={ga}/{N_MUTATIONS} "
              f"total_acc={accepted} [{elapsed:.0f}s, {remaining:.0f}s rem]")

# ============================================================================
# Analysis
# ============================================================================
print(f"\n{'='*60}")
print("RESULTS — Conflict Resolution Evolution")
print("="*60)

dn_ts_final = run_conflict_only(syn_vals_override=best_syn_vals)
final = fitness_conflict_resolution(dn_ts_final)

print(f"Baseline: esc={bl['conflict_esc']:.1f} nav={bl['conflict_nav']:.1f} "
      f"resolution={bl['resolution']:.1f} fitness={bl['fitness']:.1f}")
print(f"Final:    esc={final['conflict_esc']:.1f} nav={final['conflict_nav']:.1f} "
      f"resolution={final['resolution']:.1f} fitness={final['fitness']:.1f}")
print(f"Accepted: {accepted}/{len(all_mutations)}")

# Accepted edges
acc_edges = [(m['edge'], m['scale'], m['delta']) for m in all_mutations if m['accepted']]
print(f"\nAccepted mutations ({len(acc_edges)}):")
for edge, scale, delta in acc_edges:
    direction = "AMPLIFY" if scale > 1.0 else "suppress"
    print(f"  {edge[0]:>2}->{edge[1]:<2}  scale={scale:.2f} [{direction}]  Δfit={delta:+.1f}")

# Unique accepted edges
unique_edges = sorted(set(tuple(m['edge']) for m in all_mutations if m['accepted']))
print(f"\nUnique evolvable edges: {len(unique_edges)}: {unique_edges}")

# Check for feedback loops in accepted edges
print(f"\nFeedback loop analysis:")
edge_set = set(tuple(e) for e in unique_edges)
loops = [(a, b) for (a, b) in edge_set if (b, a) in edge_set]
if loops:
    print(f"  RECIPROCAL PAIRS (feedback loops): {loops}")
else:
    print(f"  No reciprocal pairs found (all feedforward)")

# Conflict resolution in evolved brain
conflict_dn_ev = dn_ts_final[CONFLICT_START:CONFLICT_END]
nav_per_step_ev = conflict_dn_ev[:, nav_dn_idx].sum(axis=1)
esc_per_step_ev = conflict_dn_ev[:, esc_dn_idx].sum(axis=1)
nav_active_ev = (nav_per_step_ev > 0)
esc_active_ev = (esc_per_step_ev > 0)
both_ev = nav_active_ev & esc_active_ev

print(f"\nConflict period comparison (baseline vs evolved):")
print(f"  Nav active:  {nav_active.sum():>3}/50 → {nav_active_ev.sum():>3}/50  "
      f"({'+' if nav_active_ev.sum() > nav_active.sum() else ''}{nav_active_ev.sum()-nav_active.sum():+d})")
print(f"  Esc active:  {esc_active.sum():>3}/50 → {esc_active_ev.sum():>3}/50  "
      f"({'+' if esc_active_ev.sum() > esc_active.sum() else ''}{esc_active_ev.sum()-esc_active.sum():+d})")
print(f"  Both active: {both.sum():>3}/50 → {both_ev.sum():>3}/50  "
      f"(conflict steps)")
print(f"  Nav mean spikes: {nav_per_step.mean():.2f} → {nav_per_step_ev.mean():.2f}")
print(f"  Esc mean spikes: {esc_per_step.mean():.2f} → {esc_per_step_ev.mean():.2f}")

if final['resolution'] > bl['resolution']:
    improvement = final['resolution'] - bl['resolution']
    print(f"\n>>> CONFLICT RESOLUTION IMPROVED by {improvement:.1f} "
          f"({improvement/abs(bl['resolution'])*100:.0f}% if negative baseline)")
else:
    print(f"\n>>> No improvement in conflict resolution — conflict is intractable with edge mutations alone")

# Save
outdir = '/home/ubuntu/bulletproof_results'
output = {
    'experiment': 'izhikevich_conflict_resolution',
    'baseline': bl,
    'final': final,
    'accepted_edges': unique_edges,
    'total_accepted': accepted,
    'total_mutations': len(all_mutations),
    'mutations': all_mutations,
    'dn_names': dn_names,
    'conflict_both_active_baseline': int(both.sum()),
    'conflict_both_active_evolved': int(both_ev.sum()),
    'nav_mean_baseline': float(nav_per_step.mean()),
    'nav_mean_evolved': float(nav_per_step_ev.mean()),
    'esc_mean_baseline': float(esc_per_step.mean()),
    'esc_mean_evolved': float(esc_per_step_ev.mean()),
}
with open(f'{outdir}/izh_conflict_resolution.json', 'w') as f:
    json.dump(output, f)

print(f"\nSaved to {outdir}/izh_conflict_resolution.json")
print(f"Total time: {time.time()-t_start:.0f}s")
print("DONE.")
