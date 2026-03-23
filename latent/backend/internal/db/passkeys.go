package db

import (
	"database/sql"
	"time"
)

// PasskeyUserRow represents a user in the database.
type PasskeyUserRow struct {
	ID          string
	Username    string
	DisplayName string
	Email       string
	Company     string
	Plan        string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// PasskeyCredentialRow represents a WebAuthn credential in the database.
type PasskeyCredentialRow struct {
	ID              []byte
	UserID          string
	Name            string
	PublicKey       []byte
	AttestationType string
	SignCount       int
	CreatedAt       time.Time
	LastUsedAt      sql.NullTime
}

// SavePasskeyUser upserts a user.
func SavePasskeyUser(u *PasskeyUserRow) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`
		INSERT INTO users (id, username, display_name, email, company, plan)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (id) DO UPDATE SET
			display_name = EXCLUDED.display_name,
			updated_at = NOW()
	`, u.ID, u.Username, u.DisplayName, u.Email, u.Company, u.Plan)
	return err
}

// GetPasskeyUserByID returns a user by ID.
func GetPasskeyUserByID(id string) (*PasskeyUserRow, error) {
	d := Get()
	if d == nil {
		return nil, sql.ErrNoRows
	}
	var u PasskeyUserRow
	err := d.QueryRow(`
		SELECT id, username, COALESCE(display_name,''), COALESCE(email,''), COALESCE(company,''), plan, created_at, updated_at
		FROM users WHERE id = $1
	`, id).Scan(&u.ID, &u.Username, &u.DisplayName, &u.Email, &u.Company, &u.Plan, &u.CreatedAt, &u.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// GetPasskeyUserByUsername returns a user by username.
func GetPasskeyUserByUsername(username string) (*PasskeyUserRow, error) {
	d := Get()
	if d == nil {
		return nil, sql.ErrNoRows
	}
	var u PasskeyUserRow
	err := d.QueryRow(`
		SELECT id, username, COALESCE(display_name,''), COALESCE(email,''), COALESCE(company,''), plan, created_at, updated_at
		FROM users WHERE username = $1
	`, username).Scan(&u.ID, &u.Username, &u.DisplayName, &u.Email, &u.Company, &u.Plan, &u.CreatedAt, &u.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &u, nil
}

// DeletePasskeyUser deletes a user and their credentials.
func DeletePasskeyUser(id string) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`DELETE FROM users WHERE id = $1`, id)
	return err
}

// SavePasskeyCredential inserts a WebAuthn credential.
func SavePasskeyCredential(c *PasskeyCredentialRow) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`
		INSERT INTO credentials (id, user_id, name, public_key, attestation_type, sign_count)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (id) DO UPDATE SET sign_count = EXCLUDED.sign_count
	`, c.ID, c.UserID, c.Name, c.PublicKey, c.AttestationType, c.SignCount)
	return err
}

// GetPasskeyCredentialsByUserID returns all credentials for a user.
func GetPasskeyCredentialsByUserID(userID string) ([]*PasskeyCredentialRow, error) {
	d := Get()
	if d == nil {
		return nil, nil
	}
	rows, err := d.Query(`
		SELECT id, user_id, COALESCE(name,''), public_key, COALESCE(attestation_type,''), sign_count, created_at
		FROM credentials WHERE user_id = $1
	`, userID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var creds []*PasskeyCredentialRow
	for rows.Next() {
		var c PasskeyCredentialRow
		if err := rows.Scan(&c.ID, &c.UserID, &c.Name, &c.PublicKey, &c.AttestationType, &c.SignCount, &c.CreatedAt); err != nil {
			continue
		}
		creds = append(creds, &c)
	}
	return creds, nil
}

// UpdateCredentialSignCount updates the sign count and last used time.
func UpdateCredentialSignCount(credID []byte, signCount int) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`
		UPDATE credentials SET sign_count = $2, last_used = NOW() WHERE id = $1
	`, credID, signCount)
	return err
}

// DeletePasskeyCredential removes a credential.
func DeletePasskeyCredential(userID string, credID []byte) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`DELETE FROM credentials WHERE user_id = $1 AND id = $2`, userID, credID)
	return err
}

// LoadAllPasskeyUsers loads all users from DB (for warm-starting the in-memory cache).
func LoadAllPasskeyUsers() ([]*PasskeyUserRow, error) {
	d := Get()
	if d == nil {
		return nil, nil
	}
	rows, err := d.Query(`SELECT id, username, COALESCE(display_name,''), COALESCE(email,''), COALESCE(company,''), plan, created_at, updated_at FROM users`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var users []*PasskeyUserRow
	for rows.Next() {
		var u PasskeyUserRow
		if err := rows.Scan(&u.ID, &u.Username, &u.DisplayName, &u.Email, &u.Company, &u.Plan, &u.CreatedAt, &u.UpdatedAt); err != nil {
			continue
		}
		users = append(users, &u)
	}
	return users, nil
}
