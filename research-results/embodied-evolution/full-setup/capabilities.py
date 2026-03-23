"""
Embodied evolution capabilities. Agents CAN and SHOULD add new functions.
All functions operate on connectome DataFrames.
"""

import os
os.environ['MUJOCO_GL'] = 'osmesa'
os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

import numpy as np
import pandas as pd
import copy
import random
import sys
sys.path.insert(0, '/home/ubuntu/fly-brain-embodied')

# ── Module-level caches (avoid re-init overhead) ──────────────────────────────
_BRAIN_CACHE = None   # Singleton BrainEngine
_ORIG_DF_CACHE = None  # Biological connectome values for delta-injection


def load_connectome():
    """Load the FlyWire connectome as DataFrame."""
    path = '/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet'
    df = pd.read_parquet(path)
    return df


def mutate(df, n_mutations=5, seed=None, strategy="mixed", weight_range=0.2, rewire_radius=500):
    """
    Mutate connectome.

    Args:
        df: Connectome DataFrame
        n_mutations: Number of mutations to apply
        seed: Random seed
        strategy: 'weight' (only weights), 'rewire' (only topology), 'mixed' (90% weight, 10% rewire)
        weight_range: Max relative change for weights (0.2 = ±20%)
        rewire_radius: Max index offset for rewiring

    Returns:
        (mutated_df, mutation_details) where mutation_details is a list of dicts:
        [{'index': int, 'type': 'weight'|'rewire', 'old_value': float, 'new_value': float}, ...]
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    df = df.copy()
    weight_col = 'syn_count' if 'syn_count' in df.columns else df.columns[-1]

    # Cast to float64 so fractional mutations are preserved. The parquet stores
    # 'Excitatory x Connectivity' as int64; without this, ±20% changes on small
    # values (e.g. 1 → 0.8) truncate back to the original integer and mutations
    # silently have no effect on brain behaviour.
    if df[weight_col].dtype.kind in ('i', 'u'):
        df[weight_col] = df[weight_col].astype(np.float64)

    indices = list(range(len(df)))
    chosen = random.sample(indices, min(n_mutations, len(indices)))

    mutation_details = []
    for idx in chosen:
        if strategy == "weight" or (strategy == "mixed" and random.random() < 0.9):
            old_val = float(df.iloc[idx][weight_col])
            change = np.random.uniform(-weight_range, weight_range) * abs(old_val)
            new_val = max(0, old_val + change)
            df.at[df.index[idx], weight_col] = new_val
            mutation_details.append({
                'index': int(idx),
                'type': 'weight',
                'old_value': old_val,
                'new_value': float(new_val),
            })
        else:
            # Rewire: change postsynaptic target
            pre_col = [c for c in df.columns if 'pre' in c.lower()][0]
            post_col = [c for c in df.columns if 'post' in c.lower()][0]
            old_post = int(df.iloc[idx][post_col])
            offset = random.randint(-rewire_radius, rewire_radius)
            new_post = max(0, old_post + offset)
            df.at[df.index[idx], post_col] = new_post
            mutation_details.append({
                'index': int(idx),
                'type': 'rewire',
                'old_value': old_post,
                'new_value': int(new_post),
            })

    return df, mutation_details


def run_embodied(df, duration_sec=2.0, seed=42, stimulus='sugar'):
    """
    Run embodied simulation with given connectome.

    Uses HybridTurningController (CPG + turning) so brain drive actually
    controls locomotion. Injects modified connectome weights into the
    BrainEngine so mutations are reflected in behavior.

    Args:
        df: Connectome DataFrame (weights are injected into neural sim)
        duration_sec: Simulation duration in seconds
        seed: Random seed for reproducibility
        stimulus: 'sugar', 'p9', 'lc4', 'jo', 'bitter', 'or56a'

    Returns:
        dict with fitness metrics
    """
    global _BRAIN_CACHE, _ORIG_DF_CACHE
    import torch

    np.random.seed(seed)

    from flygym import Fly
    from flygym.examples.locomotion.turning_controller import HybridTurningController
    from brain_body_bridge import BrainEngine, DNRateDecoder, BrainBodyBridge

    # ── Brain: init once, reuse across calls ─────────────────────────────────
    if _BRAIN_CACHE is None:
        _BRAIN_CACHE = BrainEngine(device='cpu')
        # CRITICAL: always use the BIOLOGICAL connectome as the delta-injection
        # reference, regardless of which df is passed first. If we use df here,
        # a mutant brain would become the reference and all injections would
        # compute deltas relative to it (not biological), making mutations
        # invisible to the neural simulation.
        _bio = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')
        _ORIG_DF_CACHE = _bio['Excitatory x Connectivity'].values.astype(np.float64)
        del _bio

    brain = _BRAIN_CACHE

    # ── Inject modified weights into BrainEngine ─────────────────────────────
    _inject_connectome_weights(brain, df, _ORIG_DF_CACHE)

    # ── Reset neural state (spike history, Hebbian accumulators) ─────────────
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0

    # ── Body: HybridTurningController (CPG + stumble + turning) ─────────────
    contact_sensors = [
        f"{leg}{seg}"
        for leg in ["LF", "LM", "LH", "RF", "RM", "RH"]
        for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]
    ]
    fly = Fly(enable_adhesion=True, contact_sensor_placements=contact_sensors,
              spawn_pos=(0.0, 0.0, 0.3), spawn_orientation=(0, 0, np.pi))  # Face AWAY from food
    sim = HybridTurningController(fly=fly, timestep=1e-4, seed=seed)
    decoder = DNRateDecoder(window_ms=50.0, dt_ms=0.1, max_rate=200.0)
    bridge = BrainBodyBridge(decoder)

    brain.set_stimulus(stimulus)
    obs, info = sim.reset(seed=seed)

    # ── Simulation loop ───────────────────────────────────────────────────────
    positions = []
    total_spikes = 0
    active_neurons_set = set()
    BRAIN_RATIO = 100
    num_steps = int(duration_sec / sim.timestep)

    for step in range(num_steps):
        if step % BRAIN_RATIO == 0:
            brain.step()
            dn_spikes = brain.get_dn_spikes()
            decoder.update(dn_spikes, None)
            # Track spike statistics
            if hasattr(brain, '_spike_acc'):
                spikes_this_step = brain._spike_acc.cpu().numpy().flatten()
                spiking_neurons = np.where(spikes_this_step > 0)[0]
                total_spikes += int(spikes_this_step.sum())
                active_neurons_set.update(spiking_neurons.tolist())

        # drive = [left, right] — passed directly to HybridTurningController
        drive = bridge.compute_drive(dt=BRAIN_RATIO * sim.timestep)

        try:
            obs, _, terminated, truncated, _ = sim.step(drive)
        except Exception:
            break

        fly_obs = obs.get('fly', np.zeros((4, 3)))
        positions.append(fly_obs[0].copy())

        if terminated or truncated:
            break

    if len(positions) < 2:
        return {'fitness': -9999.0, 'distance_traveled': 0.0,
                'food_distance': 9999.0, 'displacement': 0.0,
                'final_position': [0, 0, 0], 'initial_position': [0, 0, 0],
                'trajectory': [], 'spike_summary': {'total_spikes': 0, 'active_neurons': 0}}

    # ── Fitness metrics ───────────────────────────────────────────────────────
    final_pos = np.array(positions[-1])
    initial_pos = np.array(positions[0])
    food_pos = np.array([0.075, 0.0, 0.0])  # 75mm from origin (fly starts facing away)

    distance_traveled = float(sum(
        np.linalg.norm(np.array(positions[i+1]) - np.array(positions[i]))
        for i in range(len(positions) - 1)
    ))
    food_distance = float(np.linalg.norm(final_pos[:2] - food_pos[:2]))
    displacement = float(np.linalg.norm(final_pos[:2] - initial_pos[:2]))

    # ── Trajectory: subsample to ~100 points for reasonable JSON size ────────
    step_size = max(1, len(positions) // 100)
    trajectory = [[float(p[0]), float(p[1])] for p in positions[::step_size]]

    return {
        'fitness': -food_distance,  # Higher = better (closer to food)
        'distance_traveled': distance_traveled,
        'food_distance': food_distance,
        'displacement': displacement,
        'final_position': final_pos.tolist(),
        'initial_position': initial_pos.tolist(),
        'trajectory': trajectory,
        'spike_summary': {
            'total_spikes': total_spikes,
            'active_neurons': len(active_neurons_set),
        },
    }


def _inject_connectome_weights(brain, df, orig_vals):
    """
    Update BrainEngine weights to match df.

    Fast path: if only a few synapses changed, update in-place.
    Slow path: if structure changed (ablate/scale), rebuild full CSR.
    """
    import torch

    mod_vals = df['Excitatory x Connectivity'].values

    # ── Structural change: different number of synapses ───────────────────────
    if len(mod_vals) != len(orig_vals):
        num_neurons = brain.num_neurons
        post_idx = df['Postsynaptic_Index'].values.tolist()
        pre_idx = df['Presynaptic_Index'].values.tolist()
        vals = mod_vals.astype('float32').tolist()
        new_coo = torch.sparse_coo_tensor(
            [post_idx, pre_idx], vals, (num_neurons, num_neurons),
            dtype=torch.float32
        )
        brain.model.weights = new_coo.to_sparse_csr().to(brain.device)
        brain._init_plasticity()
        return

    # ── Weight-only change: update in-place ──────────────────────────────────
    changed_mask = mod_vals != orig_vals
    n_changed = int(changed_mask.sum())

    if n_changed == 0:
        return  # Biological brain — nothing to do

    post_changed = df['Postsynaptic_Index'].values[changed_mask]
    pre_changed = df['Presynaptic_Index'].values[changed_mask]
    new_vals = mod_vals[changed_mask].astype('float32')

    crow = brain._row_ptr.cpu().numpy()
    col_idx = brain._col_idx.cpu().numpy()

    for i in range(n_changed):
        row = int(post_changed[i])
        col = int(pre_changed[i])
        row_start = int(crow[row])
        row_end = int(crow[row + 1])
        col_slice = col_idx[row_start:row_end]
        local = int(np.searchsorted(col_slice, col))
        if local < len(col_slice) and col_slice[local] == col:
            brain._syn_vals[row_start + local] = float(new_vals[i])

    # Recompute plasticity bounds for changed synapses
    brain._sign_mask = torch.sign(brain._syn_vals)
    max_mag = 3.0 * brain._abs_orig
    brain._clamp_min = torch.where(
        brain._sign_mask < 0, -max_mag, torch.zeros_like(max_mag))
    brain._clamp_max = torch.where(
        brain._sign_mask > 0, max_mag, torch.zeros_like(max_mag))


def merge_brains(original_df, evolved_a, evolved_b):
    """Combine mutations from two independently evolved brains into one."""
    merged = original_df.copy()
    weight_col = 'syn_count' if 'syn_count' in original_df.columns else original_df.columns[-1]

    diff_a = evolved_a[weight_col].values - original_df[weight_col].values
    diff_b = evolved_b[weight_col].values - original_df[weight_col].values
    merged[weight_col] = original_df[weight_col].values + diff_a + diff_b

    return merged


def scale_brain(df, factor, seed=42):
    """
    Scale brain size.

    Args:
        df: Connectome DataFrame
        factor: 0.5 = remove half the neurons, 2.0 = duplicate all

    Returns:
        Scaled DataFrame
    """
    random.seed(seed)

    pre_col = [c for c in df.columns if 'pre' in c.lower()][0]
    post_col = [c for c in df.columns if 'post' in c.lower()][0]

    if factor < 1.0:
        # Sample from ACTUAL unique neuron IDs (not range(max_ID) — FlyWire IDs are
        # ~7e17, which would cause MemoryError with range())
        unique_neurons = list(set(df[pre_col].unique()) | set(df[post_col].unique()))
        n_keep = max(1, int(len(unique_neurons) * factor))
        keep = set(random.sample(unique_neurons, n_keep))
        mask = df[pre_col].isin(keep) & df[post_col].isin(keep)
        return df[mask].reset_index(drop=True)
    elif factor > 1.0:
        # Duplicate brain and add cross-connections
        original = df.copy()
        max_idx = max(df[pre_col].max(), df[post_col].max()) + 1
        duped = df.copy()
        duped[pre_col] = duped[pre_col] + max_idx
        duped[post_col] = duped[post_col] + max_idx
        cross = df.sample(frac=0.1, random_state=seed).copy()
        cross[post_col] = cross[post_col] + max_idx
        return pd.concat([original, duped, cross], ignore_index=True)

    return df.copy()


def compete(df_a, df_b, seed=42, stimulus='sugar'):
    """Run two brains in same arena, return both fitness scores."""
    result_a = run_embodied(df_a, seed=seed, stimulus=stimulus)
    result_b = run_embodied(df_b, seed=seed, stimulus=stimulus)

    return {
        "a": result_a,
        "b": result_b,
        "winner": "a" if result_a['fitness'] > result_b['fitness'] else "b",
        "margin": abs(result_a['fitness'] - result_b['fitness'])
    }


def crossover(original_df, evolved_a, evolved_b, ratio=0.5, seed=42):
    """
    Sexual reproduction: take ratio% of A's changes, rest from B.
    """
    random.seed(seed)
    child = original_df.copy()
    weight_col = 'syn_count' if 'syn_count' in original_df.columns else original_df.columns[-1]

    diff_a = evolved_a[weight_col].values - original_df[weight_col].values
    diff_b = evolved_b[weight_col].values - original_df[weight_col].values

    changed_a = np.where(np.abs(diff_a) > 1e-10)[0]
    changed_b = np.where(np.abs(diff_b) > 1e-10)[0]

    from_a = set(random.sample(list(changed_a), int(len(changed_a) * ratio))) if len(changed_a) > 0 else set()
    from_b = set(random.sample(list(changed_b), int(len(changed_b) * (1 - ratio)))) if len(changed_b) > 0 else set()

    for idx in from_a:
        child.at[child.index[idx], weight_col] = evolved_a.iloc[idx][weight_col]
    for idx in from_b:
        child.at[child.index[idx], weight_col] = evolved_b.iloc[idx][weight_col]

    return child


def add_plasticity(df, spike_data, rule="hebbian", rate=0.01):
    """
    Modify weights based on spike co-activity.
    Call in loop: simulate -> plasticize -> repeat.
    """
    df = df.copy()
    weight_col = 'syn_count' if 'syn_count' in df.columns else df.columns[-1]
    pre_col = [c for c in df.columns if 'pre' in c.lower()][0]
    post_col = [c for c in df.columns if 'post' in c.lower()][0]

    active_neurons = set(spike_data.get('active_neurons', [])) if isinstance(spike_data, dict) else set()

    for idx in range(min(len(df), 100000)):  # Limit for speed
        pre = df.iloc[idx][pre_col]
        post = df.iloc[idx][post_col]
        pre_active = pre in active_neurons
        post_active = post in active_neurons

        if rule == "hebbian":
            if pre_active and post_active:
                df.at[df.index[idx], weight_col] *= (1 + rate)
            elif pre_active and not post_active:
                df.at[df.index[idx], weight_col] *= (1 - rate)

    return df


def ablate(df, neuron_indices):
    """Remove all connections involving specified neurons."""
    pre_col = [c for c in df.columns if 'pre' in c.lower()][0]
    post_col = [c for c in df.columns if 'post' in c.lower()][0]
    mask = ~(df[pre_col].isin(neuron_indices) | df[post_col].isin(neuron_indices))
    return df[mask].reset_index(drop=True)


def transplant(source_df, target_df, mutation_indices):
    """Apply specific mutations from source connectome to target connectome."""
    target = target_df.copy()
    weight_col = 'syn_count' if 'syn_count' in target_df.columns else target_df.columns[-1]

    for idx in mutation_indices:
        if idx < len(source_df) and idx < len(target):
            target.at[target.index[idx], weight_col] = source_df.iloc[idx][weight_col]

    return target


# ============== Add your own functions below ==============
# Example:
# def my_new_analysis(df, ...):
#     """Your custom analysis function."""
#     pass


# ══════════════════════════════════════════════════════════════════════════════
# MEMORY FORENSICS — Read, erase, and implant memories from the connectome
# ══════════════════════════════════════════════════════════════════════════════
#
# The FlyWire connectome is from ONE specific fly that lived a specific life.
# Its memories are encoded in KC→MBON synaptic weights in the mushroom body.
# These functions let you READ what this fly learned during its lifetime.
#
# Mushroom body structure:
#   - Kenyon cells (KCs): ~2000 neurons, encode odor combinations
#   - MBONs: ~34 types, some drive APPROACH, some drive AVOIDANCE
#   - DANs: dopaminergic neurons that deliver reward/punishment
#
# Memory encoding:
#   - Appetitive memory (liked it): strong KC→approach-MBON weights
#   - Aversive memory (avoided it): strong KC→avoidance-MBON weights
#   - No memory: weak/absent KC→MBON weights
# ══════════════════════════════════════════════════════════════════════════════

# Known MBON types and their behavioral valence (from Drosophila literature)
APPROACH_MBONS = [
    'MBON01', 'MBON03', 'MBON04', 'MBON05', 'MBON06',  # γ lobe approach
    'MBON07', 'MBON14',  # α/β approach
]
AVOIDANCE_MBONS = [
    'MBON08', 'MBON09', 'MBON10', 'MBON11', 'MBON12',  # γ lobe avoidance  
    'MBON13', 'MBON15',  # α/β avoidance
]

# Olfactory glomeruli (odor channels) - each responds to specific odorants
ODOR_GLOMERULI = {
    'DM1': 'vinegar/acetic_acid',
    'DM2': 'ethyl_acetate', 
    'DM3': 'fruit_esters',
    'DM4': 'geranyl_acetate',
    'DM5': 'acetoin',
    'DL1': 'warning_pheromone',
    'DL3': 'food_odors',
    'DL4': 'benzaldehyde',
    'DL5': 'CO2_avoidance',
    'VA1d': 'male_pheromone_cVA',
    'VA1v': 'female_pheromone',
    'VA2': 'geosmin_danger',
    'VA3': 'sweet_odors',
    'VA6': 'ammonia',
    'VA7l': 'acids',
    'VL2a': 'attractive_odors',
    'VL2p': 'citrus',
    'VM2': 'attractive_food',
    'VM3': 'repulsive_odors',
    'VM7d': 'yeast',
    'VM7v': 'fermentation',
    # Add more as needed from FlyWire annotations
}


def get_mushroom_body_neurons(df):
    """
    Identify mushroom body neurons in the connectome.
    
    Returns dict with:
        'kenyon_cells': list of KC neuron indices
        'approach_mbons': list of approach MBON indices
        'avoidance_mbons': list of avoidance MBON indices
        'all_mbons': all MBON indices
        'dans': dopaminergic neuron indices
    
    Note: This searches by neuron type annotations if available,
    or by connectivity patterns if not. Agents should refine this
    based on actual FlyWire cell type data.
    """
    # Check if we have cell type annotations
    type_col = None
    for col in df.columns:
        if 'type' in col.lower() or 'class' in col.lower():
            type_col = col
            break
    
    mb_neurons = {
        'kenyon_cells': [],
        'approach_mbons': [],
        'avoidance_mbons': [],
        'all_mbons': [],
        'dans': [],
    }
    
    # If no type column, return empty (agent should find another way)
    if type_col is None:
        print("WARNING: No cell type column found. Agent should identify MB neurons from FlyWire annotations.")
        return mb_neurons
    
    # Search for mushroom body neurons by type
    for idx, row in df.iterrows():
        cell_type = str(row.get(type_col, '')).upper()
        if 'KC' in cell_type or 'KENYON' in cell_type:
            mb_neurons['kenyon_cells'].append(idx)
        elif 'MBON' in cell_type:
            mb_neurons['all_mbons'].append(idx)
            # Classify by known approach/avoidance types
            for ap_type in APPROACH_MBONS:
                if ap_type in cell_type:
                    mb_neurons['approach_mbons'].append(idx)
                    break
            for av_type in AVOIDANCE_MBONS:
                if av_type in cell_type:
                    mb_neurons['avoidance_mbons'].append(idx)
                    break
        elif 'DAN' in cell_type or 'DOPAMIN' in cell_type:
            mb_neurons['dans'].append(idx)
    
    return mb_neurons


def read_memory(df, odor_name, duration_ms=200, seed=42):
    """
    Stimulate one odor channel and read the mushroom body response.
    
    This tells you what THIS SPECIFIC FLY learned about this odor:
    - High approach MBON activation = appetitive memory (fly liked it)
    - High avoidance MBON activation = aversive memory (fly avoided it)
    - Low/no MBON activation = no memory formed
    
    Args:
        df: Connectome DataFrame
        odor_name: Name of odor to test (key in ODOR_GLOMERULI or glomerulus ID)
        duration_ms: Simulation duration in milliseconds
        seed: Random seed
        
    Returns:
        dict with:
            'odor': the tested odor
            'approach_score': summed activation of approach MBONs
            'avoidance_score': summed activation of avoidance MBONs
            'memory_type': 'appetitive', 'aversive', or 'none'
            'confidence': ratio of dominant response to total
            'kc_activation': which Kenyon cells fired
            'mbon_details': per-MBON spike counts
    """
    global _BRAIN_CACHE
    import torch
    
    np.random.seed(seed)
    
    from brain_body_bridge import BrainEngine
    
    if _BRAIN_CACHE is None:
        _BRAIN_CACHE = BrainEngine(device='cpu')
    
    brain = _BRAIN_CACHE
    
    # Get mushroom body neurons
    mb = get_mushroom_body_neurons(df)
    
    # Map odor name to stimulus (agent may need to refine this mapping)
    stimulus = odor_name.lower() if odor_name.lower() in ['sugar', 'p9', 'bitter', 'lc4', 'jo', 'or56a'] else 'sugar'
    
    # Reset brain state
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    
    # Set stimulus
    brain.set_stimulus(stimulus)
    
    # Run for duration_ms
    num_steps = int(duration_ms / 0.1)  # 0.1ms per step
    
    kc_spikes = np.zeros(len(mb['kenyon_cells']))
    approach_spikes = np.zeros(len(mb['approach_mbons']))
    avoidance_spikes = np.zeros(len(mb['avoidance_mbons']))
    
    for step in range(num_steps):
        brain.step()
        
        # Record spikes from mushroom body neurons
        if hasattr(brain, '_spike_acc'):
            spikes = brain._spike_acc.cpu().numpy().flatten()
            for i, kc_idx in enumerate(mb['kenyon_cells']):
                if kc_idx < len(spikes):
                    kc_spikes[i] += spikes[kc_idx]
            for i, mbon_idx in enumerate(mb['approach_mbons']):
                if mbon_idx < len(spikes):
                    approach_spikes[i] += spikes[mbon_idx]
            for i, mbon_idx in enumerate(mb['avoidance_mbons']):
                if mbon_idx < len(spikes):
                    avoidance_spikes[i] += spikes[mbon_idx]
    
    approach_score = float(np.sum(approach_spikes))
    avoidance_score = float(np.sum(avoidance_spikes))
    total = approach_score + avoidance_score + 1e-6
    
    # Classify memory type
    if approach_score > avoidance_score * 1.5:
        memory_type = 'appetitive'
        confidence = approach_score / total
    elif avoidance_score > approach_score * 1.5:
        memory_type = 'aversive'
        confidence = avoidance_score / total
    else:
        memory_type = 'none'
        confidence = 0.0
    
    return {
        'odor': odor_name,
        'approach_score': approach_score,
        'avoidance_score': avoidance_score,
        'memory_type': memory_type,
        'confidence': confidence,
        'kc_activation_count': int(np.sum(kc_spikes > 0)),
        'total_kc_spikes': float(np.sum(kc_spikes)),
    }


def read_all_memories(df, seed=42):
    """
    Read this fly's complete memory map — what it learned about every odor.
    
    Returns:
        dict mapping odor names to memory records
        Plus summary statistics
    """
    memories = {}
    
    for glom_id, odor_name in ODOR_GLOMERULI.items():
        result = read_memory(df, glom_id, seed=seed)
        result['glomerulus'] = glom_id
        result['odor_description'] = odor_name
        memories[glom_id] = result
    
    # Summarize
    appetitive = [k for k, v in memories.items() if v['memory_type'] == 'appetitive']
    aversive = [k for k, v in memories.items() if v['memory_type'] == 'aversive']
    no_memory = [k for k, v in memories.items() if v['memory_type'] == 'none']
    
    return {
        'memories': memories,
        'summary': {
            'appetitive_odors': appetitive,
            'aversive_odors': aversive,
            'no_memory_odors': no_memory,
            'total_appetitive': len(appetitive),
            'total_aversive': len(aversive),
            'total_no_memory': len(no_memory),
        }
    }


def erase_memory(df, target_odor, erase_strength=1.0):
    """
    Erase a specific memory by weakening KC→MBON connections for that odor.
    
    Args:
        df: Connectome DataFrame
        target_odor: Which odor memory to erase
        erase_strength: 1.0 = complete erasure, 0.5 = partial
        
    Returns:
        (modified_df, erasure_details)
    """
    df = df.copy()
    mb = get_mushroom_body_neurons(df)
    
    # Find which KCs respond to this odor (would need to trace from ORNs)
    # For now, we'll weaken ALL KC→MBON connections slightly
    # Agent should refine to target specific KCs based on odor input tracing
    
    weight_col = df.columns[-1]  # Usually 'Excitatory x Connectivity'
    
    erasure_count = 0
    pre_col = [c for c in df.columns if 'pre' in c.lower()][0]
    post_col = [c for c in df.columns if 'post' in c.lower()][0]
    
    for idx in range(len(df)):
        pre = df.iloc[idx][pre_col]
        post = df.iloc[idx][post_col]
        
        # If this is a KC→MBON connection, weaken it
        if pre in mb['kenyon_cells'] and post in mb['all_mbons']:
            old_weight = df.iloc[idx][weight_col]
            new_weight = old_weight * (1 - erase_strength)
            df.at[df.index[idx], weight_col] = new_weight
            erasure_count += 1
    
    return df, {
        'target_odor': target_odor,
        'connections_modified': erasure_count,
        'erase_strength': erase_strength,
    }


def implant_memory(df, source_odor, target_odor, strength=1.0):
    """
    Implant a memory by copying KC→MBON weight patterns.
    
    Makes the fly respond to target_odor the way it responds to source_odor.
    If source_odor triggered approach, target_odor will now trigger approach.
    
    Args:
        df: Connectome DataFrame
        source_odor: Copy memory pattern FROM this odor
        target_odor: Copy memory pattern TO this odor
        strength: How strongly to implant (1.0 = full copy)
        
    Returns:
        (modified_df, implant_details)
    """
    # This is a stub — agent should implement based on:
    # 1. Identify which KCs are activated by source_odor
    # 2. Identify which KCs are activated by target_odor
    # 3. Copy the KC→MBON weight pattern from source KCs to target KCs
    
    return df.copy(), {
        'source_odor': source_odor,
        'target_odor': target_odor,
        'strength': strength,
        'status': 'STUB — agent should implement KC mapping',
    }


def compare_memories(df_a, df_b, label_a='brain_a', label_b='brain_b'):
    """
    Compare memory maps between two connectomes.
    
    Useful for:
    - Before/after evolution: which memories survived?
    - Parent/child comparison: which memories were inherited?
    - Ablation effects: which memories were stored in ablated neurons?
    
    Returns:
        dict with per-odor comparisons and summary of changes
    """
    mem_a = read_all_memories(df_a)
    mem_b = read_all_memories(df_b)
    
    comparisons = {}
    changed = []
    preserved = []
    
    for odor in ODOR_GLOMERULI.keys():
        type_a = mem_a['memories'].get(odor, {}).get('memory_type', 'unknown')
        type_b = mem_b['memories'].get(odor, {}).get('memory_type', 'unknown')
        
        if type_a == type_b:
            preserved.append(odor)
        else:
            changed.append(odor)
        
        comparisons[odor] = {
            f'{label_a}_type': type_a,
            f'{label_b}_type': type_b,
            'changed': type_a != type_b,
        }
    
    return {
        'comparisons': comparisons,
        'summary': {
            'preserved_memories': preserved,
            'changed_memories': changed,
            'total_preserved': len(preserved),
            'total_changed': len(changed),
            'preservation_rate': len(preserved) / (len(preserved) + len(changed) + 1e-6),
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# DREAMS — Spontaneous brain activity with zero sensory input
# ══════════════════════════════════════════════════════════════════════════════
#
# Run the brain with NO sensory input: no food, no odor, no light, no touch.
# Whatever activity emerges is the connectome's spontaneous dynamics —
# the patterns that the wiring diagram produces on its own.
# 
# That's the closest thing to a dream. The brain replaying its own structure.
#
# Drosophila DO sleep in real life. Sleep is when memories consolidate.
# If dream activity correlates with stored memories, that's evidence the
# connectome encodes not just what the fly learned, but how it rehearses.
# ══════════════════════════════════════════════════════════════════════════════


def dream(df, duration_ms=2000, record_interval_ms=15, seed=42):
    """
    Run the brain with ZERO sensory input. No food, no odor, no stimuli.
    Record all spontaneous activity — this is the connectome dreaming.
    
    Args:
        df: Connectome DataFrame
        duration_ms: How long to dream (milliseconds)
        record_interval_ms: How often to snapshot neural state
        seed: Random seed
        
    Returns:
        dict with:
            'trajectory': body position over time (fly may still move!)
            'spike_timeline': list of spike snapshots at each interval
            'mbon_timeline': MBON activation over time (memory replay)
            'motor_timeline': motor neuron activation (spontaneous movement)
            'total_spikes': total spikes during dream
            'active_neurons': which neurons fired spontaneously
            'dream_duration_ms': actual duration
    """
    global _BRAIN_CACHE, _ORIG_DF_CACHE
    import torch
    
    np.random.seed(seed)
    
    from flygym import Fly
    from flygym.examples.locomotion.turning_controller import HybridTurningController
    from brain_body_bridge import BrainEngine, DNRateDecoder, BrainBodyBridge
    
    # ── Initialize brain ─────────────────────────────────────────────────────
    if _BRAIN_CACHE is None:
        _BRAIN_CACHE = BrainEngine(device='cpu')
        _bio = pd.read_parquet('/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet')
        _ORIG_DF_CACHE = _bio['Excitatory x Connectivity'].values.astype(np.float64)
        del _bio

    brain = _BRAIN_CACHE
    _inject_connectome_weights(brain, df, _ORIG_DF_CACHE)
    
    # Reset brain state
    brain.state = brain.model.state_init()
    brain.rates = torch.zeros(1, brain.num_neurons, device=brain.device)
    brain._spike_acc.zero_()
    brain._hebb_count = 0
    
    # ── CRITICAL: Set NO stimulus — the brain dreams in darkness ────────────
    # Use a null/baseline stimulus that provides no sensory drive
    try:
        brain.set_stimulus(None)  # Try None first
    except:
        try:
            brain.set_stimulus('none')  # Try 'none' string
        except:
            # If no null stimulus, use minimal sugar but we note this
            brain.set_stimulus('sugar')
            print("WARNING: Could not set null stimulus, using minimal 'sugar'")
    
    # ── Initialize body (fly may move spontaneously during dreams!) ─────────
    contact_sensors = [
        f"{leg}{seg}"
        for leg in ["LF", "LM", "LH", "RF", "RM", "RH"]
        for seg in ["Tibia", "Tarsus1", "Tarsus2", "Tarsus3", "Tarsus4", "Tarsus5"]
    ]
    fly = Fly(enable_adhesion=True, contact_sensor_placements=contact_sensors,
              spawn_pos=(0.0, 0.0, 0.3), spawn_orientation=(0, 0, np.pi))  # Face AWAY from food
    sim = HybridTurningController(fly=fly, timestep=1e-4, seed=seed)
    decoder = DNRateDecoder(window_ms=50.0, dt_ms=0.1, max_rate=200.0)
    bridge = BrainBodyBridge(decoder)
    
    obs, info = sim.reset(seed=seed)
    
    # ── Get mushroom body neurons for tracking memory replay ────────────────
    mb = get_mushroom_body_neurons(df)
    
    # ── Dream loop ───────────────────────────────────────────────────────────
    positions = []
    spike_timeline = []
    mbon_timeline = []
    motor_timeline = []
    all_active_neurons = set()
    total_spikes = 0
    
    BRAIN_RATIO = 100  # Brain steps per physics step
    num_steps = int(duration_ms / (sim.timestep * 1000))
    record_every = int(record_interval_ms / (sim.timestep * 1000 * BRAIN_RATIO))
    
    brain_step_count = 0
    
    for step in range(num_steps):
        if step % BRAIN_RATIO == 0:
            brain.step()
            brain_step_count += 1
            
            dn_spikes = brain.get_dn_spikes()
            decoder.update(dn_spikes, None)
            
            # Record spike activity
            if hasattr(brain, '_spike_acc'):
                spikes = brain._spike_acc.cpu().numpy().flatten()
                spiking = np.where(spikes > 0)[0]
                total_spikes += int(spikes.sum())
                all_active_neurons.update(spiking.tolist())
                
                # Record timeline snapshots
                if brain_step_count % max(1, record_every) == 0:
                    spike_timeline.append({
                        'time_ms': brain_step_count * 0.1 * BRAIN_RATIO,
                        'active_count': len(spiking),
                        'total_spikes': int(spikes.sum()),
                    })
                    
                    # Track MBON activation (memory replay)
                    approach_act = sum(spikes[i] for i in mb['approach_mbons'] if i < len(spikes))
                    avoidance_act = sum(spikes[i] for i in mb['avoidance_mbons'] if i < len(spikes))
                    mbon_timeline.append({
                        'time_ms': brain_step_count * 0.1 * BRAIN_RATIO,
                        'approach_mbon_spikes': float(approach_act),
                        'avoidance_mbon_spikes': float(avoidance_act),
                    })
        
        # Let the body respond to spontaneous motor commands
        drive = bridge.compute_drive(dt=BRAIN_RATIO * sim.timestep)
        motor_timeline.append({'left': float(drive[0]), 'right': float(drive[1])})
        
        try:
            obs, _, terminated, truncated, _ = sim.step(drive)
        except:
            break
        
        fly_obs = obs.get('fly', np.zeros((4, 3)))
        positions.append(fly_obs[0].copy())
        
        if terminated or truncated:
            break
    
    # ── Compute dream trajectory stats ───────────────────────────────────────
    if len(positions) >= 2:
        final_pos = np.array(positions[-1])
        initial_pos = np.array(positions[0])
        displacement = float(np.linalg.norm(final_pos[:2] - initial_pos[:2]))
        distance_traveled = float(sum(
            np.linalg.norm(np.array(positions[i+1]) - np.array(positions[i]))
            for i in range(len(positions) - 1)
        ))
    else:
        displacement = 0.0
        distance_traveled = 0.0
    
    # Subsample trajectory
    step_size = max(1, len(positions) // 100)
    trajectory = [[float(p[0]), float(p[1])] for p in positions[::step_size]]
    
    return {
        'dream_duration_ms': duration_ms,
        'trajectory': trajectory,
        'displacement': displacement,
        'distance_traveled': distance_traveled,
        'body_moved': displacement > 0.01,  # Did the fly move during dreaming?
        'spike_timeline': spike_timeline,
        'mbon_timeline': mbon_timeline,
        'motor_timeline': motor_timeline[-100:],  # Last 100 motor commands
        'total_spikes': total_spikes,
        'active_neurons': len(all_active_neurons),
        'active_neuron_indices': list(all_active_neurons)[:1000],  # First 1000 for size
    }


def compare_dream_to_waking(dream_result, waking_result):
    """
    Compare which neurons active during waking replay during dreaming.
    
    High overlap = memory consolidation (brain replays experiences)
    Low overlap = random noise (dreams are not memory-related)
    
    Args:
        dream_result: Output from dream()
        waking_result: Output from run_embodied() with spike tracking
        
    Returns:
        dict with overlap statistics and interpretation
    """
    dream_neurons = set(dream_result.get('active_neuron_indices', []))
    
    # Waking neurons might be in spike_summary or need to be extracted
    waking_neurons = set()
    if 'active_neuron_indices' in waking_result:
        waking_neurons = set(waking_result['active_neuron_indices'])
    
    if not dream_neurons or not waking_neurons:
        return {
            'overlap_count': 0,
            'overlap_ratio': 0.0,
            'interpretation': 'INSUFFICIENT DATA — need spike tracking in both conditions',
            'dream_only': len(dream_neurons),
            'waking_only': len(waking_neurons),
        }
    
    overlap = dream_neurons & waking_neurons
    dream_only = dream_neurons - waking_neurons
    waking_only = waking_neurons - dream_neurons
    
    # Jaccard similarity
    union = dream_neurons | waking_neurons
    jaccard = len(overlap) / len(union) if union else 0.0
    
    # Interpretation
    if jaccard > 0.5:
        interpretation = 'HIGH OVERLAP — strong memory replay during dreams'
    elif jaccard > 0.2:
        interpretation = 'MODERATE OVERLAP — partial memory replay'
    elif jaccard > 0.05:
        interpretation = 'LOW OVERLAP — dreams may be random exploration'
    else:
        interpretation = 'MINIMAL OVERLAP — dream activity independent of waking'
    
    return {
        'overlap_count': len(overlap),
        'overlap_ratio': jaccard,
        'dream_active': len(dream_neurons),
        'waking_active': len(waking_neurons),
        'dream_only_count': len(dream_only),
        'waking_only_count': len(waking_only),
        'interpretation': interpretation,
    }


def dream_memory_replay(df, seed=42):
    """
    Dream and specifically check which MEMORIES replay.
    
    Compares MBON activation patterns during dreams to the fly's memory map.
    If approach MBONs for "vinegar" activate during dreams, the fly is
    replaying its appetitive memory for vinegar.
    
    Returns:
        dict with memory replay analysis
    """
    # First read the fly's memories
    memories = read_all_memories(df, seed=seed)
    
    # Then let it dream
    dream_result = dream(df, duration_ms=2000, seed=seed)
    
    # Analyze MBON timeline for memory replay
    mbon_data = dream_result.get('mbon_timeline', [])
    
    if not mbon_data:
        return {
            'memories': memories,
            'dream': dream_result,
            'replay_analysis': 'NO MBON DATA',
        }
    
    # Sum approach vs avoidance activation during dreams
    total_approach = sum(m['approach_mbon_spikes'] for m in mbon_data)
    total_avoidance = sum(m['avoidance_mbon_spikes'] for m in mbon_data)
    
    # Determine what type of memories replay
    if total_approach > total_avoidance * 1.5:
        dominant_replay = 'APPETITIVE'
        replay_interpretation = 'Fly dreams about things it LIKED'
    elif total_avoidance > total_approach * 1.5:
        dominant_replay = 'AVERSIVE'
        replay_interpretation = 'Fly dreams about things it AVOIDED (nightmares?)'
    else:
        dominant_replay = 'MIXED'
        replay_interpretation = 'Balanced replay of positive and negative memories'
    
    return {
        'memories': memories['summary'],
        'dream_stats': {
            'total_spikes': dream_result['total_spikes'],
            'active_neurons': dream_result['active_neurons'],
            'body_moved': dream_result['body_moved'],
            'displacement': dream_result['displacement'],
        },
        'mbon_replay': {
            'approach_activation': total_approach,
            'avoidance_activation': total_avoidance,
            'dominant_type': dominant_replay,
        },
        'interpretation': replay_interpretation,
    }


def sleep_between_generations(df, evolve_fn, n_generations=3, dream_duration_ms=1000, seed=42):
    """
    Test if dreaming between evolution generations speeds up improvement.
    
    Alternates: evolve → dream → evolve → dream → ...
    Compares to control: evolve → evolve → evolve (no dreaming)
    
    If dreaming helps, sleep serves a measurable computational function.
    
    Args:
        df: Starting connectome
        evolve_fn: Function that takes df and returns (evolved_df, fitness)
        n_generations: How many evolution generations
        dream_duration_ms: How long to dream between generations
        seed: Random seed
        
    Returns:
        dict comparing sleep vs no-sleep evolution trajectories
    """
    np.random.seed(seed)
    
    # With sleep
    sleep_trajectory = []
    sleep_df = df.copy()
    for gen in range(n_generations):
        # Evolve
        sleep_df, fitness = evolve_fn(sleep_df)
        sleep_trajectory.append({'generation': gen, 'fitness': fitness, 'condition': 'sleep'})
        # Dream
        dream_result = dream(sleep_df, duration_ms=dream_duration_ms, seed=seed+gen)
    
    # Without sleep (control)
    np.random.seed(seed)  # Same seed for fair comparison
    nosleep_trajectory = []
    nosleep_df = df.copy()
    for gen in range(n_generations):
        nosleep_df, fitness = evolve_fn(nosleep_df)
        nosleep_trajectory.append({'generation': gen, 'fitness': fitness, 'condition': 'no_sleep'})
    
    # Compare
    sleep_final = sleep_trajectory[-1]['fitness'] if sleep_trajectory else 0
    nosleep_final = nosleep_trajectory[-1]['fitness'] if nosleep_trajectory else 0
    
    return {
        'sleep_trajectory': sleep_trajectory,
        'nosleep_trajectory': nosleep_trajectory,
        'sleep_final_fitness': sleep_final,
        'nosleep_final_fitness': nosleep_final,
        'sleep_advantage': sleep_final - nosleep_final,
        'interpretation': 'SLEEP HELPS' if sleep_final > nosleep_final else 'NO SLEEP EFFECT',
    }


# ══════════════════════════════════════════════════════════════════════════════
# ARTIFACT DETECTION — Verify results are real, not bugs
# ══════════════════════════════════════════════════════════════════════════════


# Known baseline fitness values for biological brain (to detect attractor traps)
KNOWN_BASELINE_VALUES = {
    'seed_42': -0.10039932276247479,
    'seed_123': -0.001398976054820477,  # The "perfect navigation" seed
    'seed_456': -0.10383250104126412,
    'seed_777': -0.1346638515337174,
    'seed_789': -0.1481240186878874,
    'seed_1337': -0.1104576598911781,
    'seed_2024': -0.06138282827905414,
    'old_deterministic': -1.7179888557510998,  # Bug: old code without seed injection
}


def detect_attractor(trajectories):
    """
    Check if multiple trajectories converge to the same fixed point.
    If yes, the result is an attractor artifact, not genuine improvement.
    
    Args:
        trajectories: List of trajectory arrays, each [(x,y), (x,y), ...]
        
    Returns:
        dict with analysis
    """
    if not trajectories or len(trajectories) < 2:
        return {"unique_endpoints": 0, "total": 0, "is_attractor": False, "reason": "not enough trajectories"}
    
    endpoints = []
    for t in trajectories:
        if t and len(t) > 0:
            last = t[-1]
            endpoints.append((round(last[0], 3), round(last[1], 3)))
    
    unique = len(set(endpoints))
    total = len(endpoints)
    
    # If less than 50% unique endpoints, it's an attractor
    is_attractor = unique < total * 0.5
    
    return {
        "unique_endpoints": unique,
        "total": total,
        "is_attractor": is_attractor,
        "reason": f"Only {unique}/{total} unique endpoints" if is_attractor else "endpoints are diverse",
        "endpoints": endpoints,
    }


def verify_result_is_real(fitness, baseline_fitnesses=None, tolerance=1e-6):
    """
    Check if a fitness result is suspicious (might be a bug or attractor).
    
    Args:
        fitness: The fitness value to check
        baseline_fitnesses: List of known baseline fitness values to compare against
        tolerance: How close values need to be to count as "identical"
        
    Returns:
        dict with:
            is_suspicious: bool
            reason: explanation if suspicious
            matches_known: which known value it matches (if any)
    """
    result = {
        "is_suspicious": False,
        "reason": None,
        "matches_known": None,
        "fitness": fitness,
    }
    
    # Check against known baseline values
    for name, known_val in KNOWN_BASELINE_VALUES.items():
        if abs(fitness - known_val) < tolerance:
            if name == 'old_deterministic':
                result["is_suspicious"] = True
                result["reason"] = f"Matches OLD DETERMINISTIC CODE value ({known_val:.6f}). Your code may have a bug - mutations not being injected."
            else:
                result["is_suspicious"] = True
                result["reason"] = f"Matches known baseline {name} ({known_val:.6f}). Mutation may just be triggering a different seed's behavior, not genuine improvement."
            result["matches_known"] = name
            return result
    
    # Check against provided baselines
    if baseline_fitnesses:
        for i, base_val in enumerate(baseline_fitnesses):
            if abs(fitness - base_val) < tolerance:
                result["is_suspicious"] = True
                result["reason"] = f"Identical to baseline[{i}] ({base_val:.6f}). Multiple brains producing same result = likely bug."
                return result
    
    return result


def verify_mutations_applied(original_df, mutated_df, expected_changes):
    """
    Verify that mutations were actually applied to the connectome.
    
    Args:
        original_df: Original connectome DataFrame
        mutated_df: Mutated connectome DataFrame
        expected_changes: How many changes were requested
        
    Returns:
        dict with verification results
    """
    weight_col = 'Excitatory x Connectivity'
    if weight_col not in original_df.columns:
        weight_col = original_df.columns[-1]
    
    orig_weights = original_df[weight_col].values
    mut_weights = mutated_df[weight_col].values
    
    if len(orig_weights) != len(mut_weights):
        return {
            "verified": False,
            "reason": f"DataFrame size changed: {len(orig_weights)} → {len(mut_weights)}",
            "actual_changes": "unknown",
        }
    
    actual_changes = int((orig_weights != mut_weights).sum())
    
    return {
        "verified": actual_changes > 0,
        "expected_changes": expected_changes,
        "actual_changes": actual_changes,
        "reason": "OK" if actual_changes > 0 else "NO CHANGES DETECTED - mutations not applied!",
        "change_ratio": actual_changes / expected_changes if expected_changes > 0 else 0,
    }


def compare_to_all_baselines(fitness, seed_used=None):
    """
    Compare a fitness value to all known baselines.
    Helps detect if a "mutation improvement" is actually just a different seed's behavior.
    
    Args:
        fitness: Fitness value to check
        seed_used: Which seed was used (to exclude from comparison)
        
    Returns:
        dict with closest matches and warnings
    """
    distances = []
    for name, val in KNOWN_BASELINE_VALUES.items():
        if seed_used and f'seed_{seed_used}' == name:
            continue  # Skip the seed we used
        distances.append({
            'name': name,
            'value': val,
            'distance': abs(fitness - val),
        })
    
    distances.sort(key=lambda x: x['distance'])
    closest = distances[0] if distances else None
    
    if closest and closest['distance'] < 1e-6:
        return {
            "warning": f"EXACT MATCH to {closest['name']}! This is suspicious.",
            "closest_match": closest,
            "all_distances": distances[:5],
        }
    elif closest and closest['distance'] < 0.01:
        return {
            "warning": f"Very close to {closest['name']} (diff={closest['distance']:.6f}). Verify this is real.",
            "closest_match": closest,
            "all_distances": distances[:5],
        }
    else:
        return {
            "warning": None,
            "closest_match": closest,
            "all_distances": distances[:5],
        }
