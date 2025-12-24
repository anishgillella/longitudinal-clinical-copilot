# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLINICIAN LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Next.js 14 Dashboard                              │   │
│  │  Patients │ Voice Sessions │ Review │ Analytics │ Reports           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               API LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Patients │ │ Sessions │ │ Signals  │ │Hypotheses│ │ Analysis │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       Middleware                                     │   │
│  │  Auth │ Audit │ Rate Limit │ Security Headers │ CORS                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│    VOICE LAYER        │ │   INTELLIGENCE LAYER  │ │    DATA LAYER         │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │      VAPI       │  │ │  │   OpenRouter    │  │ │  │   PostgreSQL    │  │
│  │  Voice Agent    │  │ │  │   LLM Gateway   │  │ │  │   (Supabase)    │  │
│  └────────┬────────┘  │ │  └────────┬────────┘  │ │  └────────┬────────┘  │
│           │           │ │           │           │ │           │           │
│  ┌────────▼────────┐  │ │  ┌────────▼────────┐  │ │  ┌────────▼────────┐  │
│  │    Webhooks     │  │ │  │  Signal         │  │ │  │  Transcripts    │  │
│  │  Transcription  │  │ │  │  Extraction     │  │ │  │  Signals        │  │
│  │    Audio        │  │ │  │  Domain Scoring │  │ │  │  Hypotheses     │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          POST-SESSION ANALYSIS PIPELINE                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  Session Ends → Get Transcript → LLM Analysis → Store Results       │   │
│  │                                                                      │   │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐         │   │
│  │  │ Extract  │ → │  Score   │ → │ Update   │ → │ Generate │         │   │
│  │  │ Signals  │   │ Domains  │   │Hypotheses│   │ Summary  │         │   │
│  │  └──────────┘   └──────────┘   └──────────┘   └──────────┘         │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### Clinician Layer
- **Next.js 14 Dashboard**: App Router-based SPA with Tailwind + shadcn/ui
- **Features**:
  - Patient management
  - Voice session interface with live transcript
  - Post-session review with signal confirmation
  - Longitudinal analytics and hypothesis tracking
  - Report generation

### API Layer
- **FastAPI Application**: Main backend service
- **Key Endpoints**:
  - `/api/v1/patients` - Patient CRUD
  - `/api/v1/sessions` - Session management
  - `/api/v1/signals` - Clinical signals
  - `/api/v1/hypotheses` - Diagnostic hypotheses
  - `/api/v1/vapi/webhook` - VAPI event handling
- **Middleware Stack**: Security, audit, rate limiting

### Voice Layer
- **VAPI Integration**: Voice agent platform for clinical interviews
- **Webhooks**: Real-time event processing for:
  - `status-update` - Call status changes
  - `transcript` - Real-time transcription
  - `end-of-call-report` - Session completion
- **Functions**: Server-side tools for AI agent:
  - `get_patient_context` - Retrieve patient history
  - `flag_concern` - Flag urgent clinical concerns
  - `end_session` - Graceful session termination

### Intelligence Layer
- **OpenRouter**: LLM gateway for clinical analysis
- **Signal Extraction**: Identify DSM-5 relevant observations from transcripts
- **Domain Scoring**: Aggregate signals into domain scores (A1-A3, B1-B4)
- **Hypothesis Generation**: Probabilistic ASD level predictions

### Data Layer
- **PostgreSQL (Supabase)**: Primary database
- **Key Tables**:
  - `patients`, `clinicians` - Core entities
  - `voice_sessions`, `session_transcripts` - Session data
  - `clinical_signals` - Extracted observations
  - `assessment_domain_scores` - Domain-level scores
  - `diagnostic_hypotheses` - ASD probability tracking

## Data Flow

### Complete Session Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          VOICE SESSION LIFECYCLE                             │
└─────────────────────────────────────────────────────────────────────────────┘

1. PRE-SESSION
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   Clinician  │  →   │  Quick       │  →   │  Context     │
   │   Selects    │      │  Check-in    │      │  Prepared    │
   │   Patient    │      │  Form        │      │  for AI      │
   └──────────────┘      └──────────────┘      └──────────────┘

2. VOICE SESSION
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   VAPI       │  →   │  Webhooks    │  →   │  Transcript  │
   │   Voice      │      │  Stream      │      │  Stored      │
   │   Call       │      │  Events      │      │  Real-time   │
   └──────────────┘      └──────────────┘      └──────────────┘

3. POST-SESSION ANALYSIS (5-10 seconds)
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   Get Full   │  →   │  Send to     │  →   │  Extract     │
   │   Transcript │      │  OpenRouter  │      │  Signals     │
   └──────────────┘      └──────────────┘      └──────────────┘
           │
           ▼
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   Score      │  →   │  Update      │  →   │  Generate    │
   │   Domains    │      │  Hypotheses  │      │  Summary     │
   └──────────────┘      └──────────────┘      └──────────────┘

4. CLINICIAN REVIEW
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │   Display    │  →   │  Clinician   │  →   │  Save        │
   │   Signals    │      │  Confirms/   │      │  Final       │
   │   + Domains  │      │  Edits       │      │  Results     │
   └──────────────┘      └──────────────┘      └──────────────┘
```

### Signal Extraction Flow

```
Transcript Text
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM SIGNAL EXTRACTION                         │
│                                                                  │
│  System Prompt: Clinical signal extraction for autism           │
│  User Prompt: Transcript + domain definitions                   │
│                                                                  │
│  Output (JSON):                                                  │
│  {                                                               │
│    "signals": [                                                  │
│      {                                                           │
│        "signal_type": "behavioral",                              │
│        "signal_name": "distress_at_routine_changes",             │
│        "evidence": "complete meltdown when schedule changed",    │
│        "maps_to_domain": "B2",                                   │
│        "intensity": 0.8,                                         │
│        "confidence": 0.85                                        │
│      }                                                           │
│    ]                                                             │
│  }                                                               │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ clinical_signals │  │ domain_scores    │  │ hypotheses       │
│ table            │  │ table            │  │ table            │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

### Clinician Workflow

```
Clinician Login ──► Dashboard ──► Patient Selection
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            View Patient           Start Session        Generate Report
            Profile                      │
                │                        ▼
                │              Pre-Session Check-in
                │                        │
                ▼                        ▼
        Review History           VAPI Voice Call
        & Hypotheses                    │
                │                        ▼
                │              Session Ends + Analysis
                │                        │
                │                        ▼
                └───────────► Review Extracted Signals
                                        │
                                        ▼
                              Confirm / Edit / Add
                                        │
                                        ▼
                              View Updated Hypotheses
                                        │
                                        ▼
                                 Add Clinician Notes
                                        │
                                        ▼
                                  Save & Complete
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14 + TypeScript + Tailwind | Clinician dashboard |
| UI Components | shadcn/ui + Framer Motion | UI library + animations |
| API | FastAPI (Python 3.11+) | Backend services |
| Voice | VAPI | Voice agent platform |
| LLM | OpenRouter (Claude/Gemini) | Clinical analysis |
| Database | PostgreSQL (Supabase) | Data storage |
| Auth | Supabase Auth | Authentication |

## Database Schema (Key Tables)

```sql
-- Core entities
patients (id, clinician_id, first_name, last_name, dob, ...)
clinicians (id, email, first_name, last_name, ...)

-- Session tracking
voice_sessions (id, patient_id, session_type, status, started_at, ended_at, ...)
session_transcripts (id, session_id, role, content, timestamp_ms, ...)

-- Clinical analysis
clinical_signals (id, session_id, patient_id, signal_type, signal_name,
                  evidence, maps_to_domain, intensity, confidence, ...)

assessment_domain_scores (id, session_id, patient_id, domain_code,
                          raw_score, normalized_score, confidence, ...)

diagnostic_hypotheses (id, patient_id, condition_code, evidence_strength,
                       uncertainty, supporting_signals, trend, ...)

-- Longitudinal memory
session_summaries (id, session_id, brief_summary, key_topics, ...)
timeline_events (id, patient_id, event_type, title, occurred_at, ...)
```

## Security Considerations

### HIPAA Compliance
- All PHI encrypted at rest and in transit
- Comprehensive audit logging of all data access
- Role-based access control (RBAC)
- Session timeout and secure authentication

### Data Protection
```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY LAYERS                           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  TLS 1.3 - All traffic encrypted                    │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │  Supabase RLS - Row-level security          │    │    │
│  │  │  ┌─────────────────────────────────────┐    │    │    │
│  │  │  │  JWT Auth - Authenticated requests   │    │    │    │
│  │  │  │  ┌─────────────────────────────┐    │    │    │    │
│  │  │  │  │  Audit Logging - All access │    │    │    │    │
│  │  │  │  └─────────────────────────────┘    │    │    │    │
│  │  │  └─────────────────────────────────────┘    │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Patient Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patients` | List patients |
| POST | `/api/v1/patients` | Create patient |
| GET | `/api/v1/patients/{id}` | Get patient details |
| GET | `/api/v1/patients/{id}/signals` | Get patient signals |
| GET | `/api/v1/patients/{id}/hypotheses` | Get hypotheses |

### Session Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions/{id}` | Get session details |
| GET | `/api/v1/sessions/{id}/transcript` | Get full transcript |
| POST | `/api/v1/sessions/{id}/analyze` | Trigger analysis |

### VAPI Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/vapi/webhook` | Handle VAPI events |
| POST | `/api/v1/vapi/functions/get-context` | Get patient context |
| POST | `/api/v1/vapi/functions/flag-concern` | Flag clinical concern |

## Environment Variables

```bash
# Backend
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx
OPENROUTER_API_KEY=xxx
OPENROUTER_MODEL=google/gemini-2.5-flash

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxx
NEXT_PUBLIC_VAPI_API_KEY=xxx
NEXT_PUBLIC_VAPI_ASSISTANT_ID=xxx
```
