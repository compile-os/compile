package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
	"github.com/latent-labs/latent-api/internal/config"
	"github.com/latent-labs/latent-api/internal/db"
	"github.com/latent-labs/latent-api/internal/handlers"
	"github.com/latent-labs/latent-api/internal/middleware"
	"github.com/latent-labs/latent-api/internal/services"
)

func main() {
	// Load environment variables
	if err := godotenv.Load(); err != nil {
		log.Println("No .env file found, using environment variables")
	}

	// Load configuration
	cfg := config.Load()

	// Connect to database
	if err := db.Init(cfg.DatabaseURL); err != nil {
		log.Printf("Warning: failed to connect to database: %v (using in-memory fallback)", err)
	}
	defer db.Close()

	// Load compile platform data
	if err := services.InitCompileData(cfg.CompileDataPath); err != nil {
		log.Printf("Warning: failed to load compile data: %v", err)
	}

	// Seed behavior library and edge store from compile data (single source of truth)
	services.InitBehaviorLibraryFromCompileData()

	// Set Gin mode
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize router
	router := gin.Default()

	// Apply global middleware
	router.Use(middleware.CORS())
	router.Use(middleware.RequestID())
	router.Use(middleware.Logger())
	router.Use(middleware.RateLimit(cfg.RateLimit))

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"version": cfg.Version,
			"service": "latent-api",
		})
	})

	// Initialize passkey auth
	passkeyHandler, err := handlers.NewPasskeyAuthHandler(
		cfg.WebAuthnRPID,
		cfg.WebAuthnRPOrigin,
		cfg.WebAuthnRPName,
	)
	if err != nil {
		log.Printf("Warning: passkey auth not available: %v", err)
	}

	// API v1 routes
	v1 := router.Group("/api/v1")
	{
		// Passkey auth routes (primary — no email/password)
		auth := v1.Group("/auth")
		{
			if passkeyHandler != nil {
				auth.GET("/passkey/check", passkeyHandler.CheckUserExists)
				auth.POST("/passkey/register/begin", passkeyHandler.BeginRegistration)
				auth.POST("/passkey/register/finish", passkeyHandler.FinishRegistration)
				auth.POST("/passkey/login/begin", passkeyHandler.BeginLogin)
				auth.POST("/passkey/login/finish", passkeyHandler.FinishLogin)
			}
			auth.POST("/refresh", handlers.RefreshToken)
		}

		// Protected routes
		protected := v1.Group("/")
		protected.Use(middleware.AuthRequired())
		{
			// User management
			protected.GET("/me", handlers.GetCurrentUser)
			protected.PUT("/me", handlers.UpdateUser)

			// API keys
			protected.GET("/api-keys", handlers.ListAPIKeys)
			protected.POST("/api-keys", handlers.CreateAPIKey)
			protected.DELETE("/api-keys/:id", handlers.DeleteAPIKey)

			// Neural embeddings - core product
			protected.POST("/embed", handlers.CreateEmbedding)
			protected.POST("/embed/batch", handlers.CreateBatchEmbedding)
			protected.POST("/embed/stream", handlers.StreamEmbedding)

			// Fine-tuning
			protected.POST("/fine-tune", handlers.CreateFineTuneJob)
			protected.GET("/fine-tune/:id", handlers.GetFineTuneJob)
			protected.GET("/fine-tune", handlers.ListFineTuneJobs)
			protected.DELETE("/fine-tune/:id", handlers.CancelFineTuneJob)

			// Models
			protected.GET("/models", handlers.ListModels)
			protected.GET("/models/:id", handlers.GetModel)

			// Usage & billing
			protected.GET("/usage", handlers.GetUsage)
			protected.GET("/billing", handlers.GetBillingInfo)
		}

		// Webhook endpoints (Stripe, etc.)
		webhooks := v1.Group("/webhooks")
		{
			webhooks.POST("/stripe", handlers.StripeWebhook)
		}

		// Compile platform routes
		compile := v1.Group("/compile")
		{
			// Public read endpoints
			compile.GET("/modules", handlers.ListCompileModules)
			compile.GET("/modules/:id", handlers.GetCompileModule)
			compile.GET("/fitness-functions", handlers.ListFitnessFunctions)
			compile.GET("/fitness-functions/:name", handlers.GetFitnessFunction)
			compile.GET("/three-layer-map", handlers.GetThreeLayerMap)
			compile.GET("/mutations", handlers.GetMutations)
			compile.GET("/connections/:src/:tgt", handlers.GetConnection)
			compile.GET("/catalog", handlers.GetCompileCatalog)
			compile.GET("/architectures", handlers.GetArchitectures)
			compile.POST("/classify-behavior", handlers.ClassifyBehavior)
			compile.POST("/recommend-architecture", handlers.RecommendArchitecture)

			// Evolution job endpoints (auth required — passkey or JWT)
			compileProtected := compile.Group("/")
			compileProtected.Use(middleware.AuthRequired())
			{
				compileProtected.POST("/jobs", handlers.CreateEvolutionJob)
				compileProtected.GET("/jobs/:id", handlers.GetEvolutionJob)
				compileProtected.GET("/jobs/:id/stream", handlers.StreamEvolutionJob)
			}
		}
	}

	// Create server (WriteTimeout=0 to support long-running SSE streams)
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 0,
		IdleTimeout:  120 * time.Second,
	}

	// Start server in goroutine
	go func() {
		log.Printf("Starting Latent API server on port %s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Failed to start server: %v", err)
		}
	}()

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("Server forced to shutdown: %v", err)
	}

	log.Println("Server exited properly")
}
