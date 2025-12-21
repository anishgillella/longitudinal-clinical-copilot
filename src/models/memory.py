"""
Longitudinal Memory Models

Models for storing and retrieving patient context across sessions.
Supports three types of memory:
1. Timeline Events - Discrete events/observations over time
2. Memory Summaries - Compressed summaries of past interactions
3. Context Snapshots - Point-in-time patient state for session injection
"""

from sqlalchemy import String, Text, ForeignKey, Float, Integer, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patient import Patient
    from src.models.session import VoiceSession


class TimelineEvent(Base, TimestampMixin):
    """
    Discrete events in a patient's clinical timeline.

    Examples:
    - Assessment observations
    - Significant disclosures
    - Behavioral changes
    - Treatment milestones
    """
    __tablename__ = "timeline_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: observation, disclosure, milestone, concern, behavioral_change,
    #        assessment_finding, treatment_response, external_event

    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # Categories: social, emotional, behavioral, cognitive, sensory, communication

    # Event content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Timing
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    duration_context: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # e.g., "ongoing", "single_incident", "recurring", "past"

    # Clinical significance
    significance: Mapped[str] = mapped_column(String(20), default="moderate")
    # low, moderate, high, critical

    impact_domains: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"domains": ["social_emotional_reciprocity", "sensory_reactivity"]}

    # Source and confidence
    source: Mapped[str] = mapped_column(String(50), default="session_extraction")
    # session_extraction, clinician_entry, caregiver_report, assessment_tool

    confidence: Mapped[float] = mapped_column(Float, default=0.8)

    # Linking to evidence
    evidence_quotes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"quotes": ["Patient said: '...'", "Observation: ..."]}

    related_signal_ids: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"signal_ids": ["uuid1", "uuid2"]}

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    session: Mapped[Optional["VoiceSession"]] = relationship("VoiceSession")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_timeline_patient_occurred", "patient_id", "occurred_at"),
        Index("ix_timeline_patient_type", "patient_id", "event_type"),
        Index("ix_timeline_patient_category", "patient_id", "category"),
    )


class MemorySummary(Base, TimestampMixin):
    """
    Compressed summaries of patient history.

    Created periodically to maintain context without overwhelming token limits.
    Summaries are hierarchical: recent sessions have detailed summaries,
    older periods get progressively compressed.
    """
    __tablename__ = "memory_summaries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Summary scope
    summary_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: session, weekly, monthly, quarterly, overall

    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)

    # Summary content
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured data for quick access
    key_observations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"observations": ["...", "..."]}

    domain_progress: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"social_reciprocity": {"trend": "improving", "notes": "..."}}

    concerns_raised: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"concerns": ["...", "..."]}

    topics_covered: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"topics": ["family_relationships", "school_challenges"]}

    # Statistics
    sessions_included: Mapped[int] = mapped_column(Integer, default=1)
    signals_included: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    model_version: Mapped[str] = mapped_column(String(100), nullable=True)
    supersedes_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("memory_summaries.id"), nullable=True
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("ix_memory_patient_period", "patient_id", "period_start", "period_end"),
        Index("ix_memory_patient_type", "patient_id", "summary_type"),
    )


class ContextSnapshot(Base, TimestampMixin):
    """
    Point-in-time patient context for session injection.

    Created before each session to provide the voice agent with
    relevant context about the patient's history and current state.
    """
    __tablename__ = "context_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Context scope
    snapshot_type: Mapped[str] = mapped_column(String(50), default="pre_session")
    # pre_session, mid_assessment, review

    # Compiled context (what gets injected into the session)
    context_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured components
    patient_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"name": "...", "age": 12, "primary_concern": "...", "sessions_count": 5}

    recent_observations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"observations": [{"date": "...", "summary": "..."}]}

    current_hypotheses: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"hypotheses": [{"condition": "asd_level_1", "strength": 0.65}]}

    domain_status: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"domains": {"social_reciprocity": {"score": 0.7, "trend": "stable"}}}

    exploration_priorities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"priorities": ["sensory_reactivity", "executive_function"]}

    conversation_guidelines: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"avoid_topics": [], "explore_topics": ["school_transitions"]}

    # Token count for context management
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Metadata
    model_version: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    session: Mapped[Optional["VoiceSession"]] = relationship("VoiceSession")

    __table_args__ = (
        Index("ix_context_patient_created", "patient_id", "created_at"),
    )


class ConversationThread(Base, TimestampMixin):
    """
    Tracks ongoing conversation threads across sessions.

    Helps maintain continuity for topics that span multiple sessions.
    """
    __tablename__ = "conversation_threads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )

    # Thread identification
    thread_topic: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    # active, resolved, on_hold, archived

    # Content
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Tracking
    first_mentioned_at: Mapped[datetime] = mapped_column(nullable=False)
    last_discussed_at: Mapped[datetime] = mapped_column(nullable=False)

    session_mentions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"sessions": [{"id": "...", "date": "...", "summary": "..."}]}

    mention_count: Mapped[int] = mapped_column(Integer, default=1)

    # Importance
    clinical_relevance: Mapped[str] = mapped_column(String(20), default="moderate")
    # low, moderate, high

    follow_up_needed: Mapped[bool] = mapped_column(default=False)
    follow_up_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("ix_thread_patient_status", "patient_id", "status"),
        Index("ix_thread_patient_topic", "patient_id", "thread_topic"),
    )
