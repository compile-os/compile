export interface CompileModule {
  id: number;
  role: 'source' | 'sink' | 'intermediary' | 'core';
  n_neurons: number;
  top_super_class: string;
  top_nt: string;
  top_group: string;
}

export interface EvolvablePair {
  pair: string;
  pre_module: number;
  post_module: number;
  n_synapses: number;
  best_delta: number;
  best_scale: number;
}

export interface Mutation {
  pre_module: number;
  post_module: number;
  accepted: boolean;
  delta: number;
  scale: number;
  n_synapses: number;
  seed: number;
  generation: number;
}

export interface FitnessSeed {
  seed: number;
  baseline_fitness: number;
  final_fitness: number;
  improvement: number;
  total_accepted: number;
  total_mutations: number;
}

export interface FitnessFunction {
  name: string;
  seeds: FitnessSeed[];
  evolvable_pairs: EvolvablePair[];
  all_mutations: Mutation[];
}

export interface OSLayerPair {
  src: number;
  tgt: number;
  functions: string[];
}

export interface AppLayerPair {
  src: number;
  tgt: number;
}

export interface HardwareStats {
  total_pairs: number;
  tested_pairs: number;
  evolvable_pairs: number;
  frozen_pairs: number;
  frozen_pct: number;
  irrelevant_pairs: number;
  irrelevant_pct: number;
}

export interface ThreeLayerMap {
  os_layer: OSLayerPair[];
  app_layer: Record<string, AppLayerPair[]>;
  hardware_stats: HardwareStats;
}

export interface EvolutionJob {
  id: string;
  fitness_function: string;
  seed: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: {
    current_generation: number;
    total_generations: number;
    current_fitness: number;
    accepted_count: number;
  };
  result?: FitnessFunction;
}

// Behavior colors used throughout the UI
export const BEHAVIOR_COLORS: Record<string, string> = {
  navigation: '#06b6d4',  // cyan
  escape: '#ef4444',      // red
  turning: '#22c55e',     // green
  arousal: '#f59e0b',     // amber
  efficiency: '#8b5cf6',  // violet
  inhibition: '#ec4899',  // pink
  circles: '#10b981',     // emerald
  rhythm: '#8b5cf6',      // violet
};

export const ROLE_COLORS: Record<string, string> = {
  source: '#06b6d4',      // cyan
  sink: '#ef4444',        // red
  intermediary: '#a855f7', // purple
  core: '#6b7280',        // gray
};

export interface InterferenceCell {
  compiled_for: string;
  tested_on: string;
  delta_pct: number;
  score: number;
  baseline: number;
}

export interface ProcessorSpec {
  id: string;
  name: string;
  method: 'module' | 'gene-guided';
  n_neurons: number;
  n_synapses: number;
  essential_modules: number[];
  hemilineages?: string[];
  behaviors_compiled: string[];
  behaviors_failed: string[];
  interference_matrix?: InterferenceCell[];
  compatible_pairs?: [string, string][];
  conflicting_pairs?: [string, string][];
}

export interface GrowthProgram {
  id: string;
  processor_id: string;
  cell_types: {
    hemilineage: string;
    count: number;
    proportion: number;
    neurotransmitter: string;
    spatial_centroid: [number, number, number];
  }[];
  connection_rules: {
    from_hemilineage: string;
    to_hemilineage: string;
    synapse_count: number;
    connection_probability: number;
    average_weight: number;
  }[];
  n_cell_types: number;
  n_connection_rules: number;
}

export interface Species {
  id: string;
  name: string;
  n_neurons: number;
  n_synapses: string;
  dataset: string;
  status: 'complete' | 'in_progress' | 'planned';
}
