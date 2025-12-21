# Longitudinal Clinical Copilot - Documentation

Voice-first longitudinal clinical decision support system for mental health intake, documentation, and hypothesis tracking.

## Overview

This system enables mental health clinicians to conduct early diagnosis through voice agents across multiple stages, collecting data over extended therapy periods (6+ months) while maintaining full context and providing analytics.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python (FastAPI) |
| Voice Agent | VAPI |
| LLM Provider | OpenRouter (Gemini 2.5 Flash) |
| Database | PostgreSQL |
| Initial Focus | Autism Spectrum Disorder (ASD) |

## Documentation Structure

```
docs/
├── README.md                    # This file
├── phases/                      # Feature milestone documentation
│   ├── phase-1-foundation.md    # Core infrastructure & data models
│   ├── phase-2-voice-agent.md   # VAPI integration
│   ├── phase-3-assessment.md    # Clinical assessment engine
│   ├── phase-4-memory.md        # Longitudinal context & memory
│   ├── phase-5-analytics.md     # Analytics & clinician dashboard
│   └── phase-6-production.md    # Production readiness
├── architecture/                # System architecture docs
│   ├── system-overview.md       # High-level architecture
│   ├── data-flow.md             # Data flow diagrams
│   └── security.md              # Security & HIPAA considerations
├── schemas/                     # Data schemas
│   ├── database-schema.md       # PostgreSQL schema
│   ├── patient-model.md         # Patient data model
│   └── session-model.md         # Session & transcript models
└── api/                         # API specifications
    ├── rest-api.md              # REST API endpoints
    ├── webhook-api.md           # VAPI webhook handlers
    └── llm-prompts.md           # LLM prompt templates
```

## Phase Overview

| Phase | Name | Focus | Key Deliverables |
|-------|------|-------|------------------|
| 1 | Foundation | Core Infrastructure | Database, Auth, Patient CRUD, Project structure |
| 2 | Voice Agent | VAPI Integration | Voice intake, Real-time transcription, Session management |
| 3 | Assessment | Clinical Assessment Engine | Autism screening protocols, Structured interviews, Scoring |
| 4 | Memory | Longitudinal Context | Cross-session reasoning, Timeline construction, Pattern detection |
| 5 | Analytics | Clinician Dashboard | Visualizations, Reports, Hypothesis tracking, Clinical notes |
| 6 | Production | Production Readiness | Security hardening, Audit logs, Performance, Deployment |

## Key Design Principles

1. **Clinician-in-the-loop**: System assists, never decides autonomously
2. **Longitudinal-first**: Every interaction builds on complete patient history
3. **Probabilistic hypotheses**: Present uncertainty, never false certainty
4. **Voice as clinical signal**: Extract prosody, affect, and behavioral markers
5. **Full data retention**: Raw transcripts + audio retained indefinitely
6. **Regulatory awareness**: HIPAA-ready architecture from day one

## Initial Clinical Focus: Autism Spectrum Disorder

The MVP focuses on autism assessment to:
- Provide clear, validated screening protocols (ADOS-2, ADI-R informed)
- Enable longitudinal behavioral pattern tracking
- Support early detection through structured voice interactions
- Generate hypothesis scores with confidence intervals

## Getting Started

See [Phase 1: Foundation](./phases/phase-1-foundation.md) to begin implementation.
