-- Longitudinal Clinical Copilot - Migration v2
-- Adds evidence type, reasoning, and transcript line columns for better signal tracking
-- Run this in Supabase SQL Editor after the initial schema

-- ============================================================================
-- UPDATE CLINICAL SIGNALS TABLE
-- Add new columns for evidence type and reasoning
-- ============================================================================

-- Add evidence_type column (observed, self_reported, inferred)
ALTER TABLE clinical_signals
ADD COLUMN IF NOT EXISTS evidence_type VARCHAR(20) DEFAULT 'inferred';

-- Add reasoning column for explaining clinical significance
ALTER TABLE clinical_signals
ADD COLUMN IF NOT EXISTS reasoning TEXT;

-- Add transcript_line for approximate line number in transcript
ALTER TABLE clinical_signals
ADD COLUMN IF NOT EXISTS transcript_line INTEGER;

-- ============================================================================
-- UPDATE DIAGNOSTIC HYPOTHESES TABLE
-- Add limitations column for transparency about what can't be assessed
-- ============================================================================

-- Add limitations column
ALTER TABLE diagnostic_hypotheses
ADD COLUMN IF NOT EXISTS limitations TEXT;

-- ============================================================================
-- CREATE INDEX FOR FASTER EVIDENCE QUERIES
-- ============================================================================

-- Index for querying signals by evidence type
CREATE INDEX IF NOT EXISTS ix_signals_evidence_type
ON clinical_signals(patient_id, evidence_type);

-- Index for querying signals by clinical significance
CREATE INDEX IF NOT EXISTS ix_signals_significance
ON clinical_signals(patient_id, clinical_significance);

-- ============================================================================
-- UPDATE ALEMBIC VERSION
-- ============================================================================
UPDATE alembic_version SET version_num = 'v2_evidence_types';

-- ============================================================================
-- SUMMARY OF CHANGES
-- ============================================================================
-- clinical_signals:
--   + evidence_type VARCHAR(20) DEFAULT 'inferred'
--   + reasoning TEXT
--   + transcript_line INTEGER
--
-- diagnostic_hypotheses:
--   + limitations TEXT
--
-- New Indexes:
--   + ix_signals_evidence_type
--   + ix_signals_significance
