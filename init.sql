CREATE EXTENSION IF NOT EXISTS vector;

-- Generated predictions (optional, for prediction history)
CREATE TABLE IF NOT EXISTS forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_name VARCHAR(255) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    target_date TIMESTAMPTZ NOT NULL,
    temperature NUMERIC,
    humidity NUMERIC,
    pressure NUMERIC,
    wind_speed NUMERIC,
    cloud_cover NUMERIC,
    wind_direction NUMERIC,
    dew_point NUMERIC,
    precipitation NUMERIC,
    model_version VARCHAR(50)
);

-- Theoretical knowledge base for RAG (meteorological documents)
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trained models
CREATE TABLE IF NOT EXISTS models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50),
    file_path VARCHAR(500),
    trained_at TIMESTAMPTZ,
    metrics JSONB
);

CREATE INDEX IF NOT EXISTS idx_forecasts_location_date ON forecasts (location_name, predicted_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base (category);
