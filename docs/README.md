# Longitudinal Clinical Copilot - Documentation

A voice-first clinical decision support system that helps mental health clinicians assess autism spectrum disorder (ASD) through structured voice sessions, AI-powered signal extraction, and longitudinal tracking.

## Who Is This For?

**Primary User: Mental Health Clinicians**
- Psychologists, psychiatrists, developmental pediatricians
- Clinicians conducting autism assessments
- Professionals tracking patient progress over extended periods (6+ months)

## What Does It Do?

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLINICIAN WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

1. PREPARE → Review patient history, previous signals, recommended focus
2. CONDUCT → Voice session with parent/patient via AI agent
3. REVIEW  → AI extracts signals, maps to DSM-5 domains
4. CONFIRM → Clinician reviews, edits, adds observations
5. TRACK   → View longitudinal patterns and hypothesis trends
6. REPORT  → Generate documentation for referrals, insurance, schools
```

## Core Features

| Feature | Description |
|---------|-------------|
| Voice Sessions | AI-powered voice agent conducts structured clinical interviews |
| Signal Extraction | LLM analyzes transcripts to identify DSM-5 relevant signals |
| Domain Scoring | Maps signals to autism assessment domains (A1-A3, B1-B4) |
| Hypothesis Tracking | Probabilistic confidence scores that evolve over time |
| Longitudinal Memory | Full context across all sessions, never loses history |
| Clinician Review | Review, edit, and confirm AI-extracted observations |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14 (App Router) + Tailwind + shadcn/ui |
| Backend | Python (FastAPI) |
| Voice Agent | VAPI |
| LLM Provider | OpenRouter (Claude/Gemini) |
| Database | PostgreSQL (Supabase) |
| Initial Focus | Autism Spectrum Disorder (ASD) |

## Documentation Structure

```
docs/
├── README.md                    # This file
├── clinical/                    # Clinical domain documentation
│   ├── dsm5-domains.md          # DSM-5 autism criteria explained
│   └── session-workflow.md      # Clinician session workflow
├── phases/                      # Feature milestone documentation
│   ├── phase-1-foundation.md    # Core infrastructure & data models
│   ├── phase-2-voice-agent.md   # VAPI integration
│   ├── phase-3-assessment.md    # Clinical assessment engine
│   ├── phase-4-memory.md        # Longitudinal context & memory
│   ├── phase-5-analytics.md     # Analytics & clinician dashboard
│   └── phase-6-production.md    # Production readiness
├── architecture/                # System architecture docs
│   └── system-overview.md       # High-level architecture
├── schemas/                     # Data schemas
│   └── database-schema.md       # PostgreSQL schema
├── api/                         # API specifications
│   └── rest-api.md              # REST API endpoints
└── vapi-configuration.md        # VAPI setup guide
```

## Clinical Background: Autism Assessment

### How Autism is Diagnosed Today

Autism diagnosis is **observational and interview-based**. Clinicians use structured tools:

| Tool | Full Name | Purpose |
|------|-----------|---------|
| **ADOS-2** | Autism Diagnostic Observation Schedule | Gold standard observation (2-3 hours) |
| **ADI-R** | Autism Diagnostic Interview - Revised | Parent interview (2-3 hours) |
| **DSM-5** | Diagnostic and Statistical Manual | Diagnostic criteria checklist |

**Problems we solve:**
- Long wait times (12-18 months to see specialists)
- Limited specialists (not enough trained clinicians)
- Subjective notes (easy to miss patterns)
- No longitudinal view (each visit treated in isolation)

### DSM-5 Autism Criteria

**Domain A - Social Communication Deficits** (need all 3):
- A1: Social-emotional reciprocity (back-and-forth conversation)
- A2: Nonverbal communication (eye contact, gestures, expressions)
- A3: Relationships (making and maintaining friendships)

**Domain B - Restricted/Repetitive Behaviors** (need 2 of 4):
- B1: Stereotyped movements, speech, or object use
- B2: Insistence on sameness, routines, rituals
- B3: Highly fixated, intense interests
- B4: Sensory hyper/hypo-reactivity

## Key Design Principles

1. **Clinician-in-the-loop**: System assists, never decides autonomously
2. **Evidence-based**: Every signal links back to transcript evidence
3. **Probabilistic**: Show uncertainty, never false certainty
4. **Longitudinal-first**: Every interaction builds on complete history
5. **Editable**: Clinicians can confirm, edit, or reject AI observations
6. **Auditable**: Full trail of all extractions and changes

## Phase Overview

| Phase | Name | Focus | Status |
|-------|------|-------|--------|
| 1 | Foundation | Database, Auth, Patient CRUD | ✅ Complete |
| 2 | Voice Agent | VAPI integration, transcription | ✅ Complete |
| 3 | Assessment | Signal extraction, domain scoring | 🚧 In Progress |
| 4 | Memory | Cross-session context, patterns | 📋 Planned |
| 5 | Analytics | Dashboards, reports, trends | 📋 Planned |
| 6 | Production | Security, HIPAA, deployment | 📋 Planned |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account
- VAPI account
- OpenRouter API key

### Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials
uvicorn src.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

See [Phase 1: Foundation](./phases/phase-1-foundation.md) for detailed setup.

## Environment Variables

```bash
# Backend (.env)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
OPENROUTER_API_KEY=your-openrouter-key

# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_VAPI_API_KEY=your-vapi-public-key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your-assistant-id
```
