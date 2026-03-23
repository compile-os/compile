#!/usr/bin/env python3
"""
Verify compiled brains by reconstructing the evolved state from mutation logs.
Apply mutations IN SEQUENCE (as evolution did), then measure behavior.
"""
import sys, os
os.chdir("/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied/code")
sys.path.insert(0, "/home/ubuntu/fly-brain-embodied")
sys.path.insert(0, "/home/ubuntu/autoresearch")

import torch
import numpy as np
import json
from brain_body_bridge import BrainEngine

labels = np.load('/home/ubuntu/module_labels_v2.npy')
import pandas as pd
df = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')
pre_mods = labels[df['Presynaptic_Index'].values].astype(int)
post_mods = labels[df['Postsynaptic_Index'].values].astype(int)

edge_syn_idx = {}
for i in range(len(df)):
    edge = (int(pre_mods[i]), int(post_mods[i]))
    if edge not in edge_syn_idx:
        edge_syn_idx[edge] = []
    edge_syn_idx[edge].append(i)

GAIN = 8.0

def run_and_measure(brain, stimulus, n_steps=1000):
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    brain.set_stimulus(stimulus)

    dn_names = list(brain.dn_indices.keys())
    dn_idx = [brain.dn_indices[n] for n in dn_names]
    steps = np.zeros((n_steps, len(dn_names)), dtype=np.float32)

    for step in range(n_steps):
        brain.step()
        spk = brain.state[2].squeeze(0)
        for j, idx in enumerate(dn_idx):
            steps[step, j] = spk[idx].item()

    return dn_names, steps

def measure_circles(dn_names, steps):
    da01_l = dn_names.index('DNa01_left')
    da01_r = dn_names.index('DNa01_right')
    da02_l = dn_names.index('DNa02_left') if 'DNa02_left' in dn_names else -1
    da02_r = dn_names.index('DNa02_right') if 'DNa02_right' in dn_names else -1

    turn = []
    for t in range(len(steps)):
        l = steps[t, da01_l] + (steps[t, da02_l] if da02_l >= 0 else 0)
        r = steps[t, da01_r] + (steps[t, da02_r] if da02_r >= 0 else 0)
        turn.append(l - r)

    cumulative = np.cumsum(turn)
    w = 50
    windowed = [float(sum(turn[i*w:(i+1)*w])) for i in range(len(turn)//w)]
    return {
        'angular_displacement': float(abs(cumulative[-1])),
        'consistency': float(abs(np.mean(np.sign(np.array(turn) + 1e-10)))),
        'windowed': windowed,
        'total_turn_events': float(sum(abs(x) for x in turn)),
    }

def measure_rhythm(dn_names, steps):
    activity = steps.sum(axis=1)
    w = 50
    nw = len(activity) // w
    windowed = [float(activity[i*w:(i+1)*w].sum()) for i in range(nw)]
    on = np.mean([windowed[i] for i in range(0, nw, 2)]) if nw >= 2 else 0
    off = np.mean([windowed[i] for i in range(1, nw, 2)]) if nw >= 2 else 0
    return {
        'windowed': windowed,
        'on_mean': float(on),
        'off_mean': float(off),
        'contrast': float(on - off),
        'total': float(activity.sum()),
        'variability': float(np.std(windowed)) if windowed else 0,
    }

def reconstruct_evolved_brain(brain, baseline_weights, log_path):
    """Reconstruct evolved brain by applying accepted mutations IN ORDER."""
    brain._syn_vals.copy_(baseline_weights)
    
    accepted = []
    with open(log_path) as f:
        for line in f:
            if 'ACCEPTED' not in line:
                continue
            parts = line.strip().split()
            src = tgt = scale = None
            for p in parts:
                if '->' in p and not p.startswith('Δ'):
                    src, tgt = int(p.split('->')[0]), int(p.split('->')[1])
                if p.startswith('s='):
                    scale = float(p[2:])
            if src is not None and scale is not None:
                syns = edge_syn_idx.get((src, tgt), [])
                if syns:
                    brain._syn_vals[syns] *= scale
                    accepted.append({'src': src, 'tgt': tgt, 'scale': scale, 'n_syns': len(syns)})
    
    return accepted

print("=" * 70)
print("VERIFICATION: Evolved Brains (sequential mutation reconstruction)")
print("=" * 70)

# Create baseline
brain = BrainEngine(device='cpu')
brain._syn_vals.mul_(GAIN)
baseline_weights = brain._syn_vals.clone()

# ── BASELINE MEASUREMENTS ──
print("\n--- BASELINE ---")
names, steps = run_and_measure(brain, 'sugar', 1000)
bl_circles = measure_circles(names, steps)
bl_rhythm = measure_rhythm(names, steps)
print("Circles: displacement=%.1f consistency=%.3f events=%.0f" % (
    bl_circles['angular_displacement'], bl_circles['consistency'], bl_circles['total_turn_events']))
print("  windowed: %s" % [round(x,1) for x in bl_circles['windowed']])
print("Rhythm: contrast=%.2f on=%.1f off=%.1f total=%.0f var=%.2f" % (
    bl_rhythm['contrast'], bl_rhythm['on_mean'], bl_rhythm['off_mean'],
    bl_rhythm['total'], bl_rhythm['variability']))
print("  windowed: %s" % [round(x,1) for x in bl_rhythm['windowed']])

# ── CIRCLES VERIFICATION ──
for log_name in ['circles_v2_42', 'circles_v2_123', 'circles_v2_777']:
    log_path = '/home/ubuntu/multifitness_results/%s.log' % log_name
    if not os.path.exists(log_path):
        continue
    
    print("\n--- %s (evolved brain) ---" % log_name.upper())
    brain._syn_vals.copy_(baseline_weights)
    muts = reconstruct_evolved_brain(brain, baseline_weights, log_path)
    print("Applied %d mutations sequentially:" % len(muts))
    for m in muts:
        print("  %d→%d ×%.2f (%d synapses)" % (m['src'], m['tgt'], m['scale'], m['n_syns']))
    
    names, steps = run_and_measure(brain, 'sugar', 1000)
    ev_circles = measure_circles(names, steps)
    
    pct = 100 * (ev_circles['angular_displacement'] - bl_circles['angular_displacement']) / max(bl_circles['angular_displacement'], 0.001)
    print("Circles: displacement=%.1f (baseline %.1f, %+.0f%%)" % (
        ev_circles['angular_displacement'], bl_circles['angular_displacement'], pct))
    print("  consistency: %.3f (was %.3f)" % (ev_circles['consistency'], bl_circles['consistency']))
    print("  turn events: %.0f (was %.0f)" % (ev_circles['total_turn_events'], bl_circles['total_turn_events']))
    print("  windowed: %s" % [round(x,1) for x in ev_circles['windowed']])
    
    if pct > 20:
        print("  → ✓ CIRCLES VERIFIED — significantly more rotation!")
    elif pct > 5:
        print("  → ~ Some improvement")
    else:
        print("  → ✗ No improvement")

# ── RHYTHM VERIFICATION ──
for log_name in ['rhythm_v2_42', 'rhythm_v2_123']:
    log_path = '/home/ubuntu/multifitness_results/%s.log' % log_name
    if not os.path.exists(log_path):
        continue
    
    print("\n--- %s (evolved brain) ---" % log_name.upper())
    brain._syn_vals.copy_(baseline_weights)
    muts = reconstruct_evolved_brain(brain, baseline_weights, log_path)
    print("Applied %d mutations sequentially:" % len(muts))
    for m in muts:
        print("  %d→%d ×%.2f (%d synapses)" % (m['src'], m['tgt'], m['scale'], m['n_syns']))
    
    names, steps = run_and_measure(brain, 'sugar', 1000)
    ev_rhythm = measure_rhythm(names, steps)
    
    print("Rhythm: contrast=%.2f (baseline %.2f)" % (ev_rhythm['contrast'], bl_rhythm['contrast']))
    print("  on=%.1f off=%.1f (was on=%.1f off=%.1f)" % (
        ev_rhythm['on_mean'], ev_rhythm['off_mean'], bl_rhythm['on_mean'], bl_rhythm['off_mean']))
    print("  variability: %.2f (was %.2f)" % (ev_rhythm['variability'], bl_rhythm['variability']))
    print("  windowed: %s" % [round(x,1) for x in ev_rhythm['windowed']])
    
    contrast_pct = 100 * (ev_rhythm['contrast'] - bl_rhythm['contrast']) / max(abs(bl_rhythm['contrast']), 0.001)
    if ev_rhythm['contrast'] > bl_rhythm['contrast'] * 1.5 and ev_rhythm['contrast'] > 0:
        print("  → ✓ RHYTHM VERIFIED — stronger temporal alternation!")
    elif ev_rhythm['contrast'] > bl_rhythm['contrast']:
        print("  → ~ Some improvement")
    else:
        print("  → ✗ No improvement in alternation")

# Save evolved brain weights for the best circles run
print("\n--- SAVING COMPILED BRAINS ---")
for behavior, log_prefix in [('circles', 'circles_v2_777'), ('rhythm', 'rhythm_v2_123')]:
    log_path = '/home/ubuntu/multifitness_results/%s.log' % log_prefix
    if not os.path.exists(log_path):
        log_path = '/home/ubuntu/multifitness_results/%s.log' % log_prefix.replace('777', '42').replace('123', '42')
    if not os.path.exists(log_path):
        continue
    
    brain._syn_vals.copy_(baseline_weights)
    reconstruct_evolved_brain(brain, baseline_weights, log_path)
    save_path = '/home/ubuntu/multifitness_results/%s_compiled_brain.pt' % behavior
    torch.save(brain._syn_vals.clone(), save_path)
    print("Saved %s compiled brain to %s" % (behavior, save_path))

print("\nDone!")
