package models

import (
	"time"

	"github.com/google/uuid"
)

// User represents a registered user
type User struct {
	ID           uuid.UUID `json:"id" db:"id"`
	Email        string    `json:"email" db:"email"`
	PasswordHash string    `json:"-" db:"password_hash"`
	Name         string    `json:"name" db:"name"`
	Company      string    `json:"company,omitempty" db:"company"`
	Plan         string    `json:"plan" db:"plan"` // free, pro, enterprise
	CreatedAt    time.Time `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" db:"updated_at"`
}

// APIKey represents an API key for authentication
type APIKey struct {
	ID        uuid.UUID  `json:"id" db:"id"`
	UserID    uuid.UUID  `json:"user_id" db:"user_id"`
	Name      string     `json:"name" db:"name"`
	KeyHash   string     `json:"-" db:"key_hash"`
	KeyPrefix string     `json:"key_prefix" db:"key_prefix"` // First 8 chars for display
	Scopes    []string   `json:"scopes" db:"scopes"`
	LastUsed  *time.Time `json:"last_used,omitempty" db:"last_used"`
	ExpiresAt *time.Time `json:"expires_at,omitempty" db:"expires_at"`
	CreatedAt time.Time  `json:"created_at" db:"created_at"`
}

// EmbeddingRequest represents a request to generate neural embeddings
type EmbeddingRequest struct {
	// Raw neural signal data (base64 encoded)
	Data string `json:"data" binding:"required"`

	// Signal metadata
	SampleRate    int      `json:"sample_rate" binding:"required"`    // Hz
	NumChannels   int      `json:"num_channels" binding:"required"`   // Number of electrodes
	DeviceType    string   `json:"device_type" binding:"required"`    // eeg, ecog, intracortical
	ChannelNames  []string `json:"channel_names,omitempty"`           // Electrode names
	ChannelCoords [][]float64 `json:"channel_coords,omitempty"`       // 3D positions

	// Processing options
	ModelID       string `json:"model_id,omitempty"`       // Model version to use
	WindowSizeMs  int    `json:"window_size_ms,omitempty"` // Sliding window size
	OverlapMs     int    `json:"overlap_ms,omitempty"`     // Window overlap
	ReturnRaw     bool   `json:"return_raw,omitempty"`     // Return raw features
}

// EmbeddingResponse represents the neural embedding output
type EmbeddingResponse struct {
	ID           string      `json:"id"`
	Embedding    [][]float64 `json:"embedding"`         // Shape: [num_windows, embedding_dim]
	EmbeddingDim int         `json:"embedding_dim"`
	NumWindows   int         `json:"num_windows"`
	ModelID      string      `json:"model_id"`
	ProcessingMs int64       `json:"processing_ms"`
	Usage        UsageInfo   `json:"usage"`
}

// UsageInfo tracks API usage for billing
type UsageInfo struct {
	InferenceUnits int `json:"inference_units"`
	ChannelHours   float64 `json:"channel_hours"`
}

// FineTuneJob represents a model fine-tuning job
type FineTuneJob struct {
	ID              uuid.UUID  `json:"id" db:"id"`
	UserID          uuid.UUID  `json:"user_id" db:"user_id"`
	BaseModelID     string     `json:"base_model_id" db:"base_model_id"`
	ResultModelID   *string    `json:"result_model_id,omitempty" db:"result_model_id"`
	Status          string     `json:"status" db:"status"` // pending, running, completed, failed, cancelled
	TrainingFile    string     `json:"training_file" db:"training_file"`
	ValidationFile  *string    `json:"validation_file,omitempty" db:"validation_file"`
	Hyperparameters Hyperparameters `json:"hyperparameters" db:"hyperparameters"`
	Metrics         *TrainingMetrics `json:"metrics,omitempty" db:"metrics"`
	Error           *string    `json:"error,omitempty" db:"error"`
	CreatedAt       time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt       time.Time  `json:"updated_at" db:"updated_at"`
	FinishedAt      *time.Time `json:"finished_at,omitempty" db:"finished_at"`
}

type Hyperparameters struct {
	LearningRate    float64 `json:"learning_rate"`
	BatchSize       int     `json:"batch_size"`
	NumEpochs       int     `json:"num_epochs"`
	WarmupSteps     int     `json:"warmup_steps"`
	WeightDecay     float64 `json:"weight_decay"`
}

type TrainingMetrics struct {
	TrainLoss      float64 `json:"train_loss"`
	ValidationLoss float64 `json:"validation_loss"`
	Accuracy       float64 `json:"accuracy,omitempty"`
	F1Score        float64 `json:"f1_score,omitempty"`
}

// Model represents a neural foundation model
type Model struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description"`
	Version     string    `json:"version"`
	Type        string    `json:"type"` // foundation, fine-tuned
	Parameters  int64     `json:"parameters"`
	EmbeddingDim int      `json:"embedding_dim"`
	MaxChannels int       `json:"max_channels"`
	MaxSampleRate int     `json:"max_sample_rate"`
	DeviceTypes []string  `json:"device_types"` // Supported device types
	CreatedAt   time.Time `json:"created_at"`
	IsPublic    bool      `json:"is_public"`
	OwnerID     *uuid.UUID `json:"owner_id,omitempty"`
}

// Usage represents monthly usage statistics
type Usage struct {
	UserID           uuid.UUID `json:"user_id"`
	Month            string    `json:"month"` // YYYY-MM
	InferenceUnits   int64     `json:"inference_units"`
	ChannelHours     float64   `json:"channel_hours"`
	FineTuneJobs     int       `json:"fine_tune_jobs"`
	StorageGB        float64   `json:"storage_gb"`
	EstimatedCostUSD float64   `json:"estimated_cost_usd"`
}
