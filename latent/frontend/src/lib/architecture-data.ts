// Auto-generated from architecture_specs.py + architecture_catalog.md
// Do not edit manually — regenerate from Python specs

export interface ArchitectureScores {
  navigation: number;
  escape: number;
  turning: number;
  conflict: number;
  workingMemory: number;
  total: number;
}

export interface Architecture {
  id: string;
  name: string;
  category: string;
  description: string;
  validated: boolean;
  calibrated?: boolean;
  cellTypeCount: number;
  connectionRuleCount: number;
  totalNeurons: number;
  spatialLayout: string;
  notes: string;
  tradeoffs: string[];
  bestFor: string[];
  source: string;
  scores?: ArchitectureScores;
}

// Experiment results: 26 architectures × 5 tasks, with synaptic depression (U=0.2, tau=800ms)
// All scores are evolved fitness (mean across 3 seeds, 50 generations)
export const ARCHITECTURE_SCORES: Record<string, ArchitectureScores> = {
  cellular_automaton: { navigation: 100.0, escape: 99.0, turning: 11.5, conflict: 10.0, workingMemory: 288.3, total: 508.8 },
  spiking_state_machine: { navigation: 69.0, escape: 67.7, turning: 8.3, conflict: 9.0, workingMemory: 197.3, total: 351.3 },
  winner_take_all: { navigation: 65.3, escape: 60.3, turning: 8.3, conflict: 11.7, workingMemory: 139.0, total: 284.7 },
  population_coding: { navigation: 40.0, escape: 42.0, turning: 6.2, conflict: 8.3, workingMemory: 114.7, total: 211.2 },
  evidence_accumulator: { navigation: 36.7, escape: 33.3, turning: 6.3, conflict: 8.0, workingMemory: 81.7, total: 166.0 },
  reservoir: { navigation: 21.7, escape: 25.0, turning: 6.6, conflict: 8.0, workingMemory: 53.7, total: 114.9 },
  subsumption: { navigation: 23.0, escape: 26.0, turning: 5.0, conflict: 11.0, workingMemory: 48.3, total: 113.3 },
  hierarchical_hub: { navigation: 22.0, escape: 19.7, turning: 4.3, conflict: 6.3, workingMemory: 50.0, total: 102.3 },
  recurrent_attractor: { navigation: 20.7, escape: 23.0, turning: 4.5, conflict: 7.3, workingMemory: 43.7, total: 99.2 },
  priority_queue: { navigation: 16.0, escape: 13.7, turning: 5.6, conflict: 10.0, workingMemory: 35.0, total: 80.3 },
  reward_modulated: { navigation: 15.0, escape: 13.3, turning: 4.6, conflict: 7.3, workingMemory: 35.0, total: 75.3 },
  neuromodulatory_gain: { navigation: 13.7, escape: 14.3, turning: 4.0, conflict: 6.3, workingMemory: 32.0, total: 70.3 },
  self_repairing: { navigation: 12.7, escape: 12.7, turning: 4.4, conflict: 8.0, workingMemory: 26.3, total: 64.0 },
  observer_controller: { navigation: 11.0, escape: 11.0, turning: 3.3, conflict: 6.3, workingMemory: 28.3, total: 60.0 },
  flat_distributed: { navigation: 23.0, escape: 22.3, turning: 3.8, conflict: 5.0, workingMemory: 0.0, total: 54.1 },
  bus: { navigation: 17.3, escape: 15.3, turning: 4.8, conflict: 4.7, workingMemory: 0.0, total: 42.2 },
  hebbian_assembly: { navigation: 9.3, escape: 8.3, turning: 2.8, conflict: 6.3, workingMemory: 15.3, total: 42.1 },
  ring: { navigation: 3.0, escape: 5.0, turning: 1.5, conflict: 5.3, workingMemory: 7.7, total: 22.5 },
  feedforward_pipeline: { navigation: 2.0, escape: 3.7, turning: 1.1, conflict: 2.0, workingMemory: 0.3, total: 9.1 },
  hyperdimensional: { navigation: 1.3, escape: 2.0, turning: 0.4, conflict: 2.7, workingMemory: 1.7, total: 8.0 },
  triple_redundancy: { navigation: 0.7, escape: 0.7, turning: 0.7, conflict: 1.7, workingMemory: 0.0, total: 3.7 },
  predictive_coding: { navigation: 0.7, escape: 1.0, turning: 0.4, conflict: 1.0, workingMemory: 0.3, total: 3.4 },
  dataflow: { navigation: 0.0, escape: 0.7, turning: 0.4, conflict: 0.7, workingMemory: 0.0, total: 1.7 },
  content_addressable: { navigation: 0.0, escape: 0.7, turning: 0.0, conflict: 1.0, workingMemory: 0.0, total: 1.7 },
  oscillatory: { navigation: 0.3, escape: 0.0, turning: 0.0, conflict: 0.3, workingMemory: 0.3, total: 1.0 },
  sparse_distributed_memory: { navigation: 0.0, escape: 0.0, turning: 0.0, conflict: 0.0, workingMemory: 0.0, total: 0.0 },
  hub_and_spoke: { navigation: 851.0, escape: 0.0, turning: 0.0, conflict: 0.0, workingMemory: 0.0, total: 851.0 },
};

export interface CompositeArchitecture {
  id: string;
  name: string;
  baseArchitectures: string[];
  description: string;
}

export const ARCHITECTURE_CATEGORIES = [
  { id: "routing", label: "Routing", description: "How information flows" },
  { id: "computation", label: "Computation", description: "How the circuit computes" },
  { id: "control", label: "Control", description: "How it decides what to do" },
  { id: "learning", label: "Learning", description: "How it adapts over time" },
  { id: "robustness", label: "Robustness", description: "How it handles damage" },
  { id: "exotic", label: "Exotic", description: "Novel designs biology never tried" },
] as const;

export const ARCHITECTURES: Architecture[] = [
  {
    "id": "hub_and_spoke",
    "name": "Hub-and-Spoke",
    "category": "routing",
    "description": "Biological default. 2 high-connectivity hubs gate motor output.",
    "validated": true,
    "calibrated": true,
    "cellTypeCount": 19,
    "connectionRuleCount": 7,
    "totalNeurons": 3000,
    "spatialLayout": "central_hubs_peripheral_sensory",
    "notes": "Reference implementation from FlyWire v783 connectome. Validated with sequential activity-dependent growth (851 nav score). Source of biological operating ranges used to calibrate all other architectures.",
    "tradeoffs": [
      "Precise behavioral control (tight hub gating)",
      "Requires larger perturbation scales to evolve",
      "Limited capacity (~10 behaviors before hub saturation)",
      "Single point of failure",
      "Minimal wiring cost"
    ],
    "bestFor": [
      "Decisive, fast action selection",
      "Reactive behavior",
      "Motor control"
    ],
    "source": "Fly (modules 4, 19), mouse (L5, L2/3), all known connectomes"
  },
  {
    "id": "cellular_automaton",
    "name": "Neuronal Cellular Automaton",
    "category": "exotic",
    "description": "Regular grid, local rules, emergent global behavior. #1 across all tasks (509 total). Simplest growth program.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 4,
    "connectionRuleCount": 4,
    "totalNeurons": 3000,
    "spatialLayout": "regular_3d_grid",
    "notes": "Highest scoring architecture across all 5 tasks. Grid topology with local connections. Simple developmental recipe.",
    "tradeoffs": [
      "Highest total score (509)",
      "Simplest growth program (4 cell types, 4 rules)",
      "Hard to predict emergent behavior",
      "Slow propagation across grid"
    ],
    "bestFor": [
      "Navigation",
      "Working memory",
      "General purpose"
    ],
    "source": "Conway Game of Life, Wolfram cellular automata"
  },
  {
    "id": "hierarchical_hub",
    "name": "Hierarchical Hub",
    "category": "routing",
    "description": "Multiple tiers of hubs. Tier 2 gates Tier 1. Mammalian strategy.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 16,
    "connectionRuleCount": 10,
    "totalNeurons": 3000,
    "spatialLayout": "layered_tiers_dorsal_ventral",
    "notes": "CALIBRATED. Tier 2 must grow AFTER Tier 1 so activity-dependent wiring biases tier2\u2192tier1 connections.",
    "tradeoffs": [
      "Dramatically more behavioral capacity",
      "Slower decision-making",
      "More complex growth program",
      "Enables cognitive control"
    ],
    "bestFor": [
      "Context-dependent action selection",
      "Working memory",
      "Planning"
    ],
    "source": "Thalamo-cortical loops, prefrontal gating of basal ganglia"
  },
  {
    "id": "flat_distributed",
    "name": "Flat/Distributed",
    "category": "routing",
    "description": "No hubs. Small-world topology. Robust but poor behavioral control.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 10,
    "connectionRuleCount": 5,
    "totalNeurons": 3000,
    "spatialLayout": "uniform_3d_grid",
    "notes": "CALIBRATED. Small-world: high local clustering + sparse random long-range connections. No node exceeds 2x average degree.",
    "tradeoffs": [
      "Robust to damage",
      "Poor behavioral control",
      "Slow convergence",
      "No gating bottleneck"
    ],
    "bestFor": [
      "Distributed sensing",
      "Swarm-like behavior",
      "Robustness over precision"
    ],
    "source": "Small-world networks, some invertebrate ganglia"
  },
  {
    "id": "bus",
    "name": "Bus Architecture",
    "category": "routing",
    "description": "Shared communication channel all modules read/write to.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "central_bus_lateral_modules",
    "notes": "CALIBRATED. Bus grows first. All modules wire to/from bus via activity-dependent growth.",
    "tradeoffs": [
      "Simple wiring",
      "Equal access for all modules",
      "Bandwidth-limited",
      "No inherent gating"
    ],
    "bestFor": [
      "Multi-module coordination",
      "Shared state awareness"
    ],
    "source": "Computer bus, insect ventral nerve cord features"
  },
  {
    "id": "ring",
    "name": "Ring Architecture",
    "category": "routing",
    "description": "Modules in a ring, each connects to neighbors. Token circulation.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 10,
    "connectionRuleCount": 7,
    "totalNeurons": 3000,
    "spatialLayout": "circular_2d",
    "notes": "CALIBRATED. Growth order follows ring sequence. Token cell type enables sequential activation.",
    "tradeoffs": [
      "Fair access",
      "Predictable timing",
      "Latency proportional to ring size",
      "Simple growth program"
    ],
    "bestFor": [
      "Sequential processing",
      "Rhythmic behaviors",
      "Central pattern generators"
    ],
    "source": "Token ring networks, annelid nervous systems"
  },
  {
    "id": "reservoir",
    "name": "Reservoir Computing",
    "category": "computation",
    "description": "Random recurrent core + trained readout. Simplest to grow.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 5,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "core_shell",
    "notes": "CALIBRATED. Core grows first randomly. Readout grows second with activity-dependent plasticity. Easiest architecture to grow \u2014 organoids already produce random recurrent connectivity.",
    "tradeoffs": [
      "Simple growth program for core",
      "Flexible (many readouts)",
      "Hard to get precise temporal control",
      "Can be chaotic"
    ],
    "bestFor": [
      "Pattern recognition",
      "Temporal sequence processing",
      "Classification"
    ],
    "source": "Echo state networks, liquid state machines"
  },
  {
    "id": "feedforward_pipeline",
    "name": "Feedforward Pipeline",
    "category": "computation",
    "description": "Layers of processing stages. No recurrence. Fast single-pass.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "stacked_layers_anterior_posterior",
    "notes": "CALIBRATED. Growth order MUST follow layer order. Each layer wires to the next based on activity from previous layer.",
    "tradeoffs": [
      "Fast (single pass)",
      "No memory",
      "Predictable latency",
      "Easy to analyze"
    ],
    "bestFor": [
      "Rapid sensory processing",
      "Feature extraction",
      "Reflexes"
    ],
    "source": "Retinal processing, early visual cortex (V1\u2192V2\u2192V4\u2192IT)"
  },
  {
    "id": "recurrent_attractor",
    "name": "Recurrent Attractor Network",
    "category": "computation",
    "description": "Strong recurrence creates stable attractor states. Natural memory.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 4,
    "connectionRuleCount": 5,
    "totalNeurons": 3000,
    "spatialLayout": "dense_central_cluster",
    "notes": "CALIBRATED. High recurrent connectivity is key. Winner-take-all dynamics from E/I balance. Best for working memory and decision making.",
    "tradeoffs": [
      "Natural memory (attractors persist)",
      "Pattern completion",
      "Limited capacity",
      "Slow switching"
    ],
    "bestFor": [
      "Working memory",
      "Decision-making",
      "State maintenance"
    ],
    "source": "Hopfield networks, hippocampal place cells"
  },
  {
    "id": "oscillatory",
    "name": "Oscillatory Computation",
    "category": "computation",
    "description": "E/I pairs at specific frequencies. Computation via phase relationships.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "dual_columns",
    "notes": "CALIBRATED. Frequency set by E/I loop time constants. Slow oscillators grow first to establish base rhythm. Hard to tune \u2014 sensitive to parameters.",
    "tradeoffs": [
      "Natural temporal coordination",
      "Multiplexing via frequencies",
      "Sensitive to parameter tuning",
      "Complex growth program"
    ],
    "bestFor": [
      "Temporal binding",
      "Attention",
      "Rhythm generation",
      "Motor patterns"
    ],
    "source": "Gamma oscillations in cortex, theta rhythms in hippocampus"
  },
  {
    "id": "predictive_coding",
    "name": "Predictive Coding",
    "category": "computation",
    "description": "Paired prediction/error layers. Minimizes surprise. Adaptive.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "layered_anterior_posterior",
    "notes": "CALIBRATED. Level 1 grows first. Level 2 grows on top with activity-dependent connections. Top-down predictions emerge from learning.",
    "tradeoffs": [
      "Adaptive (learns environment)",
      "Efficient (transmits only errors)",
      "Complex growth program",
      "Slow initial learning"
    ],
    "bestFor": [
      "Sensory processing in changing environments",
      "Adaptation",
      "Learning"
    ],
    "source": "Karl Friston free energy principle, Rao & Ballard"
  },
  {
    "id": "sparse_distributed_memory",
    "name": "Sparse Distributed Memory",
    "category": "computation",
    "description": "Massive sparse layer for pattern storage. Cerebellar analog.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 6,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "layered_cerebellar",
    "notes": "CALIBRATED. Granule cells are 60% of the circuit. Each input activates ~4 random granule cells (like biological cerebellum). Massive capacity.",
    "tradeoffs": [
      "Massive capacity",
      "Content-addressable",
      "Robust to noise",
      "Requires many neurons"
    ],
    "bestFor": [
      "Associative memory",
      "Pattern storage and retrieval",
      "Motor learning"
    ],
    "source": "Pentti Kanerva SDM, cerebellar granule cell layer"
  },
  {
    "id": "observer_controller",
    "name": "Observer-Controller Separation",
    "category": "control",
    "description": "Separate state estimation from action selection. Clean modularity.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "two_regions_with_bridge",
    "notes": "CALIBRATED. Observer and controller are spatially separated. Interface is a narrow bridge. Observer can be complex without slowing the controller.",
    "tradeoffs": [
      "Clean modularity",
      "Easy to swap controllers",
      "Requires well-defined interface"
    ],
    "bestFor": [
      "Complex sensory environments",
      "Robotics-style applications"
    ],
    "source": "Modern control theory, Kalman filters"
  },
  {
    "id": "winner_take_all",
    "name": "Winner-Take-All",
    "category": "control",
    "description": "Competing modules with lateral inhibition. One winner.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 5,
    "totalNeurons": 3000,
    "spatialLayout": "symmetric_quadrants",
    "notes": "CALIBRATED. Symmetric architecture. Self-excitation + global inhibition = winner suppresses all others. Growth order doesn't matter (symmetric).",
    "tradeoffs": [
      "Fast, clean decisions",
      "Only one action at a time",
      "Hard to reverse decisions"
    ],
    "bestFor": [
      "Action selection",
      "Categorical decisions"
    ],
    "source": "Lateral inhibition in retina, decision-making circuits in LIP"
  },
  {
    "id": "evidence_accumulator",
    "name": "Evidence Accumulator",
    "category": "control",
    "description": "Drift-diffusion. Accumulate evidence, threshold triggers action.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 6,
    "connectionRuleCount": 11,
    "totalNeurons": 3000,
    "spatialLayout": "bilateral_symmetric",
    "notes": "CALIBRATED. Two accumulators race. First to threshold wins. Speed-accuracy tradeoff set by threshold neuron properties.",
    "tradeoffs": [
      "Handles noisy evidence",
      "Speed-accuracy tradeoff built in",
      "Slower than WTA"
    ],
    "bestFor": [
      "Perceptual decisions under uncertainty",
      "Deliberation"
    ],
    "source": "Gold & Shadlen drift-diffusion model"
  },
  {
    "id": "priority_queue",
    "name": "Priority Queue",
    "category": "control",
    "description": "Multiple actions maintained with dynamic priority. Urgency-gated.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 8,
    "totalNeurons": 3000,
    "spatialLayout": "radial_actions_central_gate",
    "notes": "CALIBRATED. Dopaminergic urgency signal modulates all actions globally. Priority tag provides context-dependent weighting.",
    "tradeoffs": [
      "Flexible dynamic scheduling",
      "Handles concurrent goals",
      "More complex growth program"
    ],
    "bestFor": [
      "Complex behavioral scheduling",
      "Foraging",
      "Multiple concurrent goals"
    ],
    "source": "Cisek & Kalaska affordance competition, basal ganglia"
  },
  {
    "id": "subsumption",
    "name": "Subsumption Architecture",
    "category": "control",
    "description": "Layered behaviors. Higher suppresses lower. Lower can override for safety.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 22,
    "totalNeurons": 3000,
    "spatialLayout": "stacked_layers_ventral_dorsal",
    "notes": "CALIBRATED from FlyWire v783. Layer 0 grows first (survival reflexes). Higher layers grow on top. Suppression connections grow with the higher layer. Emergency bypass is hardwired.",
    "tradeoffs": [
      "No central bottleneck",
      "Reactive and fast",
      "Limited complex cognition"
    ],
    "bestFor": [
      "Insect-scale behavior",
      "Simple robots",
      "Fast reflexes"
    ],
    "source": "Rodney Brooks behavior-based robotics"
  },
  {
    "id": "hebbian_assembly",
    "name": "Hebbian Assembly",
    "category": "learning",
    "description": "Fire together, wire together. Self-organizing from experience.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 4,
    "connectionRuleCount": 5,
    "totalNeurons": 3000,
    "spatialLayout": "uniform_3d",
    "notes": "CALIBRATED. Initial connectivity is broad and weak. STDP plasticity rules strengthen co-activated connections. Assemblies emerge from experience.",
    "tradeoffs": [
      "Self-organizing",
      "No external training needed",
      "Can be unstable",
      "Capacity limited"
    ],
    "bestFor": [
      "Associative learning",
      "Memory formation",
      "Sensory map formation"
    ],
    "source": "Hebb cell assembly theory, cortical engrams"
  },
  {
    "id": "reward_modulated",
    "name": "Reward-Modulated Architecture",
    "category": "learning",
    "description": "Base circuit + dopaminergic reward signal gates plasticity.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 6,
    "connectionRuleCount": 7,
    "totalNeurons": 3000,
    "spatialLayout": "base_circuit_with_modulatory_overlay",
    "notes": "CALIBRATED. Base circuit grows first. Dopaminergic overlay grows second. Three-factor plasticity: pre \u00d7 post \u00d7 dopamine.",
    "tradeoffs": [
      "Learns from outcomes",
      "Can learn arbitrary mappings",
      "Requires reward signal",
      "Slower than Hebbian"
    ],
    "bestFor": [
      "Goal-directed learning",
      "Behavioral shaping"
    ],
    "source": "Dopaminergic reward prediction error, basal ganglia RL"
  },
  {
    "id": "neuromodulatory_gain",
    "name": "Neuromodulatory Gain Control",
    "category": "learning",
    "description": "Multiple modulatory systems shift circuit operating mode.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "base_circuit_with_modulatory_nuclei",
    "notes": "CALIBRATED. Three distinct neuromodulatory systems. Each uses a different NT. Base circuit grows first. Modulatory overlay grows second.",
    "tradeoffs": [
      "Dramatic behavioral flexibility",
      "Few additional cell types",
      "Complex to tune"
    ],
    "bestFor": [
      "Behavioral state switching",
      "Emotional regulation",
      "Sleep/wake"
    ],
    "source": "Serotonin, norepinephrine, acetylcholine systems"
  },
  {
    "id": "triple_redundancy",
    "name": "Triple Modular Redundancy",
    "category": "robustness",
    "description": "Three copies of critical circuit. Majority voting. Survives single failure.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 8,
    "totalNeurons": 3000,
    "spatialLayout": "three_spatial_copies_central_voter",
    "notes": "CALIBRATED. Three spatially separated copies. Voter activates when 2+ copies agree. Single copy failure = continued operation.",
    "tradeoffs": [
      "Survives single-point failures",
      "3x hub neuron cost",
      "Voting adds latency"
    ],
    "bestFor": [
      "Safety-critical applications",
      "Brain repair"
    ],
    "source": "Fault-tolerant computing, space shuttle avionics"
  },
  {
    "id": "population_coding",
    "name": "Graceful Degradation",
    "category": "robustness",
    "description": "Information encoded across population. Degrades proportionally, not catastrophically.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 5,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "uniform_3d",
    "notes": "CALIBRATED. No individual neuron is critical. Losing 10% of neurons degrades performance ~10%. Readout averages across population.",
    "tradeoffs": [],
    "bestFor": [],
    "source": ""
  },
  {
    "id": "self_repairing",
    "name": "Self-Repairing Architecture",
    "category": "robustness",
    "description": "Uncommitted progenitor cells differentiate on demand to replace damage.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 6,
    "connectionRuleCount": 7,
    "totalNeurons": 3000,
    "spatialLayout": "functional_core_progenitor_periphery",
    "notes": "CALIBRATED. Speculative. Progenitor cells remain undifferentiated. When damage_sensor detects activity loss, progenitors differentiate and wire in. Adult neurogenesis analog.",
    "tradeoffs": [
      "Self-healing",
      "Requires progenitor cells",
      "Repair is slow",
      "Repaired circuit may differ"
    ],
    "bestFor": [
      "Long-duration implants",
      "Brain repair tissue"
    ],
    "source": "Axonal sprouting, cortical remapping after stroke"
  },
  {
    "id": "content_addressable",
    "name": "Content-Addressable Memory",
    "category": "exotic",
    "description": "Biological hash table. Random projection to sparse code. O(1) retrieval.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 7,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "layered_hash_pipeline",
    "notes": "CALIBRATED. Random projection is the hash function. Doesn't need to be learned. Sparse code is ~1% active per input.",
    "tradeoffs": [],
    "bestFor": [],
    "source": ""
  },
  {
    "id": "dataflow",
    "name": "Dataflow Architecture",
    "category": "exotic",
    "description": "No central clock. Modules fire when inputs are ready. Data-driven execution.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 9,
    "totalNeurons": 3000,
    "spatialLayout": "directed_graph_layout",
    "notes": "CALIBRATED. Each node fires only when sufficient inputs arrive. No global timing. Naturally parallel.",
    "tradeoffs": [
      "Naturally parallel",
      "No timing bottleneck",
      "Hard to debug",
      "Hard for sequential logic"
    ],
    "bestFor": [
      "Sensory processing pipelines",
      "Parallel feature extraction"
    ],
    "source": "Dataflow computing, Kahn process networks"
  },
  {
    "id": "hyperdimensional",
    "name": "Hyperdimensional Computing",
    "category": "exotic",
    "description": "High-dimensional random vectors. Binding, bundling, permutation. Noise-tolerant.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 6,
    "connectionRuleCount": 7,
    "totalNeurons": 3000,
    "spatialLayout": "large_flat_population",
    "notes": "CALIBRATED. Large population = more dimensions = more noise tolerance. Random initial encoding is fine \u2014 high-dim random vectors are nearly orthogonal.",
    "tradeoffs": [
      "Robust to noise and damage",
      "Elegant algebraic operations",
      "Approximate, not exact",
      "Large populations needed"
    ],
    "bestFor": [
      "Symbolic reasoning in neural substrate",
      "Analogy",
      "Language-like composition"
    ],
    "source": "Pentti Kanerva, Tony Plate holographic reduced representations"
  },
  {
    "id": "spiking_state_machine",
    "name": "Spiking Neural State Machine",
    "category": "exotic",
    "description": "Discrete states in neural populations. Transitions triggered by input.",
    "validated": false,
    "calibrated": true,
    "cellTypeCount": 8,
    "connectionRuleCount": 6,
    "totalNeurons": 3000,
    "spatialLayout": "symmetric_clusters",
    "notes": "CALIBRATED. Exactly one state active at a time. Transitions are deterministic given input + current state. Verifiable behavior.",
    "tradeoffs": [
      "Predictable, verifiable",
      "Simple to analyze",
      "Limited to finite states",
      "Cannot represent continuous values"
    ],
    "bestFor": [
      "Protocol execution",
      "Safety-critical state transitions"
    ],
    "source": "Finite state machines in spiking networks"
  }
];

export const COMPOSITES: CompositeArchitecture[] = [
  {
    "id": "reservoir_hub_readout",
    "name": "Reservoir + Hub Readout",
    "baseArchitectures": [
      "reservoir",
      "hub_and_spoke"
    ],
    "description": "Reservoir core for rich dynamics. Hub readout for precise behavioral control."
  },
  {
    "id": "hierarchical_predictive",
    "name": "Hierarchical Hub + Predictive Coding",
    "baseArchitectures": [
      "hierarchical_hub",
      "predictive_coding"
    ],
    "description": "Each hub tier implements predictive coding. Deep generative model with behavioral control."
  },
  {
    "id": "subsumption_reward",
    "name": "Subsumption + Reward Modulation",
    "baseArchitectures": [
      "subsumption",
      "reward_modulated"
    ],
    "description": "Layered reactive behaviors with reward-modulated learning on higher layers."
  },
  {
    "id": "observer_accumulator",
    "name": "Observer-Controller + Evidence Accumulator",
    "baseArchitectures": [
      "observer_controller",
      "evidence_accumulator"
    ],
    "description": "Observer estimates state. Controller uses drift-diffusion for decisions under uncertainty."
  },
  {
    "id": "oscillatory_wta",
    "name": "Oscillatory + Winner-Take-All",
    "baseArchitectures": [
      "oscillatory",
      "winner_take_all"
    ],
    "description": "WTA circuits at multiple frequencies. Cross-frequency coupling for multi-scale decisions."
  }
];
