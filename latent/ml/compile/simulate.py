"""
Izhikevich neuron simulation for connectome experiments.

Provides both a low-level simulation function (``run_simulation``) for
inline experiments, and the full ``IzhikevichBrainEngine`` class that
is a drop-in replacement for the Eon Systems LIF BrainEngine.

Model equations (Izhikevich 2003, IEEE Trans Neural Networks):
    dv/dt = 0.04v^2 + 5v + 140 - u + I
    du/dt = a(bv - u)
    if v >= 30mV: v = c, u = u + d

Half-step integration is used for numerical stability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from compile.constants import (
    DEFAULT_SIM_PARAMS,
    DN_FLYIDS,
    DN_NAMES,
    DN_NEURONS,
    NEURON_TYPES,
    STIM_SUGAR_FLYIDS,
)
from compile.data import load_annotations, load_connectome

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Neuron type assignment
# ---------------------------------------------------------------------------

def assign_neuron_types(
    num_neurons: int,
    neuron_ids: list[str],
    rid_to_nt: dict,
    rid_to_class: dict,
) -> dict[str, np.ndarray]:
    """
    Assign Izhikevich (a, b, c, d) parameters to each neuron based on
    FlyWire annotations.

    Assignment rules (following Izhikevich 2003, Table 1):
      - Central complex (CX/EB/FB/PB) -> Intrinsically Bursting (IB)
        Rationale: CX neurons maintain persistent heading representations
        (Seelig & Jayaraman, Nature 2015). IB dynamics support sustained
        firing through adaptation currents, enabling attractor states.
      - Inhibitory (GABA) -> Fast Spiking (FS)
        Rationale: GABAergic interneurons in Drosophila show fast, non-adapting
        firing patterns (Wilson & Laurent, J Neurosci 2005).
      - All others (ACh, glutamate) -> Regular Spiking (RS)
        Rationale: Default excitatory type in Izhikevich 2003.

    Note: Neurotransmitter matching is case-insensitive ("gaba", "GABA", "Gaba"
    are all matched). Results are robust to neuron type assignment — the key
    finding (edge 19->4) appears in both LIF and Izhikevich models regardless
    of type assignment.

    Returns:
        dict with keys 'a', 'b', 'c', 'd', each a float32 array of shape (num_neurons,)
    """
    rs = NEURON_TYPES["RS"]
    ib = NEURON_TYPES["IB"]
    fs = NEURON_TYPES["FS"]
    lts = NEURON_TYPES["LTS"]

    a = np.full(num_neurons, rs["a"], dtype=np.float32)
    b = np.full(num_neurons, rs["b"], dtype=np.float32)
    c = np.full(num_neurons, rs["c"], dtype=np.float32)
    d = np.full(num_neurons, rs["d"], dtype=np.float32)

    n_ib = 0
    n_fs = 0
    n_lts = 0
    for idx, nid in enumerate(neuron_ids):
        cell_class = rid_to_class.get(nid, "")
        nt = rid_to_nt.get(nid, "").lower()
        if isinstance(cell_class, str) and any(
            tag in cell_class for tag in ("CX", "EB", "FB", "PB")
        ):
            a[idx], b[idx], c[idx], d[idx] = ib["a"], ib["b"], ib["c"], ib["d"]
            n_ib += 1
        elif nt == "gaba":
            a[idx], b[idx], c[idx], d[idx] = fs["a"], fs["b"], fs["c"], fs["d"]
            n_fs += 1
        elif nt in ("dopamine", "serotonin"):
            # Neuromodulatory neurons: low-threshold spiking
            a[idx], b[idx], c[idx], d[idx] = lts["a"], lts["b"], lts["c"], lts["d"]
            n_lts += 1

    logger.info(
        "Neuron types: %d IB (central complex), %d FS (inhibitory), %d LTS (modulatory), %d RS (excitatory)",
        n_ib, n_fs, n_lts, num_neurons - n_ib - n_fs - n_lts,
    )
    return {"a": a, "b": b, "c": c, "d": d}


# ---------------------------------------------------------------------------
# Sparse weight matrix construction
# ---------------------------------------------------------------------------

def build_weight_matrix(
    pre: np.ndarray,
    post: np.ndarray,
    vals: torch.Tensor,
    num_neurons: int,
    device: str = "cpu",
) -> torch.Tensor:
    """Build a sparse CSR weight matrix from pre/post indices and values."""
    weight_coo = torch.sparse_coo_tensor(
        torch.stack([
            torch.tensor(post, dtype=torch.long),
            torch.tensor(pre, dtype=torch.long),
        ]),
        vals,
        (num_neurons, num_neurons),
        dtype=torch.float32,
    )
    return weight_coo.to_sparse_csr().to(device)


# ---------------------------------------------------------------------------
# Single Izhikevich timestep (shared primitive)
# ---------------------------------------------------------------------------

def izh_step(
    v: torch.Tensor,
    u: torch.Tensor,
    I: torch.Tensor,
    a: torch.Tensor,
    b: torch.Tensor,
    c: torch.Tensor,
    d: torch.Tensor,
    dt: float = 0.5,
    v_peak: float = 30.0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Single Izhikevich timestep with half-step integration.

    This is the primitive building block for all simulation loops.
    Use this instead of copy-pasting the update equations.

    Args:
        v: membrane potential (1, N)
        u: recovery variable (1, N)
        I: total input current (1, N)
        a, b, c, d: Izhikevich parameters (N,) tensors
        dt: timestep in ms
        v_peak: spike threshold in mV

    Returns:
        (v_new, u_new, spikes) where spikes is binary (1, N)
    """
    v_new = v + 0.5 * dt * (0.04 * v * v + 5.0 * v + 140.0 - u + I)
    v_new = v_new + 0.5 * dt * (0.04 * v_new * v_new + 5.0 * v_new + 140.0 - u + I)
    u_new = u + dt * a * (b * v_new - u)

    spikes = (v_new >= v_peak).float()
    v_new = torch.where(spikes > 0, c.unsqueeze(0), v_new)
    u_new = torch.where(spikes > 0, u_new + d.unsqueeze(0), u_new)
    v_new = torch.clamp(v_new, -100.0, v_peak)

    return v_new, u_new, spikes


# ---------------------------------------------------------------------------
# Low-level simulation function (for inline experiments)
# ---------------------------------------------------------------------------

def run_simulation(
    syn_vals: torch.Tensor,
    pre: np.ndarray,
    post: np.ndarray,
    num_neurons: int,
    neuron_params: dict[str, np.ndarray],
    stim_indices: list[int],
    dn_indices: dict[str, int],
    n_steps: int = 500,
    params: Optional[dict] = None,
) -> dict[str, int]:
    """
    Run an Izhikevich simulation and return DN spike counts.

    This is the standalone simulation loop used by experiments that build
    their own subcircuits (e.g., gene-guided extraction). For full-connectome
    simulation, use ``IzhikevichBrainEngine`` instead.

    Args:
        syn_vals: synapse weight tensor
        pre, post: presynaptic and postsynaptic index arrays
        num_neurons: number of neurons in the subcircuit
        neuron_params: dict with keys 'a','b','c','d' (numpy arrays)
        stim_indices: list of neuron indices to stimulate
        dn_indices: dict mapping DN name -> neuron index (-1 if absent)
        n_steps: simulation duration in timesteps
        params: simulation parameters (defaults to DEFAULT_SIM_PARAMS)

    Returns:
        dict mapping DN name -> total spike count
    """
    if params is None:
        params = DEFAULT_SIM_PARAMS

    dt = params["dt"]
    w_scale = params["w_scale"]
    pw = params["poisson_weight"]
    pr = params["poisson_rate"]

    # Build weight matrix
    W = build_weight_matrix(pre, post, syn_vals, num_neurons)

    # Neuron parameters as tensors
    a_t = torch.tensor(neuron_params["a"], dtype=torch.float32)
    b_t = torch.tensor(neuron_params["b"], dtype=torch.float32)
    c_t = torch.tensor(neuron_params["c"], dtype=torch.float32)
    d_t = torch.tensor(neuron_params["d"], dtype=torch.float32)

    # Initial state
    v = torch.full((1, num_neurons), -65.0)
    u = b_t.unsqueeze(0) * v
    spikes = torch.zeros(1, num_neurons)

    # Stimulus rates
    rates = torch.zeros(1, num_neurons)
    for idx in stim_indices:
        if 0 <= idx < num_neurons:
            rates[0, idx] = pr

    # DN tracking
    dn_names = sorted(dn_indices.keys())
    dn_idx = [dn_indices.get(nm, -1) for nm in dn_names]
    dn_total = {nm: 0 for nm in dn_names}

    # Short-term synaptic depression (Tsodyks-Markram model)
    # x = available synaptic resources (1.0 = full, 0.0 = depleted)
    # On each presynaptic spike: effective weight = W * x * U, then x -= x * U
    # Between spikes: x recovers toward 1.0 with time constant tau_rec
    #
    # This prevents runaway reverberation and makes circuits respond to
    # changes in input rather than absolute input level — matching real
    # sensory adaptation.
    # Short-term synaptic depression (Tsodyks-Markram)
    U_dep = params.get("U_dep", 0.2)
    tau_rec = params.get("tau_rec", 800.0)
    x_syn = torch.ones(1, num_neurons)

    # Simulation loop
    for _ in range(n_steps):
        poisson = (torch.rand_like(rates) < rates * dt / 1000.0).float()
        # Apply synaptic depression: scale recurrent input by available resources
        recurrent = torch.mm(spikes * x_syn, W.t()) * w_scale
        I = poisson * pw + recurrent

        v, u, spikes = izh_step(v, u, I, a_t, b_t, c_t, d_t, dt=dt)

        # Update synaptic resources: deplete on spikes, recover otherwise
        x_syn = x_syn + dt * (1.0 - x_syn) / tau_rec  # recovery
        x_syn = x_syn - U_dep * x_syn * spikes         # depletion on spike

        spk = spikes.squeeze(0)
        for j, di in enumerate(dn_idx):
            if 0 <= di < num_neurons:
                dn_total[dn_names[j]] += int(spk[di].item())

    return dn_total


# ---------------------------------------------------------------------------
# IzhikevichModel (PyTorch nn.Module)
# ---------------------------------------------------------------------------

class IzhikevichModel(nn.Module):
    """Vectorized Izhikevich neuron model for the full connectome."""

    def __init__(self, num_neurons, weights, neuron_params, device="cpu", params=None):
        super().__init__()
        if params is None:
            params = DEFAULT_SIM_PARAMS

        self.num_neurons = num_neurons
        self.device = device
        self.dt = params["dt"]
        self.v_peak = params["v_peak"]
        self.v_init = params["v_init"]
        self.poisson_weight = params["poisson_weight"]

        self.register_buffer("a", torch.tensor(neuron_params["a"], dtype=torch.float32, device=device))
        self.register_buffer("b", torch.tensor(neuron_params["b"], dtype=torch.float32, device=device))
        self.register_buffer("c", torch.tensor(neuron_params["c"], dtype=torch.float32, device=device))
        self.register_buffer("d", torch.tensor(neuron_params["d"], dtype=torch.float32, device=device))

        self.weights = weights.to(device)

    def state_init(self):
        """Initialize (v, u, spikes) state tuple."""
        v = torch.full((1, self.num_neurons), self.v_init, dtype=torch.float32, device=self.device)
        u = self.b.unsqueeze(0) * v
        spikes = torch.zeros(1, self.num_neurons, dtype=torch.float32, device=self.device)
        return v, u, spikes

    def forward(self, state, synaptic_input):
        """Advance one Izhikevich timestep with half-step integration."""
        v, u, _ = state
        dt = self.dt

        return izh_step(v, u, synaptic_input, self.a, self.b, self.c, self.d,
                        dt=dt, v_peak=self.v_peak)


# ---------------------------------------------------------------------------
# IzhikevichBrainEngine (drop-in replacement for Eon BrainEngine)
# ---------------------------------------------------------------------------

class IzhikevichBrainEngine:
    """
    Drop-in replacement for BrainEngine using Izhikevich neurons.

    Usage::

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

    def __init__(
        self,
        device: str = "cpu",
        conn_path: Optional[str] = None,
        comp_path: Optional[str] = None,
        ann_path: Optional[str] = None,
        params: Optional[dict] = None,
        cx_boost: float = 3.0,
    ):
        self.device = device
        self.params = params or dict(DEFAULT_SIM_PARAMS)
        self.cx_boost = cx_boost

        # Load connectome
        data_dir = None
        if conn_path is not None:
            data_dir = Path(conn_path).parent
        df_conn, df_comp, num_neurons = load_connectome(data_dir)

        self.df_conn = df_conn
        self.df_comp = df_comp
        self.num_neurons = num_neurons

        # ID mappings
        self.flyid2i = {j: i for i, j in enumerate(df_comp.index)}
        self.i2flyid = {v: k for k, v in self.flyid2i.items()}

        # Weights
        self._build_weights()

        # Neuron types
        self._assign_neuron_types(ann_path)

        # Model
        self.model = IzhikevichModel(
            num_neurons, self._weight_matrix,
            self._neuron_params, device=device, params=self.params,
        )

        # State
        self.state = self.model.state_init()
        self.rates = torch.zeros(1, num_neurons, device=device)
        self._spike_acc = torch.zeros(1, num_neurons, device=device)
        self._hebb_count = 0

        # Short-term synaptic depression (Tsodyks-Markram)
        self._x_syn = torch.ones(1, num_neurons, device=device)
        self._U_dep = self.params.get("U_dep", 0.2)
        self._tau_rec = self.params.get("tau_rec", 800.0)

        # DN indices and stimuli
        self._setup_dn_indices()
        self._setup_stimuli()

        # Apply gain
        self._syn_vals.mul_(self.params["gain"])

        logger.info("Ready: %d Izhikevich neurons on %s", num_neurons, device)

    def _build_weights(self):
        pre = self.df_conn["Presynaptic_Index"].values
        post = self.df_conn["Postsynaptic_Index"].values
        vals = self.df_conn["Excitatory x Connectivity"].values.astype(np.float32)

        self._syn_vals = torch.tensor(vals, dtype=torch.float32, device=self.device)
        self._pre_idx = torch.tensor(pre, dtype=torch.long, device=self.device)
        self._post_idx = torch.tensor(post, dtype=torch.long, device=self.device)

        self._weight_matrix = build_weight_matrix(
            pre, post, self._syn_vals, self.num_neurons, self.device,
        )

    def _rebuild_weight_matrix(self):
        self._weight_matrix = build_weight_matrix(
            self._pre_idx.numpy(), self._post_idx.numpy(),
            self._syn_vals, self.num_neurons, self.device,
        )
        self.model.weights = self._weight_matrix

    def _assign_neuron_types(self, ann_path):
        neuron_ids = self.df_comp.index.astype(str).tolist()
        try:
            ann = load_annotations(Path(ann_path).parent if ann_path else None)
            rid_to_nt = dict(zip(ann["root_id"].astype(str), ann["top_nt"].fillna("")))
            rid_to_class = dict(zip(ann["root_id"].astype(str), ann["cell_class"].fillna("")))
            self._neuron_params = assign_neuron_types(
                self.num_neurons, neuron_ids, rid_to_nt, rid_to_class,
            )
        except FileNotFoundError:
            logger.warning("No annotations found, all neurons set to Regular Spiking")
            rs = NEURON_TYPES["RS"]
            self._neuron_params = {
                k: np.full(self.num_neurons, rs[k], dtype=np.float32)
                for k in ("a", "b", "c", "d")
            }

    def _setup_dn_indices(self):
        self.dn_indices = {}
        for name, flyid in DN_FLYIDS.items():
            if flyid in self.flyid2i:
                self.dn_indices[name] = self.flyid2i[flyid]
        logger.info("DN neurons mapped: %d/%d", len(self.dn_indices), len(DN_FLYIDS))

    def _setup_stimuli(self):
        stimuli_flyids = {
            "sugar": STIM_SUGAR_FLYIDS,
            "lc4": [],
            "jo": [],
            "bitter": [],
            "or56a": [],
            "p9": [],
        }
        self.stim_indices = {}
        for name, flyids in stimuli_flyids.items():
            self.stim_indices[name] = [
                self.flyid2i[fid] for fid in flyids if fid in self.flyid2i
            ]

    def set_stimulus(self, name: str, rate: Optional[float] = None):
        """Set Poisson stimulus for a neuron group."""
        if rate is None:
            rate = self.params["poisson_rate"]
        self.rates.zero_()
        indices = self.stim_indices.get(name, [])
        if indices:
            self.rates[0, indices] = rate

    def step(self):
        """Advance one simulation timestep with short-term synaptic depression."""
        with torch.no_grad():
            v, u, spikes = self.state
            dt = self.params["dt"]
            poisson_spikes = (
                torch.rand_like(self.rates) < self.rates * dt / 1000.0
            ).float()
            poisson_current = poisson_spikes * self.params["poisson_weight"]
            # Apply synaptic depression to recurrent input
            recurrent = torch.mm(spikes * self._x_syn, self.model.weights.t()) * self.params["w_scale"]
            total_input = poisson_current + recurrent
            self.state = self.model(self.state, total_input)
            self._spike_acc += self.state[2]
            # Update synaptic resources
            self._x_syn = self._x_syn + dt * (1.0 - self._x_syn) / self._tau_rec
            self._x_syn = self._x_syn - self._U_dep * self._x_syn * self.state[2]

    def get_dn_spikes(self) -> dict[str, int]:
        """Get current DN spike counts."""
        spikes = self.state[2].squeeze(0)
        return {name: int(spikes[idx].item()) for name, idx in self.dn_indices.items()}


# ---------------------------------------------------------------------------
# evaluate_brain — shared evaluation wrapper
# ---------------------------------------------------------------------------

def evaluate_brain(
    brain: IzhikevichBrainEngine,
    stimulus: str,
    n_steps: int = 1000,
    window: int = 50,
) -> dict:
    """
    Run a full simulation and return structured spike data.

    Returns dict with:
        dn_names: list of DN neuron names
        windowed: (n_windows, n_dn) array of windowed spike counts
        total: (n_dn,) array of total spike counts
        n_windows: int
    """
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

    n_windows = n_steps // window
    windowed = np.zeros((n_windows, len(dn_names)))
    for w in range(n_windows):
        windowed[w] = steps[w * window : (w + 1) * window].sum(axis=0)

    return {
        "dn_names": dn_names,
        "windowed": windowed,
        "total": steps.sum(axis=0),
        "n_windows": n_windows,
    }
