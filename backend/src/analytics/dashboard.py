"""
Dashboard Service

Provides data for clinician dashboards.
"""

import logging
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.assessment import DiagnosticHypothesis, SessionSummary
from src.models.analytics import AssessmentProgress
from src.models.memory import TimelineEvent
from src.analytics.metrics import MetricsService
from src.schemas.analytics import (
    DashboardMetrics,
    PatientSummaryCard,
    DashboardData,
    PatientListItem,
)

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics_service = MetricsService(db)

    async def get_dashboard(self, clinician_id: UUID) -> DashboardData:
        """Get full dashboard data for a clinician."""
        # Get metrics
        metrics_data = await self.metrics_service.get_clinician_metrics(clinician_id)
        metrics = DashboardMetrics(
            clinician_id=clinician_id,
            snapshot_date=date.today(),
            total_patients=metrics_data.get("total_patients", 0),
            active_patients=metrics_data.get("active_patients", 0),
            patients_in_assessment=metrics_data.get("patients_in_assessment", 0),
            total_sessions_completed=metrics_data.get("total_sessions_completed", 0),
            sessions_this_week=metrics_data.get("sessions_this_week", 0),
            sessions_this_month=metrics_data.get("sessions_this_month", 0),
            avg_session_duration_minutes=metrics_data.get("avg_session_duration_minutes"),
            assessments_in_progress=metrics_data.get("assessments_in_progress", 0),
            assessments_completed=metrics_data.get("assessments_completed", 0),
            active_concerns=metrics_data.get("active_concerns", 0),
            urgent_concerns=metrics_data.get("urgent_concerns", 0),
        )

        # Get recent patients
        recent_patients = await self._get_recent_patients(clinician_id, limit=5)

        # Get upcoming sessions
        upcoming = await self._get_upcoming_sessions(clinician_id, limit=5)

        # Get recent activity
        activity = await self._get_recent_activity(clinician_id, limit=10)

        # Get alerts
        alerts = await self._get_alerts(clinician_id)

        return DashboardData(
            metrics=metrics,
            recent_patients=recent_patients,
            upcoming_sessions=upcoming,
            recent_activity=activity,
            alerts=alerts,
        )

    async def get_patient_list(
        self,
        clinician_id: UUID,
        status: Optional[str] = None,
        assessment_status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get paginated patient list for a clinician."""
        query = (
            select(Patient)
            .where(Patient.clinician_id == clinician_id)
        )

        if status:
            query = query.where(Patient.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Patient.first_name.ilike(search_term),
                    Patient.last_name.ilike(search_term),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Patient.updated_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(query)
        patients = list(result.scalars().all())

        # Enrich with additional data
        patient_items = []
        for patient in patients:
            item = await self._enrich_patient_item(patient, assessment_status)
            if item:
                patient_items.append(item)

        total_pages = (total + page_size - 1) // page_size

        return {
            "patients": patient_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_patient_summary_card(
        self,
        patient_id: UUID,
    ) -> Optional[PatientSummaryCard]:
        """Get summary card for a single patient."""
        patient = await self.db.get(Patient, patient_id)
        if not patient:
            return None

        return await self._build_patient_card(patient)

    async def get_patients_needing_attention(
        self,
        clinician_id: UUID,
        limit: int = 10,
    ) -> list[PatientSummaryCard]:
        """Get patients that need clinician attention."""
        # Patients with concerns or stale assessments
        week_ago = datetime.utcnow() - timedelta(days=7)

        # Get patients with urgent concerns
        concern_query = (
            select(Patient)
            .join(SessionSummary, Patient.id == SessionSummary.patient_id)
            .where(
                Patient.clinician_id == clinician_id,
                SessionSummary.safety_assessment.in_(["review", "urgent"]),
            )
            .distinct()
            .limit(limit // 2)
        )
        concern_result = await self.db.execute(concern_query)
        concern_patients = list(concern_result.scalars().all())

        # Get patients with no recent sessions
        stale_query = (
            select(Patient)
            .outerjoin(
                VoiceSession,
                and_(
                    Patient.id == VoiceSession.patient_id,
                    VoiceSession.ended_at >= week_ago,
                )
            )
            .where(
                Patient.clinician_id == clinician_id,
                Patient.status == "active",
                VoiceSession.id == None,
            )
            .limit(limit // 2)
        )
        stale_result = await self.db.execute(stale_query)
        stale_patients = list(stale_result.scalars().all())

        # Combine and build cards
        all_patients = {p.id: p for p in concern_patients + stale_patients}
        cards = []
        for patient in all_patients.values():
            card = await self._build_patient_card(patient)
            if card:
                cards.append(card)

        return cards[:limit]

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_recent_patients(
        self,
        clinician_id: UUID,
        limit: int,
    ) -> list[PatientSummaryCard]:
        """Get recently active patients."""
        result = await self.db.execute(
            select(Patient)
            .join(VoiceSession, Patient.id == VoiceSession.patient_id)
            .where(Patient.clinician_id == clinician_id)
            .order_by(VoiceSession.ended_at.desc().nullslast())
            .distinct()
            .limit(limit)
        )
        patients = list(result.scalars().all())

        cards = []
        for patient in patients:
            card = await self._build_patient_card(patient)
            if card:
                cards.append(card)

        return cards

    async def _build_patient_card(self, patient: Patient) -> PatientSummaryCard:
        """Build a summary card for a patient."""
        # Calculate age
        today = date.today()
        age = today.year - patient.date_of_birth.year
        if today.month < patient.date_of_birth.month or (
            today.month == patient.date_of_birth.month and today.day < patient.date_of_birth.day
        ):
            age -= 1

        # Get session info
        session_result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("count"),
                func.max(VoiceSession.ended_at).label("last_session"),
            ).where(
                VoiceSession.patient_id == patient.id,
                VoiceSession.status == "completed",
            )
        )
        session_info = session_result.one()

        # Get assessment progress
        progress_result = await self.db.execute(
            select(AssessmentProgress).where(AssessmentProgress.patient_id == patient.id)
        )
        progress = progress_result.scalar_one_or_none()

        # Get primary hypothesis
        hyp_result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient.id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
            .limit(1)
        )
        hypothesis = hyp_result.scalar_one_or_none()

        # Check for concerns
        concern_result = await self.db.execute(
            select(func.count(SessionSummary.id)).where(
                SessionSummary.patient_id == patient.id,
                SessionSummary.safety_assessment.in_(["review", "urgent"]),
            )
        )
        has_concerns = (concern_result.scalar() or 0) > 0

        # Determine next action
        next_action = self._determine_next_action(progress, session_info.last_session)

        return PatientSummaryCard(
            patient_id=patient.id,
            name=f"{patient.first_name} {patient.last_name}",
            age=age,
            status=patient.status,
            last_session_date=session_info.last_session.date() if session_info.last_session else None,
            sessions_completed=session_info.count or 0,
            assessment_completeness=progress.overall_completeness if progress else 0.0,
            primary_hypothesis=hypothesis.condition_name if hypothesis else None,
            hypothesis_strength=hypothesis.evidence_strength if hypothesis else None,
            has_concerns=has_concerns,
            next_action=next_action,
        )

    async def _enrich_patient_item(
        self,
        patient: Patient,
        assessment_status_filter: Optional[str],
    ) -> Optional[PatientListItem]:
        """Enrich patient with additional data for list view."""
        # Calculate age
        today = date.today()
        age = today.year - patient.date_of_birth.year

        # Get session info
        session_result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("count"),
                func.max(func.date(VoiceSession.ended_at)).label("last_session"),
            ).where(
                VoiceSession.patient_id == patient.id,
                VoiceSession.status == "completed",
            )
        )
        session_info = session_result.one()

        # Get assessment progress
        progress_result = await self.db.execute(
            select(AssessmentProgress).where(AssessmentProgress.patient_id == patient.id)
        )
        progress = progress_result.scalar_one_or_none()

        assessment_status = progress.status if progress else "not_started"

        # Filter by assessment status if specified
        if assessment_status_filter and assessment_status != assessment_status_filter:
            return None

        # Get primary hypothesis
        hyp_result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient.id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
            .limit(1)
        )
        hypothesis = hyp_result.scalar_one_or_none()

        return PatientListItem(
            patient_id=patient.id,
            name=f"{patient.first_name} {patient.last_name}",
            age=age,
            primary_concern=patient.primary_concern,
            status=patient.status,
            assessment_status=assessment_status,
            completeness=progress.overall_completeness if progress else 0.0,
            last_session=session_info.last_session,
            sessions_count=session_info.count or 0,
            primary_hypothesis=hypothesis.condition_name if hypothesis else None,
        )

    async def _get_upcoming_sessions(
        self,
        clinician_id: UUID,
        limit: int,
    ) -> list[dict]:
        """Get upcoming scheduled sessions."""
        result = await self.db.execute(
            select(VoiceSession, Patient)
            .join(Patient, VoiceSession.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                VoiceSession.status == "pending",
                VoiceSession.scheduled_at != None,
                VoiceSession.scheduled_at >= datetime.utcnow(),
            )
            .order_by(VoiceSession.scheduled_at)
            .limit(limit)
        )

        return [
            {
                "session_id": str(session.id),
                "patient_name": f"{patient.first_name} {patient.last_name}",
                "session_type": session.session_type,
                "scheduled_at": session.scheduled_at.isoformat(),
            }
            for session, patient in result.all()
        ]

    async def _get_recent_activity(
        self,
        clinician_id: UUID,
        limit: int,
    ) -> list[dict]:
        """Get recent activity for the clinician."""
        activities = []

        # Recent sessions
        session_result = await self.db.execute(
            select(VoiceSession, Patient)
            .join(Patient, VoiceSession.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                VoiceSession.status == "completed",
            )
            .order_by(VoiceSession.ended_at.desc())
            .limit(limit // 2)
        )

        for session, patient in session_result.all():
            activities.append({
                "type": "session_completed",
                "timestamp": session.ended_at.isoformat() if session.ended_at else None,
                "description": f"Session with {patient.first_name} {patient.last_name}",
                "patient_id": str(patient.id),
            })

        # Recent timeline events
        event_result = await self.db.execute(
            select(TimelineEvent, Patient)
            .join(Patient, TimelineEvent.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                TimelineEvent.significance.in_(["high", "critical"]),
            )
            .order_by(TimelineEvent.occurred_at.desc())
            .limit(limit // 2)
        )

        for event, patient in event_result.all():
            activities.append({
                "type": f"event_{event.event_type}",
                "timestamp": event.occurred_at.isoformat(),
                "description": f"{event.title} - {patient.first_name} {patient.last_name}",
                "patient_id": str(patient.id),
            })

        # Sort by timestamp
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return activities[:limit]

    async def _get_alerts(self, clinician_id: UUID) -> list[dict]:
        """Get alerts for the clinician."""
        alerts = []

        # Urgent concerns
        concern_result = await self.db.execute(
            select(SessionSummary, Patient)
            .join(Patient, SessionSummary.patient_id == Patient.id)
            .where(
                Patient.clinician_id == clinician_id,
                SessionSummary.safety_assessment == "urgent",
            )
            .order_by(SessionSummary.created_at.desc())
            .limit(5)
        )

        for summary, patient in concern_result.all():
            alerts.append({
                "type": "urgent_concern",
                "severity": "critical",
                "message": f"Urgent concern flagged for {patient.first_name} {patient.last_name}",
                "patient_id": str(patient.id),
                "created_at": summary.created_at.isoformat(),
            })

        # Stale assessments (no session in 14+ days)
        two_weeks_ago = datetime.utcnow() - timedelta(days=14)
        stale_result = await self.db.execute(
            select(Patient)
            .join(AssessmentProgress, Patient.id == AssessmentProgress.patient_id)
            .where(
                Patient.clinician_id == clinician_id,
                AssessmentProgress.status.in_(["initial_assessment", "ongoing"]),
                AssessmentProgress.last_session_date < two_weeks_ago.date(),
            )
            .limit(5)
        )

        for patient in stale_result.scalars().all():
            alerts.append({
                "type": "stale_assessment",
                "severity": "warning",
                "message": f"No recent session with {patient.first_name} {patient.last_name}",
                "patient_id": str(patient.id),
            })

        return alerts

    def _determine_next_action(
        self,
        progress: Optional[AssessmentProgress],
        last_session: Optional[datetime],
    ) -> Optional[str]:
        """Determine the recommended next action for a patient."""
        if not progress:
            return "Schedule intake session"

        if progress.status == "not_started":
            return "Schedule intake session"

        if progress.status == "completed":
            return None

        if progress.recommended_focus_areas:
            areas = progress.recommended_focus_areas.get("areas", [])
            if areas:
                return f"Explore: {areas[0]}"

        if last_session:
            days_since = (datetime.utcnow() - last_session).days
            if days_since > 7:
                return "Schedule follow-up session"

        return "Continue assessment"
