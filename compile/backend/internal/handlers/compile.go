package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/latent-labs/latent-api/internal/db"
	"github.com/latent-labs/latent-api/internal/models"
	"github.com/latent-labs/latent-api/internal/services"
)

// ListCompileModules returns all modules, with optional ?role= filter
func ListCompileModules(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	modules := svc.GetModules()
	roleFilter := c.Query("role")

	type moduleEntry struct {
		ID     string `json:"id"`
		Role   string `json:"role"`
		NNeurons int  `json:"n_neurons"`
		TopSuperClass string `json:"top_super_class"`
		TopNT  string `json:"top_nt"`
		TopGroup string `json:"top_group"`
	}

	var result []moduleEntry
	for id, m := range modules {
		if roleFilter != "" && m.Role != roleFilter {
			continue
		}
		result = append(result, moduleEntry{
			ID:            id,
			Role:          m.Role,
			NNeurons:      m.NNeurons,
			TopSuperClass: m.TopSuperClass,
			TopNT:         m.TopNT,
			TopGroup:      m.TopGroup,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"modules": result,
		"count":   len(result),
	})
}

// GetCompileModule returns a single module by ID
func GetCompileModule(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	id := c.Param("id")
	m, ok := svc.GetModule(id)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "not_found",
			"message": "Module not found",
		})
		return
	}

	// Also get connections involving this module
	moduleID, err := strconv.Atoi(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Module ID must be an integer",
		})
		return
	}

	// Gather evolvable pairs where this module is src or tgt
	ffs := svc.GetFitnessFunctions()
	type pairInfo struct {
		Pair       string  `json:"pair"`
		Fitness    string  `json:"fitness_function"`
		BestDelta  float64 `json:"best_delta"`
		BestScale  float64 `json:"best_scale"`
		NSynapses  int     `json:"n_synapses"`
	}
	var connections []pairInfo
	for name, ff := range ffs {
		for _, ep := range ff.EvolvablePairs {
			if ep.PreModule == moduleID || ep.PostModule == moduleID {
				connections = append(connections, pairInfo{
					Pair:      ep.Pair,
					Fitness:   name,
					BestDelta: ep.BestDelta,
					BestScale: ep.BestScale,
					NSynapses: ep.NSynapses,
				})
			}
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"id":              id,
		"role":            m.Role,
		"n_neurons":       m.NNeurons,
		"top_super_class": m.TopSuperClass,
		"top_nt":          m.TopNT,
		"top_group":       m.TopGroup,
		"connections":     connections,
	})
}

// ListFitnessFunctions returns all fitness functions with summaries
func ListFitnessFunctions(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	ffs := svc.GetFitnessFunctions()

	type summary struct {
		Name           string  `json:"name"`
		NumSeeds       int     `json:"num_seeds"`
		EvolvablePairs int     `json:"evolvable_pairs"`
		TotalMutations int     `json:"total_mutations"`
		BestImprovement float64 `json:"best_improvement"`
	}

	var result []summary
	for name, ff := range ffs {
		bestImprovement := 0.0
		for _, s := range ff.Seeds {
			if s.Improvement > bestImprovement {
				bestImprovement = s.Improvement
			}
		}
		result = append(result, summary{
			Name:            name,
			NumSeeds:        len(ff.Seeds),
			EvolvablePairs:  len(ff.EvolvablePairs),
			TotalMutations:  len(ff.AllMutations),
			BestImprovement: bestImprovement,
		})
	}

	c.JSON(http.StatusOK, gin.H{
		"fitness_functions": result,
		"count":             len(result),
	})
}

// GetFitnessFunction returns full details for a single fitness function
func GetFitnessFunction(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	name := c.Param("name")
	ff, ok := svc.GetFitnessFunction(name)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "not_found",
			"message": "Fitness function not found",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"name":            name,
		"seeds":           ff.Seeds,
		"evolvable_pairs": ff.EvolvablePairs,
		"total_mutations": len(ff.AllMutations),
	})
}

// GetThreeLayerMap returns the OS/App/Hardware classification
func GetThreeLayerMap(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	tlm := svc.GetThreeLayerMap()

	c.JSON(http.StatusOK, gin.H{
		"os_layer":       tlm.OSLayer,
		"app_layer":      tlm.AppLayer,
		"hardware_stats": tlm.HardwareStats,
	})
}

// GetMutations returns mutations filtered by ?fitness= and optional ?seed=
func GetMutations(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	fitness := c.Query("fitness")
	if fitness == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Query parameter 'fitness' is required",
		})
		return
	}

	var seedPtr *int
	if seedStr := c.Query("seed"); seedStr != "" {
		seedVal, err := strconv.Atoi(seedStr)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error":   "validation_error",
				"message": "Query parameter 'seed' must be an integer",
			})
			return
		}
		seedPtr = &seedVal
	}

	mutations, ok := svc.GetMutations(fitness, seedPtr)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "not_found",
			"message": "Fitness function not found",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"fitness":   fitness,
		"mutations": mutations,
		"count":     len(mutations),
	})
}

// GetConnection returns mutation data for a specific src->tgt module pair
func GetConnection(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	src, err := strconv.Atoi(c.Param("src"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Parameter 'src' must be an integer",
		})
		return
	}

	tgt, err := strconv.Atoi(c.Param("tgt"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Parameter 'tgt' must be an integer",
		})
		return
	}

	result := svc.GetConnection(src, tgt)

	c.JSON(http.StatusOK, gin.H{
		"src":              src,
		"tgt":              tgt,
		"fitness_functions": result,
		"total_mutations":  countMutations(result),
	})
}

func countMutations(data map[string][]models.Mutation) int {
	total := 0
	for _, muts := range data {
		total += len(muts)
	}
	return total
}

// GetArchitectures returns the architecture catalog.
// The catalog is loaded from the Python architecture_specs.py at startup
// and enriched with experiment results as they come in.
func GetArchitectures(c *gin.Context) {
	// For now, return the catalog from the frontend data file
	// In production, this would load from architecture_specs.py or DB
	c.JSON(http.StatusOK, gin.H{
		"message": "Use frontend architecture-data.ts for now. Backend architecture loading from Python specs coming soon.",
	})
}

// GetCompileCatalog returns the behavior library with interference matrix,
// capability families, and hub capacity information.
func GetCompileCatalog(c *gin.Context) {
	svc := services.GetCompileData()
	if svc == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "service_unavailable",
			"message": "Compile data not loaded",
		})
		return
	}

	// Behavior library (includes precomputed + user-compiled)
	lib := services.GetBehaviorLibrary()
	allBehaviors := lib.GetAll()
	behaviors := make([]gin.H, 0, len(allBehaviors))

	// If user_id query param is provided, look up which behaviors this user compiled
	requestingUserID := c.Query("user_id")
	userBehaviors := make(map[string]bool)
	if requestingUserID != "" {
		if dbPool := db.Get(); dbPool != nil {
			rows, err := dbPool.Query(`
				SELECT DISTINCT fitness_function FROM evolution_jobs
				WHERE user_id = $1 AND status = 'completed'
			`, requestingUserID)
			if err == nil {
				defer rows.Close()
				for rows.Next() {
					var ff string
					if err := rows.Scan(&ff); err == nil {
						userBehaviors[ff] = true
					}
				}
			}
		}
	}

	for _, b := range allBehaviors {
		entry := gin.H{
			"id":               b.ID,
			"label":            b.Label,
			"category":         b.Category,
			"improvement":      b.Improvement,
			"edges":            b.Edges,
			"description":      b.Description,
			"capability_family": b.CapabilityFamily,
			"is_precomputed":   b.IsPrecomputed,
		}
		if requestingUserID != "" {
			entry["is_mine"] = userBehaviors[b.ID]
		}
		behaviors = append(behaviors, entry)
	}

	// Interference matrix (reactive behaviors only)
	interference := []gin.H{
		{"compiled": "navigation", "tested": "escape", "delta_pct": 58},
		{"compiled": "navigation", "tested": "turning", "delta_pct": 0},
		{"compiled": "navigation", "tested": "arousal", "delta_pct": 5},
		{"compiled": "navigation", "tested": "circles", "delta_pct": 3},
		{"compiled": "escape", "tested": "navigation", "delta_pct": 2},
		{"compiled": "escape", "tested": "turning", "delta_pct": 0},
		{"compiled": "escape", "tested": "arousal", "delta_pct": 0},
		{"compiled": "escape", "tested": "circles", "delta_pct": 0},
		{"compiled": "turning", "tested": "navigation", "delta_pct": 0},
		{"compiled": "turning", "tested": "escape", "delta_pct": 0},
		{"compiled": "turning", "tested": "arousal", "delta_pct": 0},
		{"compiled": "turning", "tested": "circles", "delta_pct": 5},
		{"compiled": "arousal", "tested": "navigation", "delta_pct": 8},
		{"compiled": "arousal", "tested": "escape", "delta_pct": 3},
		{"compiled": "arousal", "tested": "turning", "delta_pct": 0},
		{"compiled": "arousal", "tested": "circles", "delta_pct": 0},
		{"compiled": "circles", "tested": "navigation", "delta_pct": 5},
		{"compiled": "circles", "tested": "escape", "delta_pct": -41},
		{"compiled": "circles", "tested": "turning", "delta_pct": 10},
		{"compiled": "circles", "tested": "arousal", "delta_pct": 0},
	}

	// Capability families — group behaviors by their capability_family field (from library)
	familyMap := make(map[string][]string)
	for _, b := range allBehaviors {
		familyMap[b.CapabilityFamily] = append(familyMap[b.CapabilityFamily], b.ID)
	}
	families := make([]gin.H, 0)
	familyDescriptions := map[string]string{
		"state_maintenance": "Behaviors that require persistent internal state (CX activity sustained after stimulus removal).",
		"selective_gating":  "Behaviors that selectively gate inputs. Uses separate circuitry from state maintenance.",
		"reactive_motor":    "Direct stimulus-to-motor behaviors. Compose freely on the gene-guided processor.",
	}
	for family, behaviorIDs := range familyMap {
		desc := familyDescriptions[family]
		if desc == "" {
			desc = "Discovered capability family."
		}
		families = append(families, gin.H{
			"name":        family,
			"description": desc,
			"behaviors":   behaviorIDs,
		})
	}

	// Hub capacity — compute from actual module data
	totalNeurons := 0
	if svc != nil {
		for _, mod := range svc.GetModules() {
			totalNeurons += mod.NNeurons
		}
	}
	hubCapacity := gin.H{
		"total_neurons":       totalNeurons,
		"behaviors_compiled":  len(allBehaviors),
		"capability_families": len(familyMap),
	}

	c.JSON(http.StatusOK, gin.H{
		"behaviors":       behaviors,
		"interference":    interference,
		"families":        families,
		"hub_capacity":    hubCapacity,
		"total_results":   22,
		"species":         2,
	})
}

// ClassifyBehavior uses AI to determine the computational requirement tag of a custom behavior.
func ClassifyBehavior(c *gin.Context) {
	var req struct {
		Description string `json:"description" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation_error", "message": err.Error()})
		return
	}

	ai := services.GetAIClient()
	tag, err := ai.ClassifyBehavior(req.Description)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"tag": "speed", "source": "fallback", "error": err.Error()})
		return
	}

	source := "fallback"
	if ai.Available() {
		source = "ai"
	}
	c.JSON(http.StatusOK, gin.H{"tag": tag, "source": source})
}

// RecommendArchitecture uses AI to suggest the best architecture for selected behaviors.
func RecommendArchitecture(c *gin.Context) {
	var req struct {
		Behaviors   []map[string]string    `json:"behaviors" binding:"required"`
		Constraints map[string]interface{} `json:"constraints"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation_error", "message": err.Error()})
		return
	}

	ai := services.GetAIClient()
	archID, explanation, err := ai.RecommendArchitecture(req.Behaviors, req.Constraints)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"architecture": "cellular_automaton",
			"explanation":  "Default: highest scoring architecture.",
			"source":       "fallback",
			"error":        err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"architecture": archID,
		"explanation":  explanation,
		"source":       "ai",
	})
}
