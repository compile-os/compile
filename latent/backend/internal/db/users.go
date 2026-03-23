package db

import (
	"database/sql"
	"time"
)

type UserRow struct {
	ID          string
	Username    string
	DisplayName sql.NullString
	Email       sql.NullString
	Company     sql.NullString
	Plan        string
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

// CreateUser inserts a new user. Returns error if email/username already exists.
func CreateUser(id, username, email, displayName, company string, passwordHash []byte) error {
	d := Get()
	if d == nil {
		return nil
	}
	_, err := d.Exec(`
		INSERT INTO users (id, username, display_name, email, company, plan)
		VALUES ($1, $2, $3, $4, $5, 'free')
	`, id, username, displayName, email, company)
	// Store password hash — add column if not exists, or use a separate table
	// For now, store in a simple way since the schema doesn't have password_hash
	if err == nil {
		_, _ = d.Exec(`
			CREATE TABLE IF NOT EXISTS user_passwords (
				user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
				password_hash BYTEA NOT NULL
			)
		`)
		_, _ = d.Exec(`INSERT INTO user_passwords (user_id, password_hash) VALUES ($1, $2)`, id, passwordHash)
	}
	return err
}

// GetUserByEmail returns a user and their password hash.
func GetUserByEmail(email string) (*UserRow, []byte, error) {
	d := Get()
	if d == nil {
		return nil, nil, sql.ErrNoRows
	}
	var user UserRow
	var passwordHash []byte
	err := d.QueryRow(`
		SELECT u.id, u.username, u.display_name, u.email, u.company, u.plan, u.created_at, u.updated_at, COALESCE(p.password_hash, ''::bytea)
		FROM users u
		LEFT JOIN user_passwords p ON p.user_id = u.id
		WHERE u.email = $1
	`, email).Scan(&user.ID, &user.Username, &user.DisplayName, &user.Email, &user.Company, &user.Plan, &user.CreatedAt, &user.UpdatedAt, &passwordHash)
	if err != nil {
		return nil, nil, err
	}
	return &user, passwordHash, nil
}

// GetUserByID returns a user by ID.
func GetUserByID(id string) (*UserRow, error) {
	d := Get()
	if d == nil {
		return nil, sql.ErrNoRows
	}
	var user UserRow
	err := d.QueryRow(`
		SELECT id, username, display_name, email, company, plan, created_at, updated_at
		FROM users WHERE id = $1
	`, id).Scan(&user.ID, &user.Username, &user.DisplayName, &user.Email, &user.Company, &user.Plan, &user.CreatedAt, &user.UpdatedAt)
	if err != nil {
		return nil, err
	}
	return &user, nil
}
