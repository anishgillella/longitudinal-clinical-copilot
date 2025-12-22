"""
Metrics Service

Calculates analytics metrics for clinicians and the system.
"""

import logging
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.assessment import (
    ClinicalSignal,
    DiagnosticHypothesis,
    SessionSummary,
)
from src.models.analytics import (
    ClinicianDashboardSnapshot,
    AnalyticsEvent,
    AssessmentProgress,
)

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for calculating analytics metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_clinician_metrics(
        self,
        clinician_id: UUID,
        as_of_date: Optional[date] = None,
    ) -> dict:
        """
        Get comprehensive metrics for a clinician.

        Args:
            clinician_id: The clinician ID
            as_of_date: Date to calculate metrics for (default: today)

        Returns:
            Dictionary of metrics
        """
        target_date = as_of_date or date.today()
        week_start = target_date - timedelta(days=target_date.weekday())
        month_start = target_date.replace(day=1)

        # Patient counts
        patient_counts = await self._get_patient_counts(clinician_id)

        # Session counts
        session_counts = await self._get_session_counts(
            clinician_id, week_start, month_start
        )

        # Assessment metrics
        assessment_metrics = await self._get_assessment_metrics(clinician_id)

        # Concern metrics
        concern_metrics = await self._get_concern_metrics(clinician_id)

        return {
            "clinician_id": str(clinician_id),
            "snapshot_date": target_date.isoformat(),
            **patient_counts,
            **session_counts,
            **assessment_metrics,
            **concern_metrics,
        }

    async def create_dashboard_snapshot(
        self,
        clinician_id: UUID,
        snapshot_date: Optional[date] = None,
    ) -> ClinicianDashboardSnapshot:
        """Create and store a dashboard snapshot."""
        target_date = snapshot_date or date.today()
        metrics = await self.get_clinician_metrics(clinician_id, target_date)

        # Check for existing snapshot
        existing = await self.db.execute(
            select(ClinicianDashboardSnapshot).where(
                ClinicianDashboardSnapshot.clinician_id == clinician_id,
                ClinicianDashboardSnapshot.snapshot_date == target_date,
            )
        )
        snapshot = existing.scalar_one_or_none()

        if snapshot:
            # Update existing
            for key, value in metrics.items():
                if hasattr(snapshot, key) and key not in ["clinician_id", "snapshot_date"]:
                    setattr(snapshot, key, value)
        else:
            # Create new
            snapshot = ClinicianDashboardSnapshot(
                clinician_id=clinician_id,
                snapshot_date=target_date,
                total_patients=metrics.get("total_patients", 0),
                active_patients=metrics.get("active_patients", 0),
                patients_in_assessment=metrics.get("patients_in_assessment", 0),
                total_sessions_completed=metrics.get("total_sessions_completed", 0),
                sessions_this_week=metrics.get("sessions_this_week", 0),
                sessions_this_month=metrics.get("sessions_this_month", 0),
                avg_session_duration_minutes=metrics.get("avg_session_duration_minutes"),
                assessments_in_progress=metrics.get("assessments_in_progress", 0),
                assessments_completed=metrics.get("assessments_completed", 0),
                patients_with_hypotheses=metrics.get("patients_with_hypotheses", 0),
                active_concerns=metrics.get("active_concerns", 0),
                urgent_concerns=metrics.get("urgent_concerns", 0),
            )
            self.db.add(snapshot)

        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(f"Created dashboard snapshot for clinician {clinician_id}")
        return snapshot

    async def get_system_stats(self) -> dict:
        """Get system-wide statistics."""
        # Total counts
        clinician_count = await self.db.execute(
            select(func.count()).select_from(
                select(Patient.clinician_id).distinct().subquery()
            )
        )

        patient_count = await self.db.execute(
            select(func.count(Patient.id))
        )

        session_count = await self.db.execute(
            select(func.count(VoiceSession.id))
        )

        signal_count = await self.db.execute(
            select(func.count(ClinicalSignal.id))
        )

        # Recent activity
        week_ago = datetime.utcnow() - timedelta(days=7)
        month_ago = datetime.utcnow() - timedelta(days=30)

        sessions_week = await self.db.execute(
            select(func.count(VoiceSession.id)).where(
                VoiceSession.created_at >= week_ago
            )
        )

        sessions_month = await self.db.execute(
            select(func.count(VoiceSession.id)).where(
                VoiceSession.created_at >= month_ago
            )
        )

        # Assessment progress counts
        progress_result = await self.db.execute(
            select(
                func.count(AssessmentProgress.id).filter(
                    AssessmentProgress.status.in_(["initial_assessment", "ongoing", "near_completion"])
                ).label("in_progress"),
                func.count(AssessmentProgress.id).filter(
                    AssessmentProgress.status == "completed"
                ).label("completed"),
            )
        )
        progress_counts = progress_result.one()

        return {
            "total_clinicians": clinician_count.scalar() or 0,
            "total_patients": patient_count.scalar() or 0,
            "total_sessions": session_count.scalar() or 0,
            "total_signals_extracted": signal_count.scalar() or 0,
            "sessions_last_7_days": sessions_week.scalar() or 0,
            "sessions_last_30_days": sessions_month.scalar() or 0,
            "assessments_in_progress": progress_counts.in_progress or 0,
            "assessments_completed": progress_counts.completed or 0,
        }

    async def get_clinician_stats(
        self,
        clinician_id: UUID,
        period_days: int = 30,
    ) -> dict:
        """Get detailed statistics for a clinician over a period."""
        period_start = datetime.utcnow() - timedelta(days=period_days)

        # Session stats
        session_result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("total"),
                func.sum(VoiceSession.duration_seconds).label("total_seconds"),
            )
            .join(Patient, VoiceSession.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                VoiceSession.status == "completed",
                VoiceSession.ended_at >= period_start,
            )
        )
        session_stats = session_result.one()

        # Patients seen
        patients_result = await self.db.execute(
            select(func.count(func.distinct(VoiceSession.patient_id)))
            .join(Patient, VoiceSession.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                VoiceSession.ended_at >= period_start,
            )
        )

        # New patients
        new_patients_result = await self.db.execute(
            select(func.count(Patient.id)).where(
                Patient.clinician_id == clinician_id,
                Patient.created_at >= period_start,
            )
        )

        total_sessions = session_stats.total or 0
        total_seconds = session_stats.total_seconds or 0

        return {
            "clinician_id": str(clinician_id),
            "period_days": period_days,
            "total_sessions": total_sessions,
            "avg_sessions_per_week": (total_sessions / period_days) * 7 if period_days > 0 else 0,
            "total_session_minutes": total_seconds // 60,
            "patients_seen": patients_result.scalar() or 0,
            "new_patients": new_patients_result.scalar() or 0,
        }

    async def log_event(
        self,
        event_type: str,
        event_category: str,
        clinician_id: Optional[UUID] = None,
        patient_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        event_data: Optional[dict] = None,
        duration_ms: Optional[int] = None,
    ) -> AnalyticsEvent:
        """Log an analytics event."""
        event = AnalyticsEvent(
            clinician_id=clinician_id,
            patient_id=patient_id,
            session_id=session_id,
            event_type=event_type,
            event_category=event_category,
            event_data=event_data,
            duration_ms=duration_ms,
            occurred_at=datetime.utcnow(),
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_time_series(
        self,
        clinician_id: UUID,
        metric: str,
        period_days: int = 30,
    ) -> list[dict]:
        """Get time series data for a metric."""
        period_start = date.today() - timedelta(days=period_days)

        if metric == "sessions":
            result = await self.db.execute(
                select(
                    func.date(VoiceSession.ended_at).label("date"),
                    func.count(VoiceSession.id).label("value"),
                )
                .join(Patient, VoiceSession.patient_id == Patient.id)
                .where(
                    Patient.clinician_id == clinician_id,
                    VoiceSession.status == "completed",
                    func.date(VoiceSession.ended_at) >= period_start,
                )
                .group_by(func.date(VoiceSession.ended_at))
                .order_by(func.date(VoiceSession.ended_at))
            )

            return [
                {"date": row.date.isoformat(), "value": row.value}
                for row in result.all()
            ]

        elif metric == "signals":
            result = await self.db.execute(
                select(
                    func.date(ClinicalSignal.extracted_at).label("date"),
                    func.count(ClinicalSignal.id).label("value"),
                )
                .join(Patient, ClinicalSignal.patient_id == Patient.id)
                .where(
                    Patient.clinician_id == clinician_id,
                    func.date(ClinicalSignal.extracted_at) >= period_start,
                )
                .group_by(func.date(ClinicalSignal.extracted_at))
                .order_by(func.date(ClinicalSignal.extracted_at))
            )

            return [
                {"date": row.date.isoformat(), "value": row.value}
                for row in result.all()
            ]

        return []

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_patient_counts(self, clinician_id: UUID) -> dict:
        """Get patient counts for a clinician."""
        result = await self.db.execute(
            select(
                func.count(Patient.id).label("total"),
                func.count(Patient.id).filter(Patient.status == "active").label("active"),
            ).where(Patient.clinician_id == clinician_id)
        )
        counts = result.one()

        # Patients with active assessments
        in_assessment = await self.db.execute(
            select(func.count(AssessmentProgress.id))
            .join(Patient, AssessmentProgress.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                AssessmentProgress.status.in_(["initial_assessment", "ongoing", "near_completion"]),
            )
        )

        return {
            "total_patients": counts.total or 0,
            "active_patients": counts.active or 0,
            "patients_in_assessment": in_assessment.scalar() or 0,
        }

    async def _get_session_counts(
        self,
        clinician_id: UUID,
        week_start: date,
        month_start: date,
    ) -> dict:
        """Get session counts for a clinician."""
        result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("total"),
                func.count(VoiceSession.id).filter(
                    func.date(VoiceSession.ended_at) >= week_start
                ).label("this_week"),
                func.count(VoiceSession.id).filter(
                    func.date(VoiceSession.ended_at) >= month_start
                ).label("this_month"),
                func.avg(VoiceSession.duration_seconds).label("avg_duration"),
            )
            .join(Patient, VoiceSession.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                VoiceSession.status == "completed",
            )
        )
        counts = result.one()

        avg_minutes = None
        if counts.avg_duration:
            avg_minutes = round(counts.avg_duration / 60, 1)

        return {
            "total_sessions_completed": counts.total or 0,
            "sessions_this_week": counts.this_week or 0,
            "sessions_this_month": counts.this_month or 0,
            "avg_session_duration_minutes": avg_minutes,
        }

    async def _get_assessment_metrics(self, clinician_id: UUID) -> dict:
        """Get assessment metrics for a clinician."""
        result = await self.db.execute(
            select(
                func.count(AssessmentProgress.id).filter(
                    AssessmentProgress.status.in_(["initial_assessment", "ongoing", "near_completion"])
                ).label("in_progress"),
                func.count(AssessmentProgress.id).filter(
                    AssessmentProgress.status == "completed"
                ).label("completed"),
            )
            .join(Patient, AssessmentProgress.patient_id == Patient.id)
            .where(Patient.clinician_id == clinician_id)
        )
        counts = result.one()

        # Patients with hypotheses
        hyp_result = await self.db.execute(
            select(func.count(func.distinct(DiagnosticHypothesis.patient_id)))
            .join(Patient, DiagnosticHypothesis.patient_id == Patient.id)
            .where(Patient.clinician_id == clinician_id)
        )

        return {
            "assessments_in_progress": counts.in_progress or 0,
            "assessments_completed": counts.completed or 0,
            "patients_with_hypotheses": hyp_result.scalar() or 0,
        }

    async def _get_concern_metrics(self, clinician_id: UUID) -> dict:
        """Get concern metrics for a clinician."""
        result = await self.db.execute(
            select(
                func.count(SessionSummary.id).filter(
                    SessionSummary.safety_assessment.in_(["monitor", "review"])
                ).label("active"),
                func.count(SessionSummary.id).filter(
                    SessionSummary.safety_assessment == "urgent"
                ).label("urgent"),
            )
            .join(Patient, SessionSummary.patient_id == Patient.id)
            .where(Patient.clinician_id == clinician_id)
        )
        counts = result.one()

        return {
            "active_concerns": counts.active or 0,
            "urgent_concerns": counts.urgent or 0,
        }
