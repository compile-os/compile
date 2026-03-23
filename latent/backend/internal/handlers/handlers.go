package handlers

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// GetCurrentUser returns the authenticated user's profile
func GetCurrentUser(c *gin.Context) {
	userID, _ := c.Get("user_id")
	email, _ := c.Get("email")

	c.JSON(http.StatusOK, gin.H{
		"id":         userID,
		"email":      email,
		"name":       "User",
		"company":    "",
		"plan":       "free",
		"created_at": time.Now().AddDate(0, -1, 0).Format(time.RFC3339),
	})
}

// UpdateUser updates the current user's profile
func UpdateUser(c *gin.Context) {
	var req struct {
		Name    string `json:"name,omitempty"`
		Company string `json:"company,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	userID, _ := c.Get("user_id")

	c.JSON(http.StatusOK, gin.H{
		"id":         userID,
		"name":       req.Name,
		"company":    req.Company,
		"plan":       "free",
		"updated_at": time.Now().Format(time.RFC3339),
	})
}

// ListAPIKeys returns all API keys for the current user
func ListAPIKeys(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"api_keys": []gin.H{
			{
				"id":         uuid.New().String(),
				"name":       "Default Key",
				"key_prefix": "lat_xxxx",
				"scopes":     []string{"embed", "fine-tune"},
				"created_at": time.Now().AddDate(0, 0, -7).Format(time.RFC3339),
				"last_used":  time.Now().AddDate(0, 0, -1).Format(time.RFC3339),
			},
		},
	})
}

// CreateAPIKey creates a new API key
func CreateAPIKey(c *gin.Context) {
	var req struct {
		Name      string   `json:"name" binding:"required"`
		Scopes    []string `json:"scopes,omitempty"`
		ExpiresIn *int     `json:"expires_in_days,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	// Generate API key
	keyBytes := make([]byte, 32)
	rand.Read(keyBytes)
	apiKey := "lat_" + hex.EncodeToString(keyBytes)

	// Default scopes
	if len(req.Scopes) == 0 {
		req.Scopes = []string{"embed", "fine-tune", "models"}
	}

	var expiresAt *string
	if req.ExpiresIn != nil {
		t := time.Now().AddDate(0, 0, *req.ExpiresIn).Format(time.RFC3339)
		expiresAt = &t
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":         uuid.New().String(),
		"name":       req.Name,
		"key":        apiKey, // Only returned once on creation
		"key_prefix": apiKey[:12],
		"scopes":     req.Scopes,
		"expires_at": expiresAt,
		"created_at": time.Now().Format(time.RFC3339),
	})
}

// DeleteAPIKey revokes an API key
func DeleteAPIKey(c *gin.Context) {
	keyID := c.Param("id")

	// TODO: Validate ownership and delete from database

	c.JSON(http.StatusOK, gin.H{
		"deleted": true,
		"id":      keyID,
	})
}

// CreateFineTuneJob creates a new fine-tuning job
func CreateFineTuneJob(c *gin.Context) {
	var req struct {
		BaseModelID     string `json:"base_model_id" binding:"required"`
		TrainingFile    string `json:"training_file" binding:"required"`
		ValidationFile  string `json:"validation_file,omitempty"`
		Hyperparameters struct {
			LearningRate float64 `json:"learning_rate,omitempty"`
			BatchSize    int     `json:"batch_size,omitempty"`
			NumEpochs    int     `json:"num_epochs,omitempty"`
			WarmupSteps  int     `json:"warmup_steps,omitempty"`
			WeightDecay  float64 `json:"weight_decay,omitempty"`
		} `json:"hyperparameters,omitempty"`
		Suffix string `json:"suffix,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	jobID := uuid.New()

	// Default hyperparameters
	if req.Hyperparameters.LearningRate == 0 {
		req.Hyperparameters.LearningRate = 1e-4
	}
	if req.Hyperparameters.BatchSize == 0 {
		req.Hyperparameters.BatchSize = 32
	}
	if req.Hyperparameters.NumEpochs == 0 {
		req.Hyperparameters.NumEpochs = 3
	}

	c.JSON(http.StatusAccepted, gin.H{
		"id":               jobID.String(),
		"status":           "pending",
		"base_model_id":    req.BaseModelID,
		"training_file":    req.TrainingFile,
		"validation_file":  req.ValidationFile,
		"hyperparameters":  req.Hyperparameters,
		"created_at":       time.Now().Format(time.RFC3339),
		"estimated_completion": time.Now().Add(2 * time.Hour).Format(time.RFC3339),
	})
}

// GetFineTuneJob returns the status of a fine-tuning job
func GetFineTuneJob(c *gin.Context) {
	jobID := c.Param("id")

	c.JSON(http.StatusOK, gin.H{
		"id":            jobID,
		"status":        "running",
		"base_model_id": "latent-v0.1",
		"progress": gin.H{
			"current_epoch": 1,
			"total_epochs":  3,
			"current_step":  450,
			"total_steps":   1500,
		},
		"metrics": gin.H{
			"train_loss":      0.234,
			"validation_loss": 0.289,
		},
		"created_at": time.Now().Add(-30 * time.Minute).Format(time.RFC3339),
		"updated_at": time.Now().Format(time.RFC3339),
	})
}

// ListFineTuneJobs returns all fine-tuning jobs for the current user
func ListFineTuneJobs(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"jobs": []gin.H{
			{
				"id":            uuid.New().String(),
				"status":        "completed",
				"base_model_id": "latent-v0.1",
				"result_model":  "latent-v0.1:ft-user123",
				"created_at":    time.Now().AddDate(0, 0, -3).Format(time.RFC3339),
				"finished_at":   time.Now().AddDate(0, 0, -3).Add(2 * time.Hour).Format(time.RFC3339),
			},
		},
	})
}

// CancelFineTuneJob cancels a pending or running fine-tuning job
func CancelFineTuneJob(c *gin.Context) {
	jobID := c.Param("id")

	c.JSON(http.StatusOK, gin.H{
		"id":          jobID,
		"status":      "cancelled",
		"cancelled_at": time.Now().Format(time.RFC3339),
	})
}

// ListModels returns available neural foundation models
func ListModels(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"models": []gin.H{
			{
				"id":              "latent-v0.1",
				"name":            "Latent Foundation Model v0.1",
				"description":     "Initial release of the neural foundation model, trained on TUH + MOABB datasets",
				"version":         "0.1.0",
				"type":            "foundation",
				"parameters":      "125M",
				"embedding_dim":   768,
				"max_channels":    256,
				"max_sample_rate": 2048,
				"device_types":    []string{"eeg", "ecog", "intracortical", "seeg", "meg"},
				"created_at":      "2026-01-15T00:00:00Z",
			},
			{
				"id":              "latent-v0.2-preview",
				"name":            "Latent Foundation Model v0.2 (Preview)",
				"description":     "Improved model with cross-device zero-shot transfer capabilities",
				"version":         "0.2.0-preview",
				"type":            "foundation",
				"parameters":      "350M",
				"embedding_dim":   1024,
				"max_channels":    512,
				"max_sample_rate": 4096,
				"device_types":    []string{"eeg", "ecog", "intracortical", "seeg", "meg", "fnirs", "ear_eeg"},
				"created_at":      "2026-03-01T00:00:00Z",
			},
		},
	})
}

// GetModel returns details about a specific model
func GetModel(c *gin.Context) {
	modelID := c.Param("id")

	c.JSON(http.StatusOK, gin.H{
		"id":              modelID,
		"name":            "Latent Foundation Model v0.1",
		"description":     "Initial release of the neural foundation model, trained on TUH + MOABB datasets. Supports zero-shot inference on unseen subjects and sessions.",
		"version":         "0.1.0",
		"type":            "foundation",
		"parameters":      "125M",
		"embedding_dim":   768,
		"max_channels":    256,
		"max_sample_rate": 2048,
		"device_types":    []string{"eeg", "ecog", "intracortical", "seeg", "meg"},
		"training_data": gin.H{
			"datasets": []string{"TUH EEG Corpus", "MOABB", "PhysioNet"},
			"channel_hours": 650000,
			"subjects": 15000,
		},
		"benchmarks": gin.H{
			"motor_imagery_accuracy":   0.72,
			"cross_subject_transfer":   0.68,
			"zero_shot_classification": 0.61,
		},
		"created_at": "2026-01-15T00:00:00Z",
	})
}

// GetUsage returns usage statistics for the current billing period
func GetUsage(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"period": gin.H{
			"start": time.Now().AddDate(0, 0, -time.Now().Day()+1).Format("2006-01-02"),
			"end":   time.Now().Format("2006-01-02"),
		},
		"usage": gin.H{
			"inference_units": 145230,
			"channel_hours":   23.5,
			"fine_tune_jobs":  2,
			"storage_gb":      1.2,
		},
		"limits": gin.H{
			"inference_units": 1000000,
			"channel_hours":   100,
			"fine_tune_jobs":  10,
			"storage_gb":      10,
		},
		"estimated_cost_usd": 45.50,
	})
}

// GetBillingInfo returns billing information
func GetBillingInfo(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"plan": gin.H{
			"name":  "Pro",
			"price": 99.00,
			"currency": "USD",
			"interval": "month",
		},
		"payment_method": gin.H{
			"type": "card",
			"last4": "4242",
			"brand": "visa",
		},
		"next_invoice": gin.H{
			"date":   time.Now().AddDate(0, 1, 0).Format("2006-01-02"),
			"amount": 144.50,
		},
		"invoices": []gin.H{
			{
				"id":     "inv_123",
				"date":   time.Now().AddDate(0, -1, 0).Format("2006-01-02"),
				"amount": 99.00,
				"status": "paid",
			},
		},
	})
}

// StripeWebhook handles Stripe webhook events
func StripeWebhook(c *gin.Context) {
	// TODO: Implement Stripe webhook handling
	// Verify signature, process events (subscription updates, payments, etc.)

	c.JSON(http.StatusOK, gin.H{"received": true})
}
