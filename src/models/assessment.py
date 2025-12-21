"""
Assessment Models

Models for storing clinical signals, domain scores, and diagnostic hypotheses.
"""

from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.session import VoiceSession
    from src.models.patient import Patient


class ClinicalSignal(Base, TimestampMixin):
    """
    Clinical signal extracted from a voice session.

    Signals are observations that may be relevant to assessment,
    extracted by the LLM from session transcripts.
    """

    __tablename__ = "clinical_signals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Signal identification
    signal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: linguistic, behavioral, emotional, social
    signal_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Evidence
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    transcript_offset_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript_offset_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Scoring
    intensity: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Clinical mapping
    maps_to_domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    clinical_significance: Mapped[str] = mapped_column(String(20), default="moderate")
    # Significance: low, moderate, high

    # Metadata
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    session: Mapped["VoiceSession"] = relationship("VoiceSession")
    patient: Mapped["Patient"] = relationship("Patient")

    def __repr__(self) -> str:
        return f"<ClinicalSignal {self.signal_name} ({self.signal_type})>"


class AssessmentDomainScore(Base, TimestampMixin):
    """
    Score for an assessment domain from a specific session.

    Each session can produce scores for multiple domains.
    Scores are aggregated over time to track progress.
    """

    __tablename__ = "assessment_domain_scores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Domain identification
    domain_code: Mapped[str] = mapped_column(String(50), nullable=False)
    domain_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Scoring
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)

    # Evidence summary
    key_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    session: Mapped["VoiceSession"] = relationship("VoiceSession")
    patient: Mapped["Patient"] = relationship("Patient")

    def __repr__(self) -> str:
        return f"<DomainScore {self.domain_code}: {self.normalized_score:.2f}>"


class DiagnosticHypothesis(Base, TimestampMixin):
    """
    Diagnostic hypothesis for a patient.

    This is NOT a diagnosis. It represents the current evidence-based
    hypothesis that can change as more data is collected.
    """

    __tablename__ = "diagnostic_hypotheses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Hypothesis identification
    condition_code: Mapped[str] = mapped_column(String(50), nullable=False)
    # Codes: asd_level_1, asd_level_2, asd_level_3, no_asd, insufficient_data
    condition_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Evidence
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_signals: Mapped[int] = mapped_column(Integer, default=0)
    contradicting_signals: Mapped[int] = mapped_column(Integer, default=0)

    # Temporal tracking
    first_indicated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Trend: increasing, stable, decreasing

    # Explanation
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    contradicting_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    history: Mapped[list["HypothesisHistory"]] = relationship(
        "HypothesisHistory", back_populates="hypothesis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hypothesis {self.condition_name}: {self.evidence_strength:.2f}>"


class HypothesisHistory(Base, TimestampMixin):
    """
    Historical record of hypothesis changes over time.

    Tracks how hypotheses evolve as more sessions occur.
    """

    __tablename__ = "hypothesis_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    hypothesis_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnostic_hypotheses.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Snapshot
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    delta_from_previous: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    hypothesis: Mapped["DiagnosticHypothesis"] = relationship(
        "DiagnosticHypothesis", back_populates="history"
    )

    def __repr__(self) -> str:
        return f"<HypothesisHistory {self.evidence_strength:.2f} @ {self.recorded_at}>"


class SessionSummary(Base, TimestampMixin):
    """
    AI-generated summary of a voice session.

    Contains both brief and detailed summaries, plus extracted metadata.
    """

    __tablename__ = "session_summaries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Summaries
    brief_summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extracted metadata
    key_topics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    emotional_tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notable_quotes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Clinical
    clinical_observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_suggestions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Concerns flagged
    concerns: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    safety_assessment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Safety: safe, monitor, review, urgent

    # Metadata
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    session: Mapped["VoiceSession"] = relationship("VoiceSession")
    patient: Mapped["Patient"] = relationship("Patient")

    def __repr__(self) -> str:
        return f"<SessionSummary for session {self.session_id}>"
