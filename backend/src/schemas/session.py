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


# Request schemas
class SessionCreate(BaseModel):
    """Create a new voice session."""
    patient_id: UUID
    session_type: SessionType
    vapi_assistant_id: str
    scheduled_at: Optional[datetime] = None


class SessionStart(BaseModel):
    """Start a session (called from VAPI webhook)."""
    vapi_call_id: str


class SessionEnd(BaseModel):
    """End a session (called from VAPI webhook)."""
    duration_seconds: Optional[int] = None
    completion_reason: Optional[str] = None


class SessionUpdate(BaseModel):
    """Update session details."""
    status: Optional[SessionStatus] = None
    summary: Optional[str] = None
    key_topics: Optional[list[str]] = None


# Response schemas
class SessionResponse(BaseModel):
    id: UUID
    patient_id: UUID
    clinician_id: UUID
    vapi_call_id: Optional[str]
    vapi_assistant_id: str
    session_type: str
    status: str
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    completion_reason: Optional[str]
    summary: Optional[str]
    key_topics: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    id: UUID
    patient_id: UUID
    session_type: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    duration_seconds: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# Transcript schemas
class TranscriptEntry(BaseModel):
    id: UUID
    role: str
    content: str
    timestamp_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptCreate(BaseModel):
    """Create a transcript entry (from VAPI webhook)."""
    role: str
    content: str
    timestamp_ms: Optional[int] = None


class SessionTranscriptResponse(BaseModel):
    session_id: UUID
    entries: list[TranscriptEntry]
    total_entries: int


# Audio recording schemas
class AudioRecordingResponse(BaseModel):
    id: UUID
    session_id: UUID
    storage_type: str
    file_path: str
    duration_seconds: Optional[float]
    format: Optional[str]
    transcription_status: str
    analysis_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# VAPI Webhook payloads
class VAPIWebhookPayload(BaseModel):
    """Base VAPI webhook payload."""
    type: str
    call: Optional[dict] = None
    timestamp: Optional[str] = None


class VAPITranscriptPayload(BaseModel):
    """VAPI transcript webhook payload."""
    type: str = "transcript"
    call: dict
    transcript: dict
    timestamp: Optional[str] = None


class VAPIFunctionCallPayload(BaseModel):
    """VAPI function call payload."""
    type: str = "function-call"
    call: dict
    functionCall: dict
