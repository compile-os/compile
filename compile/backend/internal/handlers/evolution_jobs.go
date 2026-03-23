package handlers

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"database/sql"

	"github.com/gin-gonic/gin"
	"github.com/latent-labs/latent-api/internal/db"
	"github.com/latent-labs/latent-api/internal/models"
	"github.com/latent-labs/latent-api/internal/services"
)

var (
	jobStore   = make(map[string]*models.EvolutionJob)
	jobStoreMu sync.RWMutex
	// Maps our job ID -> worker job ID
	workerJobMap   = make(map[string]string)
	workerJobMapMu sync.RWMutex
)

// CreateEvolutionJob accepts a job request, forwards to the ML worker, returns job ID.
func CreateEvolutionJob(c *gin.Context) {
	var req models.EvolutionJobRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	// Defaults
	if req.Generations == 0 {
		req.Generations = 50
	}
	if req.MutationsPerGen == 0 {
		req.MutationsPerGen = 5
	}

	// Check worker is reachable
	ml := services.GetMLClient()
	if _, err := ml.CheckHealth(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"error":   "worker_unavailable",
			"message": fmt.Sprintf("ML worker is not available: %v", err),
		})
		return
	}
	// Architecture defaults to hub_and_spoke
	arch := req.Architecture
	if arch == "" {
		arch = "hub_and_spoke"
	}

	// Forward to worker
	workerResp, err := ml.CreateEvolutionJob(services.EvolutionJobCreateRequest{
		FitnessFunction: req.FitnessFunction,
		Seed:            req.Seed,
		Generations:     req.Generations,
		MutationsPerGen: req.MutationsPerGen,
		Architecture:    arch,
	})
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{
			"error":   "worker_error",
			"message": fmt.Sprintf("Failed to create job on ML worker: %v", err),
		})
		return
	}

	// Get user ID from auth context
	userID := ""
	if uid, exists := c.Get("user_id"); exists {
		userID, _ = uid.(string)
	}

	// Store locally with our own ID (use worker's ID for simplicity)
	now := time.Now().Format(time.RFC3339)
	job := &models.EvolutionJob{
		ID:              workerResp.ID,
		UserID:          userID,
		FitnessFunction: req.FitnessFunction,
		Seed:            req.Seed,
		Generations:     req.Generations,
		MutationsPerGen: req.MutationsPerGen,
		Architecture:    arch,
		Status:          "pending",
		Progress:        0,
		CreatedAt:       now,
		UpdatedAt:       now,
	}

	jobStoreMu.Lock()
	jobStore[job.ID] = job
	jobStoreMu.Unlock()

	workerJobMapMu.Lock()
	workerJobMap[job.ID] = workerResp.ID
	workerJobMapMu.Unlock()

	// Persist to database
	_ = db.CreateEvolutionJob(&db.EvolutionJobRow{
		ID:              job.ID,
		UserID:          sql.NullString{String: userID, Valid: userID != ""},
		FitnessFunction: job.FitnessFunction,
		Seed:            job.Seed,
		Generations:     job.Generations,
		MutationsPerGen: job.MutationsPerGen,
		Status:          "pending",
		WorkerJobID:     sql.NullString{String: workerResp.ID, Valid: true},
	})

	c.JSON(http.StatusAccepted, gin.H{
		"id":               job.ID,
		"status":           job.Status,
		"fitness_function": job.FitnessFunction,
		"seed":             job.Seed,
		"generations":      job.Generations,
		"mutations_per_gen": job.MutationsPerGen,
		"created_at":       job.CreatedAt,
	})
}

// GetEvolutionJob returns the status of a job.
func GetEvolutionJob(c *gin.Context) {
	id := c.Param("id")

	jobStoreMu.RLock()
	job, ok := jobStore[id]
	jobStoreMu.RUnlock()

	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "not_found",
			"message": "Job not found",
		})
		return
	}

	c.JSON(http.StatusOK, job)
}

// StreamEvolutionJob proxies SSE from the ML worker to the frontend client.
func StreamEvolutionJob(c *gin.Context) {
	id := c.Param("id")

	jobStoreMu.RLock()
	job, ok := jobStore[id]
	jobStoreMu.RUnlock()

	if !ok {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "not_found",
			"message": "Job not found",
		})
		return
	}

	// Get the worker job ID
	workerJobMapMu.RLock()
	workerJobID, ok := workerJobMap[id]
	workerJobMapMu.RUnlock()

	if !ok {
		workerJobID = id
	}

	// Set SSE headers
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")

	c.SSEvent("connected", gin.H{"job_id": id})
	c.Writer.Flush()

	// Open SSE stream from worker
	ml := services.GetMLClient()
	body, err := ml.StreamJobProgress(workerJobID)
	if err != nil {
		c.SSEvent("error", gin.H{"message": fmt.Sprintf("Failed to connect to worker: %v", err)})
		c.Writer.Flush()
		return
	}
	defer body.Close()

	// Proxy SSE events from worker to client
	scanner := bufio.NewScanner(body)
	var eventType string

	for scanner.Scan() {
		line := scanner.Text()

		// Check if client disconnected
		select {
		case <-c.Request.Context().Done():
			return
		default:
		}

		if strings.HasPrefix(line, "event:") {
			eventType = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
		} else if strings.HasPrefix(line, "data:") {
			data := strings.TrimSpace(strings.TrimPrefix(line, "data:"))

			// Update local job state
			var payload map[string]interface{}
			if err := json.Unmarshal([]byte(data), &payload); err == nil {
				jobStoreMu.Lock()
				switch eventType {
				case "progress":
					if p, ok := payload["progress"].(float64); ok {
						job.Progress = int(p)
					}
					fitness := 0.0
					if f, ok := payload["current_fitness"].(float64); ok {
						fitness = f
					}
					acc := 0
					if a, ok := payload["accepted_count"].(float64); ok {
						acc = int(a)
					}
					job.Status = "running"
					// Persist progress to DB
					go db.UpdateJobProgress(job.ID, job.Progress, fitness, acc)
				case "done":
					job.Status = "completed"
					job.Progress = 100
					// Persist result to DB and post-process
					if result, ok := payload["result"]; ok {
						if resultBytes, err := json.Marshal(result); err == nil {
							go db.CompleteJob(job.ID, resultBytes)
							go services.PostProcessJobResult(job.FitnessFunction, resultBytes)
						}
					}
				case "error":
					job.Status = "failed"
					errMsg := ""
					if m, ok := payload["message"].(string); ok {
						errMsg = m
					}
					go db.FailJob(job.ID, errMsg)
				}
				job.UpdatedAt = time.Now().Format(time.RFC3339)
				jobStoreMu.Unlock()
			}

			// Forward to client
			c.SSEvent(eventType, json.RawMessage(data))
			c.Writer.Flush()

			if eventType == "done" || eventType == "error" {
				return
			}
		}
	}
}
