package services

import (
	"encoding/json"
	"fmt"
	"os"
	"sync"

	"github.com/latent-labs/latent-api/internal/models"
)

var (
	compileInstance *CompileDataService
	compileOnce    sync.Once
)

// CompileDataService provides thread-safe access to the compile platform data
type CompileDataService struct {
	mu   sync.RWMutex
	data *models.CompileData
}

// InitCompileData loads the JSON file and initialises the singleton
func InitCompileData(path string) error {
	var initErr error
	compileOnce.Do(func() {
		raw, err := os.ReadFile(path)
		if err != nil {
			initErr = fmt.Errorf("failed to read compile data file: %w", err)
			return
		}

		var data models.CompileData
		if err := json.Unmarshal(raw, &data); err != nil {
			initErr = fmt.Errorf("failed to parse compile data JSON: %w", err)
			return
		}

		compileInstance = &CompileDataService{data: &data}
	})
	return initErr
}

// GetCompileData returns the singleton instance
func GetCompileData() *CompileDataService {
	return compileInstance
}

// GetModules returns all modules
func (s *CompileDataService) GetModules() map[string]models.Module_ {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.data.Modules
}

// GetModule returns a single module by its string ID
func (s *CompileDataService) GetModule(id string) (models.Module_, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	m, ok := s.data.Modules[id]
	return m, ok
}

// GetFitnessFunctions returns all fitness functions
func (s *CompileDataService) GetFitnessFunctions() map[string]models.FitnessFunction {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.data.FitnessFunctions
}

// GetFitnessFunction returns a single fitness function by name
func (s *CompileDataService) GetFitnessFunction(name string) (models.FitnessFunction, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	ff, ok := s.data.FitnessFunctions[name]
	return ff, ok
}

// GetThreeLayerMap returns the full three-layer classification
func (s *CompileDataService) GetThreeLayerMap() models.ThreeLayerMap {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.data.ThreeLayerMap
}

// GetMutations returns mutations filtered by fitness function and optionally seed
func (s *CompileDataService) GetMutations(fitness string, seed *int) ([]models.Mutation, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	ff, ok := s.data.FitnessFunctions[fitness]
	if !ok {
		return nil, false
	}

	if seed == nil {
		return ff.AllMutations, true
	}

	var filtered []models.Mutation
	for _, m := range ff.AllMutations {
		if m.Seed == *seed {
			filtered = append(filtered, m)
		}
	}
	return filtered, true
}

// GetConnection returns mutation data for a specific src->tgt module pair across all fitness functions
func (s *CompileDataService) GetConnection(src, tgt int) map[string][]models.Mutation {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make(map[string][]models.Mutation)
	for name, ff := range s.data.FitnessFunctions {
		var matches []models.Mutation
		for _, m := range ff.AllMutations {
			if m.PreModule == src && m.PostModule == tgt {
				matches = append(matches, m)
			}
		}
		if len(matches) > 0 {
			result[name] = matches
		}
	}
	return result
}
