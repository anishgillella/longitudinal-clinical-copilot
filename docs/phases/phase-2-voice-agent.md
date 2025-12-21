# Phase 2: Voice Agent Integration (VAPI)

## Objective

Integrate VAPI for voice-based patient interactions, implementing real-time transcription, session management, and webhook handlers for capturing voice data.

## Prerequisites

- Phase 1 completed (database, auth, patient CRUD)
- VAPI account with API key
- ngrok or similar for local webhook testing

## VAPI Overview

VAPI is a voice AI platform that handles:
- Outbound/inbound voice calls
- Real-time speech-to-text
- Text-to-speech responses
- LLM integration for conversation
- Webhook callbacks for events

## Deliverables

### 2.1 Extended Project Structure

```
src/
├── vapi/                        # VAPI integration
│   ├── __init__.py
│   ├── client.py                # VAPI API client
│   ├── webhooks.py              # Webhook handlers
│   ├── assistants.py            # Assistant configuration
│   └── prompts/                 # Voice agent prompts
│       ├── __init__.py
│       ├── intake.py            # Initial intake prompt
│       └── checkin.py           # Check-in prompt
│
├── models/
│   ├── session.py               # Voice session model (new)
│   ├── transcript.py            # Transcript model (new)
│   └── audio.py                 # Audio storage reference (new)
│
└── services/
    ├── session_service.py       # Session management (new)
    └── transcript_service.py    # Transcript processing (new)
```

### 2.2 Database Schema Extensions

```sql
-- Voice sessions table
CREATE TABLE voice_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),

    -- VAPI identifiers
    vapi_call_id VARCHAR(255) UNIQUE,
    vapi_assistant_id VARCHAR(255),

    -- Session metadata
    session_type VARCHAR(50) NOT NULL,  -- 'intake', 'checkin', 'targeted_probe'
    status VARCHAR(20) DEFAULT 'pending',  -- pending, active, completed, failed

    -- Timing
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,

    -- Outcome
    completion_reason VARCHAR(50),  -- 'completed', 'patient_hangup', 'error', 'timeout'

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcripts table
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,

    -- Content
    role VARCHAR(20) NOT NULL,  -- 'assistant', 'patient'
    content TEXT NOT NULL,
    timestamp_ms INTEGER,  -- Milliseconds from session start

    -- Speech features (populated in Phase 3)
    speech_speed FLOAT,
    pause_duration_ms INTEGER,
    energy_level FLOAT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audio storage references
CREATE TABLE audio_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,

    -- Storage
    storage_type VARCHAR(20) NOT NULL,  -- 'local', 's3'
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,

    -- Audio metadata
    duration_seconds FLOAT,
    sample_rate INTEGER,
    format VARCHAR(20),  -- 'wav', 'mp3', 'webm'

    -- Processing status
    transcription_status VARCHAR(20) DEFAULT 'pending',
    analysis_status VARCHAR(20) DEFAULT 'pending',

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sessions_patient ON voice_sessions(patient_id);
CREATE INDEX idx_sessions_status ON voice_sessions(status);
CREATE INDEX idx_transcripts_session ON transcripts(session_id);
CREATE INDEX idx_audio_session ON audio_recordings(session_id);
```

### 2.3 VAPI Client

```python
# src/vapi/client.py
import httpx
from typing import Optional
from src.config import get_settings

class VAPIClient:
    BASE_URL = "https://api.vapi.ai"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {self.settings.vapi_api_key}",
            "Content-Type": "application/json"
        }

    async def create_assistant(self, config: dict) -> dict:
        """Create a VAPI assistant with specific configuration."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/assistant",
                headers=self.headers,
                json=config
            )
            response.raise_for_status()
            return response.json()

    async def start_call(
        self,
        assistant_id: str,
        phone_number: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """Initiate an outbound call to a patient."""
        payload = {
            "assistantId": assistant_id,
            "customer": {
                "number": phone_number
            },
            "phoneNumberId": self.settings.vapi_phone_number_id
        }
        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/call/phone",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def get_call(self, call_id: str) -> dict:
        """Get call details and transcript."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/call/{call_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

    async def end_call(self, call_id: str) -> dict:
        """End an active call."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/call/{call_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
```

### 2.4 VAPI Assistant Configuration

```python
# src/vapi/assistants.py
from typing import Optional

def create_intake_assistant_config(
    patient_name: str,
    patient_context: Optional[str] = None
) -> dict:
    """
    Create VAPI assistant configuration for initial autism screening intake.
    """
    system_prompt = f"""You are a clinical intake assistant helping gather information
for autism spectrum assessment. You are speaking with {patient_name}.

Your role:
- Be warm, empathic, and patient
- Ask clear, simple questions
- Allow time for responses without rushing
- Acknowledge and validate responses
- Never diagnose or suggest diagnoses
- Collect information systematically

Areas to explore:
1. Current concerns and what prompted this assessment
2. Developmental history (early milestones, childhood)
3. Social interactions and relationships
4. Communication patterns
5. Repetitive behaviors or restricted interests
6. Sensory sensitivities
7. Daily living and routine preferences

Guidelines:
- Ask one question at a time
- Use open-ended questions when possible
- If the patient seems uncomfortable, offer to skip or return later
- Keep a supportive, non-judgmental tone

{"Additional context: " + patient_context if patient_context else ""}

Begin by introducing yourself and explaining the purpose of this conversation.
"""

    return {
        "name": f"Intake Assistant - {patient_name}",
        "model": {
            "provider": "openrouter",
            "model": "google/gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
            "temperature": 0.7,
            "maxTokens": 500
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",  # Rachel - calm, professional
            "stability": 0.7,
            "similarityBoost": 0.8
        },
        "firstMessage": f"Hello {patient_name}, thank you for taking the time to speak with me today. I'm here to learn more about you and understand your experiences. This conversation is completely confidential, and you can share as much or as little as you feel comfortable with. Shall we begin?",
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 1800,  # 30 minutes max
        "backgroundSound": "off",
        "serverUrl": "https://your-domain.com/api/v1/vapi/webhook",  # Your webhook URL
        "serverUrlSecret": "your-webhook-secret"
    }

def create_checkin_assistant_config(
    patient_name: str,
    previous_session_summary: str,
    focus_areas: list[str]
) -> dict:
    """
    Create VAPI assistant configuration for follow-up check-in sessions.
    """
    focus_areas_text = "\n".join([f"- {area}" for area in focus_areas])

    system_prompt = f"""You are a clinical check-in assistant following up with {patient_name}.

Previous session summary:
{previous_session_summary}

Areas to focus on this session:
{focus_areas_text}

Your role:
- Be warm and recognize this is a continuing relationship
- Reference previous conversations naturally
- Look for changes or patterns
- Be sensitive to emotional state
- Keep the conversation focused but not rigid

Guidelines:
- Start by asking how they've been since last time
- Gently explore the focus areas
- Notice any changes in mood, energy, or communication style
- Ask about specific situations or examples when relevant
- End by summarizing key points and asking if there's anything else
"""

    return {
        "name": f"Check-in Assistant - {patient_name}",
        "model": {
            "provider": "openrouter",
            "model": "google/gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": system_prompt}
            ],
            "temperature": 0.7,
            "maxTokens": 400
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",
            "stability": 0.7,
            "similarityBoost": 0.8
        },
        "firstMessage": f"Hi {patient_name}, it's good to connect with you again. How have you been since we last spoke?",
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en"
        },
        "silenceTimeoutSeconds": 20,
        "maxDurationSeconds": 900,  # 15 minutes for check-ins
        "serverUrl": "https://your-domain.com/api/v1/vapi/webhook"
    }
```

### 2.5 Webhook Handlers

```python
# src/vapi/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib
from src.config import get_settings
from src.services.session_service import SessionService
from src.services.transcript_service import TranscriptService

router = APIRouter(prefix="/vapi", tags=["VAPI Webhooks"])

async def verify_webhook_signature(
    request: Request,
    x_vapi_signature: Optional[str] = Header(None)
) -> bool:
    """Verify VAPI webhook signature."""
    if not x_vapi_signature:
        return False

    settings = get_settings()
    body = await request.body()
    expected = hmac.new(
        settings.vapi_webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, x_vapi_signature)

@router.post("/webhook")
async def handle_vapi_webhook(request: Request):
    """
    Handle all VAPI webhook events.

    Event types:
    - call-started: Call has begun
    - speech-update: Real-time transcription
    - transcript: Final transcript segment
    - call-ended: Call has completed
    - function-call: Assistant wants to call a function
    """
    payload = await request.json()
    event_type = payload.get("type")
    call_id = payload.get("call", {}).get("id")

    session_service = SessionService()
    transcript_service = TranscriptService()

    match event_type:
        case "call-started":
            await session_service.mark_session_started(
                vapi_call_id=call_id,
                started_at=payload.get("timestamp")
            )
            return {"status": "ok"}

        case "transcript":
            # Store transcript segment
            transcript_data = payload.get("transcript", {})
            await transcript_service.store_transcript(
                vapi_call_id=call_id,
                role=transcript_data.get("role"),
                content=transcript_data.get("text"),
                timestamp_ms=transcript_data.get("timestamp")
            )
            return {"status": "ok"}

        case "call-ended":
            # Finalize session
            await session_service.mark_session_ended(
                vapi_call_id=call_id,
                ended_at=payload.get("timestamp"),
                duration=payload.get("call", {}).get("duration"),
                completion_reason=payload.get("endedReason")
            )

            # Trigger post-session processing (async)
            # This will be expanded in Phase 3
            await session_service.trigger_post_processing(call_id)
            return {"status": "ok"}

        case "function-call":
            # Handle function calls from the assistant
            function_name = payload.get("functionCall", {}).get("name")
            function_args = payload.get("functionCall", {}).get("arguments")

            result = await handle_function_call(function_name, function_args)
            return {"result": result}

        case _:
            # Log unknown event types
            return {"status": "ignored", "event": event_type}

async def handle_function_call(name: str, args: dict) -> dict:
    """
    Handle function calls from the VAPI assistant.

    Supported functions:
    - get_patient_history: Retrieve relevant patient history
    - flag_concern: Mark something for clinician review
    - end_section: Move to next assessment section
    """
    match name:
        case "get_patient_history":
            # Retrieve relevant history from database
            patient_id = args.get("patient_id")
            history_type = args.get("history_type")
            # Implementation in Phase 4
            return {"history": []}

        case "flag_concern":
            # Flag for clinician review
            concern = args.get("concern")
            severity = args.get("severity", "low")
            # Store flag for clinician dashboard
            return {"flagged": True}

        case "end_section":
            section = args.get("section")
            return {"next_section": "continue"}

        case _:
            return {"error": f"Unknown function: {name}"}
```

### 2.6 Session Service

```python
# src/services/session_service.py
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.models.session import VoiceSession
from src.vapi.client import VAPIClient
from src.vapi.assistants import create_intake_assistant_config, create_checkin_assistant_config

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vapi = VAPIClient()

    async def create_intake_session(
        self,
        patient_id: UUID,
        clinician_id: UUID,
        phone_number: str,
        patient_name: str,
        context: str = None
    ) -> VoiceSession:
        """Create and initiate an intake voice session."""
        # Create assistant
        config = create_intake_assistant_config(patient_name, context)
        assistant = await self.vapi.create_assistant(config)

        # Create session record
        session = VoiceSession(
            patient_id=patient_id,
            clinician_id=clinician_id,
            vapi_assistant_id=assistant["id"],
            session_type="intake",
            status="pending"
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Initiate call
        call = await self.vapi.start_call(
            assistant_id=assistant["id"],
            phone_number=phone_number,
            metadata={
                "session_id": str(session.id),
                "patient_id": str(patient_id)
            }
        )

        # Update with VAPI call ID
        session.vapi_call_id = call["id"]
        await self.db.commit()

        return session

    async def create_checkin_session(
        self,
        patient_id: UUID,
        clinician_id: UUID,
        phone_number: str,
        patient_name: str,
        previous_summary: str,
        focus_areas: list[str]
    ) -> VoiceSession:
        """Create and initiate a check-in voice session."""
        config = create_checkin_assistant_config(
            patient_name, previous_summary, focus_areas
        )
        assistant = await self.vapi.create_assistant(config)

        session = VoiceSession(
            patient_id=patient_id,
            clinician_id=clinician_id,
            vapi_assistant_id=assistant["id"],
            session_type="checkin",
            status="pending"
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        call = await self.vapi.start_call(
            assistant_id=assistant["id"],
            phone_number=phone_number,
            metadata={
                "session_id": str(session.id),
                "patient_id": str(patient_id)
            }
        )

        session.vapi_call_id = call["id"]
        await self.db.commit()

        return session

    async def mark_session_started(self, vapi_call_id: str, started_at: str):
        """Mark session as started."""
        await self.db.execute(
            update(VoiceSession)
            .where(VoiceSession.vapi_call_id == vapi_call_id)
            .values(
                status="active",
                started_at=datetime.fromisoformat(started_at)
            )
        )
        await self.db.commit()

    async def mark_session_ended(
        self,
        vapi_call_id: str,
        ended_at: str,
        duration: int,
        completion_reason: str
    ):
        """Mark session as completed."""
        await self.db.execute(
            update(VoiceSession)
            .where(VoiceSession.vapi_call_id == vapi_call_id)
            .values(
                status="completed",
                ended_at=datetime.fromisoformat(ended_at),
                duration_seconds=duration,
                completion_reason=completion_reason
            )
        )
        await self.db.commit()

    async def trigger_post_processing(self, vapi_call_id: str):
        """Trigger post-session analysis (expanded in Phase 3)."""
        # Queue for processing:
        # - Generate session summary
        # - Extract clinical signals
        # - Update patient timeline
        # - Flag concerns for clinician
        pass
```

### 2.7 API Endpoints (Phase 2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions/intake` | Start intake session for patient |
| POST | `/api/v1/sessions/checkin` | Start check-in session |
| GET | `/api/v1/sessions/{id}` | Get session details |
| GET | `/api/v1/sessions/{id}/transcript` | Get full transcript |
| GET | `/api/v1/patients/{id}/sessions` | List patient sessions |
| POST | `/api/v1/vapi/webhook` | VAPI webhook handler |

### 2.8 Pydantic Schemas

```python
# src/schemas/session.py
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum

class SessionType(str, Enum):
    INTAKE = "intake"
    CHECKIN = "checkin"
    TARGETED_PROBE = "targeted_probe"

class SessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"

class StartIntakeRequest(BaseModel):
    patient_id: UUID
    phone_number: str
    additional_context: Optional[str] = None

class StartCheckinRequest(BaseModel):
    patient_id: UUID
    phone_number: str
    focus_areas: list[str] = []

class SessionResponse(BaseModel):
    id: UUID
    patient_id: UUID
    session_type: SessionType
    status: SessionStatus
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True

class TranscriptEntry(BaseModel):
    role: str
    content: str
    timestamp_ms: int
    created_at: datetime

class SessionTranscriptResponse(BaseModel):
    session_id: UUID
    entries: list[TranscriptEntry]
    total_entries: int
```

## Local Development Setup

### ngrok for Webhooks

```bash
# Install ngrok
brew install ngrok

# Start tunnel
ngrok http 8000

# Use the HTTPS URL in VAPI assistant config
# https://abc123.ngrok.io/api/v1/vapi/webhook
```

### Environment Variables

```bash
# .env additions for Phase 2
VAPI_API_KEY=your_vapi_api_key
VAPI_PHONE_NUMBER_ID=your_phone_number_id
VAPI_WEBHOOK_SECRET=your_webhook_secret
```

## Acceptance Criteria

- [ ] VAPI client implemented and tested
- [ ] Assistant configurations for intake and check-in created
- [ ] Webhook handlers processing all event types
- [ ] Voice sessions stored in database
- [ ] Transcripts stored per session
- [ ] Session lifecycle management working
- [ ] API endpoints for session management
- [ ] Local webhook testing with ngrok working

## Testing

```bash
# Manual testing flow
1. Create a patient via API
2. Call POST /api/v1/sessions/intake with patient ID and phone
3. Receive the call on your phone
4. Complete the conversation
5. Verify transcript stored in database
6. Check session status updated correctly
```

## Next Phase

Once Phase 2 is complete, proceed to [Phase 3: Clinical Assessment Engine](./phase-3-assessment.md).
