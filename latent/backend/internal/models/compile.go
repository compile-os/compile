package models

// CompileData is the top-level structure for the compile platform JSON
type CompileData struct {
	FitnessFunctions map[string]FitnessFunction `json:"fitness_functions"`
	Modules          map[string]Module_         `json:"modules"`
	ThreeLayerMap    ThreeLayerMap              `json:"three_layer_map"`
}

// FitnessFunction represents a single fitness function with its evolution data
type FitnessFunction struct {
	Seeds          []Seed          `json:"seeds"`
	EvolvablePairs []EvolvablePair `json:"evolvable_pairs"`
	AllMutations   []Mutation      `json:"all_mutations"`
}

// Seed represents a single seed run for a fitness function
type Seed struct {
	Seed            int     `json:"seed"`
	BaselineFitness float64 `json:"baseline_fitness"`
	FinalFitness    float64 `json:"final_fitness"`
	Improvement     float64 `json:"improvement"`
	TotalAccepted   int     `json:"total_accepted"`
	TotalMutations  int     `json:"total_mutations"`
}

// EvolvablePair is a module connection pair that improved fitness
type EvolvablePair struct {
	Pair       string  `json:"pair"`
	PreModule  int     `json:"pre_module"`
	PostModule int     `json:"post_module"`
	NSynapses  int     `json:"n_synapses"`
	BestDelta  float64 `json:"best_delta"`
	BestScale  float64 `json:"best_scale"`
}

// Mutation represents a single mutation attempt during evolution
type Mutation struct {
	PreModule  int     `json:"pre_module"`
	PostModule int     `json:"post_module"`
	Accepted   bool    `json:"accepted"`
	Delta      float64 `json:"delta"`
	Scale      float64 `json:"scale"`
	NSynapses  int     `json:"n_synapses"`
	Seed       int     `json:"seed"`
	Generation int     `json:"generation"`
}

// Module_ represents a single neural module in the connectome
// Named Module_ to avoid conflict with the existing Model type
type Module_ struct {
	Role          string `json:"role"`
	NNeurons      int    `json:"n_neurons"`
	TopSuperClass string `json:"top_super_class"`
	TopNT         string `json:"top_nt"`
	TopGroup      string `json:"top_group"`
}

// ThreeLayerMap classifies connections into OS, App, and Hardware layers
type ThreeLayerMap struct {
	OSLayer       []OSConnection           `json:"os_layer"`
	AppLayer      map[string][]AppConnection `json:"app_layer"`
	HardwareStats HardwareStats            `json:"hardware_stats"`
}

// OSConnection is a connection in the operating-system layer
type OSConnection struct {
	Src       int      `json:"src"`
	Tgt       int      `json:"tgt"`
	Functions []string `json:"functions"`
}

// AppConnection is a connection in the application layer
type AppConnection struct {
	Src int `json:"src"`
	Tgt int `json:"tgt"`
}

// HardwareStats summarises the frozen/evolvable/irrelevant breakdown
type HardwareStats struct {
	TotalPairs     int     `json:"total_pairs"`
	TestedPairs    int     `json:"tested_pairs"`
	EvolvablePairs int     `json:"evolvable_pairs"`
	FrozenPairs    int     `json:"frozen_pairs"`
	FrozenPct      float64 `json:"frozen_pct"`
	IrrelevantPairs int    `json:"irrelevant_pairs"`
	IrrelevantPct  float64 `json:"irrelevant_pct"`
}

// EvolutionJobRequest is the request body for creating a new evolution job
type EvolutionJobRequest struct {
	FitnessFunction string `json:"fitness_function" binding:"required"`
	Seed            int    `json:"seed"`
	Generations     int    `json:"generations"`
	MutationsPerGen int    `json:"mutations_per_gen"`
	Architecture    string `json:"architecture"`
}

// EvolutionJob tracks the state of an evolution job
type EvolutionJob struct {
	ID              string                 `json:"id"`
	UserID          string                 `json:"user_id,omitempty"`
	FitnessFunction string                 `json:"fitness_function"`
	Seed            int                    `json:"seed"`
	Generations     int                    `json:"generations"`
	MutationsPerGen int                    `json:"mutations_per_gen"`
	Status          string                 `json:"status"` // pending, running, completed, failed
	Progress        int                    `json:"progress"`
	CurrentFitness  float64                `json:"current_fitness,omitempty"`
	AcceptedCount   int                    `json:"accepted_count,omitempty"`
	Result          map[string]interface{} `json:"result,omitempty"`
	Error           string                 `json:"error,omitempty"`
	WorkerJobID     string                 `json:"worker_job_id,omitempty"`
	CreatedAt       string                 `json:"created_at"`
	UpdatedAt       string                 `json:"updated_at"`
	CompletedAt     string                 `json:"completed_at,omitempty"`
	Architecture    string                 `json:"architecture,omitempty"`
}

// Architecture represents a neural circuit architecture from the catalog.
type Architecture struct {
	ID                  string   `json:"id"`
	Name                string   `json:"name"`
	Category            string   `json:"category"`
	Description         string   `json:"description"`
	Validated           bool     `json:"validated"`
	CellTypeCount       int      `json:"cell_type_count"`
	ConnectionRuleCount int      `json:"connection_rule_count"`
	TotalNeurons        int      `json:"total_neurons"`
	SpatialLayout       string   `json:"spatial_layout"`
	Tradeoffs           []string `json:"tradeoffs"`
	BestFor             []string `json:"best_for"`
	Source              string   `json:"source"`
}
