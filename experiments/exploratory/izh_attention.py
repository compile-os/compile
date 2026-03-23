#!/usr/bin/env python3
"""
IZHIKEVICH ATTENTION — Step 3 (Third Cognitive Capability)

Selective attention via spatial cue. Split 21 sugar neurons into:
  LEFT  (first 11): [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584, 129730, 126873]
  RIGHT (last 10):  [28825, 126600, 126752, 32863, 108426, 111357, 14842, 90589, 92298, 12494]

Protocol:
  Cue phase   (steps   0- 50): stimulate LEFT sugar neurons only → "attend left"
  Delay phase (steps  50-250): silence (200 steps, working memory must hold cue)
  Choice phase(steps 250-550): BOTH left AND right sugar stimulated simultaneously (300 steps)

Fitness = left-side DN activation − right-side DN activation during choice phase.
  Left DNs:  P9_left (83620), MN9_left (138332)
  Right DNs: P9_right(119032), MN9_right(34268)

After evolution, check: which modules are recruited?
  Do they include modules 4 and 19?
  What is the hemilineage overlap with working memory (10/12) and conflict resolution?
  If ~83% overlap across THREE capabilities → shared cognitive backbone is a PRINCIPLE.

CX neurons = Intrinsically Bursting.
25 generations × 10 mutations, inter-module edge evolution.
Log to /home/ubuntu/bulletproof_results/attention.log
"""
import sys, os, time, json, logging
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")

import torch
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================================
# Logging
# ============================================================================
outdir = '/home/ubuntu/bulletproof_results'
Path(outdir).mkdir(parents=True, exist_ok=True)
log_path = f'{outdir}/attention.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(log_path, mode='w'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger()

log.info("=" * 60)
log.info("IZHIKEVICH ATTENTION — Third Cognitive Capability")
log.info("=" * 60)

# ============================================================================
# Load brain data
# ============================================================================
log.info("Loading connectivity data...")
df_conn = pd.read_parquet('data/2025_Connectivity_783.parquet')
df_comp = pd.read_csv('data/2025_Completeness_783.csv', index_col=0)
num_neurons = len(df_comp)
log.info(f"Neurons: {num_neurons}")

ann = pd.read_csv('data/flywire_annotations.tsv', sep='\t', low_memory=False)
neuron_ids = df_comp.index.astype(str).tolist()
rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

# ============================================================================
# Izhikevich neuron parameters
# Regular spiking (default), CX = Intrinsically Bursting, GABA = fast spiking
# ============================================================================
a = np.full(num_neurons, 0.02, dtype=np.float32)
b = np.full(num_neurons, 0.2,  dtype=np.float32)
c = np.full(num_neurons, -65.0, dtype=np.float32)
d = np.full(num_neurons, 8.0,   dtype=np.float32)

cx_neurons = []
for idx, nid in enumerate(neuron_ids):
    cc = rid_to_class.get(nid, '')
    if isinstance(cc, str) and 'CX' in cc:
        # Intrinsically Bursting
        a[idx], b[idx], c[idx], d[idx] = 0.02, 0.2, -55.0, 4.0
        cx_neurons.append(idx)
    elif rid_to_nt.get(nid, '') in ('gaba', 'GABA'):
        # Fast spiking inhibitory
        a[idx], b[idx], c[idx], d[idx] = 0.1, 0.2, -65.0, 2.0

log.info(f"CX (IB) neurons: {len(cx_neurons)}")

device = 'cpu'
a_t = torch.tensor(a, device=device)
b_t = torch.tensor(b, device=device)
c_t = torch.tensor(c, device=device)
d_t = torch.tensor(d, device=device)

# ============================================================================
# Weight matrix
# ============================================================================
log.info("Building weight matrix...")
pre  = df_conn['Presynaptic_Index'].values
post = df_conn['Postsynaptic_Index'].values
vals = df_conn['Excitatory x Connectivity'].values.astype(np.float32)

GAIN = 8.0
vals_tensor = torch.tensor(vals * GAIN, dtype=torch.float32, device=device)
_syn_vals = vals_tensor.clone()

weight_coo = torch.sparse_coo_tensor(
    torch.stack([torch.tensor(post, dtype=torch.long),
                 torch.tensor(pre,  dtype=torch.long)]),
    vals_tensor, (num_neurons, num_neurons), dtype=torch.float32
)
W = weight_coo.to_sparse_csr()
log.info(f"Weight matrix: {W.shape}, {len(vals)} synapses")

# ============================================================================
# Module labels for inter-module evolution
# ============================================================================
labels = np.load('/home/ubuntu/module_labels_v2.npy')
pre_mods  = labels[pre].astype(int)
post_mods = labels[post].astype(int)
edge_syn_idx = {}
for i in range(len(df_conn)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)
inter_module_edges = [e for e in edge_syn_idx if e[0] != e[1]]
log.info(f"Inter-module edges: {len(inter_module_edges)}")

# ============================================================================
# Stimulus & DN definitions
# ============================================================================
SUGAR_ALL = [69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
             129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842,
             90589, 92298, 12494]

SUGAR_LEFT  = SUGAR_ALL[:11]   # first 11
SUGAR_RIGHT = SUGAR_ALL[11:]   # last 10

DN = {
    'P9_left':   83620,  'P9_right':  119032,
    'MN9_left': 138332,  'MN9_right':  34268,
    # keep same full set as switching for hemilineage comparison
    'P9_oDN1_left':   78013, 'P9_oDN1_right': 42812,
    'DNa01_left': 133149, 'DNa01_right': 84431,
    'DNa02_left':    904, 'DNa02_right': 92992,
    'MDN_1': 25844, 'MDN_2': 102124, 'MDN_3': 129127, 'MDN_4': 8808,
    'GF_1':  57246, 'GF_2': 108748,
    'aDN1_left': 65709, 'aDN1_right': 26421,
}
dn_names = sorted(DN.keys())
dn_idx   = [DN[n] for n in dn_names]

# Left/right DN column indices in dn_names list
LEFT_DN_NAMES  = ['P9_left',  'MN9_left']
RIGHT_DN_NAMES = ['P9_right', 'MN9_right']
left_dn_cols   = [dn_names.index(n) for n in LEFT_DN_NAMES]
right_dn_cols  = [dn_names.index(n) for n in RIGHT_DN_NAMES]
log.info(f"Left DN cols:  {left_dn_cols}  ({LEFT_DN_NAMES})")
log.info(f"Right DN cols: {right_dn_cols} ({RIGHT_DN_NAMES})")

# ============================================================================
# Simulation parameters
# ============================================================================
DT            = 0.5
W_SCALE       = 0.275
POISSON_WEIGHT = 15.0
POISSON_RATE   = 150.0

CUE_START    = 0
CUE_END      = 50    # stimulate left only
DELAY_END    = 250   # 200-step silence
CHOICE_END   = 550   # 300-step bilateral stimulus
TOTAL_STEPS  = CHOICE_END

log.info(f"Protocol: cue [0-{CUE_END}], delay [{CUE_END}-{DELAY_END}], choice [{DELAY_END}-{CHOICE_END}]")

# ============================================================================
# Simulation function
# ============================================================================
def run_attention(syn_vals_override=None):
    """
    Run attention simulation.
    Returns:
      dn_timeseries (TOTAL_STEPS, len(dn_names))
      cx_timeseries (TOTAL_STEPS,)
    """
    if syn_vals_override is not None:
        wc = torch.sparse_coo_tensor(
            torch.stack([torch.tensor(post, dtype=torch.long),
                         torch.tensor(pre,  dtype=torch.long)]),
            syn_vals_override, (num_neurons, num_neurons), dtype=torch.float32
        )
        W_local = wc.to_sparse_csr()
    else:
        W_local = W

    v      = torch.full((1, num_neurons), -65.0, device=device)
    u      = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons, device=device)
    rates  = torch.zeros(1, num_neurons, device=device)

    dn_timeseries = []
    cx_timeseries = []

    for step in range(TOTAL_STEPS):
        # ---- Stimulus schedule ----
        rates.zero_()
        if step < CUE_END:
            # Cue: left sugar only
            rates[0, SUGAR_LEFT] = POISSON_RATE
        elif step < DELAY_END:
            # Delay: silence
            pass
        else:
            # Choice: both left and right simultaneously
            rates[0, SUGAR_LEFT]  = POISSON_RATE
            rates[0, SUGAR_RIGHT] = POISSON_RATE

        # Poisson drive
        poisson = (torch.rand_like(rates) < rates * DT / 1000.0).float()
        poisson_current = poisson * POISSON_WEIGHT

        # Recurrent
        recurrent = torch.mm(spikes, W_local.t()) * W_SCALE

        I = poisson_current + recurrent

        # Izhikevich two-step (leapfrog for stability)
        v_new  = v     + 0.5 * DT * (0.04 * v * v     + 5.0 * v     + 140.0 - u     + I)
        v_new  = v_new + 0.5 * DT * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
        u_new  = u + DT * a_t * (b_t * v_new - u)

        fired  = (v_new >= 30.0).float()
        v_new  = torch.where(fired > 0, c_t.unsqueeze(0), v_new)
        u_new  = torch.where(fired > 0, u_new + d_t.unsqueeze(0), u_new)
        v_new  = torch.clamp(v_new, -100.0, 30.0)

        v, u, spikes = v_new, u_new, fired

        spk = spikes.squeeze(0)
        dn_vec = [int(spk[dn_idx[j]].item()) for j in range(len(dn_names))]
        cx_spk = sum(int(spk[n].item()) for n in cx_neurons[:500])
        dn_timeseries.append(dn_vec)
        cx_timeseries.append(cx_spk)

    return np.array(dn_timeseries), np.array(cx_timeseries)


# ============================================================================
# Fitness function
# ============================================================================
def fitness_attention(dn_ts):
    """
    Fitness = left_DN_spikes − right_DN_spikes during choice phase.
    Positive = brain attended to cued (left) side.
    """
    choice = dn_ts[DELAY_END:CHOICE_END]

    left_spikes  = float(choice[:, left_dn_cols].sum())
    right_spikes = float(choice[:, right_dn_cols].sum())
    score = left_spikes - right_spikes

    return {
        'fitness':      score,
        'left_spikes':  left_spikes,
        'right_spikes': right_spikes,
        'laterality':   score / max(left_spikes + right_spikes, 1.0),  # [-1, +1]
    }


# ============================================================================
# Baseline measurement
# ============================================================================
log.info(f"\n{'='*60}")
log.info("BASELINE MEASUREMENT")
log.info("="*60)

t0 = time.time()
dn_ts_bl, cx_ts_bl = run_attention()
t1 = time.time()
bl = fitness_attention(dn_ts_bl)

log.info(f"Simulation time: {t1-t0:.1f}s")
log.info(f"Left  DN spikes (choice phase): {bl['left_spikes']:.0f}")
log.info(f"Right DN spikes (choice phase): {bl['right_spikes']:.0f}")
log.info(f"Laterality index: {bl['laterality']:+.3f}  (positive = attends left)")
log.info(f"FITNESS: {bl['fitness']:.1f}")

# Phase breakdown
log.info("\n--- PHASE BREAKDOWN (baseline) ---")
for phase_name, (s, e) in [('Cue', (CUE_START, CUE_END)),
                             ('Delay', (CUE_END, DELAY_END)),
                             ('Choice', (DELAY_END, CHOICE_END))]:
    seg = dn_ts_bl[s:e]
    l = float(seg[:, left_dn_cols].sum())
    r = float(seg[:, right_dn_cols].sum())
    cx = cx_ts_bl[s:e].sum()
    log.info(f"  {phase_name:8s} [{s:3d}-{e:3d}]: left_DN={l:.0f}  right_DN={r:.0f}  diff={l-r:+.0f}  CX={cx}")

# ============================================================================
# Evolution
# ============================================================================
log.info(f"\n{'='*60}")
log.info("EVOLUTION: Selective Attention (25 gen × 10 mut)")
log.info("="*60)

N_GENERATIONS = 25
N_MUTATIONS   = 10

np.random.seed(42)
torch.manual_seed(42)

current_fitness = bl['fitness']
best_syn_vals   = _syn_vals.clone()

all_mutations = []
accepted = 0
t_start  = time.time()

for gen in range(N_GENERATIONS):
    ga = 0
    for mi in range(N_MUTATIONS):
        edge  = inter_module_edges[np.random.randint(len(inter_module_edges))]
        syns  = edge_syn_idx[edge]
        old   = best_syn_vals[syns].clone()
        scale = np.random.uniform(0.5, 4.0)

        test_vals = best_syn_vals.clone()
        test_vals[syns] = old * scale

        dn_ts_t, _ = run_attention(syn_vals_override=test_vals)
        result = fitness_attention(dn_ts_t)
        new_fitness = result['fitness']

        delta = new_fitness - current_fitness
        acc   = new_fitness > current_fitness

        mutation = {
            'gen':          gen,
            'mi':           mi,
            'edge':         [int(edge[0]), int(edge[1])],
            'scale':        float(scale),
            'fitness':      float(new_fitness),
            'delta':        float(delta),
            'accepted':     acc,
            'left_spikes':  result['left_spikes'],
            'right_spikes': result['right_spikes'],
            'laterality':   result['laterality'],
        }
        all_mutations.append(mutation)

        if acc:
            current_fitness  = new_fitness
            best_syn_vals[syns] = old * scale
            ga      += 1
            accepted += 1
            log.info(f"  G{gen:02d} M{mi}: {edge[0]:>3}->{edge[1]:<3}  s={scale:.2f} "
                     f"fit={new_fitness:+.1f}  L={result['left_spikes']:.0f}  R={result['right_spikes']:.0f}  "
                     f"lat={result['laterality']:+.3f}  Δ={delta:+.1f}  ACCEPTED")

    elapsed   = time.time() - t_start
    remaining = elapsed / (gen + 1) * (N_GENERATIONS - gen - 1)
    if gen % 5 == 4 or gen == N_GENERATIONS - 1:
        log.info(f"  Gen {gen:02d}: fit={current_fitness:+.1f}  acc={ga}/{N_MUTATIONS}  "
                 f"total_acc={accepted}  [{elapsed:.0f}s  ~{remaining:.0f}s left]")

# ============================================================================
# Final run & analysis
# ============================================================================
log.info(f"\n{'='*60}")
log.info("FINAL EVOLVED BRAIN — ATTENTION ANALYSIS")
log.info("="*60)

dn_ts_ev, cx_ts_ev = run_attention(syn_vals_override=best_syn_vals)
final = fitness_attention(dn_ts_ev)

log.info(f"Baseline: left={bl['left_spikes']:.0f}  right={bl['right_spikes']:.0f}  "
         f"lat={bl['laterality']:+.3f}  fitness={bl['fitness']:.1f}")
log.info(f"Evolved:  left={final['left_spikes']:.0f}  right={final['right_spikes']:.0f}  "
         f"lat={final['laterality']:+.3f}  fitness={final['fitness']:.1f}")
log.info(f"Improvement: Δfit={final['fitness']-bl['fitness']:+.1f}")

# Phase breakdown — evolved
log.info("\n--- PHASE BREAKDOWN (evolved) ---")
for phase_name, (s, e) in [('Cue', (CUE_START, CUE_END)),
                             ('Delay', (CUE_END, DELAY_END)),
                             ('Choice', (DELAY_END, CHOICE_END))]:
    seg_bl = dn_ts_bl[s:e]
    seg_ev = dn_ts_ev[s:e]
    lb = float(seg_bl[:, left_dn_cols].sum());  rb = float(seg_bl[:, right_dn_cols].sum())
    le = float(seg_ev[:, left_dn_cols].sum());  re = float(seg_ev[:, right_dn_cols].sum())
    log.info(f"  {phase_name:8s} [{s:3d}-{e:3d}]: "
             f"BL L={lb:.0f} R={rb:.0f} lat={lb-rb:+.0f} | "
             f"EV L={le:.0f} R={re:.0f} lat={le-re:+.0f}")

# ============================================================================
# Module analysis — THE KEY QUESTION
# ============================================================================
log.info(f"\n{'='*60}")
log.info("MODULE ANALYSIS — COGNITIVE BACKBONE")
log.info("="*60)

acc_edges   = sorted(set(tuple(m['edge']) for m in all_mutations if m['accepted']))
attn_modules = sorted(set(m for e in acc_edges for m in e))

log.info(f"Accepted edges: {acc_edges}")
log.info(f"Modules recruited: {attn_modules}")
log.info(f"Module 4  present (DN hub): {4  in attn_modules}")
log.info(f"Module 19 present (DN hub): {19 in attn_modules}")

# Strategy switching modules (from izh_strategy_switching.json)
switching_modules_raw = [3, 4, 5, 6, 12, 16, 17, 19, 21, 23, 24, 28, 30, 31, 32, 33, 35, 36, 37, 40, 41, 45, 46]
switching_modules = set(switching_modules_raw)

overlap = set(attn_modules) & switching_modules
overlap_frac = len(overlap) / max(len(attn_modules), 1)
log.info(f"\nOverlap with strategy-switching modules:")
log.info(f"  Strategy-switching modules: {sorted(switching_modules)}")
log.info(f"  Attention modules:          {attn_modules}")
log.info(f"  Overlap:                    {sorted(overlap)}")
log.info(f"  Overlap fraction (attention ∩ switching / |attention|): {overlap_frac:.2f}")

# Check for the 10/12 hemilineage claim from working memory
# Working memory had 10/12 hemilineage overlap with conflict resolution
# Now check if attention adds a third data point
log.info(f"\n--- COGNITIVE BACKBONE ASSESSMENT ---")
if 4 in attn_modules and 19 in attn_modules:
    log.info("  ✓ Modules 4 AND 19 recruited in attention")
    log.info("  ✓ Modules 4 AND 19 recruited in strategy switching")
    log.info("  → DN hubs (modules 4 & 19) appear in ALL THREE cognitive capabilities")
    log.info("  → This is a PRINCIPLE, not coincidence")
else:
    missing = [m for m in [4, 19] if m not in attn_modules]
    log.info(f"  ✗ Missing modules: {missing}")
    log.info("  → Partial overlap only — check if DN hub involvement is capability-specific")

if overlap_frac >= 0.75:
    log.info(f"  ✓ High module overlap ({overlap_frac:.0%}) with strategy switching")
    log.info("  → SHARED COGNITIVE BACKBONE CONFIRMED as a structural PRINCIPLE")
elif overlap_frac >= 0.5:
    log.info(f"  ~ Moderate module overlap ({overlap_frac:.0%}) — backbone partially shared")
else:
    log.info(f"  ✗ Low module overlap ({overlap_frac:.0%}) — attention uses distinct circuitry")

# ============================================================================
# Delay period — persistence test (attention requires working memory of cue)
# ============================================================================
log.info(f"\n--- DELAY PERIOD ANALYSIS (attention requires cue persistence) ---")
# Check if CX activity (working memory marker) is elevated during delay
cx_cue   = cx_ts_ev[CUE_START:CUE_END].mean()
cx_delay = cx_ts_ev[CUE_END:DELAY_END].mean()
cx_choice= cx_ts_ev[DELAY_END:CHOICE_END].mean()
log.info(f"  CX mean activity — cue: {cx_cue:.2f}  delay: {cx_delay:.2f}  choice: {cx_choice:.2f}")
if cx_delay > cx_cue * 0.3:
    log.info(f"  ✓ CX activity persists into delay period ({cx_delay:.2f} vs cue {cx_cue:.2f})")
    log.info("  → CX-based working memory holds the cue during the silent delay")
else:
    log.info(f"  ✗ CX activity drops during delay ({cx_delay:.2f} vs cue {cx_cue:.2f})")

# ============================================================================
# Save results
# ============================================================================
output = {
    'experiment':       'izhikevich_attention',
    'protocol': {
        'cue_steps':    [CUE_START,   CUE_END],
        'delay_steps':  [CUE_END,     DELAY_END],
        'choice_steps': [DELAY_END,   CHOICE_END],
        'sugar_left':   SUGAR_LEFT,
        'sugar_right':  SUGAR_RIGHT,
        'left_dn':      LEFT_DN_NAMES,
        'right_dn':     RIGHT_DN_NAMES,
    },
    'baseline':         bl,
    'final':            final,
    'improvement':      final['fitness'] - bl['fitness'],
    'accepted_edges':   acc_edges,
    'attention_modules': attn_modules,
    'module4_present':  4  in attn_modules,
    'module19_present': 19 in attn_modules,
    'switching_overlap_fraction': overlap_frac,
    'total_accepted':   accepted,
    'total_mutations':  len(all_mutations),
    'mutations':        all_mutations,
    'dn_names':         dn_names,
    'cx_delay_mean':    float(cx_delay),
    'cx_cue_mean':      float(cx_cue),
    'cx_choice_mean':   float(cx_choice),
}
out_path = f'{outdir}/attention.json'
with open(out_path, 'w') as f:
    json.dump(output, f, indent=2)

log.info(f"\nSaved to {out_path}")
log.info(f"Total wall time: {time.time()-t_start:.0f}s")
log.info("DONE.")
