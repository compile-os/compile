package services

import (
	"encoding/json"
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/latent-labs/latent-api/internal/db"
	"github.com/latent-labs/latent-api/internal/models"
)

// CompiledBehavior represents a behavior that has been compiled through the pipeline.
type CompiledBehavior struct {
	ID              string  `json:"id"`
	Label           string  `json:"label"`
	Description     string  `json:"description"`
	Category        string  `json:"category"`
	Improvement     string  `json:"improvement"`
	ImprovementPct  float64 `json:"improvement_pct"`
	Edges           int     `json:"edges"`
	AcceptedCount   int     `json:"accepted_count"`
	CapabilityFamily string `json:"capability_family"`
	IsPrecomputed   bool    `json:"is_precomputed"`
}

// PostProcessResult contains the full deterministic analysis after a job completes.
// Structured so an AI enrichment layer can read it and generate insights.
type PostProcessResult struct {
	Behavior       CompiledBehavior `json:"behavior"`

	// Interference analysis (deterministic — edge overlap computation)
	CompatibleWith []string                `json:"compatible_with"`
	ConflictsWith  []string                `json:"conflicts_with"`
	Interference   []InterferenceEntry     `json:"interference"`

	// Hub analysis (deterministic — which modules this behavior uses)
	HubModules       []int   `json:"hub_modules"`
	HubSaturation    float64 `json:"hub_saturation"` // 0-1, how much of hub capacity this uses

	// Evolution trajectory (deterministic — from the result JSON)
	Baseline       float64 `json:"baseline"`
	FinalFitness   float64 `json:"final_fitness"`
	ImprovementPct float64 `json:"improvement_pct"`
	EdgesEvolvable int     `json:"edges_evolvable"`
	EdgesFrozen    int     `json:"edges_frozen"`
	TotalMutations int     `json:"total_mutations"`
	AcceptedCount  int     `json:"accepted_count"`
	AcceptanceRate float64 `json:"acceptance_rate"`

	// Edge classification (deterministic — from edge_classification in result)
	EvolvableEdges []string `json:"evolvable_edges"` // e.g. ["19->4", "4->3"]
	FrozenEdges    []string `json:"frozen_edges"`

	// Classification (deterministic for known fitness functions, needs persistence test for unknown)
	Category         string `json:"category"`          // "reactive" or "cognitive"
	ClassificationMethod string `json:"classification_method"` // "fitness_function_name" or "persistence_test"

	// Raw data reference (for AI enrichment layer to access later)
	JobID          string `json:"job_id"`
	Timestamp      string `json:"timestamp"`
}

// InterferenceEntry shows how this behavior affects one existing behavior.
type InterferenceEntry struct {
	BehaviorID   string  `json:"behavior_id"`
	OverlapEdges int     `json:"overlap_edges"`
	OverlapPct   float64 `json:"overlap_pct"` // % of the other behavior's edges that overlap
	IsConflict   bool    `json:"is_conflict"` // overlap > 30%
}

// BehaviorLibrary stores all compiled behaviors (precomputed + user-contributed).
type BehaviorLibrary struct {
	mu        sync.RWMutex
	behaviors map[string]*CompiledBehavior
}

var behaviorLib = &BehaviorLibrary{
	behaviors: make(map[string]*CompiledBehavior),
}

// InitBehaviorLibraryFromCompileData seeds the behavior library and edge store
// from the loaded compile platform data. This is the SINGLE source of truth.
// Called once at startup after CompileDataService is initialized.
func InitBehaviorLibraryFromCompileData() {
	svc := GetCompileData()
	if svc == nil {
		log.Println("BehaviorLibrary: no compile data, library empty")
		return
	}

	lib := GetBehaviorLibrary()
	lib.mu.Lock()
	defer lib.mu.Unlock()

	edgeStoreMu.Lock()
	defer edgeStoreMu.Unlock()

	ffs := svc.GetFitnessFunctions()
	for name, ff := range ffs {
		// Compute improvement from first seed
		improvementPct := 0.0
		if len(ff.Seeds) > 0 {
			improvementPct = ff.Seeds[0].Improvement / max(ff.Seeds[0].BaselineFitness, 0.001) * 100
		}

		// Build edge set
		edges := make(map[string]bool)
		for _, ep := range ff.EvolvablePairs {
			edges[ep.Pair] = true
		}
		edgeStore[name] = edges

		lib.behaviors[name] = &CompiledBehavior{
			ID:              name,
			Label:           behaviorLabel(name),
			Description:     behaviorDescription(name),
			Category:        behaviorCategory(name),
			Improvement:     formatImprovement(improvementPct),
			ImprovementPct:  improvementPct,
			Edges:           len(ff.EvolvablePairs),
			AcceptedCount:   countAccepted(ff),
			CapabilityFamily: behaviorFamily(name),
			IsPrecomputed:   true,
		}
	}

	log.Printf("BehaviorLibrary: loaded %d behaviors from compile data", len(lib.behaviors))

	// Also load completed jobs from the database (user-compiled behaviors)
	dbPool := db.Get()
	if dbPool != nil {
		rows, err := dbPool.Query(`
			SELECT fitness_function, result FROM evolution_jobs
			WHERE status = 'completed' AND result IS NOT NULL
		`)
		if err == nil {
			defer rows.Close()
			dbCount := 0
			for rows.Next() {
				var fitnessFunc string
				var resultJSON json.RawMessage
				if err := rows.Scan(&fitnessFunc, &resultJSON); err != nil {
					continue
				}
				// Skip if already loaded from compile data
				if _, exists := lib.behaviors[fitnessFunc]; exists {
					continue
				}
				// Post-process to add to library (without lock since we hold it)
				var data map[string]interface{}
				if err := json.Unmarshal(resultJSON, &data); err != nil {
					continue
				}
				improvementPct := 0.0
				if v, ok := data["improvement_pct"].(float64); ok {
					improvementPct = v
				}
				edges := extractEvolvableEdges(data)
				edgeStore[fitnessFunc] = edges
				lib.behaviors[fitnessFunc] = &CompiledBehavior{
					ID:              fitnessFunc,
					Label:           fitnessFunc,
					Description:     "User-compiled behavior",
					Category:        "reactive",
					Improvement:     formatImprovement(improvementPct),
					ImprovementPct:  improvementPct,
					Edges:           len(edges),
					CapabilityFamily: "reactive_motor",
					IsPrecomputed:   false,
				}
				dbCount++
			}
			if dbCount > 0 {
				log.Printf("BehaviorLibrary: loaded %d behaviors from database", dbCount)
			}
		}
	}
}

// Derived metadata — the compile data has the numbers, these provide human-readable labels.
// If a behavior isn't in these maps, it gets a default based on its ID.

func behaviorLabel(id string) string {
	labels := map[string]string{
		"navigation": "Navigation", "escape": "Escape", "turning": "Turning",
		"arousal": "Arousal", "circles": "Circular Locomotion", "rhythm": "Rhythmic Alternation",
	}
	if l, ok := labels[id]; ok {
		return l
	}
	return id
}

func behaviorDescription(id string) string {
	descs := map[string]string{
		"navigation": "Forward locomotion toward food via P9 motor neurons.",
		"escape":     "Ballistic escape via Giant Fiber pathway.",
		"turning":    "Sustained turning via asymmetric DNa01/DNa02.",
		"arousal":    "Sensory gain control through visual module gating.",
		"circles":    "Sustained circular walking.",
		"rhythm":     "Walk-stop alternation pattern.",
	}
	if d, ok := descs[id]; ok {
		return d
	}
	return "Compiled behavior"
}

func behaviorCategory(id string) string {
	cognitive := map[string]bool{"conflict_resolution": true, "working_memory": true, "attention": true}
	if cognitive[id] {
		return "cognitive"
	}
	return "reactive"
}

func behaviorFamily(id string) string {
	families := map[string]string{
		"conflict_resolution": "state_maintenance",
		"working_memory":      "state_maintenance",
		"attention":           "selective_gating",
	}
	if f, ok := families[id]; ok {
		return f
	}
	return "reactive_motor"
}

func countAccepted(ff models.FitnessFunction) int {
	total := 0
	for _, s := range ff.Seeds {
		total += s.TotalAccepted
	}
	return total
}

func max(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// GetBehaviorLibrary returns the global behavior library.
func GetBehaviorLibrary() *BehaviorLibrary {
	return behaviorLib
}

// GetAll returns all compiled behaviors.
func (lib *BehaviorLibrary) GetAll() []CompiledBehavior {
	lib.mu.RLock()
	defer lib.mu.RUnlock()
	result := make([]CompiledBehavior, 0, len(lib.behaviors))
	for _, b := range lib.behaviors {
		result = append(result, *b)
	}
	return result
}

// Get returns a single behavior by ID.
func (lib *BehaviorLibrary) Get(id string) (*CompiledBehavior, bool) {
	lib.mu.RLock()
	defer lib.mu.RUnlock()
	b, ok := lib.behaviors[id]
	return b, ok
}

// PostProcessJobResult analyzes a completed evolution job and adds the behavior to the library.
func PostProcessJobResult(fitnessFunction string, result json.RawMessage) *PostProcessResult {
	var data map[string]interface{}
	if err := json.Unmarshal(result, &data); err != nil {
		log.Printf("PostProcess: failed to parse result: %v", err)
		return nil
	}

	// Extract all numeric fields from the evolution result
	getFloat := func(key string) float64 {
		if v, ok := data[key].(float64); ok { return v }
		return 0
	}
	getInt := func(key string) int {
		if v, ok := data[key].(float64); ok { return int(v) }
		return 0
	}

	baseline := getFloat("baseline")
	finalFitness := getFloat("final_fitness")
	improvementPct := getFloat("improvement_pct")
	accepted := getInt("accepted")
	totalMutations := getInt("total_mutations")
	_ = getInt("edges_tested") // used indirectly via len(newEdges)

	// Extract edge classifications
	newEdges := extractEvolvableEdges(data)
	evolvableEdgeList := make([]string, 0, len(newEdges))
	for e := range newEdges {
		evolvableEdgeList = append(evolvableEdgeList, e)
	}

	frozenEdges := extractFrozenEdges(data)
	frozenEdgeList := make([]string, 0, len(frozenEdges))
	for e := range frozenEdges {
		frozenEdgeList = append(frozenEdgeList, e)
	}

	// Determine category deterministically from fitness function name
	// Known cognitive behaviors are identified by their fitness function definition
	// (they require persistent CX activity). Unknown behaviors default to reactive
	// and can be reclassified after a persistence test is run.
	// Determine category: check result (from persistence test or AI), fall back to name-based
	category := behaviorCategory(fitnessFunction)
	classificationMethod := "fitness_function_name"
	if cat, ok := data["category"].(string); ok && cat != "" {
		category = cat
		classificationMethod = "persistence_test"
	}
	if tag, ok := data["behavior_tag"].(string); ok && tag != "" {
		category = tag
		classificationMethod = "ai_classification"
	}

	// Acceptance rate
	acceptanceRate := 0.0
	if totalMutations > 0 {
		acceptanceRate = float64(accepted) / float64(totalMutations)
	}

	behavior := CompiledBehavior{
		ID:               fitnessFunction,
		Label:            behaviorLabel(fitnessFunction),
		Description:      fmt.Sprintf("Compiled: %.1f%% improvement, %d evolvable edges, %d mutations accepted", improvementPct, len(newEdges), accepted),
		Category:         category,
		Improvement:      formatImprovement(improvementPct),
		ImprovementPct:   improvementPct,
		Edges:            len(newEdges),
		AcceptedCount:    accepted,
		CapabilityFamily: behaviorFamily(fitnessFunction),
		IsPrecomputed:    false,
	}

	// Add to library
	lib := GetBehaviorLibrary()
	lib.mu.Lock()
	lib.behaviors[fitnessFunction] = &behavior
	lib.mu.Unlock()

	// Store edges for future interference computation
	RegisterBehaviorEdges(fitnessFunction, newEdges)

	// Compute detailed interference with every existing behavior
	compatible, conflicts, interferenceEntries, hubs, hubSaturation := computeDetailedInterference(fitnessFunction, newEdges)

	now := time.Now().Format(time.RFC3339)

	ppr := &PostProcessResult{
		Behavior:       behavior,
		CompatibleWith: compatible,
		ConflictsWith:  conflicts,
		Interference:   interferenceEntries,
		HubModules:     hubs,
		HubSaturation:  hubSaturation,

		Baseline:       baseline,
		FinalFitness:   finalFitness,
		ImprovementPct: improvementPct,
		EdgesEvolvable: len(newEdges),
		EdgesFrozen:    len(frozenEdges),
		TotalMutations: totalMutations,
		AcceptedCount:  accepted,
		AcceptanceRate: acceptanceRate,

		EvolvableEdges: evolvableEdgeList,
		FrozenEdges:    frozenEdgeList,

		Category:              category,
		ClassificationMethod:  classificationMethod,

		Timestamp: now,
	}

	// Persist the full analysis to the database for future AI enrichment
	if dbPool := db.Get(); dbPool != nil {
		analysisJSON, err := json.Marshal(ppr)
		if err == nil {
			_, _ = dbPool.Exec(`
				UPDATE evolution_jobs SET result = result || jsonb_build_object('analysis', $2::jsonb)
				WHERE fitness_function = $1 AND status = 'completed'
				ORDER BY created_at DESC LIMIT 1
			`, fitnessFunction, string(analysisJSON))
		}
	}

	log.Printf("PostProcess: %q — %.1f%% improvement, %d evolvable/%d frozen edges, %d compatible/%d conflicts, hub_saturation=%.2f, category=%s",
		fitnessFunction, improvementPct, len(newEdges), len(frozenEdges), len(compatible), len(conflicts), hubSaturation, category)

	return ppr
}

func formatImprovement(pct float64) string {
	if pct > 0 {
		return fmt.Sprintf("+%.1f%%", pct)
	}
	return fmt.Sprintf("%.1f%%", pct)
}

// extractEvolvableEdges pulls the set of evolvable edge keys from the result JSON.
func extractEvolvableEdges(data map[string]interface{}) map[string]bool {
	edges := make(map[string]bool)
	ec, ok := data["edge_classification"]
	if !ok {
		return edges
	}
	ecMap, ok := ec.(map[string]interface{})
	if !ok {
		return edges
	}
	for edgeKey, info := range ecMap {
		infoMap, ok := info.(map[string]interface{})
		if !ok {
			continue
		}
		if accepted, ok := infoMap["accepted"].(float64); ok && accepted > 0 {
			edges[edgeKey] = true
		}
	}
	return edges
}

// edgeStore holds evolvable edges per behavior — populated from compile data on startup
// and extended by every playground run.
var (
	edgeStoreMu sync.RWMutex
	edgeStore   = make(map[string]map[string]bool) // behavior_id -> set of "src->tgt" edges
)


// RegisterBehaviorEdges stores evolvable edges from a completed playground run.
func RegisterBehaviorEdges(behaviorID string, edges map[string]bool) {
	edgeStoreMu.Lock()
	defer edgeStoreMu.Unlock()
	edgeStore[behaviorID] = edges
	log.Printf("EdgeStore: registered %d edges for %q", len(edges), behaviorID)
}

// extractFrozenEdges pulls frozen edges from the result's edge_classification.
func extractFrozenEdges(data map[string]interface{}) map[string]bool {
	edges := make(map[string]bool)
	ec, ok := data["edge_classification"]
	if !ok {
		return edges
	}
	ecMap, ok := ec.(map[string]interface{})
	if !ok {
		return edges
	}
	for edgeKey, info := range ecMap {
		infoMap, ok := info.(map[string]interface{})
		if !ok {
			continue
		}
		accepted, _ := infoMap["accepted"].(float64)
		decreased, _ := infoMap["decreased"].(float64)
		total := accepted + decreased
		if accepted == 0 && total > 0 && decreased/total > 0.5 {
			edges[edgeKey] = true
		}
	}
	return edges
}

// computeDetailedInterference returns rich interference data for every existing behavior.
func computeDetailedInterference(newBehaviorID string, newEdges map[string]bool) (
	compatible []string, conflicts []string, entries []InterferenceEntry, hubs []int, hubSaturation float64,
) {
	// Discover hubs from data: count how many behaviors each module participates in
	// A "hub" is any module that appears in evolvable edges across multiple behaviors
	moduleParticipation := make(map[int]int) // module_id -> count of behaviors using it

	edgeStoreMu.RLock()
	defer edgeStoreMu.RUnlock()

	for _, existingEdges := range edgeStore {
		seen := make(map[int]bool)
		for edge := range existingEdges {
			parts := splitEdge(edge)
			if !seen[parts[0]] {
				seen[parts[0]] = true
				moduleParticipation[parts[0]]++
			}
			if !seen[parts[1]] {
				seen[parts[1]] = true
				moduleParticipation[parts[1]]++
			}
		}
	}

	// Modules that appear in >50% of behaviors are hubs
	behaviorCount := len(edgeStore)
	hubThreshold := max(float64(behaviorCount)*0.5, 2) // at least 2 behaviors
	hubSet := make(map[int]bool)
	for mod, count := range moduleParticipation {
		if float64(count) >= hubThreshold {
			hubSet[mod] = true
		}
	}

	// Count how many hub-related edges the new behavior uses
	hubEdgeCount := 0
	newModules := make(map[int]bool)
	for edge := range newEdges {
		parts := splitEdge(edge)
		newModules[parts[0]] = true
		newModules[parts[1]] = true
		if hubSet[parts[0]] || hubSet[parts[1]] {
			hubEdgeCount++
		}
	}

	totalExistingEdges := 0
	totalOverlap := 0

	for behaviorID, existingEdges := range edgeStore {
		if behaviorID == newBehaviorID {
			continue
		}
		overlap := 0
		for edge := range newEdges {
			if existingEdges[edge] {
				overlap++
			}
		}
		overlapPct := 0.0
		if len(existingEdges) > 0 {
			overlapPct = float64(overlap) / float64(len(existingEdges)) * 100
		}
		isConflict := overlapPct > 30

		entries = append(entries, InterferenceEntry{
			BehaviorID:   behaviorID,
			OverlapEdges: overlap,
			OverlapPct:   overlapPct,
			IsConflict:   isConflict,
		})

		if isConflict {
			conflicts = append(conflicts, behaviorID)
		} else {
			compatible = append(compatible, behaviorID)
		}

		totalExistingEdges += len(existingEdges)
		totalOverlap += overlap
	}

	// Return discovered hubs that this behavior touches
	for mod := range hubSet {
		if newModules[mod] {
			hubs = append(hubs, mod)
		}
	}

	// Hub saturation: fraction of this behavior's edges that touch hub modules
	if len(newEdges) > 0 {
		hubSaturation = float64(hubEdgeCount) / float64(len(newEdges))
	}

	return
}

// computeInterference checks the new behavior's edges against ALL known behaviors
// (precomputed from compile data + every past playground run).

func splitEdge(edge string) [2]int {
	// Parse "19->4" into [19, 4]
	var src, tgt int
	fmt.Sscanf(edge, "%d->%d", &src, &tgt)
	return [2]int{src, tgt}
}
