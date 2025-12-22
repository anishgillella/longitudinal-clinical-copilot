"""
Analytics Models

Models for storing analytics data, reports, and dashboard metrics.
"""

from sqlalchemy import String, Text, ForeignKey, Float, Integer, JSON, Date, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.patient import Patient
    from src.models.clinician import Clinician


class ClinicianDashboardSnapshot(Base, TimestampMixin):
    """
    Snapshot of clinician dashboard metrics.

    Stored periodically to enable historical dashboard views
    and reduce computation on dashboard load.
    """
    __tablename__ = "clinician_dashboard_snapshots"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinician_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinicians.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Patient metrics
    total_patients: Mapped[int] = mapped_column(Integer, default=0)
    active_patients: Mapped[int] = mapped_column(Integer, default=0)
    patients_in_assessment: Mapped[int] = mapped_column(Integer, default=0)

    # Session metrics
    total_sessions_completed: Mapped[int] = mapped_column(Integer, default=0)
    sessions_this_week: Mapped[int] = mapped_column(Integer, default=0)
    sessions_this_month: Mapped[int] = mapped_column(Integer, default=0)
    avg_session_duration_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Assessment metrics
    assessments_in_progress: Mapped[int] = mapped_column(Integer, default=0)
    assessments_completed: Mapped[int] = mapped_column(Integer, default=0)
    avg_sessions_per_assessment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Hypothesis metrics
    patients_with_hypotheses: Mapped[int] = mapped_column(Integer, default=0)
    high_confidence_hypotheses: Mapped[int] = mapped_column(Integer, default=0)

    # Concern metrics
    active_concerns: Mapped[int] = mapped_column(Integer, default=0)
    urgent_concerns: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed breakdowns (JSON)
    patients_by_status: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    sessions_by_type: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    hypotheses_distribution: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    clinician: Mapped["Clinician"] = relationship("Clinician")

    __table_args__ = (
        Index("ix_dashboard_clinician_date", "clinician_id", "snapshot_date"),
    )


class PatientReport(Base, TimestampMixin):
    """
    Generated patient assessment reports.

    Comprehensive reports that can be exported for clinical use.
    """
    __tablename__ = "patient_reports"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    clinician_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinicians.id", ondelete="SET NULL"), nullable=True
    )

    # Report metadata
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: progress, assessment_summary, full_assessment, session_notes

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Report period
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Content
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    detailed_content: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Assessment data included
    sessions_included: Mapped[int] = mapped_column(Integer, default=0)
    signals_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    # Domain scores at time of report
    domain_scores_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Hypotheses at time of report
    hypotheses_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Clinical notes and recommendations
    clinical_impressions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="draft")
    # draft, finalized, archived

    finalized_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    finalized_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("clinicians.id"), nullable=True
    )

    # Export tracking
    last_exported_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    export_format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # AI generation metadata
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("ix_report_patient_date", "patient_id", "report_date"),
        Index("ix_report_patient_type", "patient_id", "report_type"),
    )


class AnalyticsEvent(Base, TimestampMixin):
    """
    Analytics events for tracking system usage.

    Enables understanding of how the system is being used
    and identifying areas for improvement.
    """
    __tablename__ = "analytics_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinician_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("clinicians.id", ondelete="SET NULL"), nullable=True
    )
    patient_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    session_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("voice_sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: session_started, session_completed, report_generated,
    #        hypothesis_updated, concern_flagged, dashboard_viewed

    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    # Categories: session, assessment, report, system

    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Timing
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_analytics_clinician_date", "clinician_id", "occurred_at"),
        Index("ix_analytics_type_date", "event_type", "occurred_at"),
    )


class AssessmentProgress(Base, TimestampMixin):
    """
    Tracks assessment progress for each patient.

    Provides a high-level view of where each patient is
    in their assessment journey.
    """
    __tablename__ = "assessment_progress"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # Overall progress
    status: Mapped[str] = mapped_column(String(30), default="not_started")
    # not_started, initial_assessment, ongoing, near_completion, completed, on_hold

    overall_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    # 0.0 to 1.0 representing overall assessment progress

    # Session tracking
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    intake_completed: Mapped[bool] = mapped_column(default=False)
    last_session_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_session_recommended: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Domain coverage
    domains_explored: Mapped[int] = mapped_column(Integer, default=0)
    domains_total: Mapped[int] = mapped_column(Integer, default=10)
    domain_coverage: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # {"domain_code": {"explored": true, "confidence": 0.8}}

    # Evidence quality
    signals_collected: Mapped[int] = mapped_column(Integer, default=0)
    high_confidence_domains: Mapped[int] = mapped_column(Integer, default=0)

    # Hypothesis readiness
    primary_hypothesis_strength: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hypothesis_stability: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # volatile, stabilizing, stable

    # Recommendations
    recommended_focus_areas: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    estimated_sessions_remaining: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")

    __table_args__ = (
        Index("ix_progress_status", "status"),
    )
