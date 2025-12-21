# Database Schema

## Overview

PostgreSQL database with pgvector extension for semantic search.

## Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  clinicians  │       │   patients   │       │patient_history│
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)      │──┐    │ id (PK)      │
│ email        │  │    │ clinician_id │◄─┘    │ patient_id   │◄─┐
│ password_hash│  │    │ first_name   │       │ history_type │  │
│ first_name   │  │    │ last_name    │       │ title        │  │
│ last_name    │  │    │ date_of_birth│       │ description  │  │
│ license_num  │  │    │ status       │       │ occurred_at  │  │
│ specialty    │  │    │ created_at   │       │ created_at   │  │
└──────────────┘  │    └──────────────┘       └──────────────┘  │
                  │           │                       │          │
                  │           │                       │          │
                  │           ▼                       │          │
                  │    ┌──────────────┐              │          │
                  │    │voice_sessions│              │          │
                  │    ├──────────────┤              │          │
                  └───►│ id (PK)      │◄─────────────┘          │
                       │ patient_id   │◄────────────────────────┘
                       │ clinician_id │
                       │ vapi_call_id │
                       │ session_type │
                       │ status       │
                       │ started_at   │
                       │ ended_at     │
                       └──────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
│   transcripts    │ │audio_records │ │session_summaries │
├──────────────────┤ ├──────────────┤ ├──────────────────┤
│ id (PK)          │ │ id (PK)      │ │ id (PK)          │
│ session_id (FK)  │ │ session_id   │ │ session_id (FK)  │
│ role             │ │ file_path    │ │ summary_type     │
│ content          │ │ duration     │ │ content          │
│ timestamp_ms     │ │ format       │ │ key_topics       │
└──────────────────┘ └──────────────┘ └──────────────────┘

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│clinical_signals  │ │assessment_domains│ │diag_hypotheses   │
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ id (PK)          │ │ id (PK)          │ │ id (PK)          │
│ session_id (FK)  │ │ session_id (FK)  │ │ patient_id (FK)  │
│ patient_id (FK)  │ │ patient_id (FK)  │ │ condition_code   │
│ signal_type      │ │ domain_code      │ │ evidence_strength│
│ signal_name      │ │ raw_score        │ │ uncertainty      │
│ evidence         │ │ normalized_score │ │ trend            │
│ intensity        │ │ confidence       │ │ explanation      │
│ confidence       │ │ evidence_count   │ │ last_updated_at  │
└──────────────────┘ └──────────────────┘ └──────────────────┘

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ timeline_events  │ │detected_patterns │ │ summary_rollups  │
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ id (PK)          │ │ id (PK)          │ │ id (PK)          │
│ patient_id (FK)  │ │ patient_id (FK)  │ │ patient_id (FK)  │
│ event_date       │ │ pattern_type     │ │ rollup_type      │
│ event_type       │ │ pattern_name     │ │ period_start     │
│ title            │ │ description      │ │ period_end       │
│ description      │ │ occurrence_count │ │ summary          │
│ significance     │ │ confidence       │ │ domain_trends    │
│ session_id (FK)  │ │ is_active        │ │ hypothesis_changes│
└──────────────────┘ └──────────────────┘ └──────────────────┘

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ clinical_notes   │ │clinician_alerts  │ │   audit_logs     │
├──────────────────┤ ├──────────────────┤ ├──────────────────┤
│ id (PK)          │ │ id (PK)          │ │ id (PK)          │
│ patient_id (FK)  │ │ patient_id (FK)  │ │ user_id          │
│ clinician_id (FK)│ │ clinician_id (FK)│ │ action           │
│ session_id (FK)  │ │ alert_type       │ │ resource_type    │
│ note_type        │ │ priority         │ │ resource_id      │
│ subjective       │ │ title            │ │ previous_values  │
│ objective        │ │ description      │ │ new_values       │
│ assessment       │ │ status           │ │ ip_address       │
│ plan             │ │ evidence         │ │ created_at       │
│ status           │ │ created_at       │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## Complete Table Definitions

### Core Tables

```sql
-- =====================================================
-- CORE TABLES
-- =====================================================

CREATE TABLE clinicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    license_number VARCHAR(50),
    specialty VARCHAR(100),
    role VARCHAR(20) DEFAULT 'clinician',
    is_active BOOLEAN DEFAULT TRUE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id),
    first_name VARCHAR(100) NOT NULL,  -- Encrypted
    last_name VARCHAR(100) NOT NULL,   -- Encrypted
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    email VARCHAR(255),                 -- Encrypted
    phone VARCHAR(20),                  -- Encrypted
    primary_concern TEXT,
    referral_source VARCHAR(255),
    intake_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE patient_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    history_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    occurred_at DATE,
    source VARCHAR(50),
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES clinicians(id)
);
```

### Session Tables

```sql
-- =====================================================
-- SESSION TABLES
-- =====================================================

CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    vapi_call_id VARCHAR(255) UNIQUE,
    vapi_assistant_id VARCHAR(255),
    session_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    completion_reason VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,              -- Encrypted
    timestamp_ms INTEGER,
    speech_speed FLOAT,
    pause_duration_ms INTEGER,
    energy_level FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audio_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    storage_type VARCHAR(20) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds FLOAT,
    sample_rate INTEGER,
    format VARCHAR(20),
    transcription_status VARCHAR(20) DEFAULT 'pending',
    analysis_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE session_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    summary_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    key_topics JSONB,
    emotional_tone VARCHAR(50),
    notable_quotes JSONB,
    clinical_observations TEXT,
    follow_up_suggestions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50)
);
```

### Assessment Tables

```sql
-- =====================================================
-- ASSESSMENT TABLES
-- =====================================================

CREATE TABLE assessment_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    domain_code VARCHAR(50) NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    raw_score FLOAT,
    normalized_score FLOAT,
    confidence FLOAT,
    evidence_count INTEGER,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50),
    UNIQUE(session_id, domain_code)
);

CREATE TABLE clinical_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    signal_type VARCHAR(50) NOT NULL,
    signal_name VARCHAR(100) NOT NULL,
    evidence TEXT NOT NULL,
    transcript_offset_start INTEGER,
    transcript_offset_end INTEGER,
    intensity FLOAT,
    confidence FLOAT,
    maps_to_domain VARCHAR(50),
    clinical_significance VARCHAR(20),
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE diagnostic_hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    condition_code VARCHAR(50) NOT NULL,
    condition_name VARCHAR(255) NOT NULL,
    evidence_strength FLOAT NOT NULL,
    uncertainty FLOAT NOT NULL,
    supporting_signals INTEGER,
    contradicting_signals INTEGER,
    first_indicated_at TIMESTAMP WITH TIME ZONE,
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trend VARCHAR(20),
    model_version VARCHAR(50),
    explanation TEXT,
    UNIQUE(patient_id, condition_code)
);

CREATE TABLE hypothesis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id UUID REFERENCES diagnostic_hypotheses(id) ON DELETE CASCADE,
    session_id UUID REFERENCES voice_sessions(id),
    evidence_strength FLOAT NOT NULL,
    uncertainty FLOAT NOT NULL,
    delta_from_previous FLOAT,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Memory Tables

```sql
-- =====================================================
-- MEMORY TABLES
-- =====================================================

CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE,
    event_type VARCHAR(50) NOT NULL,
    event_subtype VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    significance VARCHAR(20) DEFAULT 'normal',
    is_pinned BOOLEAN DEFAULT FALSE,
    session_id UUID REFERENCES voice_sessions(id),
    source_type VARCHAR(50),
    source_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES clinicians(id)
);

CREATE TABLE semantic_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID NOT NULL,
    content_hash VARCHAR(64),
    embedding vector(1536),
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE detected_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(255) NOT NULL,
    description TEXT,
    first_detected_at TIMESTAMP WITH TIME ZONE,
    occurrence_count INTEGER DEFAULT 1,
    supporting_sessions JSONB,
    evidence_snippets JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE summary_rollups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    rollup_type VARCHAR(20) NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    summary TEXT NOT NULL,
    session_count INTEGER,
    total_duration_minutes INTEGER,
    domain_trends JSONB,
    hypothesis_changes JSONB,
    significant_events JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Clinical Documentation Tables

```sql
-- =====================================================
-- CLINICAL DOCUMENTATION TABLES
-- =====================================================

CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    session_id UUID REFERENCES voice_sessions(id),
    note_type VARCHAR(20) NOT NULL,
    subjective TEXT,                    -- Encrypted
    objective TEXT,                     -- Encrypted
    assessment TEXT,                    -- Encrypted
    plan TEXT,                          -- Encrypted
    content TEXT,                       -- Encrypted (for non-SOAP)
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_suggestions JSONB,
    status VARCHAR(20) DEFAULT 'draft',
    finalized_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE note_amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID REFERENCES clinical_notes(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    field_changed VARCHAR(50),
    previous_value TEXT,
    new_value TEXT,
    reason TEXT,
    amended_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE clinician_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    session_id UUID REFERENCES voice_sessions(id),
    alert_type VARCHAR(50) NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    evidence JSONB,
    status VARCHAR(20) DEFAULT 'active',
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Security & Audit Tables

```sql
-- =====================================================
-- SECURITY & AUDIT TABLES
-- =====================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    user_type VARCHAR(20),
    user_email VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    resource_details JSONB,
    previous_values JSONB,
    new_values JSONB,
    request_id UUID,
    session_id VARCHAR(255),
    endpoint VARCHAR(255),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    token_type VARCHAR(20) DEFAULT 'access',
    device_info JSONB,
    ip_address INET,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    revoke_reason VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE data_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id),
    export_type VARCHAR(50) NOT NULL,
    patient_id UUID REFERENCES patients(id),
    date_range_start DATE,
    date_range_end DATE,
    format VARCHAR(20),
    record_count INTEGER,
    file_hash VARCHAR(64),
    purpose VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE clinician_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id) UNIQUE,
    default_view VARCHAR(50) DEFAULT 'overview',
    timeline_zoom VARCHAR(20) DEFAULT 'month',
    chart_preferences JSONB,
    email_alerts BOOLEAN DEFAULT TRUE,
    alert_threshold VARCHAR(20) DEFAULT 'normal',
    default_note_type VARCHAR(20) DEFAULT 'soap',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Indexes

```sql
-- =====================================================
-- INDEXES
-- =====================================================

-- Core
CREATE INDEX idx_patients_clinician ON patients(clinician_id);
CREATE INDEX idx_patient_history_patient ON patient_history(patient_id);
CREATE INDEX idx_patient_history_type ON patient_history(history_type);

-- Sessions
CREATE INDEX idx_sessions_patient ON voice_sessions(patient_id);
CREATE INDEX idx_sessions_status ON voice_sessions(status);
CREATE INDEX idx_sessions_vapi ON voice_sessions(vapi_call_id);
CREATE INDEX idx_transcripts_session ON transcripts(session_id);
CREATE INDEX idx_audio_session ON audio_recordings(session_id);
CREATE INDEX idx_summaries_session ON session_summaries(session_id);

-- Assessment
CREATE INDEX idx_domains_patient ON assessment_domains(patient_id);
CREATE INDEX idx_domains_session ON assessment_domains(session_id);
CREATE INDEX idx_signals_patient ON clinical_signals(patient_id);
CREATE INDEX idx_signals_session ON clinical_signals(session_id);
CREATE INDEX idx_signals_type ON clinical_signals(signal_type);
CREATE INDEX idx_hypotheses_patient ON diagnostic_hypotheses(patient_id);
CREATE INDEX idx_hypothesis_history ON hypothesis_history(hypothesis_id);

-- Memory
CREATE INDEX idx_timeline_patient_date ON timeline_events(patient_id, event_date DESC);
CREATE INDEX idx_timeline_type ON timeline_events(event_type);
CREATE INDEX idx_embeddings_patient ON semantic_embeddings(patient_id);
CREATE INDEX idx_embeddings_vector ON semantic_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_patterns_patient ON detected_patterns(patient_id);
CREATE INDEX idx_rollups_patient_period ON summary_rollups(patient_id, period_start);

-- Clinical
CREATE INDEX idx_notes_patient ON clinical_notes(patient_id);
CREATE INDEX idx_notes_session ON clinical_notes(session_id);
CREATE INDEX idx_notes_status ON clinical_notes(status);
CREATE INDEX idx_alerts_clinician ON clinician_alerts(clinician_id);
CREATE INDEX idx_alerts_patient ON clinician_alerts(patient_id);
CREATE INDEX idx_alerts_status ON clinician_alerts(status);
CREATE INDEX idx_alerts_priority ON clinician_alerts(priority);

-- Audit
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_time ON audit_logs(created_at);
CREATE INDEX idx_tokens_clinician ON access_tokens(clinician_id);
CREATE INDEX idx_tokens_expires ON access_tokens(expires_at);
```

## Data Types Reference

| Type | Usage |
|------|-------|
| UUID | All primary keys, foreign keys |
| VARCHAR(n) | Short strings with length limit |
| TEXT | Long text content |
| DATE | Calendar dates |
| TIMESTAMP WITH TIME ZONE | Date/time values |
| BOOLEAN | True/false flags |
| INTEGER | Whole numbers |
| FLOAT | Decimal numbers |
| JSONB | Structured JSON data |
| INET | IP addresses |
| vector(1536) | Embeddings (pgvector) |

## Encryption Notes

Fields marked with "Encrypted" in comments use field-level encryption:
- `patients.first_name`
- `patients.last_name`
- `patients.email`
- `patients.phone`
- `transcripts.content`
- `clinical_notes.subjective`
- `clinical_notes.objective`
- `clinical_notes.assessment`
- `clinical_notes.plan`
- `clinical_notes.content`
