package handlers

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// CreateEmbedding processes neural signals and returns embeddings
func CreateEmbedding(c *gin.Context) {
	var req struct {
		Data          string      `json:"data" binding:"required"`
		SampleRate    int         `json:"sample_rate" binding:"required"`
		NumChannels   int         `json:"num_channels" binding:"required"`
		DeviceType    string      `json:"device_type" binding:"required"`
		ChannelNames  []string    `json:"channel_names,omitempty"`
		ChannelCoords [][]float64 `json:"channel_coords,omitempty"`
		ModelID       string      `json:"model_id,omitempty"`
		WindowSizeMs  int         `json:"window_size_ms,omitempty"`
		OverlapMs     int         `json:"overlap_ms,omitempty"`
		ReturnRaw     bool        `json:"return_raw,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	// Validate device type
	validDeviceTypes := map[string]bool{
		"eeg": true, "ecog": true, "intracortical": true,
		"seeg": true, "meg": true, "fnirs": true, "ear_eeg": true,
	}
	if !validDeviceTypes[req.DeviceType] {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Invalid device_type. Supported: eeg, ecog, intracortical, seeg, meg, fnirs, ear_eeg",
		})
		return
	}

	// Default model
	if req.ModelID == "" {
		req.ModelID = "latent-v0.1"
	}

	// Default window size
	if req.WindowSizeMs == 0 {
		req.WindowSizeMs = 1000 // 1 second
	}
	if req.OverlapMs == 0 {
		req.OverlapMs = 500 // 50% overlap
	}

	startTime := time.Now()

	// Forward request to ML service
	mlServiceURL := "http://localhost:8000/api/v1/embed"

	reqBody, _ := json.Marshal(req)
	mlResp, err := http.Post(mlServiceURL, "application/json", bytes.NewBuffer(reqBody))

	var embedding [][]float64
	var embeddingDim int
	var numWindows int

	if err != nil || mlResp == nil {
		// ML service unavailable - return mock response for development
		// In production, this would return an error
		embeddingDim = 768
		numWindows = 10
		embedding = make([][]float64, numWindows)
		for i := range embedding {
			embedding[i] = make([]float64, embeddingDim)
			for j := range embedding[i] {
				embedding[i][j] = float64(i+j) * 0.001
			}
		}
	} else {
		defer mlResp.Body.Close()
		body, _ := io.ReadAll(mlResp.Body)

		var mlResult struct {
			Embedding    [][]float64 `json:"embedding"`
			EmbeddingDim int         `json:"embedding_dim"`
			NumWindows   int         `json:"num_windows"`
		}
		json.Unmarshal(body, &mlResult)

		embedding = mlResult.Embedding
		embeddingDim = mlResult.EmbeddingDim
		numWindows = mlResult.NumWindows
	}

	processingMs := time.Since(startTime).Milliseconds()

	// Calculate usage
	// Inference units = num_channels * num_windows
	inferenceUnits := req.NumChannels * numWindows
	// Channel hours = (num_channels * duration_seconds) / 3600
	durationSeconds := float64(numWindows*req.WindowSizeMs) / 1000.0
	channelHours := float64(req.NumChannels) * durationSeconds / 3600.0

	c.JSON(http.StatusOK, gin.H{
		"id":            uuid.New().String(),
		"embedding":     embedding,
		"embedding_dim": embeddingDim,
		"num_windows":   numWindows,
		"model_id":      req.ModelID,
		"processing_ms": processingMs,
		"usage": gin.H{
			"inference_units": inferenceUnits,
			"channel_hours":   channelHours,
		},
	})
}

// CreateBatchEmbedding processes multiple neural signal segments
func CreateBatchEmbedding(c *gin.Context) {
	var req struct {
		Inputs []struct {
			Data          string      `json:"data" binding:"required"`
			SampleRate    int         `json:"sample_rate" binding:"required"`
			NumChannels   int         `json:"num_channels" binding:"required"`
			DeviceType    string      `json:"device_type" binding:"required"`
			ChannelNames  []string    `json:"channel_names,omitempty"`
			ChannelCoords [][]float64 `json:"channel_coords,omitempty"`
		} `json:"inputs" binding:"required,dive"`
		ModelID      string `json:"model_id,omitempty"`
		WindowSizeMs int    `json:"window_size_ms,omitempty"`
		OverlapMs    int    `json:"overlap_ms,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	if len(req.Inputs) > 100 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Maximum 100 inputs per batch request",
		})
		return
	}

	startTime := time.Now()

	// Process each input (in production, this would be parallelized)
	results := make([]gin.H, len(req.Inputs))
	totalInferenceUnits := 0
	totalChannelHours := 0.0

	for i, input := range req.Inputs {
		// Mock embedding generation
		embeddingDim := 768
		numWindows := 10
		embedding := make([][]float64, numWindows)
		for j := range embedding {
			embedding[j] = make([]float64, embeddingDim)
		}

		inferenceUnits := input.NumChannels * numWindows
		channelHours := float64(input.NumChannels) * float64(numWindows) / 3600.0

		totalInferenceUnits += inferenceUnits
		totalChannelHours += channelHours

		results[i] = gin.H{
			"index":         i,
			"embedding":     embedding,
			"embedding_dim": embeddingDim,
			"num_windows":   numWindows,
		}
	}

	processingMs := time.Since(startTime).Milliseconds()

	c.JSON(http.StatusOK, gin.H{
		"id":            uuid.New().String(),
		"results":       results,
		"model_id":      req.ModelID,
		"processing_ms": processingMs,
		"usage": gin.H{
			"inference_units": totalInferenceUnits,
			"channel_hours":   totalChannelHours,
		},
	})
}

// StreamEmbedding processes neural signals in real-time streaming mode
func StreamEmbedding(c *gin.Context) {
	// Set headers for SSE
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("X-Accel-Buffering", "no")

	var req struct {
		Data          string      `json:"data" binding:"required"`
		SampleRate    int         `json:"sample_rate" binding:"required"`
		NumChannels   int         `json:"num_channels" binding:"required"`
		DeviceType    string      `json:"device_type" binding:"required"`
		ChannelNames  []string    `json:"channel_names,omitempty"`
		ChannelCoords [][]float64 `json:"channel_coords,omitempty"`
		ModelID       string      `json:"model_id,omitempty"`
		WindowSizeMs  int         `json:"window_size_ms,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.SSEvent("error", gin.H{"message": err.Error()})
		return
	}

	streamID := uuid.New().String()
	c.SSEvent("connected", gin.H{"stream_id": streamID})

	// Simulate streaming embeddings
	embeddingDim := 768
	for i := 0; i < 10; i++ {
		embedding := make([]float64, embeddingDim)
		for j := range embedding {
			embedding[j] = float64(i+j) * 0.001
		}

		c.SSEvent("embedding", gin.H{
			"window_index":  i,
			"embedding":     embedding,
			"timestamp_ms":  i * req.WindowSizeMs,
			"embedding_dim": embeddingDim,
		})
		c.Writer.Flush()
		time.Sleep(100 * time.Millisecond)
	}

	c.SSEvent("done", gin.H{
		"stream_id":    streamID,
		"total_windows": 10,
	})
}
