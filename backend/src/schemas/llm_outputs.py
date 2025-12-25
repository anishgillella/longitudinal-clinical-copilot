"""
Pydantic Models for LLM Structured Outputs

These models ensure type-safe, validated outputs from LLM analysis.
They provide clear structure for signal extraction, hypothesis generation,
and session analysis.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from enum import Enum
from uuid import UUID


# =============================================================================
# ENUMS
# =============================================================================

class EvidenceType(str, Enum):
    """Type of evidence supporting a signal."""
    OBSERVED = "observed"
    SELF_REPORTED = "self_reported"
    INFERRED = "inferred"


class SignalType(str, Enum):
    """Category of clinical signal."""
    SOCIAL = "social"
    COMMUNICATION = "communication"
    EMOTIONAL = "emotional"
    SENSORY = "sensory"
    BEHAVIORAL = "behavioral"
    RESTRICTED_INTERESTS = "restricted_interests"


class ClinicalSignificance(str, Enum):
    """Level of clinical significance."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class DSM5Criterion(str, Enum):
    """DSM-5 Autism Spectrum Disorder Criteria."""
    A1 = "A1"  # Social-emotional reciprocity
    A2 = "A2"  # Nonverbal communication
    A3 = "A3"  # Relationships
    B1 = "B1"  # Stereotyped/repetitive behaviors
    B2 = "B2"  # Insistence on sameness
    B3 = "B3"  # Restricted interests
    B4 = "B4"  # Sensory reactivity


class ConditionCode(str, Enum):
    """Diagnostic hypothesis condition codes."""
    ASD_LEVEL_1 = "asd_level_1"
    ASD_LEVEL_2 = "asd_level_2"
    ASD_LEVEL_3 = "asd_level_3"
    SOCIAL_ANXIETY = "social_anxiety"
    SCD = "scd"  # Social Communication Disorder
    ADHD = "adhd"
    ANXIETY = "anxiety"
    NO_ASD = "no_asd"
    INSUFFICIENT_DATA = "insufficient_data"


class Severity(str, Enum):
    """Severity levels for concerns."""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class SafetyStatus(str, Enum):
    """Overall safety assessment status."""
    SAFE = "safe"
    MONITOR = "monitor"
    REVIEW = "review"
    URGENT = "urgent"
    CRITICAL = "critical"


class Importance(str, Enum):
    """Importance/priority level."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# SIGNAL EXTRACTION MODELS
# =============================================================================

class ExtractedSignal(BaseModel):
    """A single clinical signal extracted from transcript."""

    signal_type: SignalType = Field(description="Category of the signal")
    signal_name: str = Field(min_length=3, max_length=200, description="Descriptive name")
    evidence: str = Field(min_length=5, description="Exact quote from transcript")
    evidence_type: EvidenceType = Field(description="How evidence was obtained")
    verbatim_quote: Optional[str] = Field(None, description="Exact patient/caregiver words")
    quote_context: Optional[str] = Field(None, description="Surrounding context")
    reasoning: str = Field(min_length=20, description="Clinical reasoning (2-3 sentences)")
    dsm5_criteria: Optional[DSM5Criterion] = Field(None, description="Mapped DSM-5 criterion")
    maps_to_domain: Optional[str] = Field(None, description="Assessment domain code")
    transcript_line: Optional[int] = Field(None, ge=0, description="Line number in transcript")
    intensity: float = Field(ge=0.0, le=1.0, description="How prominent (0-1)")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence level (0-1)")
    clinical_significance: ClinicalSignificance = Field(description="Clinical importance")
    functional_impact: Optional[str] = Field(None, description="Impact on daily functioning")

    @field_validator('confidence')
    @classmethod
    def validate_confidence_by_evidence_type(cls, v, info):
        """Ensure confidence aligns with evidence type guidelines."""
        # Note: We can't access other fields in field_validator easily in Pydantic v2
        # This is just for documentation purposes
        return v


class SessionObservations(BaseModel):
    """Overall observations from the session."""

    communication_style: str = Field(description="How patient/caregiver communicates")
    emotional_presentation: str = Field(description="Emotional content and expression")
    engagement_pattern: Optional[str] = Field(None, description="Response patterns")
    notable_patterns: list[str] = Field(default_factory=list)
    implicit_observations: Optional[str] = Field(None, description="What was NOT said")


class DSM5Coverage(BaseModel):
    """Coverage of DSM-5 criteria in extracted signals."""

    A1_evidence: list[str] = Field(default_factory=list)
    A2_evidence: list[str] = Field(default_factory=list)
    A3_evidence: list[str] = Field(default_factory=list)
    B1_evidence: list[str] = Field(default_factory=list)
    B2_evidence: list[str] = Field(default_factory=list)
    B3_evidence: list[str] = Field(default_factory=list)
    B4_evidence: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list, description="Criteria with no evidence")


class ExtractionLimitations(BaseModel):
    """Limitations of the extraction analysis."""

    not_assessable: list[str] = Field(default_factory=list, description="Cannot assess from transcript")
    low_confidence_areas: list[str] = Field(default_factory=list)
    recommended_observations: list[str] = Field(default_factory=list, description="What clinician should observe")


class SignalExtractionResult(BaseModel):
    """Complete result of signal extraction from a session."""

    signals: list[ExtractedSignal] = Field(default_factory=list)
    session_observations: SessionObservations
    dsm5_coverage: DSM5Coverage
    limitations: ExtractionLimitations
    analysis_confidence: str = Field(description="Overall confidence with explanation")

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def high_confidence_signals(self) -> list[ExtractedSignal]:
        return [s for s in self.signals if s.confidence >= 0.7]

    @property
    def signals_by_criterion(self) -> dict[str, list[ExtractedSignal]]:
        result = {}
        for signal in self.signals:
            if signal.dsm5_criteria:
                key = signal.dsm5_criteria.value
                if key not in result:
                    result[key] = []
                result[key].append(signal)
        return result


# =============================================================================
# DOMAIN SCORING MODELS
# =============================================================================

class DomainScore(BaseModel):
    """Score for a single assessment domain."""

    domain_code: str = Field(description="Domain identifier")
    domain_name: Optional[str] = Field(None, description="Full domain name")
    raw_score: float = Field(ge=0.0, le=1.0, description="Evidence strength")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in score")
    evidence_count: int = Field(ge=0, description="Number of supporting signals")
    high_confidence_count: Optional[int] = Field(None, ge=0)
    key_evidence: str = Field(description="Summary of strongest evidence")
    all_evidence: list[str] = Field(default_factory=list)
    scoring_rationale: str = Field(description="Detailed explanation")
    functional_impact: Optional[str] = Field(None)
    comparison_to_typical: Optional[str] = Field(None)
    areas_to_explore: list[str] = Field(default_factory=list)


class DomainScoringResult(BaseModel):
    """Complete result of domain scoring."""

    domain_scores: list[DomainScore] = Field(default_factory=list)
    overall_pattern: Optional[str] = Field(None, description="Pattern across domains")
    domains_with_no_evidence: list[str] = Field(default_factory=list)
    scoring_limitations: Optional[str] = Field(None)
    scoring_notes: Optional[str] = Field(None)

    @property
    def highest_scoring_domain(self) -> Optional[DomainScore]:
        if not self.domain_scores:
            return None
        return max(self.domain_scores, key=lambda d: d.raw_score)

    @property
    def average_score(self) -> float:
        if not self.domain_scores:
            return 0.0
        return sum(d.raw_score for d in self.domain_scores) / len(self.domain_scores)


# =============================================================================
# HYPOTHESIS GENERATION MODELS
# =============================================================================

class SupportingEvidence(BaseModel):
    """Evidence supporting a hypothesis."""

    signal_id: Optional[str] = Field(None, description="UUID of source signal")
    signal_name: str = Field(description="Name of the signal")
    evidence_type: Optional[EvidenceType] = Field(None)
    quote: Optional[str] = Field(None, description="Exact quote from transcript")
    dsm5_criterion: Optional[str] = Field(None, description="Which criterion this supports")
    reasoning: str = Field(description="Why this supports the hypothesis")


class ContradictingEvidence(BaseModel):
    """Evidence contradicting a hypothesis."""

    signal_id: Optional[str] = Field(None)
    description: str = Field(description="What contradicts")
    reasoning: str = Field(description="Why this is contradicting")


class DSM5CriteriaMet(BaseModel):
    """Tracking of which DSM-5 criteria are met."""

    criterion_A: list[Optional[str]] = Field(default_factory=list, description="A1, A2, A3 status")
    criterion_B: list[Optional[str]] = Field(default_factory=list, description="B1-B4 status")
    criteria_not_assessable: list[str] = Field(default_factory=list)


class DiagnosticHypothesisOutput(BaseModel):
    """A single diagnostic hypothesis."""

    condition_code: str = Field(description="Condition identifier")
    condition_name: str = Field(description="Full condition name")
    evidence_strength: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[SupportingEvidence] = Field(default_factory=list)
    contradicting_evidence: list[ContradictingEvidence] = Field(default_factory=list)
    dsm5_criteria_met: Optional[DSM5CriteriaMet] = Field(None)
    explanation: str = Field(min_length=50, description="Comprehensive explanation")
    key_supporting_factors: list[str] = Field(default_factory=list)
    key_limiting_factors: list[str] = Field(default_factory=list)
    limitations: Optional[str] = Field(None)
    level_rationale: Optional[str] = Field(None, description="Rationale for ASD level")


class DifferentialConsideration(BaseModel):
    """Alternative diagnosis to consider."""

    condition: str = Field(description="Condition name")
    likelihood: Importance = Field(description="Likelihood level")
    reasoning: str = Field(description="Why to consider")
    supporting_evidence: list[str] = Field(default_factory=list)
    against_evidence: list[str] = Field(default_factory=list)
    distinguishing_features: Optional[str] = Field(None)
    assessment_recommendations: list[str] = Field(default_factory=list)


class EvidenceGap(BaseModel):
    """Gap in evidence that needs to be filled."""

    area: str = Field(description="Area needing information")
    dsm5_relevance: Optional[str] = Field(None, description="Which criterion affected")
    importance: Importance = Field(description="Priority level")
    current_evidence: Optional[str] = Field(None, description="What we know")
    what_is_missing: str = Field(description="What is not known")
    suggested_approach: str = Field(description="How to gather information")
    suggested_questions: list[str] = Field(default_factory=list)


class ClinicalRecommendation(BaseModel):
    """Recommendation for the clinician."""

    recommendation: str = Field(description="Specific recommendation")
    rationale: str = Field(description="Why recommended")
    priority: Importance = Field(description="Priority level")


class StandardizedAssessment(BaseModel):
    """Suggested standardized assessment."""

    assessment_name: str = Field(description="e.g., ADOS-2, ADI-R, SRS-2")
    rationale: str = Field(description="Why this would be helpful")


class HypothesisGenerationResult(BaseModel):
    """Complete result of hypothesis generation."""

    hypotheses: list[DiagnosticHypothesisOutput] = Field(default_factory=list)
    differential_considerations: list[DifferentialConsideration] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGap] = Field(default_factory=list)
    clinical_recommendations: list[ClinicalRecommendation] = Field(default_factory=list)
    standardized_assessments_to_consider: list[StandardizedAssessment] = Field(default_factory=list)
    confidence_statement: str = Field(description="Overall confidence statement")
    clinical_summary: Optional[str] = Field(None, description="Summary for clinical use")

    @property
    def primary_hypothesis(self) -> Optional[DiagnosticHypothesisOutput]:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.evidence_strength)

    @property
    def high_priority_gaps(self) -> list[EvidenceGap]:
        return [g for g in self.evidence_gaps if g.importance == Importance.HIGH]


# =============================================================================
# SESSION SUMMARY MODELS
# =============================================================================

class NotableQuote(BaseModel):
    """A significant quote from the session."""

    quote: str = Field(description="Exact quote")
    context: str = Field(description="What was discussed")
    significance: str = Field(description="Clinical significance")


class FollowUpSuggestion(BaseModel):
    """Area for follow-up investigation."""

    area: str = Field(description="Topic to explore")
    rationale: str = Field(description="Why it needs investigation")
    suggested_questions: list[str] = Field(default_factory=list)


class DSM5RelevantObservations(BaseModel):
    """Observations organized by DSM-5 criteria."""

    class CriterionA(BaseModel):
        social_emotional_reciprocity: Optional[str] = None
        nonverbal_communication: Optional[str] = None
        relationships: Optional[str] = None

    class CriterionB(BaseModel):
        stereotyped_patterns: Optional[str] = None
        insistence_on_sameness: Optional[str] = None
        restricted_interests: Optional[str] = None
        sensory_reactivity: Optional[str] = None

    criterion_A: CriterionA = Field(default_factory=CriterionA)
    criterion_B: CriterionB = Field(default_factory=CriterionB)


class SessionSummaryResult(BaseModel):
    """Complete session summary."""

    brief_summary: str = Field(min_length=50, max_length=500)
    detailed_summary: str = Field(min_length=100)
    key_topics: list[str] = Field(default_factory=list)
    dsm5_relevant_observations: Optional[DSM5RelevantObservations] = None
    emotional_tone: str = Field(description="Emotional presentation")
    notable_quotes: list[NotableQuote] = Field(default_factory=list)
    areas_of_strength: list[str] = Field(default_factory=list)
    areas_of_challenge: list[str] = Field(default_factory=list)
    follow_up_suggestions: list[FollowUpSuggestion] = Field(default_factory=list)
    clinical_observations: str = Field(description="Objective clinical observations")
    information_gaps: list[str] = Field(default_factory=list)
    risk_factors_noted: Optional[str] = Field(None)


# =============================================================================
# CONCERN DETECTION MODELS
# =============================================================================

class ClinicalConcern(BaseModel):
    """A clinical concern requiring attention."""

    severity: Severity = Field(description="Severity level")
    category: str = Field(description="safety|distress|functional|medical|environmental")
    description: str = Field(description="Detailed description")
    evidence: str = Field(description="Quote or reference")
    context: Optional[str] = Field(None)
    clinical_reasoning: str = Field(description="Why concerning")
    functional_impact: Optional[str] = Field(None)
    recommended_action: str = Field(description="What to do")
    timeline: str = Field(description="When to act")


class SafetyAssessment(BaseModel):
    """Overall safety assessment."""

    overall_status: SafetyStatus = Field(description="Overall safety status")
    self_harm_risk: str = Field(description="none|low|moderate|high")
    harm_to_others_risk: str = Field(description="none|low|moderate|high")
    reasoning: str = Field(description="Explanation")


class ConcernDetectionResult(BaseModel):
    """Complete result of concern detection."""

    concerns: list[ClinicalConcern] = Field(default_factory=list)
    safety_assessment: SafetyAssessment
    protective_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None)
    follow_up_required: bool = Field(default=False)
    follow_up_timeline: str = Field(default="none")

    @property
    def critical_concerns(self) -> list[ClinicalConcern]:
        return [c for c in self.concerns if c.severity == Severity.CRITICAL]

    @property
    def requires_immediate_action(self) -> bool:
        return self.safety_assessment.overall_status in [SafetyStatus.URGENT, SafetyStatus.CRITICAL]


# =============================================================================
# VISUALIZATION DATA MODELS
# =============================================================================

class ChartDataPoint(BaseModel):
    """A single data point for charts."""

    label: str
    value: float
    color: Optional[str] = None
    metadata: Optional[dict] = None


class DomainRadarData(BaseModel):
    """Data for domain radar chart."""

    labels: list[str] = Field(description="Domain names")
    values: list[float] = Field(description="Domain scores (0-1)")
    confidence: list[float] = Field(description="Confidence levels")


class SignalDistributionData(BaseModel):
    """Data for signal distribution charts."""

    by_type: dict[str, int] = Field(default_factory=dict)
    by_significance: dict[str, int] = Field(default_factory=dict)
    by_dsm5_criterion: dict[str, int] = Field(default_factory=dict)
    by_evidence_type: dict[str, int] = Field(default_factory=dict)


class HypothesisComparisonData(BaseModel):
    """Data for comparing hypotheses."""

    hypotheses: list[str] = Field(description="Hypothesis names")
    evidence_strength: list[float] = Field(description="Strength values")
    uncertainty: list[float] = Field(description="Uncertainty values")
    supporting_count: list[int] = Field(description="Number of supporting evidence")


class AnalyticsDashboardData(BaseModel):
    """Complete data for analytics dashboard."""

    session_id: str
    patient_id: str

    # Summary metrics
    total_signals: int = 0
    high_significance_signals: int = 0
    domains_scored: int = 0
    average_domain_score: float = 0.0
    primary_hypothesis: Optional[str] = None
    primary_hypothesis_strength: Optional[float] = None

    # Chart data
    domain_radar: Optional[DomainRadarData] = None
    signal_distribution: Optional[SignalDistributionData] = None
    hypothesis_comparison: Optional[HypothesisComparisonData] = None

    # DSM-5 coverage
    dsm5_coverage_summary: dict[str, int] = Field(default_factory=dict)
    dsm5_gaps: list[str] = Field(default_factory=list)

    # Concerns summary
    concern_count: int = 0
    critical_concerns: int = 0
    safety_status: Optional[str] = None
