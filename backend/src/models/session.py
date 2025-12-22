from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patient import Patient
    from src.models.clinician import Clinician


class VoiceSession(Base, TimestampMixin):
    """Voice session model - represents a single voice call with a patient."""

    __tablename__ = "voice_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    clinician_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinicians.id"), nullable=False
    )

    # VAPI identifiers
    vapi_call_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    vapi_assistant_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Session metadata
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)  # intake, checkin, targeted_probe
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, active, completed, failed

    # Timing
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Outcome
    completion_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Reasons: completed, patient_hangup, assistant_hangup, error, timeout, silence

    # Summary (populated after processing)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_topics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="sessions")
    clinician: Mapped["Clinician"] = relationship("Clinician")
    transcripts: Mapped[list["Transcript"]] = relationship(
        "Transcript", back_populates="session", cascade="all, delete-orphan"
    )
    audio_recording: Mapped[Optional["AudioRecording"]] = relationship(
        "AudioRecording", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VoiceSession {self.id} ({self.session_type})>"


class Transcript(Base, TimestampMixin):
    """Individual transcript entries from a voice session."""

    __tablename__ = "session_transcripts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False
    )

    # Content
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # assistant, user
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Speech features (populated during analysis)
    speech_speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pause_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    energy_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    session: Mapped["VoiceSession"] = relationship("VoiceSession", back_populates="transcripts")

    def __repr__(self) -> str:
        return f"<Transcript {self.role}: {self.content[:50]}...>"


class AudioRecording(Base, TimestampMixin):
    """Audio recording reference for a voice session."""

    __tablename__ = "audio_recordings"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Storage
    storage_type: Mapped[str] = mapped_column(String(20), nullable=False)  # local, s3, vapi
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Audio metadata
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # wav, mp3, webm

    # Processing status
    transcription_status: Mapped[str] = mapped_column(String(20), default="pending")
    analysis_status: Mapped[str] = mapped_column(String(20), default="pending")

    # Relationships
    session: Mapped["VoiceSession"] = relationship("VoiceSession", back_populates="audio_recording")

    def __repr__(self) -> str:
        return f"<AudioRecording {self.file_path}>"
