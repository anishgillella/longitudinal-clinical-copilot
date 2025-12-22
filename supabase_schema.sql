-- Longitudinal Clinical Copilot - Complete Database Schema
-- Run this directly in Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CLINICIAN TABLE
-- ============================================================================
CREATE TABLE clinicians (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL DEFAULT 'not-used-in-dev',
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    license_number VARCHAR(50),
    specialty VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- PATIENT TABLE
-- ============================================================================
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinician_id UUID NOT NULL REFERENCES clinicians(id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    email VARCHAR(255),
    phone VARCHAR(20),
    primary_concern TEXT,
    referral_source VARCHAR(255),
    intake_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- PATIENT HISTORY TABLE
-- ============================================================================
CREATE TABLE patient_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    history_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    occurred_at DATE,
    source VARCHAR(50) DEFAULT 'clinician_entry',
    confidence FLOAT,
    created_by UUID REFERENCES clinicians(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- VOICE SESSION TABLE
-- ============================================================================
CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID NOT NULL REFERENCES clinicians(id),
    vapi_call_id VARCHAR(255) UNIQUE,
    vapi_assistant_id VARCHAR(255) NOT NULL,
    session_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    completion_reason VARCHAR(50),
    summary TEXT,
    key_topics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- SESSION TRANSCRIPT TABLE
-- ============================================================================
CREATE TABLE session_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES voice_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp_ms INTEGER,
    speech_speed FLOAT,
    pause_duration_ms INTEGER,
    energy_level FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- AUDIO RECORDING TABLE
-- ============================================================================
CREATE TABLE audio_recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES voice_sessions(id) ON DELETE CASCADE,
    storage_type VARCHAR(20) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,
    sample_rate INTEGER,
    format VARCHAR(20),
    transcription_status VARCHAR(20) DEFAULT 'pending',
    analysis_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- CLINICAL SIGNALS TABLE
-- ============================================================================
CREATE TABLE clinical_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    signal_type VARCHAR(50) NOT NULL,
    signal_name VARCHAR(100) NOT NULL,
    evidence TEXT NOT NULL,
    transcript_offset_start INTEGER,
    transcript_offset_end INTEGER,
    intensity FLOAT NOT NULL DEFAULT 0.5,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    maps_to_domain VARCHAR(50),
    clinical_significance VARCHAR(20) DEFAULT 'moderate',
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- ASSESSMENT DOMAIN SCORES TABLE
-- ============================================================================
CREATE TABLE assessment_domain_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    domain_code VARCHAR(50) NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    raw_score FLOAT NOT NULL,
    normalized_score FLOAT NOT NULL,
    confidence FLOAT NOT NULL,
    evidence_count INTEGER DEFAULT 0,
    key_evidence TEXT,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- DIAGNOSTIC HYPOTHESES TABLE
-- ============================================================================
CREATE TABLE diagnostic_hypotheses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_code VARCHAR(50) NOT NULL,
    condition_name VARCHAR(255) NOT NULL,
    evidence_strength FLOAT NOT NULL,
    uncertainty FLOAT NOT NULL,
    supporting_signals INTEGER DEFAULT 0,
    contradicting_signals INTEGER DEFAULT 0,
    first_indicated_at TIMESTAMP WITH TIME ZONE,
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    trend VARCHAR(20),
    explanation TEXT,
    supporting_evidence JSONB,
    contradicting_evidence JSONB,
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- HYPOTHESIS HISTORY TABLE
-- ============================================================================
CREATE TABLE hypothesis_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hypothesis_id UUID NOT NULL REFERENCES diagnostic_hypotheses(id) ON DELETE CASCADE,
    session_id UUID REFERENCES voice_sessions(id) ON DELETE SET NULL,
    evidence_strength FLOAT NOT NULL,
    uncertainty FLOAT NOT NULL,
    delta_from_previous FLOAT,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- SESSION SUMMARY TABLE
-- ============================================================================
CREATE TABLE session_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    brief_summary TEXT NOT NULL,
    detailed_summary TEXT,
    key_topics JSONB,
    emotional_tone VARCHAR(50),
    notable_quotes JSONB,
    clinical_observations TEXT,
    follow_up_suggestions JSONB,
    concerns JSONB,
    safety_assessment VARCHAR(20),
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- ============================================================================
-- TIMELINE EVENTS TABLE
-- ============================================================================
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    session_id UUID REFERENCES voice_sessions(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_context VARCHAR(100),
    significance VARCHAR(20) DEFAULT 'moderate',
    impact_domains JSONB,
    source VARCHAR(50) DEFAULT 'session_extraction',
    confidence FLOAT DEFAULT 0.8,
    evidence_quotes JSONB,
    related_signal_ids JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Timeline Events Indexes
CREATE INDEX ix_timeline_patient_occurred ON timeline_events(patient_id, occurred_at);
CREATE INDEX ix_timeline_patient_type ON timeline_events(patient_id, event_type);
CREATE INDEX ix_timeline_patient_category ON timeline_events(patient_id, category);

-- ============================================================================
-- MEMORY SUMMARIES TABLE
-- ============================================================================
CREATE TABLE memory_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    summary_type VARCHAR(50) NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    summary_text TEXT NOT NULL,
    key_observations JSONB,
    domain_progress JSONB,
    concerns_raised JSONB,
    topics_covered JSONB,
    sessions_included INTEGER DEFAULT 1,
    signals_included INTEGER DEFAULT 0,
    model_version VARCHAR(100),
    supersedes_id UUID REFERENCES memory_summaries(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Memory Summaries Indexes
CREATE INDEX ix_memory_patient_period ON memory_summaries(patient_id, period_start, period_end);
CREATE INDEX ix_memory_patient_type ON memory_summaries(patient_id, summary_type);

-- ============================================================================
-- CONTEXT SNAPSHOTS TABLE
-- ============================================================================
CREATE TABLE context_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    session_id UUID REFERENCES voice_sessions(id) ON DELETE SET NULL,
    snapshot_type VARCHAR(50) DEFAULT 'pre_session',
    context_text TEXT NOT NULL,
    patient_summary JSONB,
    recent_observations JSONB,
    current_hypotheses JSONB,
    domain_status JSONB,
    exploration_priorities JSONB,
    conversation_guidelines JSONB,
    token_count INTEGER,
    model_version VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Context Snapshots Index
CREATE INDEX ix_context_patient_created ON context_snapshots(patient_id, created_at);

-- ============================================================================
-- CONVERSATION THREADS TABLE
-- ============================================================================
CREATE TABLE conversation_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    thread_topic VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    summary TEXT NOT NULL,
    first_mentioned_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_discussed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    session_mentions JSONB,
    mention_count INTEGER DEFAULT 1,
    clinical_relevance VARCHAR(20) DEFAULT 'moderate',
    follow_up_needed BOOLEAN DEFAULT false,
    follow_up_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Conversation Threads Indexes
CREATE INDEX ix_thread_patient_status ON conversation_threads(patient_id, status);
CREATE INDEX ix_thread_patient_topic ON conversation_threads(patient_id, thread_topic);

-- ============================================================================
-- CLINICIAN DASHBOARD SNAPSHOTS TABLE
-- ============================================================================
CREATE TABLE clinician_dashboard_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinician_id UUID NOT NULL REFERENCES clinicians(id) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    total_patients INTEGER DEFAULT 0,
    active_patients INTEGER DEFAULT 0,
    patients_in_assessment INTEGER DEFAULT 0,
    total_sessions_completed INTEGER DEFAULT 0,
    sessions_this_week INTEGER DEFAULT 0,
    sessions_this_month INTEGER DEFAULT 0,
    avg_session_duration_minutes FLOAT,
    assessments_in_progress INTEGER DEFAULT 0,
    assessments_completed INTEGER DEFAULT 0,
    avg_sessions_per_assessment FLOAT,
    patients_with_hypotheses INTEGER DEFAULT 0,
    high_confidence_hypotheses INTEGER DEFAULT 0,
    active_concerns INTEGER DEFAULT 0,
    urgent_concerns INTEGER DEFAULT 0,
    patients_by_status JSONB,
    sessions_by_type JSONB,
    hypotheses_distribution JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Dashboard Snapshots Index
CREATE INDEX ix_dashboard_clinician_date ON clinician_dashboard_snapshots(clinician_id, snapshot_date);

-- ============================================================================
-- PATIENT REPORTS TABLE
-- ============================================================================
CREATE TABLE patient_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id) ON DELETE SET NULL,
    report_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    report_date DATE NOT NULL,
    period_start DATE,
    period_end DATE,
    executive_summary TEXT NOT NULL,
    detailed_content JSONB,
    sessions_included INTEGER DEFAULT 0,
    signals_analyzed INTEGER DEFAULT 0,
    domain_scores_snapshot JSONB,
    hypotheses_snapshot JSONB,
    clinical_impressions TEXT,
    recommendations JSONB,
    status VARCHAR(20) DEFAULT 'draft',
    finalized_at TIMESTAMP WITH TIME ZONE,
    finalized_by UUID REFERENCES clinicians(id),
    last_exported_at TIMESTAMP WITH TIME ZONE,
    export_format VARCHAR(20),
    model_version VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Patient Reports Indexes
CREATE INDEX ix_report_patient_date ON patient_reports(patient_id, report_date);
CREATE INDEX ix_report_patient_type ON patient_reports(patient_id, report_type);

-- ============================================================================
-- ANALYTICS EVENTS TABLE
-- ============================================================================
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clinician_id UUID REFERENCES clinicians(id) ON DELETE SET NULL,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    session_id UUID REFERENCES voice_sessions(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_data JSONB,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Analytics Events Indexes
CREATE INDEX ix_analytics_clinician_date ON analytics_events(clinician_id, occurred_at);
CREATE INDEX ix_analytics_type_date ON analytics_events(event_type, occurred_at);

-- ============================================================================
-- ASSESSMENT PROGRESS TABLE
-- ============================================================================
CREATE TABLE assessment_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID NOT NULL UNIQUE REFERENCES patients(id) ON DELETE CASCADE,
    status VARCHAR(30) DEFAULT 'not_started',
    overall_completeness FLOAT DEFAULT 0.0,
    total_sessions INTEGER DEFAULT 0,
    intake_completed BOOLEAN DEFAULT false,
    last_session_date DATE,
    next_session_recommended DATE,
    domains_explored INTEGER DEFAULT 0,
    domains_total INTEGER DEFAULT 10,
    domain_coverage JSONB,
    signals_collected INTEGER DEFAULT 0,
    high_confidence_domains INTEGER DEFAULT 0,
    primary_hypothesis_strength FLOAT,
    hypothesis_stability VARCHAR(20),
    recommended_focus_areas JSONB,
    estimated_sessions_remaining INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Assessment Progress Index
CREATE INDEX ix_progress_status ON assessment_progress(status);

-- ============================================================================
-- ALEMBIC VERSION TABLE (for migration tracking)
-- ============================================================================
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    PRIMARY KEY (version_num)
);

-- Insert initial version
INSERT INTO alembic_version (version_num) VALUES ('initial_schema');

-- ============================================================================
-- SUMMARY OF TABLES CREATED
-- ============================================================================
-- Core Tables:
--   - clinicians
--   - patients
--   - patient_history
--
-- Session Tables:
--   - voice_sessions
--   - transcripts
--   - audio_recordings
--   - session_summaries
--
-- Assessment Tables:
--   - clinical_signals
--   - assessment_domain_scores
--   - diagnostic_hypotheses
--   - hypothesis_history
--
-- Memory Tables:
--   - timeline_events
--   - memory_summaries
--   - context_snapshots
--   - conversation_threads
--
-- Analytics Tables:
--   - clinician_dashboard_snapshots
--   - patient_reports
--   - analytics_events
--   - assessment_progress
--
-- Migration Table:
--   - alembic_version (for tracking)
