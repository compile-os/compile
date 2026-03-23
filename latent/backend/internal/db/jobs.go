package db

import (
	"database/sql"
	"encoding/json"
	"time"
)

// EvolutionJobRow represents a row in the evolution_jobs table.
type EvolutionJobRow struct {
	ID              string
	UserID          sql.NullString
	FitnessFunction string
	Seed            int
	Generations     int
	MutationsPerGen int
	Status          string
	Progress        int
	CurrentFitness  float64
	AcceptedCount   int
	Result          json.RawMessage
	Error           sql.NullString
	WorkerJobID     sql.NullString
	CreatedAt       time.Time
	UpdatedAt       time.Time
	CompletedAt     sql.NullTime
}

// CreateEvolutionJob inserts a new evolution job.
func CreateEvolutionJob(job *EvolutionJobRow) error {
	db := Get()
	if db == nil {
		return nil // No DB configured, use in-memory fallback
	}

	_, err := db.Exec(`
		INSERT INTO evolution_jobs (id, user_id, fitness_function, seed, generations, mutations_per_gen, status, worker_job_id)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
	`, job.ID, job.UserID, job.FitnessFunction, job.Seed, job.Generations, job.MutationsPerGen, job.Status, job.WorkerJobID)
	return err
}

// GetEvolutionJob retrieves a job by ID.
func GetEvolutionJob(id string) (*EvolutionJobRow, error) {
	db := Get()
	if db == nil {
		return nil, nil
	}

	row := db.QueryRow(`
		SELECT id, user_id, fitness_function, seed, generations, mutations_per_gen,
		       status, progress, current_fitness, accepted_count, result, error,
		       worker_job_id, created_at, updated_at, completed_at
		FROM evolution_jobs WHERE id = $1
	`, id)

	var j EvolutionJobRow
	err := row.Scan(
		&j.ID, &j.UserID, &j.FitnessFunction, &j.Seed, &j.Generations, &j.MutationsPerGen,
		&j.Status, &j.Progress, &j.CurrentFitness, &j.AcceptedCount, &j.Result, &j.Error,
		&j.WorkerJobID, &j.CreatedAt, &j.UpdatedAt, &j.CompletedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	return &j, err
}

// UpdateJobProgress updates the progress fields of a running job.
func UpdateJobProgress(id string, progress int, fitness float64, accepted int) error {
	db := Get()
	if db == nil {
		return nil
	}

	_, err := db.Exec(`
		UPDATE evolution_jobs
		SET progress = $2, current_fitness = $3, accepted_count = $4, status = 'running'
		WHERE id = $1
	`, id, progress, fitness, accepted)
	return err
}

// CompleteJob marks a job as completed with results.
func CompleteJob(id string, result json.RawMessage) error {
	db := Get()
	if db == nil {
		return nil
	}

	_, err := db.Exec(`
		UPDATE evolution_jobs
		SET status = 'completed', progress = 100, result = $2, completed_at = NOW()
		WHERE id = $1
	`, id, result)
	return err
}

// FailJob marks a job as failed with an error message.
func FailJob(id string, errMsg string) error {
	db := Get()
	if db == nil {
		return nil
	}

	_, err := db.Exec(`
		UPDATE evolution_jobs
		SET status = 'failed', error = $2, completed_at = NOW()
		WHERE id = $1
	`, id, errMsg)
	return err
}
