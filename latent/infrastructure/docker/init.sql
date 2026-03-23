-- Latent Database Schema
-- PostgreSQL 16

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    company VARCHAR(255),
    plan VARCHAR(20) DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'enterprise')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Passkey credentials (supports multiple per user)
CREATE TABLE IF NOT EXISTS credentials (
    id BYTEA PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) DEFAULT 'Passkey',
    public_key BYTEA NOT NULL,
    attestation_type VARCHAR(50),
    transports TEXT[],
    sign_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON credentials(user_id);

-- API Keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(128) NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,
    scopes TEXT[] DEFAULT ARRAY['embed', 'models'],
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);

-- Neural Models
CREATE TABLE IF NOT EXISTS models (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version VARCHAR(20) NOT NULL,
    type VARCHAR(20) DEFAULT 'foundation' CHECK (type IN ('foundation', 'fine-tuned')),
    parameters BIGINT,
    embedding_dim INTEGER,
    max_channels INTEGER,
    max_sample_rate INTEGER,
    device_types TEXT[],
    s3_path VARCHAR(500),
    is_public BOOLEAN DEFAULT false,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Fine-tuning Jobs
CREATE TABLE IF NOT EXISTS fine_tune_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    base_model_id VARCHAR(50) REFERENCES models(id),
    result_model_id VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    training_file VARCHAR(500) NOT NULL,
    validation_file VARCHAR(500),
    hyperparameters JSONB DEFAULT '{}',
    metrics JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_fine_tune_jobs_user_id ON fine_tune_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_fine_tune_jobs_status ON fine_tune_jobs(status);

-- Usage Tracking
CREATE TABLE IF NOT EXISTS usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
    model_id VARCHAR(50) REFERENCES models(id),
    endpoint VARCHAR(50) NOT NULL,
    inference_units INTEGER NOT NULL,
    channel_hours DECIMAL(10, 4) NOT NULL,
    processing_ms INTEGER,
    request_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_created_at ON usage(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage(user_id, date_trunc('month', created_at));

-- Monthly Usage Aggregates (for billing)
CREATE TABLE IF NOT EXISTS usage_monthly (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    month DATE NOT NULL, -- First day of month
    inference_units BIGINT DEFAULT 0,
    channel_hours DECIMAL(12, 4) DEFAULT 0,
    fine_tune_jobs INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls BIGINT DEFAULT 0,
    estimated_cost_usd DECIMAL(10, 2),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (user_id, month)
);

CREATE INDEX IF NOT EXISTS idx_usage_monthly_user_month ON usage_monthly(user_id, month);

-- Billing (Stripe integration)
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id VARCHAR(100) UNIQUE,
    stripe_customer_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'past_due', 'trialing')),
    plan VARCHAR(20) NOT NULL,
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_id ON subscriptions(stripe_subscription_id);

-- Insert default foundation model
INSERT INTO models (id, name, description, version, type, parameters, embedding_dim, max_channels, max_sample_rate, device_types, is_public)
VALUES (
    'compile-v0.1',
    'Latent Foundation Model v0.1',
    'Initial release of the neural foundation model. Pre-trained on TUH EEG Corpus and MOABB datasets. Supports zero-shot cross-subject transfer for motor imagery, cognitive state classification, and general neural embedding.',
    '0.1.0',
    'foundation',
    125000000,
    768,
    256,
    2048,
    ARRAY['eeg', 'ecog', 'intracortical', 'seeg', 'meg', 'fnirs'],
    true
) ON CONFLICT (id) DO NOTHING;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fine_tune_jobs_updated_at
    BEFORE UPDATE ON fine_tune_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Evolution jobs (compile pipeline)
CREATE TABLE IF NOT EXISTS evolution_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    fitness_function VARCHAR(50) NOT NULL,
    seed INTEGER NOT NULL,
    generations INTEGER NOT NULL DEFAULT 50,
    mutations_per_gen INTEGER NOT NULL DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    progress INTEGER DEFAULT 0,
    current_fitness DOUBLE PRECISION DEFAULT 0,
    accepted_count INTEGER DEFAULT 0,
    result JSONB,
    error TEXT,
    worker_job_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_evolution_jobs_user_id ON evolution_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_evolution_jobs_status ON evolution_jobs(status);

CREATE TRIGGER update_evolution_jobs_updated_at
    BEFORE UPDATE ON evolution_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
