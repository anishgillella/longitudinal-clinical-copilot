"""
Assessment Progress Service

Tracks and updates patient assessment progress.
"""

import logging
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.assessment import (
    ClinicalSignal,
    AssessmentDomainScore,
    DiagnosticHypothesis,
)
from src.models.analytics import AssessmentProgress
from src.assessment.domains import AUTISM_DOMAINS
from src.assessment.scoring import DomainScoringService

logger = logging.getLogger(__name__)


class ProgressService:
    """Service for tracking assessment progress."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scoring_service = DomainScoringService(db)
        self.total_domains = len(AUTISM_DOMAINS)

    async def get_or_create_progress(self, patient_id: UUID) -> AssessmentProgress:
        """Get or create assessment progress for a patient."""
        result = await self.db.execute(
            select(AssessmentProgress).where(AssessmentProgress.patient_id == patient_id)
        )
        progress = result.scalar_one_or_none()

        if not progress:
            progress = AssessmentProgress(
                patient_id=patient_id,
                domains_total=self.total_domains,
            )
            self.db.add(progress)
            await self.db.commit()
            await self.db.refresh(progress)

        return progress

    async def update_progress(self, patient_id: UUID) -> AssessmentProgress:
        """
        Update assessment progress for a patient.

        Recalculates all progress metrics based on current data.
        """
        progress = await self.get_or_create_progress(patient_id)

        # Update session counts
        session_info = await self._get_session_info(patient_id)
        progress.total_sessions = session_info["total"]
        progress.intake_completed = session_info["intake_completed"]
        progress.last_session_date = session_info["last_session_date"]

        # Update domain coverage
        domain_coverage = await self._get_domain_coverage(patient_id)
        progress.domains_explored = domain_coverage["explored_count"]
        progress.domain_coverage = domain_coverage["details"]
        progress.high_confidence_domains = domain_coverage["high_confidence_count"]

        # Update signal count
        signal_count = await self._get_signal_count(patient_id)
        progress.signals_collected = signal_count

        # Update hypothesis info
        hypothesis_info = await self._get_hypothesis_info(patient_id)
        progress.primary_hypothesis_strength = hypothesis_info["strength"]
        progress.hypothesis_stability = hypothesis_info["stability"]

        # Calculate overall completeness
        progress.overall_completeness = self._calculate_completeness(
            domains_explored=progress.domains_explored,
            domains_total=progress.domains_total,
            sessions=progress.total_sessions,
            has_hypothesis=hypothesis_info["strength"] is not None,
        )

        # Update status
        progress.status = self._determine_status(
            completeness=progress.overall_completeness,
            sessions=progress.total_sessions,
            intake_completed=progress.intake_completed,
            hypothesis_strength=hypothesis_info["strength"],
        )

        # Get recommended focus areas
        progress.recommended_focus_areas = await self._get_focus_areas(patient_id)

        # Estimate remaining sessions
        progress.estimated_sessions_remaining = self._estimate_remaining_sessions(
            completeness=progress.overall_completeness,
            current_sessions=progress.total_sessions,
        )

        await self.db.commit()
        await self.db.refresh(progress)

        logger.info(f"Updated progress for patient {patient_id}: {progress.status}")
        return progress

    async def get_progress_details(self, patient_id: UUID) -> dict:
        """Get detailed progress information."""
        progress = await self.get_or_create_progress(patient_id)

        # Get domain details
        domain_scores = await self.scoring_service.get_latest_scores_for_patient(patient_id)

        domain_details = []
        for domain in AUTISM_DOMAINS:
            score = domain_scores.get(domain.code)
            domain_details.append({
                "domain_code": domain.code,
                "domain_name": domain.name,
                "explored": score is not None,
                "confidence": score.confidence if score else None,
                "score": score.normalized_score if score else None,
                "evidence_count": score.evidence_count if score else 0,
                "last_assessed": score.assessed_at.date().isoformat() if score else None,
            })

        # Get focus areas
        focus_areas = progress.recommended_focus_areas or {}

        return {
            "patient_id": str(patient_id),
            "status": progress.status,
            "overall_completeness": progress.overall_completeness,
            "total_sessions": progress.total_sessions,
            "intake_completed": progress.intake_completed,
            "last_session_date": progress.last_session_date.isoformat() if progress.last_session_date else None,
            "next_session_recommended": progress.next_session_recommended.isoformat() if progress.next_session_recommended else None,
            "domains_explored": progress.domains_explored,
            "domains_total": progress.domains_total,
            "domain_details": domain_details,
            "signals_collected": progress.signals_collected,
            "high_confidence_domains": progress.high_confidence_domains,
            "primary_hypothesis_strength": progress.primary_hypothesis_strength,
            "hypothesis_stability": progress.hypothesis_stability,
            "recommended_focus_areas": focus_areas.get("areas", []),
            "estimated_sessions_remaining": progress.estimated_sessions_remaining,
        }

    async def set_status(
        self,
        patient_id: UUID,
        status: str,
        notes: Optional[str] = None,
    ) -> AssessmentProgress:
        """Manually set assessment status."""
        progress = await self.get_or_create_progress(patient_id)
        progress.status = status
        await self.db.commit()
        await self.db.refresh(progress)
        return progress

    async def schedule_next_session(
        self,
        patient_id: UUID,
        recommended_date: date,
    ) -> AssessmentProgress:
        """Set recommended next session date."""
        progress = await self.get_or_create_progress(patient_id)
        progress.next_session_recommended = recommended_date
        await self.db.commit()
        await self.db.refresh(progress)
        return progress

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_session_info(self, patient_id: UUID) -> dict:
        """Get session information for a patient."""
        result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("total"),
                func.count(VoiceSession.id).filter(
                    VoiceSession.session_type == "intake"
                ).label("intake_count"),
                func.max(func.date(VoiceSession.ended_at)).label("last_date"),
            ).where(
                VoiceSession.patient_id == patient_id,
                VoiceSession.status == "completed",
            )
        )
        info = result.one()

        return {
            "total": info.total or 0,
            "intake_completed": (info.intake_count or 0) > 0,
            "last_session_date": info.last_date,
        }

    async def _get_domain_coverage(self, patient_id: UUID) -> dict:
        """Get domain coverage information."""
        scores = await self.scoring_service.get_latest_scores_for_patient(patient_id)

        details = {}
        explored_count = 0
        high_confidence_count = 0

        for domain in AUTISM_DOMAINS:
            score = scores.get(domain.code)
            if score:
                explored_count += 1
                if score.confidence >= 0.6:
                    high_confidence_count += 1
                details[domain.code] = {
                    "explored": True,
                    "confidence": score.confidence,
                    "score": score.normalized_score,
                }
            else:
                details[domain.code] = {
                    "explored": False,
                    "confidence": None,
                    "score": None,
                }

        return {
            "explored_count": explored_count,
            "high_confidence_count": high_confidence_count,
            "details": details,
        }

    async def _get_signal_count(self, patient_id: UUID) -> int:
        """Get total signal count for a patient."""
        result = await self.db.execute(
            select(func.count(ClinicalSignal.id)).where(
                ClinicalSignal.patient_id == patient_id
            )
        )
        return result.scalar() or 0

    async def _get_hypothesis_info(self, patient_id: UUID) -> dict:
        """Get hypothesis information."""
        # Get primary hypothesis
        result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient_id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
            .limit(1)
        )
        hypothesis = result.scalar_one_or_none()

        if not hypothesis:
            return {"strength": None, "stability": None}

        # Determine stability based on trend
        stability = "stable"
        if hypothesis.trend == "increasing" or hypothesis.trend == "decreasing":
            stability = "stabilizing"
        elif hypothesis.uncertainty > 0.3:
            stability = "volatile"

        return {
            "strength": hypothesis.evidence_strength,
            "stability": stability,
        }

    def _calculate_completeness(
        self,
        domains_explored: int,
        domains_total: int,
        sessions: int,
        has_hypothesis: bool,
    ) -> float:
        """Calculate overall assessment completeness."""
        # Domain coverage (40%)
        domain_score = (domains_explored / domains_total) * 0.4 if domains_total > 0 else 0

        # Session progress (30%) - assumes ~10 sessions for complete assessment
        session_score = min(sessions / 10, 1.0) * 0.3

        # Hypothesis generation (30%)
        hypothesis_score = 0.3 if has_hypothesis else 0

        return min(domain_score + session_score + hypothesis_score, 1.0)

    def _determine_status(
        self,
        completeness: float,
        sessions: int,
        intake_completed: bool,
        hypothesis_strength: Optional[float],
    ) -> str:
        """Determine assessment status."""
        if completeness >= 0.9 and hypothesis_strength and hypothesis_strength >= 0.7:
            return "completed"
        elif completeness >= 0.7:
            return "near_completion"
        elif sessions > 3:
            return "ongoing"
        elif intake_completed:
            return "initial_assessment"
        elif sessions > 0:
            return "initial_assessment"
        else:
            return "not_started"

    async def _get_focus_areas(self, patient_id: UUID) -> dict:
        """Get recommended focus areas."""
        # Get domains needing exploration
        domains_needing = await self.scoring_service.get_domains_needing_exploration(patient_id)

        # Prioritize by domain importance
        priority_domains = [
            "social_emotional_reciprocity",
            "nonverbal_communication",
            "relationships",
            "stereotyped_movements",
            "restricted_interests",
        ]

        focus_areas = []
        for domain in priority_domains:
            if domain in domains_needing:
                domain_info = next((d for d in AUTISM_DOMAINS if d.code == domain), None)
                if domain_info:
                    focus_areas.append(domain_info.name)

        # Add remaining needed domains
        for domain_code in domains_needing:
            if domain_code not in priority_domains and len(focus_areas) < 5:
                domain_info = next((d for d in AUTISM_DOMAINS if d.code == domain_code), None)
                if domain_info:
                    focus_areas.append(domain_info.name)

        return {"areas": focus_areas[:5]}

    def _estimate_remaining_sessions(
        self,
        completeness: float,
        current_sessions: int,
    ) -> Optional[int]:
        """Estimate remaining sessions needed."""
        if completeness >= 0.9:
            return 0
        if current_sessions == 0:
            return 8  # Typical full assessment

        # Estimate based on current rate
        remaining = 1.0 - completeness
        rate = completeness / current_sessions if current_sessions > 0 else 0.1
        if rate > 0:
            estimated = int(remaining / rate) + 1
            return min(estimated, 15)  # Cap at 15

        return 5  # Default
