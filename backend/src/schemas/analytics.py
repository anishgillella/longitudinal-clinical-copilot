"""
Analytics Schemas

Pydantic schemas for analytics, dashboard, and reporting data.
"""

from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import UUID
from typing import Optional
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class ReportType(str, Enum):
    PROGRESS = "progress"
    ASSESSMENT_SUMMARY = "assessment_summary"
    FULL_ASSESSMENT = "full_assessment"
    SESSION_NOTES = "session_notes"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    ARCHIVED = "archived"


class AssessmentStatus(str, Enum):
    NOT_STARTED = "not_started"
    INITIAL_ASSESSMENT = "initial_assessment"
    ONGOING = "ongoing"
    NEAR_COMPLETION = "near_completion"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"


class HypothesisStability(str, Enum):
    VOLATILE = "volatile"
    STABILIZING = "stabilizing"
    STABLE = "stable"


# =============================================================================
# Dashboard Schemas
# =============================================================================

class DashboardMetrics(BaseModel):
    """Core dashboard metrics for a clinician."""
    clinician_id: UUID
    snapshot_date: date

    # Patient counts
    total_patients: int
    active_patients: int
    patients_in_assessment: int

    # Session counts
    total_sessions_completed: int
    sessions_this_week: int
    sessions_this_month: int
    avg_session_duration_minutes: Optional[float]

    # Assessment status
    assessments_in_progress: int
    assessments_completed: int

    # Concerns
    active_concerns: int
    urgent_concerns: int


class PatientSummaryCard(BaseModel):
    """Summary card for a patient on the dashboard."""
    patient_id: UUID
    name: str
    age: int
    status: str
    last_session_date: Optional[date]
    sessions_completed: int
    assessment_completeness: float
    primary_hypothesis: Optional[str]
    hypothesis_strength: Optional[float]
    has_concerns: bool
    next_action: Optional[str]


class DashboardData(BaseModel):
    """Full dashboard data for a clinician."""
    metrics: DashboardMetrics
    recent_patients: list[PatientSummaryCard]
    upcoming_sessions: list[dict]
    recent_activity: list[dict]
    alerts: list[dict]


class PatientListItem(BaseModel):
    """Patient item for list views."""
    patient_id: UUID
    name: str
    age: int
    primary_concern: Optional[str]
    status: str
    assessment_status: str
    completeness: float
    last_session: Optional[date]
    sessions_count: int
    primary_hypothesis: Optional[str]


class PatientListResponse(BaseModel):
    """Paginated patient list."""
    patients: list[PatientListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# =============================================================================
# Assessment Progress Schemas
# =============================================================================

class DomainProgress(BaseModel):
    """Progress for a single domain."""
    domain_code: str
    domain_name: str
    explored: bool
    confidence: Optional[float]
    score: Optional[float]
    evidence_count: int
    last_assessed: Optional[date]


class AssessmentProgressResponse(BaseModel):
    """Full assessment progress for a patient."""
    patient_id: UUID
    status: str
    overall_completeness: float

    # Session info
    total_sessions: int
    intake_completed: bool
    last_session_date: Optional[date]
    next_session_recommended: Optional[date]

    # Domain progress
    domains_explored: int
    domains_total: int
    domain_details: list[DomainProgress]

    # Evidence quality
    signals_collected: int
    high_confidence_domains: int

    # Hypothesis info
    primary_hypothesis: Optional[str]
    primary_hypothesis_strength: Optional[float]
    hypothesis_stability: Optional[str]

    # Recommendations
    recommended_focus_areas: list[str]
    estimated_sessions_remaining: Optional[int]


class AssessmentProgressUpdate(BaseModel):
    """Update assessment progress."""
    status: Optional[AssessmentStatus] = None
    next_session_recommended: Optional[date] = None
    recommended_focus_areas: Optional[list[str]] = None


# =============================================================================
# Report Schemas
# =============================================================================

class ReportCreate(BaseModel):
    """Create a new report."""
    report_type: ReportType
    title: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class ReportContent(BaseModel):
    """Report content sections."""
    patient_background: Optional[str] = None
    assessment_overview: Optional[str] = None
    session_summaries: Optional[list[dict]] = None
    domain_analysis: Optional[dict] = None
    hypothesis_analysis: Optional[dict] = None
    behavioral_observations: Optional[str] = None
    recommendations: Optional[list[str]] = None
    next_steps: Optional[list[str]] = None


class ReportResponse(BaseModel):
    """Report response."""
    id: UUID
    patient_id: UUID
    clinician_id: Optional[UUID]
    report_type: str
    title: str
    report_date: date
    period_start: Optional[date]
    period_end: Optional[date]
    executive_summary: str
    detailed_content: Optional[dict]
    sessions_included: int
    signals_analyzed: int
    domain_scores_snapshot: Optional[dict]
    hypotheses_snapshot: Optional[dict]
    clinical_impressions: Optional[str]
    recommendations: Optional[dict]
    status: str
    finalized_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    """Report item for list views."""
    id: UUID
    report_type: str
    title: str
    report_date: date
    status: str
    created_at: datetime


# =============================================================================
# Analytics Schemas
# =============================================================================

class ClinicianStats(BaseModel):
    """Statistics for a clinician."""
    clinician_id: UUID
    period_days: int

    # Session stats
    total_sessions: int
    avg_sessions_per_week: float
    total_session_minutes: int

    # Patient stats
    patients_seen: int
    new_patients: int

    # Assessment stats
    assessments_completed: int
    avg_sessions_per_assessment: float

    # Report stats
    reports_generated: int


class SystemStats(BaseModel):
    """System-wide statistics."""
    total_clinicians: int
    total_patients: int
    total_sessions: int
    total_signals_extracted: int
    total_reports_generated: int

    # Recent activity
    sessions_last_7_days: int
    sessions_last_30_days: int

    # Assessment stats
    assessments_in_progress: int
    assessments_completed: int


class TimeSeriesDataPoint(BaseModel):
    """Single data point in a time series."""
    date: date
    value: float
    label: Optional[str] = None


class TimeSeriesData(BaseModel):
    """Time series data for charts."""
    metric_name: str
    data_points: list[TimeSeriesDataPoint]
    period_start: date
    period_end: date


class DomainScoreChart(BaseModel):
    """Domain scores for radar/spider chart."""
    patient_id: UUID
    assessment_date: date
    scores: dict[str, float]  # domain_code -> score


class HypothesisProgressChart(BaseModel):
    """Hypothesis strength over time."""
    patient_id: UUID
    hypothesis_code: str
    hypothesis_name: str
    data_points: list[TimeSeriesDataPoint]


# =============================================================================
# Export Schemas
# =============================================================================

class ExportRequest(BaseModel):
    """Request to export data."""
    format: str = Field(default="pdf", pattern="^(pdf|json|csv)$")
    include_charts: bool = True
    include_raw_data: bool = False


class ExportResponse(BaseModel):
    """Export response."""
    export_id: UUID
    status: str
    format: str
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
