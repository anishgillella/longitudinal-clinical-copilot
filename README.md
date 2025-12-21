# Phoenix - Longitudinal Clinical Copilot

Voice-first longitudinal clinical decision support system for mental health intake, documentation, and hypothesis tracking.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI
- **Database**: PostgreSQL
- **Voice Agent**: VAPI (Phase 2)
- **LLM**: OpenRouter / Gemini 2.5 Flash (Phase 3)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+

### Setup

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup PostgreSQL database**
   ```bash
   createdb clinical_copilot
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials if different from defaults
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn src.main:app --reload
   ```

7. **Open API docs**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /health/db` - Health check with database status

### Clinicians
- `GET /api/v1/clinicians` - List clinicians
- `POST /api/v1/clinicians` - Create clinician
- `GET /api/v1/clinicians/{id}` - Get clinician
- `PUT /api/v1/clinicians/{id}` - Update clinician
- `DELETE /api/v1/clinicians/{id}` - Delete clinician

### Patients
- `GET /api/v1/patients` - List patients
- `POST /api/v1/patients` - Create patient
- `GET /api/v1/patients/{id}` - Get patient
- `PUT /api/v1/patients/{id}` - Update patient
- `DELETE /api/v1/patients/{id}` - Soft delete patient

### Patient History
- `GET /api/v1/patients/{id}/history` - Get patient history
- `POST /api/v1/patients/{id}/history` - Add history entry
- `DELETE /api/v1/patients/{id}/history/{history_id}` - Delete history entry

## Development

### Run tests
```bash
# Create test database first
createdb clinical_copilot_test

# Run tests
pytest -v
```

### Generate migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

## Project Structure

```
phoenix/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API routes
│   └── services/            # Business logic
├── tests/                   # Test suite
├── alembic/                 # Database migrations
├── docs/                    # Documentation
├── requirements.txt
└── README.md
```

## Documentation

See the `docs/` folder for detailed documentation:
- [Phase 1: Foundation](docs/phases/phase-1-foundation.md)
- [Phase 2: Voice Agent](docs/phases/phase-2-voice-agent.md)
- [Phase 3: Assessment Engine](docs/phases/phase-3-assessment.md)
- [Phase 4: Longitudinal Memory](docs/phases/phase-4-memory.md)
- [Phase 5: Analytics Dashboard](docs/phases/phase-5-analytics.md)
- [Phase 6: Production](docs/phases/phase-6-production.md)
