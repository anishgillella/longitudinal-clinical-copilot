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
    COMMUNICATION = "communication"
    SOCIAL = "social"
    SENSORY = "sensory"
    BEHAVIORAL = "behavioral"
    EMOTIONAL = "emotional"


class EvidenceType(str, Enum):
    OBSERVED = "observed"  # Directly observable in speech
    SELF_REPORTED = "self_reported"  # Patient described
    INFERRED = "inferred"  # Interpreted from context


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
    evidence_type: str = "inferred"  # observed, self_reported, inferred
    reasoning: Optional[str] = None
    transcript_line: Optional[int] = None
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


class ReasoningStep(BaseModel):
    """A single step in the clinical reasoning chain."""
    step: str
    contribution: float
    running_total: float
    signals_used: Optional[list[str]] = None
    explanation: str


class HypothesisResponse(BaseModel):
    id: UUID
    patient_id: UUID
    condition_code: str
    condition_name: str
    evidence_strength: float
    uncertainty: float
    # Confidence interval (95% CI)
    confidence_low: float  # Lower bound
    confidence_high: float  # Upper bound
    confidence_interval_lower: float  # Explicit CI lower
    confidence_interval_upper: float  # Explicit CI upper
    # Reasoning chain for clinical transparency
    reasoning_chain: Optional[dict] = None
    # Evidence quality
    evidence_quality_score: Optional[float] = None
    gold_standard_evidence_count: int = 0
    # DSM-5 criteria status
    criterion_a_met: Optional[bool] = None
    criterion_a_count: int = 0
    criterion_b_met: Optional[bool] = None
    criterion_b_count: int = 0
    functional_impairment_documented: Optional[bool] = None
    developmental_period_documented: Optional[bool] = None
    # Session tracking
    last_session_delta: Optional[float] = None
    sessions_since_stable: int = 0
    # Differential diagnosis
    differential_considerations: Optional[list] = None
    # Core fields
    supporting_signals: int
    contradicting_signals: int
    trend: Optional[str]
    explanation: Optional[str]
    limitations: Optional[str] = None
    first_indicated_at: Optional[datetime]
    last_updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_bounds(cls, obj):
        """Create response with calculated confidence bounds and enhanced fields."""
        ci_lower = getattr(obj, 'confidence_interval_lower', None) or max(0.0, obj.evidence_strength - obj.uncertainty)
        ci_upper = getattr(obj, 'confidence_interval_upper', None) or min(1.0, obj.evidence_strength + obj.uncertainty)

        return cls(
            id=obj.id,
            patient_id=obj.patient_id,
            condition_code=obj.condition_code,
            condition_name=obj.condition_name,
            evidence_strength=obj.evidence_strength,
            uncertainty=obj.uncertainty,
            confidence_low=ci_lower,
            confidence_high=ci_upper,
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
            reasoning_chain=getattr(obj, 'reasoning_chain', None),
            evidence_quality_score=getattr(obj, 'evidence_quality_score', None),
            gold_standard_evidence_count=getattr(obj, 'gold_standard_evidence_count', 0) or 0,
            criterion_a_met=getattr(obj, 'criterion_a_met', None),
            criterion_a_count=getattr(obj, 'criterion_a_count', 0) or 0,
            criterion_b_met=getattr(obj, 'criterion_b_met', None),
            criterion_b_count=getattr(obj, 'criterion_b_count', 0) or 0,
            functional_impairment_documented=getattr(obj, 'functional_impairment_documented', None),
            developmental_period_documented=getattr(obj, 'developmental_period_documented', None),
            last_session_delta=getattr(obj, 'last_session_delta', None),
            sessions_since_stable=getattr(obj, 'sessions_since_stable', 0) or 0,
            differential_considerations=getattr(obj, 'differential_considerations', None),
            supporting_signals=obj.supporting_signals,
            contradicting_signals=obj.contradicting_signals,
            trend=obj.trend,
            explanation=obj.explanation,
            limitations=getattr(obj, 'limitations', None),
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
# Detailed Hypothesis with Linked Evidence
# =============================================================================

class LinkedEvidence(BaseModel):
    """Evidence point linked to its source signal."""
    signal_id: Optional[UUID] = None
    signal_name: str
    evidence_type: str  # observed, self_reported, inferred
    quote: str
    reasoning: str
    session_id: Optional[UUID] = None
    transcript_line: Optional[int] = None


class HypothesisDetailResponse(BaseModel):
    """Detailed hypothesis response with linked signals and full context."""
    id: UUID
    patient_id: UUID
    condition_code: str
    condition_name: str
    evidence_strength: float
    uncertainty: float
    confidence_low: float
    confidence_high: float
    supporting_signals: int
    contradicting_signals: int
    trend: Optional[str]
    explanation: Optional[str]
    limitations: Optional[str]  # What cannot be assessed from transcript
    first_indicated_at: Optional[datetime]
    last_updated_at: datetime

    # Linked evidence with signal references
    supporting_evidence: list[LinkedEvidence] = []
    contradicting_evidence: list[LinkedEvidence] = []

    # Related signals for deep-linking
    related_signals: list[ClinicalSignalResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_hypothesis_with_signals(
        cls,
        hypothesis,
        related_signals: list = None,
    ):
        """Create detailed response with linked signals."""
        # Parse supporting evidence
        supporting = []
        if hypothesis.supporting_evidence and "points" in hypothesis.supporting_evidence:
            for point in hypothesis.supporting_evidence["points"]:
                if isinstance(point, dict):
                    supporting.append(LinkedEvidence(
                        signal_id=point.get("signal_id"),
                        signal_name=point.get("signal_name", "Unknown"),
                        evidence_type=point.get("evidence_type", "inferred"),
                        quote=point.get("quote", ""),
                        reasoning=point.get("reasoning", ""),
                        session_id=point.get("session_id"),
                        transcript_line=point.get("transcript_line"),
                    ))
                else:
                    # Legacy format - just a string
                    supporting.append(LinkedEvidence(
                        signal_name="Unknown",
                        evidence_type="inferred",
                        quote=str(point),
                        reasoning="",
                    ))

        # Parse contradicting evidence
        contradicting = []
        if hypothesis.contradicting_evidence and "points" in hypothesis.contradicting_evidence:
            for point in hypothesis.contradicting_evidence["points"]:
                if isinstance(point, dict):
                    contradicting.append(LinkedEvidence(
                        signal_id=point.get("signal_id"),
                        signal_name=point.get("description", "Unknown"),
                        evidence_type="inferred",
                        quote="",
                        reasoning=point.get("reasoning", ""),
                    ))
                else:
                    contradicting.append(LinkedEvidence(
                        signal_name="Unknown",
                        evidence_type="inferred",
                        quote=str(point),
                        reasoning="",
                    ))

        return cls(
            id=hypothesis.id,
            patient_id=hypothesis.patient_id,
            condition_code=hypothesis.condition_code,
            condition_name=hypothesis.condition_name,
            evidence_strength=hypothesis.evidence_strength,
            uncertainty=hypothesis.uncertainty,
            confidence_low=max(0.0, hypothesis.evidence_strength - hypothesis.uncertainty),
            confidence_high=min(1.0, hypothesis.evidence_strength + hypothesis.uncertainty),
            supporting_signals=hypothesis.supporting_signals,
            contradicting_signals=hypothesis.contradicting_signals,
            trend=hypothesis.trend,
            explanation=hypothesis.explanation,
            limitations=getattr(hypothesis, 'limitations', None),
            first_indicated_at=hypothesis.first_indicated_at,
            last_updated_at=hypothesis.last_updated_at,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            related_signals=[
                ClinicalSignalResponse.model_validate(s) for s in (related_signals or [])
            ],
        )


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
