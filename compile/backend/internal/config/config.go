package config

import (
	"os"
	"strconv"
	"sync"
)

var (
	globalCfg  *Config
	cfgOnce    sync.Once
)

// Get returns the global config singleton. Must call Load() first.
func Get() *Config {
	return globalCfg
}

type Config struct {
	Environment string
	Port        string
	Version     string

	// Database
	DatabaseURL string

	// Redis
	RedisURL string

	// JWT
	JWTSecret        string
	JWTRefreshSecret string
	JWTExpiration    int // hours

	// Rate limiting
	RateLimit int // requests per minute

	// ML Service
	MLServiceURL string

	// Stripe
	StripeSecretKey      string
	StripeWebhookSecret  string

	// AWS
	AWSRegion          string
	AWSAccessKeyID     string
	AWSSecretAccessKey string
	S3Bucket           string

	// OpenAI (for behavior classification + architecture recommendation)
	OpenAIAPIKey string
	OpenAIOrgID  string

	// Compile platform
	CompileDataPath string

	// WebAuthn (Passkey)
	WebAuthnRPID     string
	WebAuthnRPOrigin string
	WebAuthnRPName   string
}

func Load() *Config {
	cfgOnce.Do(func() {
		globalCfg = &Config{
			Environment: getEnv("ENVIRONMENT", "development"),
			Port:        getEnv("PORT", "8080"),
			Version:     getEnv("VERSION", "0.1.0"),

			DatabaseURL: getEnv("DATABASE_URL", "postgres://compile:compile_dev_password@localhost:5432/compile?sslmode=disable"),
			RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379"),

			JWTSecret:        getEnv("JWT_SECRET", "compile-dev-jwt-secret-change-in-production"),
			JWTRefreshSecret: getEnv("JWT_REFRESH_SECRET", "compile-dev-refresh-secret-change-in-production"),
			JWTExpiration:    getEnvInt("JWT_EXPIRATION_HOURS", 24),

			RateLimit: getEnvInt("RATE_LIMIT", 100),

			MLServiceURL: getEnv("ML_SERVICE_URL", "http://localhost:8000"),

			StripeSecretKey:     getEnv("STRIPE_SECRET_KEY", ""),
			StripeWebhookSecret: getEnv("STRIPE_WEBHOOK_SECRET", ""),

			AWSRegion:          getEnv("AWS_REGION", "us-east-1"),
			AWSAccessKeyID:     getEnv("AWS_ACCESS_KEY_ID", ""),
			AWSSecretAccessKey: getEnv("AWS_SECRET_ACCESS_KEY", ""),
			S3Bucket:           getEnv("S3_BUCKET", "compile-models"),

			OpenAIAPIKey: getEnv("OPENAI_API_KEY", ""),
			OpenAIOrgID:  getEnv("OPENAI_ORG_ID", ""),

			CompileDataPath: getEnv("COMPILE_DATA_PATH", "data/compile_platform_data.json"),

			WebAuthnRPID:     getEnv("WEBAUTHN_RP_ID", "localhost"),
			WebAuthnRPOrigin: getEnv("WEBAUTHN_RP_ORIGIN", "http://localhost:3000"),
			WebAuthnRPName:   getEnv("WEBAUTHN_RP_NAME", "Compile"),
		}
	})
	return globalCfg
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
