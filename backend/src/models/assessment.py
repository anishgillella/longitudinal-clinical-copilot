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

    Evidence Quality Tiers (per clinical research standards):
    - Tier 1 (Gold): Standardized assessment results (ADOS-2, ADI-R, SRS-2)
    - Tier 2 (High): Direct clinician observation during session
    - Tier 3 (Moderate): Structured interview responses
    - Tier 4 (Low): Unstructured self-report
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
    # Types: communication, social, sensory, behavioral, emotional, restricted_interests
    signal_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Evidence - now with type classification
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(20), default="inferred")
    # Types: observed (directly seen in speech), self_reported (patient described), inferred (interpreted)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Explanation of WHY this is clinically significant

    # Transcript position for deep-linking
    transcript_offset_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript_offset_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Approximate line number in transcript for UI display

    # Scoring
    intensity: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Clinical mapping
    maps_to_domain: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    dsm5_criteria: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # DSM-5 criteria codes: A1, A2, A3, B1, B2, B3, B4 for autism
    clinical_significance: Mapped[str] = mapped_column(String(20), default="moderate")
    # Significance: low, moderate, high

    # Quote-level evidence
    verbatim_quote: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Exact patient words when available
    quote_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Surrounding context for the quote

    # === NEW: Evidence Quality & Consistency Tracking ===
    # Evidence quality tier (1-4, per clinical research standards)
    evidence_quality_tier: Mapped[int] = mapped_column(Integer, default=3)
    # 1=Gold (standardized), 2=High (clinician observed), 3=Moderate (structured), 4=Low (unstructured)

    # Cross-session consistency tracking
    consistency_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # 0-1: How often this pattern appears across sessions (null if first occurrence)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    # Number of sessions where similar signal was observed

    # Informant tracking (critical for pediatric assessments)
    informant_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # parent, patient, teacher, clinician, collateral
    informant_agreement: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # aligned, discrepant, single_source (when multiple informants report on same domain)

    # Temporal pattern (important for differential diagnosis)
    temporal_pattern: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    # consistent (always present), episodic (comes and goes), situational (context-specific)

    # Functional impact (required for DSM-5 diagnosis)
    functional_impact_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    functional_impact_severity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # none, mild, moderate, severe (maps to ASD support levels)

    # Clinician verification
    clinician_verified: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    clinician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("clinicians.id", ondelete="SET NULL"), nullable=True
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

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

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "patient_id": str(self.patient_id),
            "signal_type": self.signal_type,
            "signal_name": self.signal_name,
            "evidence": self.evidence,
            "evidence_type": self.evidence_type,
            "reasoning": self.reasoning,
            "transcript_line": self.transcript_line,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "maps_to_domain": self.maps_to_domain,
            "dsm5_criteria": self.dsm5_criteria,
            "clinical_significance": self.clinical_significance,
            "verbatim_quote": self.verbatim_quote,
            "quote_context": self.quote_context,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
        }


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

    Follows Bayesian reasoning principles with explicit prior/posterior tracking.
    Confidence intervals follow clinical research standards (typically 95% CI).
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

    # Evidence - point estimate and uncertainty
    evidence_strength: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_signals: Mapped[int] = mapped_column(Integer, default=0)
    contradicting_signals: Mapped[int] = mapped_column(Integer, default=0)

    # === NEW: Confidence Interval (95% CI per clinical standards) ===
    confidence_interval_lower: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_interval_upper: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    interval_method: Mapped[str] = mapped_column(String(30), default="evidence_weighted")
    # Methods: evidence_weighted, bayesian_posterior, bootstrap

    # === NEW: Reasoning Chain (audit trail for clinical transparency) ===
    reasoning_chain: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: [{"step": "base_rate", "value": 0.15, "explanation": "..."}, ...]
    # Captures the step-by-step reasoning that led to this conclusion

    # === NEW: Evidence Quality Summary ===
    evidence_quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # 0-1: Weighted average of evidence quality tiers (1=all gold, 0=all low quality)
    gold_standard_evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    # Count of Tier 1 (standardized assessment) evidence

    # === NEW: DSM-5 Criteria Status (required for diagnosis) ===
    criterion_a_met: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    criterion_a_count: Mapped[int] = mapped_column(Integer, default=0)  # Need 3/3 for ASD
    criterion_b_met: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    criterion_b_count: Mapped[int] = mapped_column(Integer, default=0)  # Need 2/4 for ASD
    functional_impairment_documented: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    developmental_period_documented: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Temporal tracking
    first_indicated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    trend: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Trend: increasing, stable, decreasing

    # === NEW: Session delta tracking ===
    last_session_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # How much the evidence_strength changed from the last session
    sessions_since_stable: Mapped[int] = mapped_column(Integer, default=0)
    # Number of sessions where change < 0.05 (hypothesis stabilizing)

    # Explanation
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    supporting_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    contradicting_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    limitations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # What cannot be assessed from transcript alone

    # === NEW: Differential diagnosis context ===
    differential_considerations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Structure: [{"condition": "Social Anxiety", "likelihood": 0.35, "distinguishing_features": [...]}]
    rule_outs_addressed: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Conditions that have been explicitly ruled out with reasoning

    # Metadata
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    history: Mapped[list["HypothesisHistory"]] = relationship(
        "HypothesisHistory", back_populates="hypothesis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Hypothesis {self.condition_name}: {self.evidence_strength:.2f}>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "patient_id": str(self.patient_id),
            "condition_code": self.condition_code,
            "condition_name": self.condition_name,
            "evidence_strength": self.evidence_strength,
            "uncertainty": self.uncertainty,
            "supporting_signals": self.supporting_signals,
            "contradicting_signals": self.contradicting_signals,
            "trend": self.trend,
            "explanation": self.explanation,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "limitations": self.limitations,
            "first_indicated_at": self.first_indicated_at.isoformat() if self.first_indicated_at else None,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
        }


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
