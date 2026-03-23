package handlers

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/go-webauthn/webauthn/protocol"
	"github.com/go-webauthn/webauthn/webauthn"
	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
	"github.com/latent-labs/latent-api/internal/config"
	"github.com/latent-labs/latent-api/internal/db"
)

// PasskeyAuthHandler handles WebAuthn passkey authentication
type PasskeyAuthHandler struct {
	webAuthn     *webauthn.WebAuthn
	sessionStore map[string]*webauthn.SessionData
	mu           sync.RWMutex
	// In production, these would be database operations
	users       map[uuid.UUID]*PasskeyUser
	credentials map[uuid.UUID][]*PasskeyCredential
}

// PasskeyUser implements webauthn.User interface
type PasskeyUser struct {
	ID          uuid.UUID `json:"id"`
	Username    string    `json:"username"`
	DisplayName string    `json:"display_name"`
	Email       string    `json:"email,omitempty"`
	Company     string    `json:"company,omitempty"`
	Plan        string    `json:"plan"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// WebAuthn interface implementation
func (u *PasskeyUser) WebAuthnID() []byte {
	return u.ID[:]
}

func (u *PasskeyUser) WebAuthnName() string {
	return u.Username
}

func (u *PasskeyUser) WebAuthnDisplayName() string {
	if u.DisplayName != "" {
		return u.DisplayName
	}
	return u.Username
}

func (u *PasskeyUser) WebAuthnCredentials() []webauthn.Credential {
	// This will be populated from database in real implementation
	return []webauthn.Credential{}
}

func (u *PasskeyUser) WebAuthnIcon() string {
	return ""
}

// PasskeyCredential stores credential data
type PasskeyCredential struct {
	ID              []byte    `json:"id"`
	UserID          uuid.UUID `json:"user_id"`
	Name            string    `json:"name"` // Friendly name like "MacBook Pro", "iPhone"
	PublicKey       []byte    `json:"public_key"`
	AttestationType string    `json:"attestation_type"`
	Transports      []string  `json:"transports"`
	SignCount       uint32    `json:"sign_count"`
	CreatedAt       time.Time `json:"created_at"`
	LastUsedAt      *time.Time `json:"last_used_at,omitempty"`
}

// NewPasskeyAuthHandler creates a new passkey auth handler
func NewPasskeyAuthHandler(rpID, rpOrigin, rpName string) (*PasskeyAuthHandler, error) {
	wconfig := &webauthn.Config{
		RPDisplayName: rpName,
		RPID:          rpID,
		RPOrigins:     []string{rpOrigin},
		AuthenticatorSelection: protocol.AuthenticatorSelection{
			AuthenticatorAttachment: protocol.CrossPlatform,
			UserVerification:        protocol.VerificationPreferred,
			ResidentKey:             protocol.ResidentKeyRequirementPreferred,
		},
		AttestationPreference: protocol.PreferNoAttestation,
		Timeouts: webauthn.TimeoutsConfig{
			Login: webauthn.TimeoutConfig{
				Enforce:    true,
				Timeout:    60 * time.Second,
				TimeoutUVD: 60 * time.Second,
			},
			Registration: webauthn.TimeoutConfig{
				Enforce:    true,
				Timeout:    120 * time.Second,
				TimeoutUVD: 120 * time.Second,
			},
		},
	}

	wa, err := webauthn.New(wconfig)
	if err != nil {
		return nil, err
	}

	return &PasskeyAuthHandler{
		webAuthn:     wa,
		sessionStore: make(map[string]*webauthn.SessionData),
		users:        make(map[uuid.UUID]*PasskeyUser),
		credentials:  make(map[uuid.UUID][]*PasskeyCredential),
	}, nil
}

// BeginRegistration starts the passkey registration process
func (h *PasskeyAuthHandler) BeginRegistration(c *gin.Context) {
	var req struct {
		Username    string `json:"username" binding:"required,min=3,max=50"`
		DisplayName string `json:"display_name,omitempty"`
		Email       string `json:"email,omitempty"`
		Company     string `json:"company,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	// Check if username exists with completed registration
	existingUser := h.getUserByUsername(req.Username)
	if existingUser != nil {
		creds := h.getCredentialsByUserID(existingUser.ID)
		if len(creds) > 0 {
			c.JSON(http.StatusConflict, gin.H{
				"error":   "username_taken",
				"message": "Username is already registered. Use login instead.",
			})
			return
		}
		// Orphaned user - delete and recreate
		h.deleteUser(existingUser.ID)
	}

	// Create new user
	user := &PasskeyUser{
		ID:          uuid.New(),
		Username:    req.Username,
		DisplayName: req.DisplayName,
		Email:       req.Email,
		Company:     req.Company,
		Plan:        "free",
		CreatedAt:   time.Now(),
		UpdatedAt:   time.Now(),
	}

	h.saveUser(user)

	// Generate WebAuthn registration options
	options, session, err := h.webAuthn.BeginRegistration(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "webauthn_error",
			"message": "Failed to begin registration: " + err.Error(),
		})
		return
	}

	// Store session for verification
	sessionID := uuid.New().String()
	h.mu.Lock()
	h.sessionStore[sessionID] = session
	h.mu.Unlock()

	// Clean up session after 2 minutes
	go func() {
		time.Sleep(2 * time.Minute)
		h.mu.Lock()
		delete(h.sessionStore, sessionID)
		h.mu.Unlock()
	}()

	c.JSON(http.StatusOK, gin.H{
		"options":    options,
		"user_id":    user.ID.String(),
		"session_id": sessionID,
	})
}

// FinishRegistration completes the passkey registration
func (h *PasskeyAuthHandler) FinishRegistration(c *gin.Context) {
	var req struct {
		SessionID      string `json:"session_id" binding:"required"`
		UserID         string `json:"user_id" binding:"required"`
		CredentialName string `json:"credential_name,omitempty"`
	}

	// First parse the JSON to get session_id and user_id
	body, err := c.GetRawData()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "parse_error",
			"message": "Failed to read request body",
		})
		return
	}

	// Parse our custom fields
	if err := json.Unmarshal(body, &req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Invalid user_id",
		})
		return
	}

	// Get session
	h.mu.RLock()
	session, exists := h.sessionStore[req.SessionID]
	h.mu.RUnlock()

	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "session_expired",
			"message": "Registration session expired. Please start again.",
		})
		return
	}

	// Get user
	user := h.getUserByID(userID)
	if user == nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "user_not_found",
			"message": "User not found",
		})
		return
	}

	// Parse the credential from the request body
	parsedResponse, err := protocol.ParseCredentialCreationResponseBody(c.Request.Body)
	if err != nil {
		// Try parsing from the body we already read
		c.Request.Body = nil // Reset
		// For SimpleWebAuthn, the credential is in the response field
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "parse_error",
			"message": "Failed to parse credential: " + err.Error(),
		})
		return
	}

	// Verify the credential
	credential, err := h.webAuthn.CreateCredential(user, *session, parsedResponse)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "verification_error",
			"message": "Failed to verify credential: " + err.Error(),
		})
		return
	}

	// Save credential
	credName := req.CredentialName
	if credName == "" {
		credName = "Passkey " + time.Now().Format("Jan 2, 2006")
	}

	// Convert transports
	transports := make([]string, len(credential.Transport))
	for i, t := range credential.Transport {
		transports[i] = string(t)
	}

	storedCred := &PasskeyCredential{
		ID:              credential.ID,
		UserID:          userID,
		Name:            credName,
		PublicKey:       credential.PublicKey,
		AttestationType: string(credential.AttestationType),
		Transports:      transports,
		SignCount:       credential.Authenticator.SignCount,
		CreatedAt:       time.Now(),
	}

	h.saveCredential(storedCred)

	// Delete session
	h.mu.Lock()
	delete(h.sessionStore, req.SessionID)
	h.mu.Unlock()

	// Generate JWT
	token, err := h.generateToken(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "token_error",
			"message": "Failed to generate token",
		})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"token":      token,
		"token_type": "Bearer",
		"expires_in": 86400,
		"user": gin.H{
			"id":           user.ID.String(),
			"username":     user.Username,
			"display_name": user.DisplayName,
			"email":        user.Email,
			"company":      user.Company,
			"plan":         user.Plan,
			"created_at":   user.CreatedAt.Format(time.RFC3339),
		},
	})
}

// BeginLogin starts the passkey authentication process
func (h *PasskeyAuthHandler) BeginLogin(c *gin.Context) {
	var req struct {
		Username string `json:"username" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	// Get user
	user := h.getUserByUsername(req.Username)
	if user == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "user_not_found",
			"message": "User not found",
		})
		return
	}

	// Get all credentials for user
	storedCreds := h.getCredentialsByUserID(user.ID)
	if len(storedCreds) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "no_credentials",
			"message": "No passkeys registered for this user",
		})
		return
	}

	// Convert to WebAuthn credentials
	webAuthnCreds := make([]webauthn.Credential, len(storedCreds))
	for i, cred := range storedCreds {
		transports := make([]protocol.AuthenticatorTransport, len(cred.Transports))
		for j, t := range cred.Transports {
			transports[j] = protocol.AuthenticatorTransport(t)
		}

		webAuthnCreds[i] = webauthn.Credential{
			ID:              cred.ID,
			PublicKey:       cred.PublicKey,
			AttestationType: cred.AttestationType,
			Transport:       transports,
			Authenticator: webauthn.Authenticator{
				SignCount: cred.SignCount,
			},
		}
	}

	// Create a user wrapper that returns the credentials
	userWithCreds := &userWithCredentials{
		PasskeyUser: user,
		credentials: webAuthnCreds,
	}

	// Generate WebAuthn login options
	options, session, err := h.webAuthn.BeginLogin(userWithCreds)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "webauthn_error",
			"message": "Failed to begin login: " + err.Error(),
		})
		return
	}

	// Store session
	sessionID := uuid.New().String()
	h.mu.Lock()
	h.sessionStore[sessionID] = session
	h.mu.Unlock()

	// Clean up session after 1 minute
	go func() {
		time.Sleep(1 * time.Minute)
		h.mu.Lock()
		delete(h.sessionStore, sessionID)
		h.mu.Unlock()
	}()

	c.JSON(http.StatusOK, gin.H{
		"options":    options,
		"user_id":    user.ID.String(),
		"session_id": sessionID,
	})
}

// FinishLogin completes the passkey authentication
func (h *PasskeyAuthHandler) FinishLogin(c *gin.Context) {
	var req struct {
		SessionID string `json:"session_id" binding:"required"`
		UserID    string `json:"user_id" binding:"required"`
	}

	body, err := c.GetRawData()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "parse_error",
			"message": "Failed to read request body",
		})
		return
	}

	if err := json.Unmarshal(body, &req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": err.Error(),
		})
		return
	}

	userID, err := uuid.Parse(req.UserID)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "Invalid user_id",
		})
		return
	}

	// Get session
	h.mu.RLock()
	session, exists := h.sessionStore[req.SessionID]
	h.mu.RUnlock()

	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "session_expired",
			"message": "Login session expired. Please start again.",
		})
		return
	}

	// Get user and credentials
	user := h.getUserByID(userID)
	if user == nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "user_not_found",
			"message": "User not found",
		})
		return
	}

	storedCreds := h.getCredentialsByUserID(userID)
	webAuthnCreds := make([]webauthn.Credential, len(storedCreds))
	for i, cred := range storedCreds {
		transports := make([]protocol.AuthenticatorTransport, len(cred.Transports))
		for j, t := range cred.Transports {
			transports[j] = protocol.AuthenticatorTransport(t)
		}

		webAuthnCreds[i] = webauthn.Credential{
			ID:              cred.ID,
			PublicKey:       cred.PublicKey,
			AttestationType: cred.AttestationType,
			Transport:       transports,
			Authenticator: webauthn.Authenticator{
				SignCount: cred.SignCount,
			},
		}
	}

	userWithCreds := &userWithCredentials{
		PasskeyUser: user,
		credentials: webAuthnCreds,
	}

	// Parse credential assertion
	parsedResponse, err := protocol.ParseCredentialRequestResponseBody(c.Request.Body)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "parse_error",
			"message": "Failed to parse assertion: " + err.Error(),
		})
		return
	}

	// Verify the assertion
	credential, err := h.webAuthn.ValidateLogin(userWithCreds, *session, parsedResponse)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "verification_error",
			"message": "Failed to verify assertion: " + err.Error(),
		})
		return
	}

	// Update sign count
	h.updateCredentialSignCount(credential.ID, credential.Authenticator.SignCount)

	// Delete session
	h.mu.Lock()
	delete(h.sessionStore, req.SessionID)
	h.mu.Unlock()

	// Generate JWT
	token, err := h.generateToken(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "token_error",
			"message": "Failed to generate token",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"token":      token,
		"token_type": "Bearer",
		"expires_in": 86400,
		"user": gin.H{
			"id":           user.ID.String(),
			"username":     user.Username,
			"display_name": user.DisplayName,
			"email":        user.Email,
			"company":      user.Company,
			"plan":         user.Plan,
			"created_at":   user.CreatedAt.Format(time.RFC3339),
		},
	})
}

// CheckUserExists checks if a username has completed registration
func (h *PasskeyAuthHandler) CheckUserExists(c *gin.Context) {
	username := c.Query("username")
	if username == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "validation_error",
			"message": "username query parameter required",
		})
		return
	}

	user := h.getUserByUsername(username)
	if user == nil {
		c.JSON(http.StatusOK, gin.H{"exists": false})
		return
	}

	// Check if user has any credentials
	creds := h.getCredentialsByUserID(user.ID)
	c.JSON(http.StatusOK, gin.H{
		"exists":    len(creds) > 0,
		"user_id":   user.ID.String(),
		"num_passkeys": len(creds),
	})
}

// ListUserPasskeys returns all passkeys for the authenticated user
func (h *PasskeyAuthHandler) ListUserPasskeys(c *gin.Context) {
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "unauthorized",
		})
		return
	}

	userID, err := uuid.Parse(userIDStr.(string))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid user_id",
		})
		return
	}

	creds := h.getCredentialsByUserID(userID)
	passkeys := make([]gin.H, len(creds))
	for i, cred := range creds {
		passkeys[i] = gin.H{
			"id":         cred.ID,
			"name":       cred.Name,
			"transports": cred.Transports,
			"created_at": cred.CreatedAt.Format(time.RFC3339),
			"last_used":  cred.LastUsedAt,
		}
	}

	c.JSON(http.StatusOK, gin.H{
		"passkeys": passkeys,
	})
}

// AddPasskey adds a new passkey to an existing user account
func (h *PasskeyAuthHandler) AddPasskey(c *gin.Context) {
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "unauthorized",
		})
		return
	}

	userID, err := uuid.Parse(userIDStr.(string))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid user_id",
		})
		return
	}

	user := h.getUserByID(userID)
	if user == nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "user_not_found",
		})
		return
	}

	// Generate registration options
	options, session, err := h.webAuthn.BeginRegistration(user)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "webauthn_error",
			"message": err.Error(),
		})
		return
	}

	sessionID := uuid.New().String()
	h.mu.Lock()
	h.sessionStore[sessionID] = session
	h.mu.Unlock()

	go func() {
		time.Sleep(2 * time.Minute)
		h.mu.Lock()
		delete(h.sessionStore, sessionID)
		h.mu.Unlock()
	}()

	c.JSON(http.StatusOK, gin.H{
		"options":    options,
		"session_id": sessionID,
	})
}

// DeletePasskey removes a passkey from user account
func (h *PasskeyAuthHandler) DeletePasskey(c *gin.Context) {
	userIDStr, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{
			"error": "unauthorized",
		})
		return
	}

	userID, err := uuid.Parse(userIDStr.(string))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "invalid user_id",
		})
		return
	}

	credID := c.Param("id")

	// Check user has more than one passkey
	creds := h.getCredentialsByUserID(userID)
	if len(creds) <= 1 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "last_passkey",
			"message": "Cannot delete last passkey. Add another passkey first.",
		})
		return
	}

	// Delete the credential
	h.deleteCredential(userID, []byte(credID))

	c.JSON(http.StatusOK, gin.H{
		"deleted": true,
	})
}

// Helper methods - in production these would be database operations

func (h *PasskeyAuthHandler) saveUser(user *PasskeyUser) {
	h.mu.Lock()
	h.users[user.ID] = user
	h.mu.Unlock()

	// Persist to DB
	db.SavePasskeyUser(&db.PasskeyUserRow{
		ID:          user.ID.String(),
		Username:    user.Username,
		DisplayName: user.DisplayName,
		Email:       user.Email,
		Company:     user.Company,
		Plan:        user.Plan,
	})
}

func (h *PasskeyAuthHandler) getUserByID(id uuid.UUID) *PasskeyUser {
	h.mu.RLock()
	if u, ok := h.users[id]; ok {
		h.mu.RUnlock()
		return u
	}
	h.mu.RUnlock()

	// Try DB
	row, err := db.GetPasskeyUserByID(id.String())
	if err != nil || row == nil {
		return nil
	}
	user := h.rowToUser(row)
	h.mu.Lock()
	h.users[id] = user
	h.mu.Unlock()
	return user
}

func (h *PasskeyAuthHandler) getUserByUsername(username string) *PasskeyUser {
	h.mu.RLock()
	for _, user := range h.users {
		if user.Username == username {
			h.mu.RUnlock()
			return user
		}
	}
	h.mu.RUnlock()

	// Try DB
	row, err := db.GetPasskeyUserByUsername(username)
	if err != nil || row == nil {
		return nil
	}
	user := h.rowToUser(row)
	h.mu.Lock()
	h.users[user.ID] = user
	h.mu.Unlock()
	return user
}

func (h *PasskeyAuthHandler) deleteUser(id uuid.UUID) {
	h.mu.Lock()
	delete(h.users, id)
	delete(h.credentials, id)
	h.mu.Unlock()
	db.DeletePasskeyUser(id.String())
}

func (h *PasskeyAuthHandler) saveCredential(cred *PasskeyCredential) {
	h.mu.Lock()
	h.credentials[cred.UserID] = append(h.credentials[cred.UserID], cred)
	h.mu.Unlock()

	db.SavePasskeyCredential(&db.PasskeyCredentialRow{
		ID:              cred.ID,
		UserID:          cred.UserID.String(),
		Name:            cred.Name,
		PublicKey:       cred.PublicKey,
		AttestationType: cred.AttestationType,
		SignCount:       int(cred.SignCount),
	})
}

func (h *PasskeyAuthHandler) getCredentialsByUserID(userID uuid.UUID) []*PasskeyCredential {
	h.mu.RLock()
	if creds, ok := h.credentials[userID]; ok && len(creds) > 0 {
		h.mu.RUnlock()
		return creds
	}
	h.mu.RUnlock()

	// Try DB
	rows, err := db.GetPasskeyCredentialsByUserID(userID.String())
	if err != nil || len(rows) == 0 {
		return nil
	}
	creds := make([]*PasskeyCredential, 0, len(rows))
	for _, r := range rows {
		creds = append(creds, &PasskeyCredential{
			ID:              r.ID,
			UserID:          userID,
			Name:            r.Name,
			PublicKey:       r.PublicKey,
			AttestationType: r.AttestationType,
			SignCount:       uint32(r.SignCount),
			CreatedAt:       r.CreatedAt,
		})
	}
	h.mu.Lock()
	h.credentials[userID] = creds
	h.mu.Unlock()
	return creds
}

func (h *PasskeyAuthHandler) updateCredentialSignCount(credID []byte, signCount uint32) {
	h.mu.Lock()
	for _, creds := range h.credentials {
		for _, cred := range creds {
			if string(cred.ID) == string(credID) {
				cred.SignCount = signCount
				now := time.Now()
				cred.LastUsedAt = &now
				break
			}
		}
	}
	h.mu.Unlock()
	db.UpdateCredentialSignCount(credID, int(signCount))
}

func (h *PasskeyAuthHandler) deleteCredential(userID uuid.UUID, credID []byte) {
	h.mu.Lock()
	creds := h.credentials[userID]
	for i, cred := range creds {
		if string(cred.ID) == string(credID) {
			h.credentials[userID] = append(creds[:i], creds[i+1:]...)
			break
		}
	}
	h.mu.Unlock()
	db.DeletePasskeyCredential(userID.String(), credID)
}

func (h *PasskeyAuthHandler) rowToUser(row *db.PasskeyUserRow) *PasskeyUser {
	id, _ := uuid.Parse(row.ID)
	return &PasskeyUser{
		ID:          id,
		Username:    row.Username,
		DisplayName: row.DisplayName,
		Email:       row.Email,
		Company:     row.Company,
		Plan:        row.Plan,
		CreatedAt:   row.CreatedAt,
		UpdatedAt:   row.UpdatedAt,
	}
}

func (h *PasskeyAuthHandler) generateToken(user *PasskeyUser) (string, error) {
	secret := []byte(config.Get().JWTSecret)

	claims := jwt.MapClaims{
		"sub":      user.ID.String(),
		"username": user.Username,
		"email":    user.Email,
		"plan":     user.Plan,
		"iat":      time.Now().Unix(),
		"exp":      time.Now().Add(24 * time.Hour).Unix(),
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	return token.SignedString(secret)
}

// userWithCredentials wraps PasskeyUser to provide credentials
type userWithCredentials struct {
	*PasskeyUser
	credentials []webauthn.Credential
}

func (u *userWithCredentials) WebAuthnCredentials() []webauthn.Credential {
	return u.credentials
}
