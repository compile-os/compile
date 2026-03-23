"""
Izhikevich Brain Engine — drop-in replacement for LIF BrainEngine.

Izhikevich neurons support:
  - Regular spiking (excitatory cortical)
  - Intrinsically bursting (persistent activity!)
  - Fast spiking (inhibitory interneurons)
  - Low-threshold spiking
  - Chattering
  - Rebound bursting
  - Bistability (key for attractors)

The critical upgrade over LIF: recurrent loops can sustain persistent activity
through adaptation currents and bistable dynamics. This enables:
  - Central complex heading representation (ring attractor)
  - Working memory (sustained firing after input removal)
  - Strategy switching (self-monitoring via persistent state)

Model equations (Izhikevich 2003):
  dv/dt = 0.04v² + 5v + 140 - u + I
  du/dt = a(bv - u)
  if v >= 30mV: v = c, u = u + d

Parameters (a, b, c, d) set neuron type. We assign types based on
FlyWire neurotransmitter annotations:
  - Excitatory (ACh, glutamate) → Regular Spiking or Intrinsically Bursting
  - Inhibitory (GABA) → Fast Spiking
  - Central complex neurons → Intrinsically Bursting (for persistent activity)

Same interface as BrainEngine:
  - .step()
  - .set_stimulus(name)
  - .state (v, u, spikes)
  - .dn_indices
  - ._syn_vals
  - .model.state_init()

Compatible with existing edge_sweep.py, evolution scripts, and fitness functions.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from pathlib import Path


# ============================================================================
# Izhikevich neuron types
# ============================================================================

NEURON_TYPES = {
    'RS':  {'a': 0.02,  'b': 0.2,  'c': -65.0, 'd': 8.0},   # Regular Spiking
    'IB':  {'a': 0.02,  'b': 0.2,  'c': -55.0, 'd': 4.0},   # Intrinsically Bursting
    'CH':  {'a': 0.02,  'b': 0.2,  'c': -50.0, 'd': 2.0},   # Chattering
    'FS':  {'a': 0.1,   'b': 0.2,  'c': -65.0, 'd': 2.0},   # Fast Spiking
    'LTS': {'a': 0.02,  'b': 0.25, 'c': -65.0, 'd': 2.0},   # Low-Threshold Spiking
}

# Default params matching original LIF where possible
DEFAULT_PARAMS = {
    'dt': 0.5,            # ms — Izhikevich uses 0.5ms steps (not 0.1ms like LIF)
    'v_peak': 30.0,       # mV — spike threshold
    'v_init': -65.0,      # mV — resting potential
    'u_init_scale': 0.2,  # u_init = b * v_init
    'poisson_rate': 150.0, # Hz
    'poisson_weight': 15.0, # mV equivalent current per Poisson spike
    'w_scale': 0.275,     # weight scale (from LIF)
    # Validated at 4x-8x. 7x is optimal. See gain_sensitivity experiment.
    'gain': 8.0,          # gain amplification
}


# ============================================================================
# Izhikevich Model (PyTorch)
# ============================================================================

class IzhikevichModel(nn.Module):
    """
    Vectorized Izhikevich neuron model for the full connectome.

    State: (v, u, spikes) where v=membrane potential, u=recovery variable
    """

    def __init__(self, num_neurons, weights, neuron_params, device='cpu', params=None):
        super().__init__()
        if params is None:
            params = DEFAULT_PARAMS

        self.num_neurons = num_neurons
        self.device = device
        self.dt = params['dt']
        self.v_peak = params['v_peak']
        self.v_init = params['v_init']
        self.poisson_weight = params['poisson_weight']

        # Store per-neuron Izhikevich parameters as tensors
        self.register_buffer('a', torch.tensor(neuron_params['a'], dtype=torch.float32, device=device))
        self.register_buffer('b', torch.tensor(neuron_params['b'], dtype=torch.float32, device=device))
        self.register_buffer('c', torch.tensor(neuron_params['c'], dtype=torch.float32, device=device))
        self.register_buffer('d', torch.tensor(neuron_params['d'], dtype=torch.float32, device=device))

        # Sparse weight matrix (CSR format)
        self.weights = weights.to(device)

    def state_init(self):
        """Initialize neural state."""
        v = torch.full((1, self.num_neurons), self.v_init, dtype=torch.float32, device=self.device)
        u = self.b.unsqueeze(0) * v
        spikes = torch.zeros(1, self.num_neurons, dtype=torch.float32, device=self.device)
        return v, u, spikes

    def forward(self, state, synaptic_input):
        """
        Advance one timestep.

        Args:
            state: (v, u, spikes) tuple
            synaptic_input: (1, num_neurons) external + recurrent input current

        Returns:
            (v_new, u_new, spikes_new)
        """
        v, u, _ = state
        dt = self.dt

        # Izhikevich dynamics (half-step for numerical stability)
        # dv/dt = 0.04v² + 5v + 140 - u + I
        # du/dt = a(bv - u)
        v_new = v + 0.5 * dt * (0.04 * v * v + 5.0 * v + 140.0 - u + synaptic_input)
        v_new = v_new + 0.5 * dt * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + synaptic_input)
        u_new = u + dt * self.a * (self.b * v_new - u)

        # Spike detection
        spikes = (v_new >= self.v_peak).float()

        # Reset spiking neurons
        v_new = torch.where(spikes > 0, self.c.unsqueeze(0), v_new)
        u_new = torch.where(spikes > 0, u_new + self.d.unsqueeze(0), u_new)

        # Clamp voltage to prevent numerical explosion
        v_new = torch.clamp(v_new, -100.0, self.v_peak)

        return v_new, u_new, spikes


# ============================================================================
# Brain Engine (drop-in replacement)
# ============================================================================

class IzhikevichBrainEngine:
    """
    Drop-in replacement for BrainEngine using Izhikevich neurons.

    Usage:
        brain = IzhikevichBrainEngine(device='cpu')
        brain.set_stimulus('sugar')
        brain.state = brain.model.state_init()
        for step in range(1000):
            brain.step()
            spikes = brain.state[2].squeeze(0)
            for name, idx in brain.dn_indices.items():
                if spikes[idx] > 0:
                    print(f"{name} fired!")
    """

    def __init__(self, device='cpu',
                 conn_path=None, comp_path=None, ann_path=None,
                 params=None, cx_boost=3.0):
        """
        Args:
            device: 'cpu' or 'cuda'
            conn_path: path to connectivity parquet
            comp_path: path to completeness CSV
            ann_path: path to FlyWire annotations TSV
            params: override default parameters
            cx_boost: gain multiplier for central complex recurrent connections
                      (to enable persistent activity / attractor dynamics)
        """
        self.device = device
        self.params = params or dict(DEFAULT_PARAMS)
        self.cx_boost = cx_boost

        # Default paths (same as original BrainEngine)
        if conn_path is None:
            for p in [
                '/home/ubuntu/fly-brain-embodied/data/2025_Connectivity_783.parquet',
                'data/2025_Connectivity_783.parquet',
            ]:
                if Path(p).exists():
                    conn_path = p
                    break
        if comp_path is None:
            for p in [
                '/home/ubuntu/fly-brain-embodied/data/2025_Completeness_783.csv',
                'data/2025_Completeness_783.csv',
            ]:
                if Path(p).exists():
                    comp_path = p
                    break
        if ann_path is None:
            for p in [
                '/home/ubuntu/fly-brain-embodied/data/flywire_annotations.tsv',
                'data/flywire_annotations.tsv',
            ]:
                if Path(p).exists():
                    ann_path = p
                    break

        # Load connectome
        print(f"[IzhBrain] Loading connectome...")
        self.df_conn = pd.read_parquet(conn_path)
        self.df_comp = pd.read_csv(comp_path, index_col=0)
        self.num_neurons = len(self.df_comp)
        print(f"[IzhBrain] {self.num_neurons} neurons")

        # Build ID mappings
        self.flyid2i = {j: i for i, j in enumerate(self.df_comp.index)}
        self.i2flyid = {j: i for i, j in self.flyid2i.items()}

        # Build sparse weight matrix
        self._build_weights()

        # Assign neuron types based on annotations
        self._assign_neuron_types(ann_path)

        # Build model
        self.model = IzhikevichModel(
            self.num_neurons, self._weight_matrix,
            self._neuron_params, device=device, params=self.params
        )

        # Initialize state
        self.state = self.model.state_init()
        self.rates = torch.zeros(1, self.num_neurons, device=device)
        self._spike_acc = torch.zeros(1, self.num_neurons, device=device)
        self._hebb_count = 0

        # Set up DN indices (descending neurons) — same as original
        self._setup_dn_indices()

        # Set up stimulus groups — same as original
        self._setup_stimuli()

        # Apply gain
        self._syn_vals.mul_(self.params['gain'])

        print(f"[IzhBrain] Ready. {self.num_neurons} Izhikevich neurons on {device}")

    def _build_weights(self):
        """Build sparse weight matrix from connectivity data."""
        pre = self.df_conn['Presynaptic_Index'].values
        post = self.df_conn['Postsynaptic_Index'].values
        vals = self.df_conn['Excitatory x Connectivity'].values.astype(np.float32)

        # Store raw values for manipulation
        self._syn_vals = torch.tensor(vals, dtype=torch.float32, device=self.device)
        self._pre_idx = torch.tensor(pre, dtype=torch.long, device=self.device)
        self._post_idx = torch.tensor(post, dtype=torch.long, device=self.device)

        # Build CSR sparse matrix
        weight_coo = torch.sparse_coo_tensor(
            torch.stack([torch.tensor(post, dtype=torch.long),
                        torch.tensor(pre, dtype=torch.long)]),
            self._syn_vals,
            (self.num_neurons, self.num_neurons),
            dtype=torch.float32
        )
        self._weight_matrix = weight_coo.to_sparse_csr().to(self.device)

    def _rebuild_weight_matrix(self):
        """Rebuild sparse matrix from current _syn_vals."""
        weight_coo = torch.sparse_coo_tensor(
            torch.stack([self._post_idx, self._pre_idx]),
            self._syn_vals,
            (self.num_neurons, self.num_neurons),
            dtype=torch.float32
        )
        self._weight_matrix = weight_coo.to_sparse_csr().to(self.device)
        self.model.weights = self._weight_matrix

    def _assign_neuron_types(self, ann_path):
        """
        Assign Izhikevich neuron types based on FlyWire annotations.

        Key assignment:
          - Central complex neurons → Intrinsically Bursting (IB)
            This is the critical change: IB neurons can sustain persistent activity
          - Inhibitory (GABA) → Fast Spiking (FS)
          - Excitatory (ACh, glutamate) → Regular Spiking (RS)
        """
        a = np.full(self.num_neurons, NEURON_TYPES['RS']['a'], dtype=np.float32)
        b = np.full(self.num_neurons, NEURON_TYPES['RS']['b'], dtype=np.float32)
        c = np.full(self.num_neurons, NEURON_TYPES['RS']['c'], dtype=np.float32)
        d = np.full(self.num_neurons, NEURON_TYPES['RS']['d'], dtype=np.float32)

        neuron_ids = self.df_comp.index.astype(str).tolist()
        n_ib = 0
        n_fs = 0

        if ann_path and Path(ann_path).exists():
            ann = pd.read_csv(ann_path, sep='\t', low_memory=False)
            rid_to_nt = dict(zip(ann['root_id'].astype(str), ann['top_nt'].fillna('')))
            rid_to_class = dict(zip(ann['root_id'].astype(str), ann['cell_class'].fillna('')))

            for idx, nid in enumerate(neuron_ids):
                nt = rid_to_nt.get(nid, '')
                cell_class = rid_to_class.get(nid, '')

                # Central complex → Intrinsically Bursting (persistent activity!)
                if 'CX' in cell_class or 'EB' in cell_class or 'FB' in cell_class or 'PB' in cell_class:
                    for k in ['a', 'b', 'c', 'd']:
                        locals()[k][idx] = NEURON_TYPES['IB'][k]
                    n_ib += 1
                # GABA → Fast Spiking
                elif nt == 'gaba' or nt == 'GABA':
                    for k in ['a', 'b', 'c', 'd']:
                        locals()[k][idx] = NEURON_TYPES['FS'][k]
                    n_fs += 1
                # Everything else stays RS (default)

            print(f"[IzhBrain] Neuron types: {n_ib} IB (central complex), {n_fs} FS (inhibitory), "
                  f"{self.num_neurons - n_ib - n_fs} RS (excitatory)")
        else:
            print(f"[IzhBrain] No annotations found, all neurons set to Regular Spiking")

        self._neuron_params = {'a': a, 'b': b, 'c': c, 'd': d}

    def _setup_dn_indices(self):
        """Set up descending neuron indices — matches original BrainEngine."""
        # These are the DN neuron FlyWire IDs from brain_body_bridge.py
        DN_NEURONS = {
            'DNa01_left': 720575940614404063,
            'DNa01_right': 720575940627237849,
            'DNa02_left': 720575940604361597,
            'DNa02_right': 720575940626691453,
            'GF_1': 720575940620869198,
            'GF_2': 720575940638640863,
            'MDN_1': 720575940637711543,
            'MDN_2': 720575940623900042,
            'MDN_3': 720575940639434571,
            'MDN_4': 720575940607389267,
            'MN9_left': 720575940628279452,
            'MN9_right': 720575940639895014,
            'P9_left': 720575940606503061,
            'P9_right': 720575940631587275,
            'P9_oDN1_left': 720575940609747580,
            'P9_oDN1_right': 720575940627889681,
            'aDN1_left': 720575940625482855,
            'aDN1_right': 720575940625125833,
        }

        self.dn_indices = {}
        mapped = 0
        for name, flyid in DN_NEURONS.items():
            if flyid in self.flyid2i:
                self.dn_indices[name] = self.flyid2i[flyid]
                mapped += 1
        print(f"[IzhBrain] DN neurons mapped: {mapped}/{len(DN_NEURONS)}")

    def _setup_stimuli(self):
        """Set up stimulus neuron groups — matches original BrainEngine."""
        STIMULI = {
            'sugar': [
                720575940637240468, 720575940625824886, 720575940626476997,
                720575940625569537, 720575940636483358, 720575940624465498,
                720575940624469518, 720575940633498854, 720575940613498969,
                720575940637753498, 720575940613996621, 720575940613662738,
                720575940625756948, 720575940613637689, 720575940621809015,
                720575940604754683, 720575940604806596, 720575940609424399,
                720575940620587501, 720575940613704038, 720575940626099502,
            ],
            'lc4': [], 'jo': [], 'bitter': [], 'or56a': [], 'p9': [],
        }

        # Map FlyWire IDs to tensor indices
        self.stim_indices = {}
        for name, flyids in STIMULI.items():
            indices = [self.flyid2i[fid] for fid in flyids if fid in self.flyid2i]
            self.stim_indices[name] = indices
            if indices:
                print(f"  '{name}': {len(indices)}/{len(flyids)} neurons")

    def set_stimulus(self, name, rate=None):
        """Set Poisson stimulus for a neuron group."""
        if rate is None:
            rate = self.params['poisson_rate']
        self.rates.zero_()
        if name in self.stim_indices:
            indices = self.stim_indices[name]
            if indices:
                self.rates[0, indices] = rate

    def step(self):
        """Advance one simulation timestep."""
        with torch.no_grad():
            v, u, spikes = self.state

            # Poisson input
            poisson_spikes = (torch.rand_like(self.rates) < self.rates * self.params['dt'] / 1000.0).float()
            poisson_current = poisson_spikes * self.params['poisson_weight']

            # Recurrent input (sparse matmul)
            recurrent = torch.mm(spikes, self.model.weights.t()) * self.params['w_scale']

            # Total input current
            total_input = poisson_current + recurrent

            # Izhikevich step
            self.state = self.model(self.state, total_input)

            # Accumulate spikes
            self._spike_acc += self.state[2]

    def get_dn_spikes(self):
        """Get current DN spike counts."""
        spikes = self.state[2].squeeze(0)
        return {name: int(spikes[idx].item()) for name, idx in self.dn_indices.items()}


# ============================================================================
# Quick test
# ============================================================================

if __name__ == '__main__':
    import time

    print("=" * 60)
    print("IZHIKEVICH BRAIN ENGINE TEST")
    print("=" * 60)

    brain = IzhikevichBrainEngine(device='cpu')

    # Test 1: Baseline activity
    print("\n--- Test 1: Baseline (no stimulus, 500 steps) ---")
    brain.state = brain.model.state_init()
    brain.rates.zero_()
    brain._spike_acc.zero_()

    t0 = time.time()
    total_spikes = 0
    for step in range(500):
        brain.step()
        total_spikes += brain.state[2].sum().item()
    t1 = time.time()
    print(f"  Spontaneous spikes: {total_spikes:.0f} in {t1-t0:.1f}s")

    # Test 2: Sugar stimulus
    print("\n--- Test 2: Sugar stimulus (500 steps) ---")
    brain.state = brain.model.state_init()
    brain.set_stimulus('sugar')
    brain._spike_acc.zero_()

    total_spikes = 0
    dn_total = {}
    for step in range(500):
        brain.step()
        spk = brain.state[2].squeeze(0)
        total_spikes += spk.sum().item()
        for name, idx in brain.dn_indices.items():
            dn_total[name] = dn_total.get(name, 0) + int(spk[idx].item())
    print(f"  Total spikes: {total_spikes:.0f}")
    print(f"  DN spikes: {dict(sorted([(k,v) for k,v in dn_total.items() if v > 0]))}")

    # Test 3: PERSISTENCE TEST (the critical one!)
    print("\n--- Test 3: PERSISTENCE (200 steps stimulus, then 500 steps silence) ---")
    brain.state = brain.model.state_init()
    brain.set_stimulus('sugar')

    stim_spikes = 0
    for step in range(200):
        brain.step()
        stim_spikes += brain.state[2].sum().item()
    print(f"  During stimulus: {stim_spikes:.0f} total spikes")

    # Remove stimulus
    brain.rates.zero_()
    post_windows = []
    for window in range(10):
        window_spikes = 0
        for step in range(50):
            brain.step()
            window_spikes += brain.state[2].sum().item()
        post_windows.append(window_spikes)
        status = "ACTIVE" if window_spikes > 5 else "silent"
        print(f"  Post-stimulus {window*50}-{(window+1)*50}: {window_spikes:.0f} spikes [{status}]")

    if post_windows[-1] > 5:
        print("  >>> PERSISTENT ACTIVITY DETECTED! Attractor dynamics working!")
    elif any(w > 5 for w in post_windows[3:]):
        print("  >>> DELAYED PERSISTENCE — recurrent reverberation present")
    else:
        decay = next((i*50 for i, w in enumerate(post_windows) if w < 2), 500)
        print(f"  >>> Activity decayed after ~{decay} steps")

    print("\nDONE.")
