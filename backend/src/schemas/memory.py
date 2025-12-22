"""
Longitudinal Memory Schemas

Pydantic schemas for memory and context data.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class EventType(str, Enum):
    OBSERVATION = "observation"
    DISCLOSURE = "disclosure"
    MILESTONE = "milestone"
    CONCERN = "concern"
    BEHAVIORAL_CHANGE = "behavioral_change"
    ASSESSMENT_FINDING = "assessment_finding"
    TREATMENT_RESPONSE = "treatment_response"
    EXTERNAL_EVENT = "external_event"


class EventCategory(str, Enum):
    SOCIAL = "social"
    EMOTIONAL = "emotional"
    BEHAVIORAL = "behavioral"
    COGNITIVE = "cognitive"
    SENSORY = "sensory"
    COMMUNICATION = "communication"


class Significance(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SummaryType(str, Enum):
    SESSION = "session"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    OVERALL = "overall"


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ON_HOLD = "on_hold"
    ARCHIVED = "archived"


# =============================================================================
# Timeline Event Schemas
# =============================================================================

class TimelineEventCreate(BaseModel):
    """Create a timeline event."""
    event_type: EventType
    category: EventCategory
    title: str = Field(min_length=1, max_length=255)
    description: str
    occurred_at: datetime
    duration_context: Optional[str] = None
    significance: Significance = Significance.MODERATE
    impact_domains: Optional[list[str]] = None
    source: str = "session_extraction"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    evidence_quotes: Optional[list[str]] = None
    related_signal_ids: Optional[list[str]] = None


class TimelineEventUpdate(BaseModel):
    """Update a timeline event."""
    title: Optional[str] = None
    description: Optional[str] = None
    significance: Optional[Significance] = None
    duration_context: Optional[str] = None


class TimelineEventResponse(BaseModel):
    id: UUID
    patient_id: UUID
    session_id: Optional[UUID]
    event_type: str
    category: str
    title: str
    description: str
    occurred_at: datetime
    duration_context: Optional[str]
    significance: str
    impact_domains: Optional[dict]
    source: str
    confidence: float
    evidence_quotes: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class TimelineResponse(BaseModel):
    """Full timeline for a patient."""
    patient_id: UUID
    events: list[TimelineEventResponse]
    total_events: int
    date_range: Optional[dict]  # {start: datetime, end: datetime}
    events_by_category: dict[str, int]
    events_by_significance: dict[str, int]


# =============================================================================
# Memory Summary Schemas
# =============================================================================

class MemorySummaryCreate(BaseModel):
    """Create a memory summary."""
    summary_type: SummaryType
    period_start: datetime
    period_end: datetime
    summary_text: str
    key_observations: Optional[list[str]] = None
    domain_progress: Optional[dict] = None
    concerns_raised: Optional[list[str]] = None
    topics_covered: Optional[list[str]] = None
    sessions_included: int = 1
    signals_included: int = 0


class MemorySummaryResponse(BaseModel):
    id: UUID
    patient_id: UUID
    summary_type: str
    period_start: datetime
    period_end: datetime
    summary_text: str
    key_observations: Optional[dict]
    domain_progress: Optional[dict]
    concerns_raised: Optional[dict]
    topics_covered: Optional[dict]
    sessions_included: int
    signals_included: int
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Context Snapshot Schemas
# =============================================================================

class ContextSnapshotCreate(BaseModel):
    """Create a context snapshot."""
    snapshot_type: str = "pre_session"
    context_text: str
    patient_summary: Optional[dict] = None
    recent_observations: Optional[list[dict]] = None
    current_hypotheses: Optional[list[dict]] = None
    domain_status: Optional[dict] = None
    exploration_priorities: Optional[list[str]] = None
    conversation_guidelines: Optional[dict] = None
    token_count: Optional[int] = None


class ContextSnapshotResponse(BaseModel):
    id: UUID
    patient_id: UUID
    session_id: Optional[UUID]
    snapshot_type: str
    context_text: str
    patient_summary: Optional[dict]
    recent_observations: Optional[dict]
    current_hypotheses: Optional[dict]
    domain_status: Optional[dict]
    exploration_priorities: Optional[dict]
    conversation_guidelines: Optional[dict]
    token_count: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Conversation Thread Schemas
# =============================================================================

class ConversationThreadCreate(BaseModel):
    """Create a conversation thread."""
    thread_topic: str = Field(min_length=1, max_length=255)
    category: str
    summary: str
    first_mentioned_at: datetime
    clinical_relevance: str = "moderate"


class ConversationThreadUpdate(BaseModel):
    """Update a conversation thread."""
    summary: Optional[str] = None
    status: Optional[ThreadStatus] = None
    clinical_relevance: Optional[str] = None
    follow_up_needed: Optional[bool] = None
    follow_up_notes: Optional[str] = None


class ConversationThreadResponse(BaseModel):
    id: UUID
    patient_id: UUID
    thread_topic: str
    category: str
    status: str
    summary: str
    first_mentioned_at: datetime
    last_discussed_at: datetime
    mention_count: int
    clinical_relevance: str
    follow_up_needed: bool
    follow_up_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Context Retrieval Schemas
# =============================================================================

class ContextRequest(BaseModel):
    """Request for patient context."""
    patient_id: UUID
    session_type: str = "checkin"
    max_tokens: int = Field(default=2000, ge=500, le=8000)
    include_hypotheses: bool = True
    include_domain_scores: bool = True
    include_recent_events: bool = True
    recent_events_days: int = Field(default=30, ge=1, le=365)


class PatientContext(BaseModel):
    """Compiled patient context for session injection."""
    patient_id: UUID
    context_text: str
    token_count: int

    # Structured data
    patient_info: dict
    session_history: dict
    current_assessment: dict
    recent_timeline: list[dict]
    active_threads: list[dict]
    exploration_priorities: list[str]

    # Metadata
    generated_at: datetime
    context_version: str = "1.0"


# =============================================================================
# Longitudinal Analysis Schemas
# =============================================================================

class LongitudinalProgress(BaseModel):
    """Progress analysis over time."""
    patient_id: UUID
    analysis_period_days: int

    # Overall trajectory
    overall_trajectory: str  # improving, stable, concerning, insufficient_data
    confidence: float

    # Domain-specific progress
    domain_trajectories: dict[str, dict]  # {domain: {trajectory, change, sessions}}

    # Key milestones
    milestones_achieved: list[dict]

    # Areas of concern
    areas_of_concern: list[dict]

    # Recommendations
    recommended_focus_areas: list[str]

    # Data quality
    sessions_analyzed: int
    signals_analyzed: int
    data_completeness: float


class SessionContextInjection(BaseModel):
    """Context to inject into a new session."""
    session_id: UUID
    patient_id: UUID

    # System prompt additions
    system_context: str

    # First message context
    opening_context: str

    # Topics to explore
    exploration_topics: list[str]

    # Topics to avoid or handle carefully
    sensitive_topics: list[str]

    # Follow-up items from previous sessions
    follow_up_items: list[dict]
