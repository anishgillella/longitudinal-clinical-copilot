# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLINICIAN LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Web Dashboard (React)                            │   │
│  │  Patient List │ Timeline │ Analytics │ Notes │ Alerts               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               API LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Patients │ │ Sessions │ │Dashboard │ │  Notes   │ │  Alerts  │  │   │
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
│  │  Voice Agent    │  │ │  │   LLM Gateway   │  │ │  │   + pgvector    │  │
│  └────────┬────────┘  │ │  └────────┬────────┘  │ │  └────────┬────────┘  │
│           │           │ │           │           │ │           │           │
│  ┌────────▼────────┐  │ │  ┌────────▼────────┐  │ │  ┌────────▼────────┐  │
│  │    Webhooks     │  │ │  │   Assessment    │  │ │  │   Audit Logs    │  │
│  │  Transcription  │  │ │  │   Hypothesis    │  │ │  │   Embeddings    │  │
│  │    Audio        │  │ │  │   Patterns      │  │ │  │   Timelines     │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│   MEMORY LAYER        │ │   PROCESSING LAYER    │ │   MONITORING LAYER    │
│  ┌─────────────────┐  │ │  ┌─────────────────┐  │ │  ┌─────────────────┐  │
│  │    Timeline     │  │ │  │ Post-Session    │  │ │  │   Prometheus    │  │
│  │    Context      │  │ │  │ Processing      │  │ │  │   Grafana       │  │
│  │    Rollups      │  │ │  │ Pipeline        │  │ │  │   Alerts        │  │
│  └─────────────────┘  │ │  └─────────────────┘  │ │  └─────────────────┘  │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
```

## Component Descriptions

### Clinician Layer
- **Web Dashboard**: React-based SPA for clinician interaction
- **Features**: Patient management, timeline visualization, analytics, note editing

### API Layer
- **FastAPI Application**: Main backend service
- **Middleware Stack**: Security, audit, rate limiting

### Voice Layer
- **VAPI Integration**: Voice agent platform
- **Webhooks**: Real-time event processing
- **Transcription**: Speech-to-text processing

### Intelligence Layer
- **OpenRouter**: LLM gateway for multiple models
- **Assessment Engine**: Clinical signal extraction and scoring
- **Hypothesis Engine**: Probabilistic hypothesis generation

### Data Layer
- **PostgreSQL**: Primary database with pgvector extension
- **Audit Logs**: Comprehensive access logging
- **Embeddings**: Semantic search vectors

### Memory Layer
- **Timeline Service**: Patient event chronology
- **Context Retrieval**: Session context preparation
- **Rollup Service**: Periodic summaries

### Processing Layer
- **Post-Session Pipeline**: Automated analysis after calls
- **Signal Extraction**: Clinical signal detection
- **Pattern Detection**: Cross-session pattern identification

### Monitoring Layer
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Alerting**: Operational alerts

## Data Flow

### Voice Session Flow

```
Patient Call ──► VAPI Voice Agent ──► Real-time Webhooks ──► FastAPI
                       │                                        │
                       │                                        ▼
                       └──► Audio/Transcript Storage ──► PostgreSQL
                                                               │
                                                               ▼
                                                    Post-Session Processing
                                                               │
                       ┌───────────────────────────────────────┤
                       ▼                   ▼                   ▼
                Signal Extraction   Domain Scoring   Pattern Detection
                       │                   │                   │
                       └───────────────────┼───────────────────┘
                                           ▼
                                Hypothesis Generation
                                           │
                       ┌───────────────────┼───────────────────┐
                       ▼                   ▼                   ▼
                 Timeline Update    Alert Generation    Summary Rollup
                                           │
                                           ▼
                                Clinician Dashboard
```

### Clinician Workflow

```
Clinician Login ──► Dashboard ──► Patient Selection
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              View Overview       Start Session         Review Notes
                    │                    │                    │
                    ▼                    ▼                    ▼
            Check Hypotheses     VAPI Voice Call       Edit/Finalize
                    │                    │                    │
                    ▼                    ▼                    ▼
             Review Alerts      Session Completes       Export to EHR
                    │                    │
                    └────────────────────┘
                              │
                              ▼
                      Timeline Updated
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React + TypeScript | Clinician dashboard |
| API | FastAPI (Python) | Backend services |
| Voice | VAPI | Voice agent platform |
| LLM | OpenRouter (Gemini 2.5 Flash) | LLM gateway |
| Database | PostgreSQL + pgvector | Data storage + vectors |
| Monitoring | Prometheus + Grafana | Metrics and dashboards |
| Deployment | Docker + Kubernetes | Container orchestration |

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY PERIMETER                        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    TLS 1.3                             │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │                  WAF / DDoS                      │  │  │
│  │  │  ┌───────────────────────────────────────────┐  │  │  │
│  │  │  │              Rate Limiting                 │  │  │  │
│  │  │  │  ┌─────────────────────────────────────┐  │  │  │  │
│  │  │  │  │           JWT Auth + RBAC            │  │  │  │  │
│  │  │  │  │  ┌───────────────────────────────┐  │  │  │  │  │
│  │  │  │  │  │    Field-Level Encryption     │  │  │  │  │  │
│  │  │  │  │  │  ┌─────────────────────────┐  │  │  │  │  │  │
│  │  │  │  │  │  │   Application Logic     │  │  │  │  │  │  │
│  │  │  │  │  │  │                         │  │  │  │  │  │  │
│  │  │  │  │  │  │     PHI Data Store      │  │  │  │  │  │  │
│  │  │  │  │  │  └─────────────────────────┘  │  │  │  │  │  │
│  │  │  │  │  └───────────────────────────────┘  │  │  │  │  │
│  │  │  │  └─────────────────────────────────────┘  │  │  │  │
│  │  │  └───────────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Comprehensive Audit Logging               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API servers behind load balancer
- Database read replicas for heavy read operations
- Async processing queue for post-session analysis

### Data Partitioning
- Patient data partitioned by clinician/clinic
- Time-series data partitioned by date
- Audit logs archived to cold storage after retention period

### Caching Strategy
- Redis for session data and hot patient context
- LLM response caching for repeated operations
- Dashboard aggregation caching

## Disaster Recovery

- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour

### Backup Strategy
- Continuous PostgreSQL WAL archiving
- Daily full database backups
- Cross-region backup replication
- Audio file backups to separate storage

### Failover
- Multi-AZ database deployment
- Automatic API server failover
- DNS-based failover for complete region failure
