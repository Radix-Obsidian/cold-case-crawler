-- Murder Index Database Schema
-- Run this in your Supabase SQL editor

-- Drop existing tables if they exist (careful in production!)
DROP TABLE IF EXISTS case_sources CASCADE;
DROP TABLE IF EXISTS case_evidence CASCADE;
DROP TABLE IF EXISTS case_victims CASCADE;
DROP TABLE IF EXISTS case_files CASCADE;

-- Core case files table
CREATE TABLE case_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    case_type VARCHAR(50) NOT NULL DEFAULT 'homicide', -- homicide, missing_person, unidentified
    status VARCHAR(50) NOT NULL DEFAULT 'unsolved', -- unsolved, solved, cold
    
    -- Dates
    date_occurred DATE,
    date_reported DATE,
    date_closed DATE,
    
    -- Location
    city VARCHAR(200),
    county VARCHAR(200),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'USA',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Details
    summary TEXT,
    raw_content TEXT,
    
    -- Metadata
    source_dataset VARCHAR(100), -- kaggle_homicide, virginia_cold_case, namus, etc.
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Victims table
CREATE TABLE case_victims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_file_id UUID REFERENCES case_files(id) ON DELETE CASCADE,
    
    -- Identity
    name VARCHAR(300),
    alias VARCHAR(300),
    age_min INTEGER,
    age_max INTEGER,
    gender VARCHAR(20),
    race VARCHAR(50),
    ethnicity VARCHAR(100),
    
    -- Physical description
    height_inches INTEGER,
    weight_lbs INTEGER,
    hair_color VARCHAR(50),
    eye_color VARCHAR(50),
    distinguishing_marks TEXT,
    
    -- Media
    photo_url TEXT,
    photo_local_path TEXT,
    
    -- Status
    victim_type VARCHAR(50) DEFAULT 'victim', -- victim, missing, unidentified
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Evidence table
CREATE TABLE case_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_file_id UUID REFERENCES case_files(id) ON DELETE CASCADE,
    
    evidence_type VARCHAR(50) NOT NULL, -- physical, witness, forensic, documentary, circumstantial
    description TEXT NOT NULL,
    
    -- Media
    media_url TEXT,
    media_local_path TEXT,
    media_type VARCHAR(50), -- image, document, video, audio
    
    -- Metadata
    source VARCHAR(200),
    date_collected DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Sources table (track where data came from)
CREATE TABLE case_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_file_id UUID REFERENCES case_files(id) ON DELETE CASCADE,
    
    source_name VARCHAR(200) NOT NULL,
    source_type VARCHAR(50), -- kaggle, api, scrape, manual
    url TEXT,
    
    -- Raw data storage
    raw_json JSONB,
    
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(case_file_id, source_name)
);

-- Indexes for performance
CREATE INDEX idx_case_files_status ON case_files(status);
CREATE INDEX idx_case_files_type ON case_files(case_type);
CREATE INDEX idx_case_files_state ON case_files(state);
CREATE INDEX idx_case_files_date ON case_files(date_occurred);
CREATE INDEX idx_case_files_source ON case_files(source_dataset);
CREATE INDEX idx_case_victims_case ON case_victims(case_file_id);
CREATE INDEX idx_case_evidence_case ON case_evidence(case_file_id);
CREATE INDEX idx_case_sources_case ON case_sources(case_file_id);

-- Full text search on case summaries
CREATE INDEX idx_case_files_summary_fts ON case_files USING gin(to_tsvector('english', summary));

-- Enable Row Level Security (optional, for Supabase)
ALTER TABLE case_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_victims ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_sources ENABLE ROW LEVEL SECURITY;

-- Public read access policies
CREATE POLICY "Public read access" ON case_files FOR SELECT USING (true);
CREATE POLICY "Public read access" ON case_victims FOR SELECT USING (true);
CREATE POLICY "Public read access" ON case_evidence FOR SELECT USING (true);
CREATE POLICY "Public read access" ON case_sources FOR SELECT USING (true);

-- Helpful views
CREATE OR REPLACE VIEW unsolved_cases AS
SELECT 
    cf.*,
    COUNT(DISTINCT cv.id) as victim_count,
    COUNT(DISTINCT ce.id) as evidence_count
FROM case_files cf
LEFT JOIN case_victims cv ON cf.id = cv.case_file_id
LEFT JOIN case_evidence ce ON cf.id = ce.case_file_id
WHERE cf.status = 'unsolved'
GROUP BY cf.id;

-- Summary stats function
CREATE OR REPLACE FUNCTION get_case_stats()
RETURNS TABLE (
    total_cases BIGINT,
    unsolved_cases BIGINT,
    missing_persons BIGINT,
    unidentified BIGINT,
    states_covered BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_cases,
        COUNT(*) FILTER (WHERE status = 'unsolved')::BIGINT as unsolved_cases,
        COUNT(*) FILTER (WHERE case_type = 'missing_person')::BIGINT as missing_persons,
        COUNT(*) FILTER (WHERE case_type = 'unidentified')::BIGINT as unidentified,
        COUNT(DISTINCT state)::BIGINT as states_covered
    FROM case_files;
END;
$$ LANGUAGE plpgsql;
