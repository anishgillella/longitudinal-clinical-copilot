# Phase 1: Foundation & Core Infrastructure

## Objective

Establish the core project structure, database schema, authentication, and basic CRUD operations for patients and clinicians.

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Poetry or pip for dependency management

> **Note**: Authentication is disabled for local development. Auth will be added in Phase 6 for production readiness.

## Deliverables

### 1.1 Project Structure

```
phoenix/
├── src/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry
│   ├── config.py                # Configuration management
│   ├── database.py              # Database connection & session
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py              # Base model class
│   │   ├── patient.py           # Patient model
│   │   ├── clinician.py         # Clinician model
│   │   ├── session.py           # Voice session model
│   │   └── transcript.py        # Transcript & audio references
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── patient.py           # Patient request/response schemas
│   │   ├── clinician.py         # Clinician schemas
│   │   └── session.py           # Session schemas
│   │
│   ├── api/                     # API routes
│   │   ├── __init__.py
│   │   ├── router.py            # Main router
│   │   ├── patients.py          # Patient endpoints
│   │   ├── clinicians.py        # Clinician endpoints
│   │   └── health.py            # Health check endpoints
│   │
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── patient_service.py   # Patient operations
│   │   └── clinician_service.py # Clinician operations
│   │
│   └── utils/                   # Utilities
│       ├── __init__.py
│       └── logging.py           # Logging configuration
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_patients.py
│   └── test_clinicians.py
│
├── alembic/                     # Database migrations
│   ├── versions/
│   └── env.py
│
├── docs/                        # Documentation (this folder)
├── .env.example                 # Environment template
├── pyproject.toml               # Dependencies
├── alembic.ini                  # Alembic config
└── README.md                    # Project README
```

### 1.2 Database Schema

#### Core Tables

```sql
-- Clinicians table
CREATE TABLE clinicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    license_number VARCHAR(50),
    specialty VARCHAR(100),  -- e.g., 'psychiatrist', 'psychologist', 'therapist'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Patients table
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id),

    -- Demographics
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),

    -- Contact
    email VARCHAR(255),
    phone VARCHAR(20),

    -- Clinical
    primary_concern TEXT,  -- Initial presenting concern
    referral_source VARCHAR(255),
    intake_date DATE,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active, inactive, discharged

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Patient clinical history (for longitudinal tracking)
CREATE TABLE patient_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- History type
    history_type VARCHAR(50) NOT NULL,  -- 'medical', 'psychiatric', 'medication', 'life_event'

    -- Content
    title VARCHAR(255) NOT NULL,
    description TEXT,
    occurred_at DATE,

    -- Source
    source VARCHAR(50),  -- 'clinician_entry', 'patient_reported', 'ai_extracted'
    confidence FLOAT,  -- For AI-extracted entries

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES clinicians(id)
);

-- Index for fast patient lookups
CREATE INDEX idx_patients_clinician ON patients(clinician_id);
CREATE INDEX idx_patient_history_patient ON patient_history(patient_id);
CREATE INDEX idx_patient_history_type ON patient_history(history_type);
```

### 1.3 Core Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
sqlalchemy = "^2.0.25"
asyncpg = "^0.29.0"
alembic = "^1.13.1"
pydantic = "^2.5.3"
pydantic-settings = "^2.1.0"
# Auth dependencies (for Phase 6)
# python-jose = {extras = ["cryptography"], version = "^3.3.0"}
# passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.6"
httpx = "^0.26.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
pytest-asyncio = "^0.23.3"
pytest-cov = "^4.1.0"
black = "^24.1.0"
ruff = "^0.1.13"
mypy = "^1.8.0"
```

### 1.4 Configuration Management

```python
# src/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    app_name: str = "Longitudinal Clinical Copilot"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/clinical_copilot"

    # Auth (Phase 6 - disabled for local dev)
    # secret_key: str
    # algorithm: str = "HS256"
    # access_token_expire_minutes: int = 60

    # VAPI (Phase 2)
    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""

    # OpenRouter (Phase 3)
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### 1.5 API Endpoints (Phase 1)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/clinicians` | List clinicians |
| POST | `/api/v1/clinicians` | Create clinician |
| GET | `/api/v1/clinicians/{id}` | Get clinician details |
| GET | `/api/v1/patients` | List patients |
| POST | `/api/v1/patients` | Create new patient |
| GET | `/api/v1/patients/{id}` | Get patient details |
| PUT | `/api/v1/patients/{id}` | Update patient |
| DELETE | `/api/v1/patients/{id}` | Soft delete patient |
| GET | `/api/v1/patients/{id}/history` | Get patient history |
| POST | `/api/v1/patients/{id}/history` | Add history entry |

> **Note**: No authentication required for local development. All endpoints are open.

### 1.6 Pydantic Schemas

```python
# src/schemas/patient.py
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from uuid import UUID
from typing import Optional
from enum import Enum

class PatientStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCHARGED = "discharged"

class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    primary_concern: Optional[str] = None
    referral_source: Optional[str] = None

class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    primary_concern: Optional[str] = None
    status: Optional[PatientStatus] = None

class PatientResponse(BaseModel):
    id: UUID
    clinician_id: UUID
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    primary_concern: Optional[str]
    status: PatientStatus
    intake_date: Optional[date]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class HistoryType(str, Enum):
    MEDICAL = "medical"
    PSYCHIATRIC = "psychiatric"
    MEDICATION = "medication"
    LIFE_EVENT = "life_event"

class PatientHistoryCreate(BaseModel):
    history_type: HistoryType
    title: str
    description: Optional[str] = None
    occurred_at: Optional[date] = None

class PatientHistoryResponse(BaseModel):
    id: UUID
    patient_id: UUID
    history_type: HistoryType
    title: str
    description: Optional[str]
    occurred_at: Optional[date]
    source: str
    confidence: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True
```

### 1.7 Development Mode (No Auth)

For local development, we skip authentication. A default clinician is used for all operations.

```python
# src/api/deps.py
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.models.clinician import Clinician

# Default clinician ID for local development
DEFAULT_CLINICIAN_ID = UUID("00000000-0000-0000-0000-000000000001")

async def get_current_clinician(db: AsyncSession = Depends(get_db)) -> Clinician:
    """
    Get current clinician - returns default clinician for local dev.
    Authentication will be added in Phase 6.
    """
    clinician = await db.get(Clinician, DEFAULT_CLINICIAN_ID)
    if not clinician:
        # Create default clinician if doesn't exist
        clinician = Clinician(
            id=DEFAULT_CLINICIAN_ID,
            email="dev@localhost",
            password_hash="not-used-in-dev",
            first_name="Development",
            last_name="Clinician",
            specialty="development"
        )
        db.add(clinician)
        await db.commit()
        await db.refresh(clinician)
    return clinician
```

## Acceptance Criteria

- [ ] Project structure created with all directories
- [ ] PostgreSQL database running locally
- [ ] Alembic migrations configured and initial migration created
- [ ] Default development clinician created on startup
- [ ] Clinician CRUD operations working
- [ ] Patient CRUD operations working
- [ ] Patient history CRUD operations working
- [ ] Basic test suite passing
- [ ] API documentation available at `/docs` (Swagger UI)

## Commands

```bash
# Setup
poetry install
cp .env.example .env
# Edit .env with your database credentials

# Database
createdb clinical_copilot
alembic upgrade head

# Run
uvicorn src.main:app --reload

# Test
pytest -v
```

## Next Phase

Once Phase 1 is complete, proceed to [Phase 2: Voice Agent Integration](./phase-2-voice-agent.md).
