# Phoenix - Longitudinal Clinical Copilot

Voice-first longitudinal clinical decision support system for mental health intake, documentation, and hypothesis tracking.

## Project Structure

```
troy/
├── backend/              # FastAPI Backend
│   ├── src/              # Source code
│   │   ├── api/          # API routes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── vapi/         # VAPI integration
│   │   └── main.py       # FastAPI app
│   ├── tests/            # Test suite
│   ├── alembic/          # Database migrations
│   └── requirements.txt
├── frontend/             # Next.js 14 Frontend
│   ├── src/
│   │   ├── app/          # App router pages
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom hooks (VAPI)
│   │   ├── lib/          # API client, Supabase
│   │   └── types/        # TypeScript types
│   └── package.json
├── docs/                 # Documentation
└── supabase_schema.sql   # Database schema
```

## Tech Stack

### Backend
- **Framework**: Python 3.11+ / FastAPI
- **Database**: PostgreSQL (Supabase)
- **Voice Agent**: VAPI
- **LLM**: OpenRouter / Gemini 2.5 Flash

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + shadcn/ui
- **Animations**: Framer Motion
- **Voice**: VAPI Web SDK

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Supabase account
- VAPI account

### 1. Database Setup

1. Create a Supabase project at https://supabase.com
2. Go to SQL Editor and run the contents of `supabase_schema.sql`
3. Note your Supabase URL and keys

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Supabase and VAPI credentials

# Start the server
uvicorn src.main:app --reload --port 8000
```

Backend runs at http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (already set up)
# Edit .env.local if needed

# Start development server
npm run dev
```

Frontend runs at http://localhost:3000

## Environment Variables

### Backend (backend/.env)
```env
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres
VAPI_API_KEY=your_vapi_key
VAPI_ASSISTANT_ID=your_assistant_id
OPENROUTER_API_KEY=your_openrouter_key
```

### Frontend (frontend/.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
NEXT_PUBLIC_VAPI_API_KEY=your_vapi_key
NEXT_PUBLIC_VAPI_ASSISTANT_ID=your_assistant_id
```

## Features

### Dashboard
- At-a-glance metrics (patients, sessions, assessments)
- Quick actions (Start session, Add patient, Generate report)
- Recent sessions overview
- Patient progress tracking

### Patients
- Patient list with search and filters
- Patient profile with assessment progress
- Diagnostic hypotheses tracking
- Clinical timeline of observations
- Domain scores visualization

### Voice Sessions
- Real-time voice conversations via VAPI
- Live transcript display with speaker identification
- Audio waveform visualization
- Session type selection (Intake, Check-in, Targeted Probe)

### Sessions
- Session history with transcripts
- Upcoming session management
- Session summaries and clinical signals

## API Documentation

Once the backend is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/patients` | List patients |
| `POST /api/v1/patients` | Create patient |
| `GET /api/v1/patients/{id}` | Get patient details |
| `GET /api/v1/sessions` | List sessions |
| `POST /api/v1/sessions` | Create session |
| `POST /api/v1/vapi/webhook` | VAPI webhook handler |

## Development

### Run Tests (Backend)
```bash
cd backend
pytest -v
```

### Code Formatting
```bash
# Backend
cd backend && black src/ && ruff check src/

# Frontend
cd frontend && npm run lint
```

### Build for Production
```bash
# Frontend
cd frontend && npm run build
```

## Documentation

See the `docs/` folder for detailed documentation:
- [Phase 1: Foundation](docs/phases/phase-1-foundation.md)
- [Phase 2: Voice Agent](docs/phases/phase-2-voice-agent.md)
- [Phase 3: Assessment Engine](docs/phases/phase-3-assessment.md)
- [Phase 4: Longitudinal Memory](docs/phases/phase-4-memory.md)
- [Phase 5: Analytics Dashboard](docs/phases/phase-5-analytics.md)
- [Phase 6: Production](docs/phases/phase-6-production.md)

## License

MIT
