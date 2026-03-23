package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/golang-jwt/jwt/v5"
	"github.com/latent-labs/latent-api/internal/config"
	"github.com/latent-labs/latent-api/internal/db"
)

// RefreshToken generates new access token from refresh token.
// This is shared between passkey and any future auth methods.
func RefreshToken(c *gin.Context) {
	var req struct {
		RefreshToken string `json:"refresh_token" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	secret := []byte(config.Get().JWTRefreshSecret)

	token, err := jwt.Parse(req.RefreshToken, func(token *jwt.Token) (interface{}, error) {
		return secret, nil
	})

	if err != nil || !token.Valid {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error":   "invalid_token",
			"message": "Invalid refresh token",
		})
		return
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error":   "invalid_token",
			"message": "Invalid token claims",
		})
		return
	}

	userID := claims["sub"].(string)

	// Look up user from database
	user, err := db.GetUserByID(userID)
	email := ""
	if err == nil && user != nil && user.Email.Valid {
		email = user.Email.String
	}

	accessToken, err := GenerateAccessToken(userID, email)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "internal_error",
			"message": "Failed to generate access token",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token": accessToken,
		"token_type":   "Bearer",
		"expires_in":   86400,
	})
}

// GenerateAccessToken creates a JWT access token. Exported for use by passkey handler.
func GenerateAccessToken(userID, email string) (string, error) {
	secret := []byte(config.Get().JWTSecret)

	claims := jwt.MapClaims{
		"sub":   userID,
		"email": email,
		"type":  "access",
		"iat":   time.Now().Unix(),
		"exp":   time.Now().Add(24 * time.Hour).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(secret)
}

// GenerateRefreshToken creates a JWT refresh token. Exported for use by passkey handler.
func GenerateRefreshToken(userID string) (string, error) {
	secret := []byte(config.Get().JWTRefreshSecret)

	claims := jwt.MapClaims{
		"sub":  userID,
		"type": "refresh",
		"iat":  time.Now().Unix(),
		"exp":  time.Now().Add(7 * 24 * time.Hour).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(secret)
}
