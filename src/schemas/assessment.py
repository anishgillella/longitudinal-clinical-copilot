"""
Assessment Schemas

Pydantic schemas for assessment-related data.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class SignalType(str, Enum):
    LINGUISTIC = "linguistic"
    BEHAVIORAL = "behavioral"
    EMOTIONAL = "emotional"
    SOCIAL = "social"


class ClinicalSignificance(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class SafetyAssessment(str, Enum):
    SAFE = "safe"
    MONITOR = "monitor"
    REVIEW = "review"
    URGENT = "urgent"


class HypothesisTrend(str, Enum):
    INCREASING = "increasing"
    STABLE = "stable"
    DECREASING = "decreasing"


# =============================================================================
# Clinical Signal Schemas
# =============================================================================

class ClinicalSignalCreate(BaseModel):
    """Create a clinical signal (usually from LLM extraction)."""
    signal_type: SignalType
    signal_name: str
    evidence: str
    intensity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    maps_to_domain: Optional[str] = None
    clinical_significance: ClinicalSignificance = ClinicalSignificance.MODERATE


class ClinicalSignalResponse(BaseModel):
    id: UUID
    session_id: UUID
    patient_id: UUID
    signal_type: str
    signal_name: str
    evidence: str
    intensity: float
    confidence: float
    maps_to_domain: Optional[str]
    clinical_significance: str
    extracted_at: datetime

    class Config:
        from_attributes = True


class SignalListResponse(BaseModel):
    signals: list[ClinicalSignalResponse]
    total: int
    by_type: dict[str, int]
    by_significance: dict[str, int]


# =============================================================================
# Domain Score Schemas
# =============================================================================

class DomainScoreCreate(BaseModel):
    """Create a domain score (from LLM scoring)."""
    domain_code: str
    domain_name: str
    category: str
    raw_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_count: int = 0
    key_evidence: Optional[str] = None


class DomainScoreResponse(BaseModel):
    id: UUID
    session_id: UUID
    patient_id: UUID
    domain_code: str
    domain_name: str
    category: str
    raw_score: float
    normalized_score: float
    confidence: float
    evidence_count: int
    key_evidence: Optional[str]
    assessed_at: datetime

    class Config:
        from_attributes = True


class DomainScoreWithTrend(BaseModel):
    """Domain score with historical trend information."""
    domain_code: str
    domain_name: str
    category: str
    current_score: float
    confidence: float
    evidence_count: int
    trend: Optional[str]  # increasing, stable, decreasing
    change_30d: Optional[float]
    history: list[dict]  # [{date, score}]


# =============================================================================
# Hypothesis Schemas
# =============================================================================

class HypothesisCreate(BaseModel):
    """Create or update a hypothesis."""
    condition_code: str
    condition_name: str
    evidence_strength: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    supporting_signals: int = 0
    contradicting_signals: int = 0
    explanation: Optional[str] = None
    supporting_evidence: Optional[list[str]] = None
    contradicting_evidence: Optional[list[str]] = None


class HypothesisResponse(BaseModel):
    id: UUID
    patient_id: UUID
    condition_code: str
    condition_name: str
    evidence_strength: float
    uncertainty: float
    confidence_low: float  # evidence_strength - uncertainty
    confidence_high: float  # evidence_strength + uncertainty
    supporting_signals: int
    contradicting_signals: int
    trend: Optional[str]
    explanation: Optional[str]
    first_indicated_at: Optional[datetime]
    last_updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_bounds(cls, obj):
        """Create response with calculated confidence bounds."""
        return cls(
            id=obj.id,
            patient_id=obj.patient_id,
            condition_code=obj.condition_code,
            condition_name=obj.condition_name,
            evidence_strength=obj.evidence_strength,
            uncertainty=obj.uncertainty,
            confidence_low=max(0.0, obj.evidence_strength - obj.uncertainty),
            confidence_high=min(1.0, obj.evidence_strength + obj.uncertainty),
            supporting_signals=obj.supporting_signals,
            contradicting_signals=obj.contradicting_signals,
            trend=obj.trend,
            explanation=obj.explanation,
            first_indicated_at=obj.first_indicated_at,
            last_updated_at=obj.last_updated_at,
        )


class HypothesisHistoryEntry(BaseModel):
    date: datetime
    evidence_strength: float
    uncertainty: float
    delta: Optional[float]
    session_id: Optional[UUID]


class HypothesisWithHistory(BaseModel):
    """Hypothesis with full history."""
    hypothesis: HypothesisResponse
    history: list[HypothesisHistoryEntry]


# =============================================================================
# Session Summary Schemas
# =============================================================================

class SessionSummaryCreate(BaseModel):
    """Create a session summary."""
    brief_summary: str
    detailed_summary: Optional[str] = None
    key_topics: Optional[list[str]] = None
    emotional_tone: Optional[str] = None
    notable_quotes: Optional[list[str]] = None
    clinical_observations: Optional[str] = None
    follow_up_suggestions: Optional[list[str]] = None


class SessionSummaryResponse(BaseModel):
    id: UUID
    session_id: UUID
    patient_id: UUID
    brief_summary: str
    detailed_summary: Optional[str]
    key_topics: Optional[dict]
    emotional_tone: Optional[str]
    notable_quotes: Optional[dict]
    clinical_observations: Optional[str]
    follow_up_suggestions: Optional[dict]
    concerns: Optional[dict]
    safety_assessment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# Processing Schemas
# =============================================================================

class ProcessingRequest(BaseModel):
    """Request to process a session."""
    session_id: UUID
    extract_signals: bool = True
    score_domains: bool = True
    update_hypotheses: bool = True
    generate_summary: bool = True
    check_concerns: bool = True


class ProcessingResult(BaseModel):
    """Result of session processing."""
    session_id: UUID
    status: str  # completed, partial, failed
    signals_extracted: int
    domains_scored: int
    hypotheses_updated: bool
    summary_generated: bool
    concerns_flagged: int
    processing_time_ms: int
    errors: list[str] = []


# =============================================================================
# Assessment Overview Schemas
# =============================================================================

class PatientAssessmentOverview(BaseModel):
    """Overview of a patient's assessment status."""
    patient_id: UUID
    total_sessions: int
    completed_sessions: int
    total_signals: int
    domains_with_data: int
    current_hypotheses: list[HypothesisResponse]
    last_session_date: Optional[datetime]
    assessment_completeness: float  # 0-1, how much of assessment is done
    areas_needing_exploration: list[str]


class DomainOverview(BaseModel):
    """Overview of all domains for a patient."""
    patient_id: UUID
    domains: list[DomainScoreWithTrend]
    last_updated: Optional[datetime]
