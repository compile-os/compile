package middleware

import (
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/latent-labs/latent-api/internal/config"
)

// CORS middleware for handling cross-origin requests
func CORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS, PATCH")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Accept, Authorization, X-Request-ID, X-API-Key")
		c.Header("Access-Control-Expose-Headers", "X-Request-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset")
		c.Header("Access-Control-Max-Age", "86400")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// RequestID middleware adds a unique request ID to each request
func RequestID() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}
		c.Set("request_id", requestID)
		c.Header("X-Request-ID", requestID)
		c.Next()
	}
}

// Logger middleware for request logging
func Logger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()

		// Log format: timestamp | status | latency | client_ip | method | path
		gin.DefaultWriter.Write([]byte(
			time.Now().Format("2006-01-02 15:04:05") +
				" | " + http.StatusText(status) +
				" | " + latency.String() +
				" | " + c.ClientIP() +
				" | " + c.Request.Method +
				" | " + path + "\n",
		))
	}
}

// Rate limiter using token bucket algorithm
type rateLimiter struct {
	visitors map[string]*visitor
	mu       sync.RWMutex
	limit    int
	window   time.Duration
}

type visitor struct {
	tokens    int
	lastReset time.Time
}

var limiter *rateLimiter

// RateLimit middleware limits requests per IP/API key
func RateLimit(requestsPerMinute int) gin.HandlerFunc {
	limiter = &rateLimiter{
		visitors: make(map[string]*visitor),
		limit:    requestsPerMinute,
		window:   time.Minute,
	}

	// Cleanup old entries periodically
	go func() {
		for range time.Tick(time.Minute * 5) {
			limiter.mu.Lock()
			for ip, v := range limiter.visitors {
				if time.Since(v.lastReset) > time.Hour {
					delete(limiter.visitors, ip)
				}
			}
			limiter.mu.Unlock()
		}
	}()

	return func(c *gin.Context) {
		// Use API key if present, otherwise use IP
		key := c.GetHeader("X-API-Key")
		if key == "" {
			key = c.ClientIP()
		}

		limiter.mu.Lock()
		v, exists := limiter.visitors[key]
		if !exists || time.Since(v.lastReset) > limiter.window {
			limiter.visitors[key] = &visitor{
				tokens:    limiter.limit - 1,
				lastReset: time.Now(),
			}
			limiter.mu.Unlock()
			c.Header("X-RateLimit-Limit", strconv.Itoa(limiter.limit))
			c.Header("X-RateLimit-Remaining", strconv.Itoa(limiter.limit-1))
			c.Next()
			return
		}

		if v.tokens <= 0 {
			limiter.mu.Unlock()
			c.Header("X-RateLimit-Limit", strconv.Itoa(limiter.limit))
			c.Header("X-RateLimit-Remaining", "0")
			c.Header("X-RateLimit-Reset", v.lastReset.Add(limiter.window).Format(time.RFC3339))
			c.JSON(http.StatusTooManyRequests, gin.H{
				"error":   "rate_limit_exceeded",
				"message": "Too many requests. Please wait before making more requests.",
			})
			c.Abort()
			return
		}

		v.tokens--
		remaining := v.tokens
		limiter.mu.Unlock()

		c.Header("X-RateLimit-Limit", strconv.Itoa(limiter.limit))
		c.Header("X-RateLimit-Remaining", strconv.Itoa(remaining))
		c.Next()
	}
}

// AuthRequired middleware validates JWT or API key authentication
func AuthRequired() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Check for API key first
		apiKey := c.GetHeader("X-API-Key")
		if apiKey != "" {
			// TODO: Validate API key against database
			// For now, just check format
			if strings.HasPrefix(apiKey, "lat_") && len(apiKey) > 20 {
				c.Set("auth_type", "api_key")
				c.Set("api_key", apiKey)
				c.Next()
				return
			}
		}

		// Check for JWT Bearer token (header or query param for SSE)
		authHeader := c.GetHeader("Authorization")
		var tokenString string

		if authHeader != "" {
			parts := strings.Split(authHeader, " ")
			if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
				c.JSON(http.StatusUnauthorized, gin.H{
					"error":   "invalid_token",
					"message": "Invalid Authorization header format. Expected: Bearer <token>",
				})
				c.Abort()
				return
			}
			tokenString = parts[1]
		} else if queryToken := c.Query("token"); queryToken != "" {
			// SSE (EventSource) cannot send headers, so accept token as query param
			tokenString = queryToken
		} else {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "unauthorized",
				"message": "Missing authentication. Provide either X-API-Key header or Authorization Bearer token.",
			})
			c.Abort()
			return
		}

		// Parse and validate JWT
		secret := []byte(config.Get().JWTSecret)

		token, err := jwt.Parse(tokenString, func(token *jwt.Token) (interface{}, error) {
			if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
				return nil, jwt.ErrSignatureInvalid
			}
			return secret, nil
		})

		if err != nil || !token.Valid {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error":   "invalid_token",
				"message": "Invalid or expired token.",
			})
			c.Abort()
			return
		}

		// Extract claims
		if claims, ok := token.Claims.(jwt.MapClaims); ok {
			c.Set("auth_type", "jwt")
			c.Set("user_id", claims["sub"])
			c.Set("email", claims["email"])
		}

		c.Next()
	}
}
