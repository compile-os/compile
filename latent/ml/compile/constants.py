"""
Shared constants for connectome evolution experiments.

All neuron indices, stimulus lists, and simulation parameters live here.
Every experiment imports from this module instead of re-defining inline.

Neuron indices were derived from FlyWire connectome v783 using
scripts/derive_neuron_indices.py — see that script for the mapping
from FlyWire root_id to connectome index.
"""

# ---------------------------------------------------------------------------
# Descending neuron (DN) indices into the v783 connectome
# ---------------------------------------------------------------------------
# These are integer indices into the completeness matrix (df_comp).
# The mapping root_id -> index is deterministic given the v783 data files.

DN_NEURONS = {
    "P9_left": 83620,
    "P9_right": 119032,
    "P9_oDN1_left": 78013,
    "P9_oDN1_right": 42812,
    "DNa01_left": 133149,
    "DNa01_right": 84431,
    "DNa02_left": 904,
    "DNa02_right": 92992,
    "MDN_1": 25844,
    "MDN_2": 102124,
    "MDN_3": 129127,
    "MDN_4": 8808,
    "GF_1": 57246,
    "GF_2": 108748,
    "aDN1_left": 65709,
    "aDN1_right": 26421,
    "MN9_left": 138332,
    "MN9_right": 34268,
}

DN_NAMES = sorted(DN_NEURONS.keys())

# FlyWire root_id for each DN neuron (the biological identifier).
# Derived from BrainEngine on v783 data: df_comp.index[position] = root_id.
# Verified by scripts/derive_neuron_indices.py.
DN_FLYIDS = {
    "DNa01_left": 720575940644438551,
    "DNa01_right": 720575940627787609,
    "DNa02_left": 720575940604737708,
    "DNa02_right": 720575940629327659,
    "GF_1": 720575940622838154,
    "GF_2": 720575940632499757,
    "MDN_1": 720575940616026939,
    "MDN_2": 720575940631082808,
    "MDN_3": 720575940640331472,
    "MDN_4": 720575940610236514,
    "MN9_left": 720575940660219265,
    "MN9_right": 720575940618238523,
    "P9_left": 720575940627652358,
    "P9_right": 720575940635872101,
    "P9_oDN1_left": 720575940626730883,
    "P9_oDN1_right": 720575940620300308,
    "aDN1_left": 720575940624319124,
    "aDN1_right": 720575940616185531,
}

# ---------------------------------------------------------------------------
# Stimulus neuron indices (sensory neurons driving each behavior)
# ---------------------------------------------------------------------------

STIM_SUGAR = [
    69093, 97602, 122795, 124291, 29281, 100605, 110469, 51107, 49584,
    129730, 126873, 28825, 126600, 126752, 32863, 108426, 111357, 14842,
    90589, 92298, 12494,
]

STIM_LC4 = [
    1911, 10627, 14563, 16821, 16836, 22002, 23927, 29887, 30208, 36646,
    45558, 53122, 63894, 69551, 73977, 74288, 77298, 77411, 88373, 88424,
    100901, 124935,
]

# Extended LC4 list (99 visual neurons) used in strategy switching experiments.
STIM_LC4_EXTENDED = STIM_LC4 + [
    264, 9350, 13067, 13728, 13909, 14284, 14345, 15883,
    17935, 18045, 20770, 20810, 22455, 22751, 23130, 24281, 25985, 28213,
    29383, 30533, 33149, 34245, 34246, 34402, 34409, 34445, 34603, 36093,
    36239, 36310, 38907, 42880, 42886, 45196, 46146, 47583, 49698, 51100,
    54455, 55583, 57783, 64467, 68119, 68461, 73496, 73522, 73846, 73964,
    77031, 79150, 82937, 86033, 86146, 88184, 88693, 89165, 89200, 89699,
    90786, 95107, 96243, 97190, 98862, 101707, 101892, 103513, 108651,
    109680, 109955, 110942, 111699, 112907, 115387, 118928, 121451,
    124829, 127954, 129665, 130519, 134682, 136520, 137218,
]

STIM_JO = [
    133917, 23290, 40779, 42646, 43215, 100833, 108537, 114244, 1828, 4290,
    6375, 24322, 43314, 51816, 54541, 59929, 74572, 82120, 96822, 107107,
]

# Extended JO list (22 neurons) used in persistence tests.
STIM_JO_EXTENDED = STIM_JO + [107820, 116136]

# Mapping from stimulus name to neuron index list.
STIMULUS_MAP = {
    "sugar": STIM_SUGAR,
    "lc4": STIM_LC4,
    "jo": STIM_JO,
}

# FlyWire root_ids for stimulus groups (derived from BrainEngine on v783 data).
STIM_SUGAR_FLYIDS = [
    720575940624963786, 720575940630233916, 720575940637568838,
    720575940638202345, 720575940617000768, 720575940630797113,
    720575940632889389, 720575940621754367, 720575940621502051,
    720575940640649691, 720575940639332736, 720575940616885538,
    720575940639198653, 720575940639259967, 720575940617937543,
    720575940632425919, 720575940633143833, 720575940612670570,
    720575940628853239, 720575940629176663, 720575940611875570,
]

# ---------------------------------------------------------------------------
# Gene-guided circuit specification (hemilineage signatures)
# ---------------------------------------------------------------------------

SIGNATURE_HEMIS = {
    "VPNd2", "VLPp2", "DM3_CX_d2", "LB23", "LB12", "VLPl2_medial",
    "LB7", "VLPl&p2_posterior", "MD3", "MX12", "VLPl&p2_lateral",
    "DM1_CX_d2", "WEDd1", "MX3", "VPNd1", "putative_primary",
    "CREa2_medial", "CREa1_dorsal", "SLPal3_and_SLPal4_dorsal",
}

# ---------------------------------------------------------------------------
# Izhikevich neuron type parameters (Izhikevich 2003)
# ---------------------------------------------------------------------------

NEURON_TYPES = {
    "RS":  {"a": 0.02,  "b": 0.2,  "c": -65.0, "d": 8.0},   # Regular Spiking
    "IB":  {"a": 0.02,  "b": 0.2,  "c": -55.0, "d": 4.0},   # Intrinsically Bursting
    "CH":  {"a": 0.02,  "b": 0.2,  "c": -50.0, "d": 2.0},   # Chattering
    "FS":  {"a": 0.1,   "b": 0.2,  "c": -65.0, "d": 2.0},   # Fast Spiking
    "LTS": {"a": 0.02,  "b": 0.25, "c": -65.0, "d": 2.0},   # Low-Threshold Spiking
}

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

DEFAULT_SIM_PARAMS = {
    "dt": 0.5,              # ms — timestep (Izhikevich uses 0.5ms, not 0.1ms like LIF)
    "v_peak": 30.0,         # mV — spike threshold
    "v_init": -65.0,        # mV — resting potential
    "u_init_scale": 0.2,    # u_init = b * v_init
    "poisson_rate": 150.0,  # Hz — stimulus firing rate
    "poisson_weight": 15.0, # mV — equivalent current per Poisson spike
    "w_scale": 0.275,       # weight scale for recurrent input
    "gain": 8.0,            # synaptic gain multiplier (validated at 4x-8x; 7x optimal)
    # Short-term synaptic depression (Tsodyks-Markram)
    # U_dep: fraction of resources used per spike (0.0 = no depression, 0.5 = strong)
    # tau_rec: recovery time constant in ms (higher = slower recovery = stronger depression effect)
    # Calibrated from Markram et al. 1998, Wang et al. 2006
    "U_dep": 0.2,           # typical excitatory cortical synapse
    "tau_rec": 800.0,       # ms — recovery time constant
}

# Convenience aliases
DT = DEFAULT_SIM_PARAMS["dt"]
W_SCALE = DEFAULT_SIM_PARAMS["w_scale"]
GAIN = DEFAULT_SIM_PARAMS["gain"]
POISSON_WEIGHT = DEFAULT_SIM_PARAMS["poisson_weight"]
POISSON_RATE = DEFAULT_SIM_PARAMS["poisson_rate"]

# ---------------------------------------------------------------------------
# Neurotransmitter compatibility matrix (for growth models)
# ---------------------------------------------------------------------------

NT_COMPATIBILITY = {
    ("acetylcholine", "acetylcholine"): 1.0,
    ("acetylcholine", "gaba"):          0.8,
    ("acetylcholine", "glutamate"):     0.7,
    ("acetylcholine", "dopamine"):      0.5,
    ("acetylcholine", "serotonin"):     0.4,
    ("gaba",          "acetylcholine"): 1.0,
    ("gaba",          "gaba"):          0.3,
    ("gaba",          "glutamate"):     0.5,
    ("gaba",          "dopamine"):      0.3,
    ("glutamate",     "acetylcholine"): 0.9,
    ("glutamate",     "gaba"):          0.6,
    ("glutamate",     "glutamate"):     0.4,
    ("dopamine",      "acetylcholine"): 1.0,
    ("dopamine",      "gaba"):          0.7,
    ("dopamine",      "dopamine"):      0.2,
    ("serotonin",     "acetylcholine"): 0.8,
}
NT_COMPATIBILITY_DEFAULT = 0.3
