package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/latent-labs/latent-api/internal/config"
)

// MLClient communicates with the Python FastAPI ML worker.
type MLClient struct {
	baseURL    string
	httpClient *http.Client
}

// NewMLClient creates a client for the ML worker service.
func NewMLClient() *MLClient {
	cfg := config.Get()
	return &MLClient{
		baseURL: cfg.MLServiceURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// EvolutionRequest matches the worker's expected request body.
type EvolutionJobCreateRequest struct {
	FitnessFunction        string `json:"fitness_function"`
	Seed                   int    `json:"seed"`
	Generations            int    `json:"generations"`
	MutationsPerGen        int    `json:"mutations_per_gen"`
	Architecture           string `json:"architecture"`
	UseBiologicalReference bool   `json:"use_biological_reference"`
}

// WorkerJobResponse is what the worker returns on job creation.
type WorkerJobResponse struct {
	ID              string `json:"id"`
	Status          string `json:"status"`
	FitnessFunction string `json:"fitness_function"`
	Seed            int    `json:"seed"`
}

// WorkerHealth is the worker's health endpoint response.
type WorkerHealth struct {
	Status             string   `json:"status"`
	HasData            bool     `json:"has_data"`
	DataDir            string   `json:"data_dir"`
	AvailableBehaviors []string `json:"available_behaviors"`
}

// CheckHealth returns the worker health status.
func (c *MLClient) CheckHealth() (*WorkerHealth, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/health")
	if err != nil {
		return nil, fmt.Errorf("worker unreachable: %w", err)
	}
	defer resp.Body.Close()

	var health WorkerHealth
	if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
		return nil, fmt.Errorf("invalid health response: %w", err)
	}
	return &health, nil
}

// CreateEvolutionJob sends a job request to the worker.
func (c *MLClient) CreateEvolutionJob(req EvolutionJobCreateRequest) (*WorkerJobResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	resp, err := c.httpClient.Post(
		c.baseURL+"/jobs/evolution",
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return nil, fmt.Errorf("worker unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("worker error (status %d): %s", resp.StatusCode, string(respBody))
	}

	var jobResp WorkerJobResponse
	if err := json.NewDecoder(resp.Body).Decode(&jobResp); err != nil {
		return nil, fmt.Errorf("invalid job response: %w", err)
	}
	return &jobResp, nil
}

// StreamJobProgress opens an SSE connection to the worker's job stream.
// Returns the raw response body — caller must read SSE events and close it.
func (c *MLClient) StreamJobProgress(workerJobID string) (io.ReadCloser, error) {
	// No timeout for streaming connections
	streamClient := &http.Client{Timeout: 0}

	resp, err := streamClient.Get(c.baseURL + "/jobs/" + workerJobID + "/stream")
	if err != nil {
		return nil, fmt.Errorf("worker stream unreachable: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, fmt.Errorf("worker stream error (status %d)", resp.StatusCode)
	}

	return resp.Body, nil
}

// Global singleton
var mlClient *MLClient

func GetMLClient() *MLClient {
	if mlClient == nil {
		mlClient = NewMLClient()
	}
	return mlClient
}
