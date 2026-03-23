# Architecture Developmental Specifications
# Each spec is executable by the sequential activity-dependent growth model
# Format: cell_types, proportions, connection_rules, spatial_layout, growth_order

import json

ARCHITECTURES = {

    # =========================================================================
    # CATEGORY 1: ROUTING ARCHITECTURES
    # =========================================================================

    "hub_and_spoke": {
        "name": "Hub-and-Spoke",
        "category": "routing",
        "description": "Biological default. 2 high-connectivity hubs gate motor output.",
        "validated": True,
        "cell_types": [
            {"id": "hub_A", "nt": "ACH", "role": "integration_hub"},
            {"id": "hub_B", "nt": "ACH", "role": "output_hub"},
            {"id": "sensory_visual", "nt": "ACH", "role": "sensory"},
            {"id": "sensory_chemo", "nt": "ACH", "role": "sensory"},
            {"id": "sensory_mechano", "nt": "ACH", "role": "sensory"},
            {"id": "interneuron_A", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_B", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_C", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_D", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_E", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_F", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_G", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_H", "nt": "ACH", "role": "processing"},
            {"id": "interneuron_I", "nt": "ACH", "role": "processing"},
            {"id": "inhibitory_A", "nt": "GABA", "role": "inhibitory"},
            {"id": "inhibitory_B", "nt": "GABA", "role": "inhibitory"},
            {"id": "modulatory_A", "nt": "DA", "role": "modulatory"},
            {"id": "modulatory_B", "nt": "DA", "role": "modulatory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "hub_A": 0.1093, "hub_B": 0.082,
            "sensory_visual": 0.0301, "sensory_chemo": 0.0301, "sensory_mechano": 0.0301,
            "interneuron_A": 0.0683, "interneuron_B": 0.0683, "interneuron_C": 0.0683,
            "interneuron_D": 0.0546, "interneuron_E": 0.0546, "interneuron_F": 0.0546,
            "interneuron_G": 0.041, "interneuron_H": 0.041, "interneuron_I": 0.041,
            "inhibitory_A": 0.082, "inhibitory_B": 0.0683,
            "modulatory_A": 0.041, "modulatory_B": 0.0273,
            "motor": 0.0082,
        },
        "connection_rules": [
            {"from": "sensory_*", "to": "interneuron_*", "prob": 0.03, "mean_weight": 7.0, "type": "feedforward"},
            {"from": "interneuron_*", "to": "hub_A", "prob": 0.06, "mean_weight": 9.0, "type": "convergent"},
            {"from": "hub_A", "to": "hub_B", "prob": 0.08, "mean_weight": 11.0, "type": "hub_relay"},
            {"from": "hub_B", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "inhibitory_*", "to": "hub_*", "prob": 0.06, "mean_weight": 8.0, "type": "gating"},
            {"from": "hub_*", "to": "interneuron_*", "prob": 0.02, "mean_weight": 6.0, "type": "feedback"},
            {"from": "modulatory_*", "to": "*", "prob": 0.005, "mean_weight": 2.5, "type": "broadcast"},
        ],
        "spatial_layout": "central_hubs_peripheral_sensory",
        "growth_order": ["sensory_*", "interneuron_*", "inhibitory_*", "hub_A", "hub_B", "modulatory_*", "motor"],
        "total_neurons": 8158,
        "notes": "Reference implementation from FlyWire v783 connectome. Validated with sequential activity-dependent growth (851 nav score). Source of biological operating ranges used to calibrate all other architectures.",
    },

    "hierarchical_hub": {
        "name": "Hierarchical Hub",
        "category": "routing",
        "description": "Multiple tiers of hubs. Tier 2 gates Tier 1. Mammalian strategy.",
        "validated": False,
        "cell_types": [
            {"id": "tier1_hub_A", "nt": "ACH", "role": "motor_hub"},
            {"id": "tier1_hub_B", "nt": "ACH", "role": "motor_hub"},
            {"id": "tier2_hub_A", "nt": "ACH", "role": "selection_hub"},
            {"id": "tier2_hub_B", "nt": "ACH", "role": "selection_hub"},
            {"id": "tier2_gate", "nt": "GABA", "role": "tier2_inhibitory"},
            {"id": "sensory_A", "nt": "ACH", "role": "sensory"},
            {"id": "sensory_B", "nt": "ACH", "role": "sensory"},
            {"id": "sensory_C", "nt": "ACH", "role": "sensory"},
            {"id": "intern_A", "nt": "ACH", "role": "processing"},
            {"id": "intern_B", "nt": "ACH", "role": "processing"},
            {"id": "intern_C", "nt": "ACH", "role": "processing"},
            {"id": "intern_D", "nt": "ACH", "role": "processing"},
            {"id": "inhib_A", "nt": "GABA", "role": "inhibitory"},
            {"id": "inhib_B", "nt": "GABA", "role": "inhibitory"},
            {"id": "mod_A", "nt": "DA", "role": "modulatory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "tier1_hub_A": 0.0101, "tier1_hub_B": 0.0101,
            "tier2_hub_A": 0.0842, "tier2_hub_B": 0.0673, "tier2_gate": 0.0673,
            "sensory_A": 0.037, "sensory_B": 0.037, "sensory_C": 0.037,
            "intern_A": 0.1347, "intern_B": 0.1178, "intern_C": 0.101, "intern_D": 0.0842,
            "inhib_A": 0.0842, "inhib_B": 0.0673,
            "mod_A": 0.0505,
            "motor": 0.0101,
        },
        "connection_rules": [
            {"from": "sensory_*", "to": "intern_*", "prob": 0.03, "mean_weight": 7.0, "type": "feedforward"},
            {"from": "intern_*", "to": "tier2_hub_*", "prob": 0.06, "mean_weight": 9.0, "type": "convergent"},
            {"from": "tier2_hub_*", "to": "tier1_hub_*", "prob": 0.06, "mean_weight": 10.0, "type": "tier_relay"},
            {"from": "tier2_gate", "to": "tier1_hub_*", "prob": 0.06, "mean_weight": 8.0, "type": "gating"},
            {"from": "tier1_hub_A", "to": "tier1_hub_B", "prob": 0.08, "mean_weight": 11.0, "type": "hub_relay"},
            {"from": "tier1_hub_B", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "inhib_*", "to": "tier1_hub_*", "prob": 0.06, "mean_weight": 8.0, "type": "inhibitory"},
            {"from": "inhib_*", "to": "tier2_hub_*", "prob": 0.06, "mean_weight": 8.0, "type": "inhibitory"},
            {"from": "mod_A", "to": "*", "prob": 0.005, "mean_weight": 2.5, "type": "broadcast"},
            {"from": "tier1_hub_*", "to": "intern_*", "prob": 0.02, "mean_weight": 6.0, "type": "feedback"},
        ],
        "spatial_layout": "layered_tiers_dorsal_ventral",
        "growth_order": ["sensory_*", "intern_*", "inhib_*", "tier1_hub_A", "tier1_hub_B", "tier2_hub_A", "tier2_hub_B", "tier2_gate", "mod_A", "motor"],
        "total_neurons": 3000,
        "notes": "Tier 2 must grow AFTER Tier 1 so activity-dependent wiring biases tier2→tier1 connections.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "flat_distributed": {
        "name": "Flat/Distributed",
        "category": "routing",
        "description": "No hubs. Small-world topology. Robust but poor behavioral control.",
        "validated": False,
        "cell_types": [
            {"id": "excit_A", "nt": "ACH", "role": "processing"},
            {"id": "excit_B", "nt": "ACH", "role": "processing"},
            {"id": "excit_C", "nt": "ACH", "role": "processing"},
            {"id": "excit_D", "nt": "ACH", "role": "processing"},
            {"id": "excit_E", "nt": "ACH", "role": "processing"},
            {"id": "excit_F", "nt": "ACH", "role": "processing"},
            {"id": "inhib_A", "nt": "GABA", "role": "inhibitory"},
            {"id": "inhib_B", "nt": "GABA", "role": "inhibitory"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "excit_A": 0.1415, "excit_B": 0.1415, "excit_C": 0.1415,
            "excit_D": 0.1179, "excit_E": 0.1179, "excit_F": 0.1179,
            "inhib_A": 0.0943, "inhib_B": 0.0943,
            "sensory": 0.0259, "motor": 0.0071,
        },
        "connection_rules": [
            {"from": "excit_*", "to": "excit_*", "prob": 0.02, "mean_weight": 6.0, "type": "local_recurrent", "distance_decay": 0.5},
            {"from": "excit_*", "to": "excit_*", "prob": 0.003, "mean_weight": 5.0, "type": "long_range_shortcut", "distance_decay": 0.0},
            {"from": "inhib_*", "to": "excit_*", "prob": 0.04, "mean_weight": 7.0, "type": "local_inhibition", "distance_decay": 0.5},
            {"from": "sensory", "to": "excit_*", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "excit_*", "to": "motor", "prob": 0.008, "mean_weight": 6.0, "type": "distributed_output"},
        ],
        "spatial_layout": "uniform_3d_grid",
        "growth_order": ["sensory", "excit_A", "excit_B", "excit_C", "excit_D", "excit_E", "excit_F", "inhib_A", "inhib_B", "motor"],
        "total_neurons": 3000,
        "notes": "Small-world: high local clustering + sparse random long-range connections. No node exceeds 2x average degree.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "bus": {
        "name": "Bus Architecture",
        "category": "routing",
        "description": "Shared communication channel all modules read/write to.",
        "validated": False,
        "cell_types": [
            {"id": "bus_excit", "nt": "ACH", "role": "bus"},
            {"id": "bus_inhib", "nt": "GABA", "role": "bus_arbitration"},
            {"id": "module_A", "nt": "ACH", "role": "processing"},
            {"id": "module_B", "nt": "ACH", "role": "processing"},
            {"id": "module_C", "nt": "ACH", "role": "processing"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "bus_excit": 0.1953, "bus_inhib": 0.0651,
            "module_A": 0.2344, "module_B": 0.2344, "module_C": 0.2344,
            "sensory": 0.0286, "motor": 0.0078,
        },
        "connection_rules": [
            {"from": "sensory", "to": "bus_excit", "prob": 0.02, "mean_weight": 6.0, "type": "write"},
            {"from": "module_*", "to": "bus_excit", "prob": 0.02, "mean_weight": 6.0, "type": "write"},
            {"from": "bus_excit", "to": "module_*", "prob": 0.02, "mean_weight": 6.0, "type": "read"},
            {"from": "bus_excit", "to": "motor", "prob": 0.02, "mean_weight": 6.0, "type": "read"},
            {"from": "bus_inhib", "to": "bus_excit", "prob": 0.06, "mean_weight": 8.0, "type": "arbitration"},
            {"from": "module_*", "to": "module_*", "prob": 0.02, "mean_weight": 6.0, "type": "local_recurrent"},
        ],
        "spatial_layout": "central_bus_lateral_modules",
        "growth_order": ["sensory", "bus_excit", "bus_inhib", "module_A", "module_B", "module_C", "motor"],
        "total_neurons": 3000,
        "notes": "Bus grows first. All modules wire to/from bus via activity-dependent growth.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "ring": {
        "name": "Ring / CPG Architecture",
        "category": "routing",
        "description": "4-node central pattern generator. Each node is E/I pair with strong internal recurrence. Nodes inhibit neighbors to produce alternating rhythm. Based on spinal cord CPG biology.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 E/I ranges + spinal cord CPG literature (reciprocal inhibition model)",
        "cell_types": [
            # 4 nodes, each an E/I pair that oscillates internally
            {"id": "node0_E", "nt": "ACH", "role": "cpg_excitatory"},
            {"id": "node0_I", "nt": "GABA", "role": "cpg_inhibitory"},
            {"id": "node1_E", "nt": "ACH", "role": "cpg_excitatory"},
            {"id": "node1_I", "nt": "GABA", "role": "cpg_inhibitory"},
            {"id": "node2_E", "nt": "ACH", "role": "cpg_excitatory"},
            {"id": "node2_I", "nt": "GABA", "role": "cpg_inhibitory"},
            {"id": "node3_E", "nt": "ACH", "role": "cpg_excitatory"},
            {"id": "node3_I", "nt": "GABA", "role": "cpg_inhibitory"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "node0_E": 0.12, "node0_I": 0.06,
            "node1_E": 0.12, "node1_I": 0.06,
            "node2_E": 0.12, "node2_I": 0.06,
            "node3_E": 0.12, "node3_I": 0.06,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Internal E/I oscillators: STRONG recurrence within each node
            {"from": "node0_E", "to": "node0_I", "prob": 0.10, "mean_weight": 12.0, "type": "E_to_I"},
            {"from": "node0_I", "to": "node0_E", "prob": 0.10, "mean_weight": 12.0, "type": "I_to_E"},
            {"from": "node1_E", "to": "node1_I", "prob": 0.10, "mean_weight": 12.0, "type": "E_to_I"},
            {"from": "node1_I", "to": "node1_E", "prob": 0.10, "mean_weight": 12.0, "type": "I_to_E"},
            {"from": "node2_E", "to": "node2_I", "prob": 0.10, "mean_weight": 12.0, "type": "E_to_I"},
            {"from": "node2_I", "to": "node2_E", "prob": 0.10, "mean_weight": 12.0, "type": "I_to_E"},
            {"from": "node3_E", "to": "node3_I", "prob": 0.10, "mean_weight": 12.0, "type": "E_to_I"},
            {"from": "node3_I", "to": "node3_E", "prob": 0.10, "mean_weight": 12.0, "type": "I_to_E"},
            # Self-excitation within each node (sustains activity)
            {"from": "node0_E", "to": "node0_E", "prob": 0.035, "mean_weight": 8.0, "type": "self_excitation"},
            {"from": "node1_E", "to": "node1_E", "prob": 0.035, "mean_weight": 8.0, "type": "self_excitation"},
            {"from": "node2_E", "to": "node2_E", "prob": 0.035, "mean_weight": 8.0, "type": "self_excitation"},
            {"from": "node3_E", "to": "node3_E", "prob": 0.035, "mean_weight": 8.0, "type": "self_excitation"},
            # Reciprocal inhibition between adjacent nodes (rhythm generator)
            {"from": "node0_I", "to": "node1_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node1_I", "to": "node0_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node1_I", "to": "node2_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node2_I", "to": "node1_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node2_I", "to": "node3_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node3_I", "to": "node2_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node3_I", "to": "node0_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "node0_I", "to": "node3_E", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            # Input and output
            {"from": "sensory", "to": "node0_E", "prob": 0.016, "mean_weight": 5.0, "type": "input"},
            {"from": "sensory", "to": "node2_E", "prob": 0.016, "mean_weight": 5.0, "type": "input"},
            # All nodes drive motor (different phases = locomotion gait)
            {"from": "node0_E", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
            {"from": "node1_E", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
            {"from": "node2_E", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
            {"from": "node3_E", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "circular_2d",
        "growth_order": ["sensory", "node0_E", "node0_I", "node1_E", "node1_I", "node2_E", "node2_I", "node3_E", "node3_I", "motor"],
        "total_neurons": 3000,
        "notes": "Corrected CPG spec: 4 E/I oscillator nodes with reciprocal inhibition. Each node self-oscillates, neighbors suppress each other to produce alternating rhythm. All nodes output to motor for gait-like patterns.",
    },

    # =========================================================================
    # CATEGORY 2: COMPUTATION ARCHITECTURES
    # =========================================================================

    "reservoir": {
        "name": "Reservoir Computing",
        "category": "computation",
        "description": "Random recurrent core + trained readout. CALIBRATED from FlyWire operating ranges.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 — connection probability ranges from subsumption functional group analysis",
        "cell_types": [
            {"id": "reservoir_excit", "nt": "ACH", "role": "reservoir_core"},
            {"id": "reservoir_inhib", "nt": "GABA", "role": "reservoir_core"},
            {"id": "readout", "nt": "ACH", "role": "readout"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "reservoir_excit": 0.55, "reservoir_inhib": 0.15,
            "readout": 0.05,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Input: sparse like biology's sensory→processing
            {"from": "sensory", "to": "reservoir_excit", "prob": 0.015, "mean_weight": 5.0, "type": "input"},
            # Recurrent: matches cross-layer recurrence in fly brain
            {"from": "reservoir_excit", "to": "reservoir_excit", "prob": 0.025, "mean_weight": 7.0, "type": "recurrent"},
            # E/I balance: matches suppression pathway range
            {"from": "reservoir_excit", "to": "reservoir_inhib", "prob": 0.06, "mean_weight": 8.0, "type": "E_to_I"},
            {"from": "reservoir_inhib", "to": "reservoir_excit", "prob": 0.08, "mean_weight": 10.0, "type": "I_to_E"},
            # Readout: convergent like layer→motor
            {"from": "reservoir_excit", "to": "readout", "prob": 0.10, "mean_weight": 12.0, "type": "reservoir_to_readout"},
            # Output: matches layer→motor pathway
            {"from": "readout", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "core_shell",
        "growth_order": ["sensory", "reservoir_excit", "reservoir_inhib", "readout", "motor"],
        "total_neurons": 3000,
        "notes": "CALIBRATED. Probabilities from FlyWire biological operating ranges. Sensory first for activity-dependent wiring. Core recurrence at biological density (2.5%, not 10%)."
    },

    "feedforward_pipeline": {
        "name": "Feedforward Pipeline",
        "category": "computation",
        "description": "Layers of processing stages. No recurrence. Fast single-pass.",
        "validated": False,
        "cell_types": [
            {"id": "layer_1", "nt": "ACH", "role": "processing_layer"},
            {"id": "layer_2", "nt": "ACH", "role": "processing_layer"},
            {"id": "layer_3", "nt": "ACH", "role": "processing_layer"},
            {"id": "layer_4", "nt": "ACH", "role": "processing_layer"},
            {"id": "inhib_1", "nt": "GABA", "role": "layer_inhibition"},
            {"id": "inhib_2", "nt": "GABA", "role": "layer_inhibition"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "layer_1": 0.2406, "layer_2": 0.2139, "layer_3": 0.1872, "layer_4": 0.1604,
            "inhib_1": 0.0802, "inhib_2": 0.0802,
            "sensory": 0.0294, "motor": 0.008,
        },
        "connection_rules": [
            {"from": "sensory", "to": "layer_1", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "layer_1", "to": "layer_2", "prob": 0.03, "mean_weight": 7.0, "type": "feedforward"},
            {"from": "layer_2", "to": "layer_3", "prob": 0.03, "mean_weight": 7.0, "type": "feedforward"},
            {"from": "layer_3", "to": "layer_4", "prob": 0.03, "mean_weight": 7.0, "type": "feedforward"},
            {"from": "layer_4", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "inhib_1", "to": "layer_1", "prob": 0.04, "mean_weight": 7.0, "type": "lateral_inhibition"},
            {"from": "inhib_1", "to": "layer_2", "prob": 0.04, "mean_weight": 7.0, "type": "lateral_inhibition"},
            {"from": "inhib_2", "to": "layer_3", "prob": 0.04, "mean_weight": 7.0, "type": "lateral_inhibition"},
            {"from": "inhib_2", "to": "layer_4", "prob": 0.04, "mean_weight": 7.0, "type": "lateral_inhibition"},
        ],
        "spatial_layout": "stacked_layers_anterior_posterior",
        "growth_order": ["sensory", "layer_1", "inhib_1", "layer_2", "layer_3", "inhib_2", "layer_4", "motor"],
        "total_neurons": 3000,
        "notes": "Growth order MUST follow layer order. Each layer wires to the next based on activity from previous layer.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "recurrent_attractor": {
        "name": "Recurrent Attractor Network",
        "category": "computation",
        "description": "Strong recurrence creates stable attractor states. CALIBRATED from FlyWire.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 — recurrence from cross-layer stats, E/I from suppression pathways",
        "cell_types": [
            {"id": "attractor_excit", "nt": "ACH", "role": "attractor_population"},
            {"id": "attractor_inhib", "nt": "GABA", "role": "global_inhibition"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "attractor_excit": 0.60, "attractor_inhib": 0.15,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Input: sparse sensory
            {"from": "sensory", "to": "attractor_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            # Recurrent: slightly higher than cross-layer (attractor needs stronger recurrence)
            {"from": "attractor_excit", "to": "attractor_excit", "prob": 0.035, "mean_weight": 8.0, "type": "strong_recurrent"},
            # E/I balance: matches biological suppression
            {"from": "attractor_excit", "to": "attractor_inhib", "prob": 0.08, "mean_weight": 9.0, "type": "E_to_I"},
            {"from": "attractor_inhib", "to": "attractor_excit", "prob": 0.09, "mean_weight": 10.5, "type": "global_I_to_E"},
            # Output: matches layer→motor
            {"from": "attractor_excit", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "dense_central_cluster",
        "growth_order": ["sensory", "attractor_excit", "attractor_inhib", "motor"],
        "total_neurons": 3000,
        "notes": "CALIBRATED. Recurrence at 3.5% (top of biological range — attractors need strong recurrence). E/I from FlyWire suppression pathway stats."
    },

    "oscillatory": {
        "name": "Oscillatory Computation",
        "category": "computation",
        "description": "E/I pairs at specific frequencies. Computation via phase relationships.",
        "validated": False,
        "cell_types": [
            {"id": "osc_fast_E", "nt": "ACH", "role": "fast_oscillator"},
            {"id": "osc_fast_I", "nt": "GABA", "role": "fast_oscillator"},
            {"id": "osc_slow_E", "nt": "ACH", "role": "slow_oscillator"},
            {"id": "osc_slow_I", "nt": "GABA", "role": "slow_oscillator"},
            {"id": "coupler", "nt": "ACH", "role": "phase_coupling"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "osc_fast_E": 0.2825, "osc_fast_I": 0.1412,
            "osc_slow_E": 0.2825, "osc_slow_I": 0.1412,
            "coupler": 0.113,
            "sensory": 0.0311, "motor": 0.0085,
        },
        "connection_rules": [
            {"from": "osc_fast_E", "to": "osc_fast_I", "prob": 0.06, "mean_weight": 8.5, "type": "fast_EI"},
            {"from": "osc_fast_I", "to": "osc_fast_E", "prob": 0.08, "mean_weight": 10.0, "type": "fast_IE"},
            {"from": "osc_slow_E", "to": "osc_slow_I", "prob": 0.06, "mean_weight": 8.5, "type": "slow_EI"},
            {"from": "osc_slow_I", "to": "osc_slow_E", "prob": 0.08, "mean_weight": 10.0, "type": "slow_IE"},
            {"from": "coupler", "to": "osc_fast_E", "prob": 0.015, "mean_weight": 6.0, "type": "cross_frequency"},
            {"from": "coupler", "to": "osc_slow_E", "prob": 0.015, "mean_weight": 6.0, "type": "cross_frequency"},
            {"from": "osc_slow_E", "to": "coupler", "prob": 0.01, "mean_weight": 5.0, "type": "phase_feedback"},
            {"from": "sensory", "to": "osc_fast_E", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "osc_slow_E", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "dual_columns",
        "growth_order": ["sensory", "osc_slow_E", "osc_slow_I", "osc_fast_E", "osc_fast_I", "coupler", "motor"],
        "total_neurons": 3000,
        "notes": "Frequency set by E/I loop time constants. Slow oscillators grow first to establish base rhythm. Hard to tune — sensitive to parameters.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "predictive_coding": {
        "name": "Predictive Coding",
        "category": "computation",
        "description": "Paired prediction/error layers. Minimizes surprise. CALIBRATED from FlyWire.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 — prediction/error mapped to feedforward/feedback layer stats, inhibition from suppression pathways",
        "cell_types": [
            {"id": "pred_L1", "nt": "ACH", "role": "predictor_level_1"},
            {"id": "error_L1", "nt": "ACH", "role": "error_level_1"},
            {"id": "pred_L2", "nt": "ACH", "role": "predictor_level_2"},
            {"id": "error_L2", "nt": "ACH", "role": "error_level_2"},
            {"id": "inhib_L1", "nt": "GABA", "role": "prediction_subtraction_1"},
            {"id": "inhib_L2", "nt": "GABA", "role": "prediction_subtraction_2"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "pred_L1": 0.18, "error_L1": 0.15,
            "pred_L2": 0.18, "error_L2": 0.15,
            "inhib_L1": 0.09, "inhib_L2": 0.09,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Sensory input: sparse, biological
            {"from": "sensory", "to": "error_L1", "prob": 0.016, "mean_weight": 5.0, "type": "sensory_input"},
            # Prediction → inhibition: matches drive_suppression range
            {"from": "pred_L1", "to": "inhib_L1", "prob": 0.06, "mean_weight": 8.5, "type": "prediction"},
            # Inhibition → error: matches suppress_lower range
            {"from": "inhib_L1", "to": "error_L1", "prob": 0.07, "mean_weight": 10.0, "type": "subtract_prediction"},
            # Error ascending: matches cross-layer
            {"from": "error_L1", "to": "pred_L2", "prob": 0.03, "mean_weight": 7.0, "type": "error_ascending"},
            # Level 2 prediction/error (same ranges)
            {"from": "pred_L2", "to": "inhib_L2", "prob": 0.06, "mean_weight": 8.5, "type": "prediction"},
            {"from": "inhib_L2", "to": "error_L2", "prob": 0.07, "mean_weight": 10.0, "type": "subtract_prediction"},
            # Top-down prediction: matches feedback range
            {"from": "pred_L2", "to": "pred_L1", "prob": 0.025, "mean_weight": 7.0, "type": "top_down_prediction"},
            # Output pathways
            {"from": "error_L2", "to": "motor", "prob": 0.12, "mean_weight": 14.0, "type": "output"},
            {"from": "pred_L1", "to": "motor", "prob": 0.08, "mean_weight": 12.0, "type": "direct_output"},
        ],
        "spatial_layout": "layered_anterior_posterior",
        "growth_order": ["sensory", "error_L1", "pred_L1", "inhib_L1", "error_L2", "pred_L2", "inhib_L2", "motor"],
        "total_neurons": 3000,
        "notes": "CALIBRATED. Prediction/error pathway probabilities from FlyWire suppression/gating stats. Sensory input sparse. Output dense. Top-down weaker than bottom-up (biological asymmetry)."
    },

    "sparse_distributed_memory": {
        "name": "Sparse Distributed Memory",
        "category": "computation",
        "description": "Structured conjunction detectors for pattern storage. Small-scale cerebellar analog with structured (not random) sparse coding.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 E/I ranges + cerebellar microcircuit literature. Structured divergence replaces random projection for small-scale viability.",
        "cell_types": [
            {"id": "input_mossy", "nt": "ACH", "role": "input_divergent"},
            {"id": "granule", "nt": "ACH", "role": "conjunction_detector"},
            {"id": "purkinje", "nt": "GABA", "role": "readout_convergent"},
            {"id": "golgi", "nt": "GABA", "role": "sparsity_regulation"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            # Fewer granule cells but each is structured, not random
            "input_mossy": 0.10, "granule": 0.50, "purkinje": 0.15,
            "golgi": 0.08,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Input: mossy fibers diverge broadly to granule cells
            # Higher prob than before — structured divergence needs more connections
            {"from": "sensory", "to": "input_mossy", "prob": 0.04, "mean_weight": 8.0, "type": "input"},
            {"from": "input_mossy", "to": "granule", "prob": 0.03, "mean_weight": 6.0, "type": "divergent_sparse"},
            # Granule → Purkinje: the parallel fiber system (higher prob for structured coding)
            {"from": "granule", "to": "purkinje", "prob": 0.04, "mean_weight": 8.0, "type": "convergent"},
            # Golgi regulation: prevents runaway activation
            {"from": "golgi", "to": "granule", "prob": 0.06, "mean_weight": 9.0, "type": "sparsity_enforcement"},
            {"from": "granule", "to": "golgi", "prob": 0.04, "mean_weight": 7.0, "type": "feedback"},
            # Input also reaches Purkinje directly (climbing fiber analog)
            {"from": "input_mossy", "to": "purkinje", "prob": 0.02, "mean_weight": 12.0, "type": "feedforward"},
            # Output
            {"from": "purkinje", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "layered_cerebellar",
        "growth_order": ["sensory", "input_mossy", "granule", "golgi", "purkinje", "motor"],
        "total_neurons": 3000,
        "notes": "Corrected for small scale: structured conjunction detectors replace random sparse coding. Higher connection probabilities compensate for fewer granule cells. Direct climbing fiber pathway added for signal propagation.",
    },

    # =========================================================================
    # CATEGORY 3: CONTROL ARCHITECTURES
    # =========================================================================

    "observer_controller": {
        "name": "Observer-Controller Separation",
        "category": "control",
        "description": "Separate state estimation from action selection. Clean modularity.",
        "validated": False,
        "cell_types": [
            {"id": "observer_excit", "nt": "ACH", "role": "state_estimation"},
            {"id": "observer_inhib", "nt": "GABA", "role": "observer_regulation"},
            {"id": "interface", "nt": "ACH", "role": "state_vector"},
            {"id": "controller_excit", "nt": "ACH", "role": "action_selection"},
            {"id": "controller_inhib", "nt": "GABA", "role": "controller_regulation"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "observer_excit": 0.3743, "observer_inhib": 0.1198,
            "interface": 0.0749,
            "controller_excit": 0.2994, "controller_inhib": 0.0898,
            "sensory": 0.0329, "motor": 0.009,
        },
        "connection_rules": [
            {"from": "sensory", "to": "observer_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "observer_excit", "to": "observer_excit", "prob": 0.025, "mean_weight": 7.0, "type": "recurrent"},
            {"from": "observer_excit", "to": "observer_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "observer_inhib", "to": "observer_excit", "prob": 0.08, "mean_weight": 10.0, "type": "IE"},
            {"from": "observer_excit", "to": "interface", "prob": 0.15, "mean_weight": 14.0, "type": "state_output"},
            {"from": "interface", "to": "controller_excit", "prob": 0.012, "mean_weight": 5.0, "type": "state_input"},
            {"from": "controller_excit", "to": "controller_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "controller_inhib", "to": "controller_excit", "prob": 0.08, "mean_weight": 10.0, "type": "IE"},
            {"from": "controller_excit", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "two_regions_with_bridge",
        "growth_order": ["sensory", "observer_excit", "observer_inhib", "interface", "controller_excit", "controller_inhib", "motor"],
        "total_neurons": 3000,
        "notes": "Observer and controller are spatially separated. Interface is a narrow bridge. Observer can be complex without slowing the controller.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "winner_take_all": {
        "name": "Winner-Take-All",
        "category": "control",
        "description": "Competing modules with lateral inhibition. One winner.",
        "validated": False,
        "cell_types": [
            {"id": "option_A", "nt": "ACH", "role": "competing_option"},
            {"id": "option_B", "nt": "ACH", "role": "competing_option"},
            {"id": "option_C", "nt": "ACH", "role": "competing_option"},
            {"id": "option_D", "nt": "ACH", "role": "competing_option"},
            {"id": "global_inhib", "nt": "GABA", "role": "competition"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "option_A": 0.206, "option_B": 0.206, "option_C": 0.206, "option_D": 0.206,
            "global_inhib": 0.1374,
            "sensory": 0.0302, "motor": 0.0082,
        },
        "connection_rules": [
            {"from": "sensory", "to": "option_*", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "option_*", "to": "option_*", "prob": 0.03, "mean_weight": 8.0, "type": "self_excitation", "self_only": True},
            {"from": "option_*", "to": "global_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "drive_inhibition"},
            {"from": "global_inhib", "to": "option_*", "prob": 0.08, "mean_weight": 10.0, "type": "suppress_all"},
            {"from": "option_*", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "symmetric_quadrants",
        "growth_order": ["sensory", "option_A", "option_B", "option_C", "option_D", "global_inhib", "motor"],
        "total_neurons": 3000,
        "notes": "Symmetric architecture. Self-excitation + global inhibition = winner suppresses all others. Growth order doesn't matter (symmetric).",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "evidence_accumulator": {
        "name": "Evidence Accumulator",
        "category": "control",
        "description": "Drift-diffusion. Accumulate evidence, threshold triggers action. CALIBRATED from FlyWire.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 — self-excitation from recurrence stats, mutual inhibition from suppression, output from layer→motor",
        "cell_types": [
            {"id": "accum_A", "nt": "ACH", "role": "evidence_for_A"},
            {"id": "accum_B", "nt": "ACH", "role": "evidence_for_B"},
            {"id": "mutual_inhib", "nt": "GABA", "role": "competition"},
            {"id": "threshold", "nt": "ACH", "role": "threshold_detector"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "accum_A": 0.30, "accum_B": 0.30,
            "mutual_inhib": 0.12, "threshold": 0.06,
            "sensory": 0.022, "motor": 0.006,
        },
        "connection_rules": [
            # Evidence input: sparse sensory
            {"from": "sensory", "to": "accum_A", "prob": 0.012, "mean_weight": 5.0, "type": "evidence_input"},
            {"from": "sensory", "to": "accum_B", "prob": 0.012, "mean_weight": 5.0, "type": "evidence_input"},
            # Self-excitation: recurrence range for accumulation
            {"from": "accum_A", "to": "accum_A", "prob": 0.03, "mean_weight": 8.0, "type": "self_excitation"},
            {"from": "accum_B", "to": "accum_B", "prob": 0.03, "mean_weight": 8.0, "type": "self_excitation"},
            # Mutual inhibition: suppression pathway range
            {"from": "accum_A", "to": "mutual_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "drive_inhibition"},
            {"from": "accum_B", "to": "mutual_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "drive_inhibition"},
            {"from": "mutual_inhib", "to": "accum_A", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            {"from": "mutual_inhib", "to": "accum_B", "prob": 0.08, "mean_weight": 10.0, "type": "suppress"},
            # Threshold detection: convergent like layer→motor
            {"from": "accum_A", "to": "threshold", "prob": 0.10, "mean_weight": 12.0, "type": "threshold_check"},
            {"from": "accum_B", "to": "threshold", "prob": 0.10, "mean_weight": 12.0, "type": "threshold_check"},
            # Output: matches layer→motor
            {"from": "threshold", "to": "motor", "prob": 0.18, "mean_weight": 15.0, "type": "output"},
        ],
        "spatial_layout": "bilateral_symmetric",
        "growth_order": ["sensory", "accum_A", "accum_B", "mutual_inhib", "threshold", "motor"],
        "total_neurons": 3000,
        "notes": "CALIBRATED. Self-excitation at biological recurrence rate. Mutual inhibition from suppression stats. Sensory first for activity bootstrapping."
    },

    "priority_queue": {
        "name": "Priority Queue",
        "category": "control",
        "description": "Multiple actions maintained with dynamic priority. Urgency-gated.",
        "validated": False,
        "cell_types": [
            {"id": "action_A", "nt": "ACH", "role": "action_option"},
            {"id": "action_B", "nt": "ACH", "role": "action_option"},
            {"id": "action_C", "nt": "ACH", "role": "action_option"},
            {"id": "priority_tag", "nt": "ACH", "role": "priority_modulation"},
            {"id": "urgency", "nt": "DA", "role": "urgency_broadcast"},
            {"id": "gate", "nt": "GABA", "role": "action_gating"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "action_A": 0.2212, "action_B": 0.2212, "action_C": 0.2212,
            "priority_tag": 0.118, "urgency": 0.059, "gate": 0.118,
            "sensory": 0.0324, "motor": 0.0088,
        },
        "connection_rules": [
            {"from": "sensory", "to": "action_*", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "sensory", "to": "priority_tag", "prob": 0.012, "mean_weight": 5.0, "type": "context_input"},
            {"from": "priority_tag", "to": "action_*", "prob": 0.02, "mean_weight": 6.0, "type": "priority_modulation"},
            {"from": "urgency", "to": "action_*", "prob": 0.005, "mean_weight": 2.5, "type": "urgency_broadcast"},
            {"from": "urgency", "to": "gate", "prob": 0.02, "mean_weight": 6.0, "type": "urgency_gate"},
            {"from": "action_*", "to": "gate", "prob": 0.02, "mean_weight": 6.0, "type": "action_to_gate"},
            {"from": "gate", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "gated_output"},
            {"from": "action_*", "to": "action_*", "prob": 0.03, "mean_weight": 8.0, "type": "self_excitation", "self_only": True},
        ],
        "spatial_layout": "radial_actions_central_gate",
        "growth_order": ["sensory", "action_A", "action_B", "action_C", "priority_tag", "urgency", "gate", "motor"],
        "total_neurons": 3000,
        "notes": "Dopaminergic urgency signal modulates all actions globally. Priority tag provides context-dependent weighting.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "subsumption": {
        "name": "Subsumption Architecture",
        "category": "control",
        "description": "Layered behaviors. Higher suppresses lower. Lower can override for safety. CALIBRATED from FlyWire v783.",
        "validated": False,
        "calibrated": True,
        "calibration_source": "FlyWire v783 connectome — functional group analysis of DN upstream interneurons",
        "cell_types": [
            {"id": "layer0_escape", "nt": "ACH", "role": "reflex_layer"},
            {"id": "layer1_avoid", "nt": "ACH", "role": "avoidance_layer"},
            {"id": "layer2_navigate", "nt": "ACH", "role": "navigation_layer"},
            {"id": "suppress_1to0", "nt": "GABA", "role": "layer_suppression"},
            {"id": "suppress_2to1", "nt": "GABA", "role": "layer_suppression"},
            {"id": "emergency", "nt": "ACH", "role": "emergency_override"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        # Proportions from FlyWire functional group sizes (2904 total mapped neurons)
        "proportions": {
            "layer0_escape": 0.20, "layer1_avoid": 0.22, "layer2_navigate": 0.40,
            "suppress_1to0": 0.09, "suppress_2to1": 0.06,
            "emergency": 0.008,
            "sensory": 0.022, "motor": 0.006,
        },
        # Connection probabilities extracted from FlyWire v783 real synaptic data.
        # Each prob is: actual_connections / (n_source * n_target) from the connectome.
        # Mean weights are the average synapse count on that pathway.
        "connection_rules": [
            # Layer → motor (output pathways)
            {"from": "layer1_avoid", "to": "motor", "prob": 0.239, "mean_weight": 13.63, "type": "output"},
            {"from": "suppress_2to1", "to": "motor", "prob": 0.253, "mean_weight": 14.75, "type": "output"},
            {"from": "layer2_navigate", "to": "motor", "prob": 0.137, "mean_weight": 16.20, "type": "output"},
            {"from": "suppress_1to0", "to": "motor", "prob": 0.101, "mean_weight": 12.81, "type": "output"},
            {"from": "layer0_escape", "to": "motor", "prob": 0.084, "mean_weight": 9.14, "type": "output"},
            {"from": "emergency", "to": "motor", "prob": 0.063, "mean_weight": 7.27, "type": "output"},
            # Suppression pathways
            {"from": "layer1_avoid", "to": "suppress_2to1", "prob": 0.102, "mean_weight": 8.45, "type": "drive_suppression"},
            {"from": "suppress_2to1", "to": "layer1_avoid", "prob": 0.088, "mean_weight": 10.54, "type": "suppress_lower"},
            {"from": "suppress_1to0", "to": "layer0_escape", "prob": 0.057, "mean_weight": 7.40, "type": "suppress_lower"},
            {"from": "layer0_escape", "to": "suppress_1to0", "prob": 0.047, "mean_weight": 6.71, "type": "drive_suppression"},
            {"from": "layer2_navigate", "to": "suppress_2to1", "prob": 0.043, "mean_weight": 8.57, "type": "drive_suppression"},
            {"from": "suppress_2to1", "to": "layer2_navigate", "prob": 0.037, "mean_weight": 10.14, "type": "feedback"},
            # Emergency override
            {"from": "emergency", "to": "layer0_escape", "prob": 0.045, "mean_weight": 3.07, "type": "emergency_override"},
            {"from": "emergency", "to": "suppress_1to0", "prob": 0.045, "mean_weight": 5.50, "type": "emergency_suppression"},
            # Cross-layer interactions (real, not designed)
            {"from": "layer2_navigate", "to": "layer1_avoid", "prob": 0.034, "mean_weight": 6.92, "type": "cross_layer"},
            {"from": "layer1_avoid", "to": "layer2_navigate", "prob": 0.032, "mean_weight": 7.84, "type": "cross_layer"},
            {"from": "layer2_navigate", "to": "layer0_escape", "prob": 0.016, "mean_weight": 8.42, "type": "cross_layer"},
            {"from": "layer0_escape", "to": "layer2_navigate", "prob": 0.015, "mean_weight": 6.30, "type": "cross_layer"},
            # Sensory input (sparse — biology routes through many hops)
            {"from": "sensory", "to": "motor", "prob": 0.022, "mean_weight": 7.27, "type": "direct_sensorimotor"},
            {"from": "sensory", "to": "suppress_1to0", "prob": 0.018, "mean_weight": 5.11, "type": "input"},
            {"from": "sensory", "to": "layer0_escape", "prob": 0.016, "mean_weight": 3.06, "type": "input"},
            {"from": "sensory", "to": "emergency", "prob": 0.057, "mean_weight": 1.18, "type": "threat_detection"},
            {"from": "sensory", "to": "layer2_navigate", "prob": 0.003, "mean_weight": 5.70, "type": "input"},
            {"from": "sensory", "to": "layer1_avoid", "prob": 0.002, "mean_weight": 3.50, "type": "input"},
        ],
        "spatial_layout": "stacked_layers_ventral_dorsal",
        # Sensory first — it needs to establish input paths before layers wire
        "growth_order": ["sensory", "emergency", "layer0_escape", "suppress_1to0", "layer1_avoid", "suppress_2to1", "layer2_navigate", "motor"],
        "total_neurons": 3000,
        "notes": "CALIBRATED from FlyWire v783. Connection probabilities extracted from real synaptic data between functional neuron groups (DN upstream analysis). Sensory grows first so activity-dependent wiring has input signal. Total neurons reduced to match biological functional group size."
    },

    # =========================================================================
    # CATEGORY 4: LEARNING AND ADAPTATION
    # =========================================================================

    "hebbian_assembly": {
        "name": "Hebbian Assembly",
        "category": "learning",
        "description": "Fire together, wire together. Self-organizing from experience.",
        "validated": False,
        "cell_types": [
            {"id": "assembly_excit", "nt": "ACH", "role": "assembly_population"},
            {"id": "assembly_inhib", "nt": "GABA", "role": "homeostatic_regulation"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "assembly_excit": 0.7555, "assembly_inhib": 0.206,
            "sensory": 0.0302, "motor": 0.0082,
        },
        "connection_rules": [
            {"from": "sensory", "to": "assembly_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "assembly_excit", "to": "assembly_excit", "prob": 0.02, "mean_weight": 6.0, "type": "plastic_recurrent", "plasticity": "STDP"},
            {"from": "assembly_excit", "to": "assembly_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "assembly_inhib", "to": "assembly_excit", "prob": 0.08, "mean_weight": 10.0, "type": "homeostatic_IE"},
            {"from": "assembly_excit", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "uniform_3d",
        "growth_order": ["sensory", "assembly_excit", "assembly_inhib", "motor"],
        "total_neurons": 3000,
        "notes": "Initial connectivity is broad and weak. STDP plasticity rules strengthen co-activated connections. Assemblies emerge from experience.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "reward_modulated": {
        "name": "Reward-Modulated Architecture",
        "category": "learning",
        "description": "Base circuit + dopaminergic reward signal gates plasticity.",
        "validated": False,
        "cell_types": [
            {"id": "base_excit", "nt": "ACH", "role": "base_processing"},
            {"id": "base_inhib", "nt": "GABA", "role": "base_inhibition"},
            {"id": "reward_input", "nt": "ACH", "role": "reward_detection"},
            {"id": "dopamine", "nt": "DA", "role": "reward_broadcast"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "base_excit": 0.6173, "base_inhib": 0.1852,
            "reward_input": 0.0772, "dopamine": 0.0772,
            "sensory": 0.034, "motor": 0.0093,
        },
        "connection_rules": [
            {"from": "sensory", "to": "base_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "base_excit", "to": "base_excit", "prob": 0.025, "mean_weight": 7.0, "type": "recurrent", "plasticity": "three_factor"},
            {"from": "base_excit", "to": "base_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "base_inhib", "to": "base_excit", "prob": 0.08, "mean_weight": 10.0, "type": "IE"},
            {"from": "base_excit", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output", "plasticity": "three_factor"},
            {"from": "reward_input", "to": "dopamine", "prob": 0.02, "mean_weight": 6.0, "type": "reward_signal"},
            {"from": "dopamine", "to": "base_excit", "prob": 0.005, "mean_weight": 2.5, "type": "modulatory_broadcast"},
        ],
        "spatial_layout": "base_circuit_with_modulatory_overlay",
        "growth_order": ["sensory", "reward_input", "base_excit", "base_inhib", "dopamine", "motor"],
        "total_neurons": 3000,
        "notes": "Base circuit grows first. Dopaminergic overlay grows second. Three-factor plasticity: pre × post × dopamine.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "neuromodulatory_gain": {
        "name": "Neuromodulatory Gain Control",
        "category": "learning",
        "description": "Multiple modulatory systems shift circuit operating mode.",
        "validated": False,
        "cell_types": [
            {"id": "base_excit", "nt": "ACH", "role": "base_processing"},
            {"id": "base_inhib", "nt": "GABA", "role": "base_inhibition"},
            {"id": "mod_arousal", "nt": "NE", "role": "arousal_modulation"},
            {"id": "mod_reward", "nt": "DA", "role": "reward_modulation"},
            {"id": "mod_attention", "nt": "5HT", "role": "attention_modulation"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "base_excit": 0.5864, "base_inhib": 0.1852,
            "mod_arousal": 0.0617, "mod_reward": 0.0617, "mod_attention": 0.0617,
            "sensory": 0.034, "motor": 0.0093,
        },
        "connection_rules": [
            {"from": "sensory", "to": "base_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "base_excit", "to": "base_excit", "prob": 0.025, "mean_weight": 7.0, "type": "recurrent"},
            {"from": "base_excit", "to": "base_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "base_inhib", "to": "base_excit", "prob": 0.08, "mean_weight": 10.0, "type": "IE"},
            {"from": "base_excit", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "mod_arousal", "to": "base_excit", "prob": 0.02, "mean_weight": 6.0, "type": "gain_increase"},
            {"from": "mod_reward", "to": "base_excit", "prob": 0.02, "mean_weight": 6.0, "type": "plasticity_gate"},
            {"from": "mod_attention", "to": "base_inhib", "prob": 0.02, "mean_weight": 6.0, "type": "snr_increase"},
            {"from": "sensory", "to": "mod_arousal", "prob": 0.02, "mean_weight": 6.0, "type": "arousal_drive"},
        ],
        "spatial_layout": "base_circuit_with_modulatory_nuclei",
        "growth_order": ["sensory", "base_excit", "base_inhib", "mod_arousal", "mod_reward", "mod_attention", "motor"],
        "total_neurons": 3000,
        "notes": "Three distinct neuromodulatory systems. Each uses a different NT. Base circuit grows first. Modulatory overlay grows second.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    # =========================================================================
    # CATEGORY 5: ROBUSTNESS
    # =========================================================================

    "triple_redundancy": {
        "name": "Triple Modular Redundancy",
        "category": "robustness",
        "description": "Three copies of critical circuit. Majority voting. Survives single failure.",
        "validated": False,
        "cell_types": [
            {"id": "copy_A", "nt": "ACH", "role": "redundant_copy"},
            {"id": "copy_B", "nt": "ACH", "role": "redundant_copy"},
            {"id": "copy_C", "nt": "ACH", "role": "redundant_copy"},
            {"id": "voter", "nt": "ACH", "role": "majority_voting"},
            {"id": "inhib", "nt": "GABA", "role": "inhibitory"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "copy_A": 0.2639, "copy_B": 0.2639, "copy_C": 0.2639,
            "voter": 0.066, "inhib": 0.1055,
            "sensory": 0.029, "motor": 0.0079,
        },
        "connection_rules": [
            {"from": "sensory", "to": "copy_A", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "sensory", "to": "copy_B", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "sensory", "to": "copy_C", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "copy_A", "to": "voter", "prob": 0.02, "mean_weight": 6.0, "type": "vote"},
            {"from": "copy_B", "to": "voter", "prob": 0.02, "mean_weight": 6.0, "type": "vote"},
            {"from": "copy_C", "to": "voter", "prob": 0.02, "mean_weight": 6.0, "type": "vote"},
            {"from": "voter", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "inhib", "to": "copy_*", "prob": 0.06, "mean_weight": 8.0, "type": "regulation"},
        ],
        "spatial_layout": "three_spatial_copies_central_voter",
        "growth_order": ["sensory", "copy_A", "copy_B", "copy_C", "voter", "inhib", "motor"],
        "total_neurons": 3000,
        "notes": "Three spatially separated copies. Voter activates when 2+ copies agree. Single copy failure = continued operation.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "population_coding": {
        "name": "Graceful Degradation",
        "category": "robustness",
        "description": "Information encoded across population. Degrades proportionally, not catastrophically.",
        "validated": False,
        "cell_types": [
            {"id": "population", "nt": "ACH", "role": "distributed_encoding"},
            {"id": "inhib", "nt": "GABA", "role": "normalization"},
            {"id": "readout", "nt": "ACH", "role": "population_readout"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "population": 0.6868, "inhib": 0.1648, "readout": 0.1099,
            "sensory": 0.0302, "motor": 0.0082,
        },
        "connection_rules": [
            {"from": "sensory", "to": "population", "prob": 0.012, "mean_weight": 5.0, "type": "input_distributed"},
            {"from": "population", "to": "population", "prob": 0.025, "mean_weight": 7.0, "type": "overlapping_recurrent"},
            {"from": "population", "to": "inhib", "prob": 0.02, "mean_weight": 6.0, "type": "normalization_drive"},
            {"from": "inhib", "to": "population", "prob": 0.06, "mean_weight": 8.0, "type": "divisive_normalization"},
            {"from": "population", "to": "readout", "prob": 0.02, "mean_weight": 6.0, "type": "population_average"},
            {"from": "readout", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "uniform_3d",
        "growth_order": ["sensory", "population", "inhib", "readout", "motor"],
        "total_neurons": 3000,
        "notes": "No individual neuron is critical. Losing 10% of neurons degrades performance ~10%. Readout averages across population.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "self_repairing": {
        "name": "Self-Repairing Architecture",
        "category": "robustness",
        "description": "Uncommitted progenitor cells differentiate on demand to replace damage.",
        "validated": False,
        "cell_types": [
            {"id": "functional_excit", "nt": "ACH", "role": "active_processing"},
            {"id": "functional_inhib", "nt": "GABA", "role": "active_inhibition"},
            {"id": "progenitor", "nt": "none", "role": "undifferentiated_reserve"},
            {"id": "damage_sensor", "nt": "ACH", "role": "activity_monitoring"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "functional_excit": 0.5014, "functional_inhib": 0.1719,
            "progenitor": 0.2149, "damage_sensor": 0.0716,
            "sensory": 0.0315, "motor": 0.0086,
        },
        "connection_rules": [
            {"from": "sensory", "to": "functional_excit", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "functional_excit", "to": "functional_excit", "prob": 0.025, "mean_weight": 7.0, "type": "recurrent"},
            {"from": "functional_excit", "to": "functional_inhib", "prob": 0.06, "mean_weight": 8.5, "type": "EI"},
            {"from": "functional_inhib", "to": "functional_excit", "prob": 0.08, "mean_weight": 10.0, "type": "IE"},
            {"from": "functional_excit", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "functional_excit", "to": "damage_sensor", "prob": 0.02, "mean_weight": 6.0, "type": "activity_report"},
            {"from": "damage_sensor", "to": "progenitor", "prob": 0.02, "mean_weight": 6.0, "type": "differentiation_signal"},
        ],
        "spatial_layout": "functional_core_progenitor_periphery",
        "growth_order": ["sensory", "functional_excit", "functional_inhib", "progenitor", "damage_sensor", "motor"],
        "total_neurons": 3000,
        "notes": "Speculative. Progenitor cells remain undifferentiated. When damage_sensor detects activity loss, progenitors differentiate and wire in. Adult neurogenesis analog.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    # =========================================================================
    # CATEGORY 6: EXOTIC
    # =========================================================================

    "content_addressable": {
        "name": "Content-Addressable Memory",
        "category": "exotic",
        "description": "Biological hash table. Random projection to sparse code. O(1) retrieval.",
        "validated": False,
        "cell_types": [
            {"id": "input", "nt": "ACH", "role": "input_encoding"},
            {"id": "hash_layer", "nt": "ACH", "role": "random_projection"},
            {"id": "sparse_code", "nt": "ACH", "role": "address_space"},
            {"id": "readout", "nt": "ACH", "role": "output_decoding"},
            {"id": "inhib", "nt": "GABA", "role": "sparsity_enforcement"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "input": 0.1114, "hash_layer": 0.2089, "sparse_code": 0.4178,
            "readout": 0.1114, "inhib": 0.1114,
            "sensory": 0.0306, "motor": 0.0084,
        },
        "connection_rules": [
            {"from": "sensory", "to": "input", "prob": 0.012, "mean_weight": 5.0, "type": "input"},
            {"from": "input", "to": "hash_layer", "prob": 0.02, "mean_weight": 6.0, "type": "encoding"},
            {"from": "hash_layer", "to": "sparse_code", "prob": 0.02, "mean_weight": 6.0, "type": "random_projection"},
            {"from": "inhib", "to": "sparse_code", "prob": 0.06, "mean_weight": 8.0, "type": "sparsification"},
            {"from": "sparse_code", "to": "readout", "prob": 0.02, "mean_weight": 6.0, "type": "address_to_value"},
            {"from": "readout", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
        ],
        "spatial_layout": "layered_hash_pipeline",
        "growth_order": ["input", "sensory", "hash_layer", "sparse_code", "inhib", "readout", "motor"],
        "total_neurons": 3000,
        "notes": "Random projection is the hash function. Doesn't need to be learned. Sparse code is ~1% active per input.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "dataflow": {
        "name": "Dataflow Architecture",
        "category": "exotic",
        "description": "No central clock. Modules fire when inputs are ready. Data-driven execution.",
        "validated": False,
        "cell_types": [
            {"id": "node_A", "nt": "ACH", "role": "dataflow_node"},
            {"id": "node_B", "nt": "ACH", "role": "dataflow_node"},
            {"id": "node_C", "nt": "ACH", "role": "dataflow_node"},
            {"id": "node_D", "nt": "ACH", "role": "dataflow_node"},
            {"id": "node_E", "nt": "ACH", "role": "dataflow_node"},
            {"id": "threshold_gate", "nt": "GABA", "role": "input_readiness"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "node_A": 0.1777, "node_B": 0.1777, "node_C": 0.1777,
            "node_D": 0.1777, "node_E": 0.1777,
            "threshold_gate": 0.0761,
            "sensory": 0.0279, "motor": 0.0076,
        },
        "connection_rules": [
            {"from": "sensory", "to": "node_A", "prob": 0.012, "mean_weight": 5.0, "type": "data_input"},
            {"from": "sensory", "to": "node_B", "prob": 0.012, "mean_weight": 5.0, "type": "data_input"},
            {"from": "node_A", "to": "node_C", "prob": 0.02, "mean_weight": 6.0, "type": "dataflow_edge"},
            {"from": "node_B", "to": "node_C", "prob": 0.02, "mean_weight": 6.0, "type": "dataflow_edge"},
            {"from": "node_C", "to": "node_D", "prob": 0.02, "mean_weight": 6.0, "type": "dataflow_edge"},
            {"from": "node_C", "to": "node_E", "prob": 0.02, "mean_weight": 6.0, "type": "dataflow_edge"},
            {"from": "node_D", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "node_E", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "output"},
            {"from": "threshold_gate", "to": "node_*", "prob": 0.02, "mean_weight": 6.0, "type": "readiness_gate"},
        ],
        "spatial_layout": "directed_graph_layout",
        "growth_order": ["sensory", "node_A", "node_B", "node_C", "node_D", "node_E", "threshold_gate", "motor"],
        "total_neurons": 3000,
        "notes": "Each node fires only when sufficient inputs arrive. No global timing. Naturally parallel.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "cellular_automaton": {
        "name": "Neuronal Cellular Automaton",
        "category": "exotic",
        "description": "Regular grid, local rules, emergent global behavior. Simplest growth program.",
        "validated": False,
        "cell_types": [
            {"id": "grid_cell", "nt": "ACH", "role": "automaton_unit"},
            {"id": "grid_inhib", "nt": "GABA", "role": "local_inhibition"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "grid_cell": 0.7555, "grid_inhib": 0.206,
            "sensory": 0.0302, "motor": 0.0082,
        },
        "connection_rules": [
            {"from": "grid_cell", "to": "grid_cell", "prob": 0.02, "mean_weight": 6.0, "type": "local_neighbors_only", "radius": 1},
            {"from": "grid_inhib", "to": "grid_cell", "prob": 0.04, "mean_weight": 7.0, "type": "local_inhibition", "radius": 1},
            {"from": "sensory", "to": "grid_cell", "prob": 0.012, "mean_weight": 5.0, "type": "sparse_input"},
            {"from": "grid_cell", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "sparse_output"},
        ],
        "spatial_layout": "regular_3d_grid",
        "growth_order": ["sensory", "grid_cell", "grid_inhib", "motor"],
        "total_neurons": 3000,
        "notes": "Simplest possible growth program. Regular grid, local connections only. Complex behavior emerges from simple local rules.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "hyperdimensional": {
        "name": "Hyperdimensional Computing",
        "category": "exotic",
        "description": "High-dimensional random vectors. Binding, bundling, permutation. Noise-tolerant.",
        "validated": False,
        "cell_types": [
            {"id": "hd_excit", "nt": "ACH", "role": "dimension_encoding"},
            {"id": "hd_bind", "nt": "GABA", "role": "binding_operation"},
            {"id": "hd_bundle", "nt": "ACH", "role": "bundling_operation"},
            {"id": "similarity", "nt": "ACH", "role": "similarity_matching"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "hd_excit": 0.565, "hd_bind": 0.1412, "hd_bundle": 0.1412,
            "similarity": 0.113,
            "sensory": 0.0311, "motor": 0.0085,
        },
        "connection_rules": [
            {"from": "sensory", "to": "hd_excit", "prob": 0.02, "mean_weight": 6.0, "type": "random_encoding"},
            {"from": "hd_excit", "to": "hd_bind", "prob": 0.012, "mean_weight": 5.0, "type": "binding_input"},
            {"from": "hd_bind", "to": "hd_excit", "prob": 0.06, "mean_weight": 8.0, "type": "bound_representation"},
            {"from": "hd_excit", "to": "hd_bundle", "prob": 0.012, "mean_weight": 5.0, "type": "bundling_input"},
            {"from": "hd_bundle", "to": "hd_excit", "prob": 0.02, "mean_weight": 6.0, "type": "bundled_representation"},
            {"from": "hd_excit", "to": "similarity", "prob": 0.02, "mean_weight": 6.0, "type": "query"},
            {"from": "similarity", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "match_output"},
        ],
        "spatial_layout": "large_flat_population",
        "growth_order": ["sensory", "hd_excit", "hd_bind", "hd_bundle", "similarity", "motor"],
        "total_neurons": 3000,
        "notes": "Large population = more dimensions = more noise tolerance. Random initial encoding is fine — high-dim random vectors are nearly orthogonal.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },

    "spiking_state_machine": {
        "name": "Spiking Neural State Machine",
        "category": "exotic",
        "description": "Discrete states in neural populations. Transitions triggered by input.",
        "validated": False,
        "cell_types": [
            {"id": "state_A", "nt": "ACH", "role": "state_population"},
            {"id": "state_B", "nt": "ACH", "role": "state_population"},
            {"id": "state_C", "nt": "ACH", "role": "state_population"},
            {"id": "state_D", "nt": "ACH", "role": "state_population"},
            {"id": "transition", "nt": "ACH", "role": "transition_detector"},
            {"id": "global_inhib", "nt": "GABA", "role": "mutual_exclusion"},
            {"id": "sensory", "nt": "ACH", "role": "sensory"},
            {"id": "motor", "nt": "ACH", "role": "motor"},
        ],
        "proportions": {
            "state_A": 0.1872, "state_B": 0.1872, "state_C": 0.1872, "state_D": 0.1872,
            "transition": 0.107, "global_inhib": 0.107,
            "sensory": 0.0294, "motor": 0.008,
        },
        "connection_rules": [
            {"from": "state_*", "to": "state_*", "prob": 0.03, "mean_weight": 8.0, "type": "self_excitation", "self_only": True},
            {"from": "state_*", "to": "global_inhib", "prob": 0.02, "mean_weight": 6.0, "type": "drive_mutual_exclusion"},
            {"from": "global_inhib", "to": "state_*", "prob": 0.08, "mean_weight": 10.0, "type": "suppress_all"},
            {"from": "sensory", "to": "transition", "prob": 0.02, "mean_weight": 6.0, "type": "transition_trigger"},
            {"from": "transition", "to": "state_*", "prob": 0.02, "mean_weight": 6.0, "type": "state_activation"},
            {"from": "state_*", "to": "motor", "prob": 0.15, "mean_weight": 14.0, "type": "state_output"},
        ],
        "spatial_layout": "symmetric_clusters",
        "growth_order": ["sensory", "state_A", "state_B", "state_C", "state_D", "global_inhib", "transition", "motor"],
        "total_neurons": 3000,
        "notes": "Exactly one state active at a time. Transitions are deterministic given input + current state. Verifiable behavior.",
        "calibrated": True,
        "calibration_source": "FlyWire v783 — biological operating ranges from functional group analysis",
    },
}

# =========================================================================
# COMPOSITE ARCHITECTURES (combinations)
# =========================================================================

COMPOSITES = {
    "reservoir_hub_readout": {
        "name": "Reservoir + Hub Readout",
        "base_architectures": ["reservoir", "hub_and_spoke"],
        "description": "Reservoir core for rich dynamics. Hub readout for precise behavioral control.",
        "merge_rules": "Reservoir sensory/motor replaced by hub sensory/motor. Reservoir readout connects to hub interneurons.",
    },
    "hierarchical_predictive": {
        "name": "Hierarchical Hub + Predictive Coding",
        "base_architectures": ["hierarchical_hub", "predictive_coding"],
        "description": "Each hub tier implements predictive coding. Deep generative model with behavioral control.",
        "merge_rules": "Each tier's hub is replaced by a prediction/error pair. Top-down predictions flow between tiers.",
    },
    "subsumption_reward": {
        "name": "Subsumption + Reward Modulation",
        "base_architectures": ["subsumption", "reward_modulated"],
        "description": "Layered reactive behaviors with reward-modulated learning on higher layers.",
        "merge_rules": "Layer 0 is hardwired. Layers 1+ have dopaminergic plasticity. Reward system added as overlay.",
    },
    "observer_accumulator": {
        "name": "Observer-Controller + Evidence Accumulator",
        "base_architectures": ["observer_controller", "evidence_accumulator"],
        "description": "Observer estimates state. Controller uses drift-diffusion for decisions under uncertainty.",
        "merge_rules": "Controller module replaced by evidence accumulator. Observer interface feeds accumulator inputs.",
    },
    "oscillatory_wta": {
        "name": "Oscillatory + Winner-Take-All",
        "base_architectures": ["oscillatory", "winner_take_all"],
        "description": "WTA circuits at multiple frequencies. Cross-frequency coupling for multi-scale decisions.",
        "merge_rules": "Each WTA option is an oscillator pair. Phase coupling determines which option wins at each timescale.",
    },
}


def get_architecture(name):
    """Get a single architecture spec by name."""
    return ARCHITECTURES.get(name)

def get_all_architectures():
    """Get all architecture specs."""
    return ARCHITECTURES

def get_composite(name):
    """Get a composite architecture spec."""
    return COMPOSITES.get(name)

def list_architectures():
    """List all available architectures with category and status."""
    for name, spec in ARCHITECTURES.items():
        status = "VALIDATED" if spec.get("validated") else "TESTABLE"
        print(f"  [{status}] {spec['category']:12s} | {spec['name']:35s} | {spec.get('total_neurons', '?'):>6} neurons | {len(spec.get('cell_types', [])):>2} cell types")

def get_growth_spec(name):
    """Extract the growth-model-compatible spec from an architecture."""
    arch = ARCHITECTURES[name]
    return {
        "cell_types": arch["cell_types"],
        "proportions": arch["proportions"],
        "connection_rules": arch["connection_rules"],
        "growth_order": arch["growth_order"],
        "total_neurons": arch["total_neurons"],
        "spatial_layout": arch["spatial_layout"],
    }


if __name__ == "__main__":
    print("=" * 100)
    print("COMPILE ARCHITECTURE CATALOG")
    print("=" * 100)
    print(f"\n  {len(ARCHITECTURES)} architectures + {len(COMPOSITES)} composites\n")
    list_architectures()
    print(f"\n  Composites:")
    for name, spec in COMPOSITES.items():
        print(f"    {spec['name']:45s} = {' + '.join(spec['base_architectures'])}")
    print()
