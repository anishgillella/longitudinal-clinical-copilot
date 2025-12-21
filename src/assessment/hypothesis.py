"""
Hypothesis Generation Engine

Generates and updates diagnostic hypotheses based on accumulated evidence.

CRITICAL: This system generates HYPOTHESES for clinician review,
NOT diagnoses. All outputs include uncertainty and are framed
as patterns to investigate.
"""

import logging
import json
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import HYPOTHESIS_GENERATION_SYSTEM, HYPOTHESIS_GENERATION_USER
from src.models.assessment import (
    ClinicalSignal,
    AssessmentDomainScore,
    DiagnosticHypothesis,
    HypothesisHistory,
)
from src.assessment.scoring import DomainScoringService

logger = logging.getLogger(__name__)


class HypothesisEngine:
    """Engine for generating and updating diagnostic hypotheses."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()
        self.scoring_service = DomainScoringService(db)

    async def generate_hypotheses(
        self,
        patient_id: UUID,
        session_id: Optional[UUID] = None,
    ) -> list[DiagnosticHypothesis]:
        """
        Generate or update hypotheses based on all accumulated evidence.

        Args:
            patient_id: The patient ID
            session_id: Optional session that triggered this update

        Returns:
            List of updated hypothesis objects
        """
        # Gather all evidence
        domain_scores = await self.scoring_service.get_latest_scores_for_patient(patient_id)
        signals = await self._get_all_signals(patient_id)
        session_summary = await self._get_session_summary(patient_id)

        # Prepare data for prompt
        domain_scores_json = json.dumps([
            {
                "domain": score.domain_code,
                "name": score.domain_name,
                "score": score.normalized_score,
                "confidence": score.confidence,
                "evidence_count": score.evidence_count,
            }
            for score in domain_scores.values()
        ], indent=2)

        signals_summary = self._summarize_signals(signals)

        user_prompt = HYPOTHESIS_GENERATION_USER.format(
            domain_scores_json=domain_scores_json,
            signal_count=len(signals),
            signals_summary=signals_summary,
            session_summary=session_summary,
        )

        # Call LLM
        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": HYPOTHESIS_GENERATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            raise

        # Update hypotheses in database
        hypotheses = []
        for hyp_data in result.get("hypotheses", []):
            hypothesis = await self._update_hypothesis(
                patient_id=patient_id,
                session_id=session_id,
                hypothesis_data=hyp_data,
            )
            hypotheses.append(hypothesis)

        await self.db.commit()

        for hyp in hypotheses:
            await self.db.refresh(hyp)

        logger.info(f"Generated/updated {len(hypotheses)} hypotheses for patient {patient_id}")
        return hypotheses

    async def _update_hypothesis(
        self,
        patient_id: UUID,
        session_id: Optional[UUID],
        hypothesis_data: dict,
    ) -> DiagnosticHypothesis:
        """Create or update a single hypothesis."""
        condition_code = hypothesis_data.get("condition_code", "unknown")

        # Check for existing hypothesis
        result = await self.db.execute(
            select(DiagnosticHypothesis).where(
                DiagnosticHypothesis.patient_id == patient_id,
                DiagnosticHypothesis.condition_code == condition_code,
            )
        )
        existing = result.scalar_one_or_none()

        new_strength = float(hypothesis_data.get("evidence_strength", 0.0))
        new_uncertainty = float(hypothesis_data.get("uncertainty", 0.5))

        if existing:
            # Update existing
            previous_strength = existing.evidence_strength

            # Calculate trend
            delta = new_strength - previous_strength
            if abs(delta) < 0.05:
                trend = "stable"
            elif delta > 0:
                trend = "increasing"
            else:
                trend = "decreasing"

            # Record history
            history = HypothesisHistory(
                hypothesis_id=existing.id,
                session_id=session_id,
                evidence_strength=new_strength,
                uncertainty=new_uncertainty,
                delta_from_previous=delta,
            )
            self.db.add(history)

            # Update hypothesis
            existing.evidence_strength = new_strength
            existing.uncertainty = new_uncertainty
            existing.trend = trend
            existing.explanation = hypothesis_data.get("explanation")
            existing.supporting_evidence = {"points": hypothesis_data.get("supporting_evidence", [])}
            existing.contradicting_evidence = {"points": hypothesis_data.get("contradicting_evidence", [])}
            existing.supporting_signals = len(hypothesis_data.get("supporting_evidence", []))
            existing.contradicting_signals = len(hypothesis_data.get("contradicting_evidence", []))
            existing.model_version = self.llm.model

            return existing
        else:
            # Create new
            hypothesis = DiagnosticHypothesis(
                patient_id=patient_id,
                condition_code=condition_code,
                condition_name=hypothesis_data.get("condition_name", condition_code),
                evidence_strength=new_strength,
                uncertainty=new_uncertainty,
                supporting_signals=len(hypothesis_data.get("supporting_evidence", [])),
                contradicting_signals=len(hypothesis_data.get("contradicting_evidence", [])),
                first_indicated_at=datetime.utcnow(),
                trend="stable",
                explanation=hypothesis_data.get("explanation"),
                supporting_evidence={"points": hypothesis_data.get("supporting_evidence", [])},
                contradicting_evidence={"points": hypothesis_data.get("contradicting_evidence", [])},
                model_version=self.llm.model,
            )
            self.db.add(hypothesis)

            # Also add first history entry
            await self.db.flush()  # Get the ID
            history = HypothesisHistory(
                hypothesis_id=hypothesis.id,
                session_id=session_id,
                evidence_strength=new_strength,
                uncertainty=new_uncertainty,
                delta_from_previous=None,
            )
            self.db.add(history)

            return hypothesis

    async def get_hypotheses_for_patient(
        self,
        patient_id: UUID,
    ) -> list[DiagnosticHypothesis]:
        """Get all hypotheses for a patient."""
        result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient_id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
        )
        return list(result.scalars().all())

    async def get_hypothesis_history(
        self,
        hypothesis_id: UUID,
    ) -> list[HypothesisHistory]:
        """Get history for a specific hypothesis."""
        result = await self.db.execute(
            select(HypothesisHistory)
            .where(HypothesisHistory.hypothesis_id == hypothesis_id)
            .order_by(HypothesisHistory.recorded_at)
        )
        return list(result.scalars().all())

    async def get_primary_hypothesis(
        self,
        patient_id: UUID,
    ) -> Optional[DiagnosticHypothesis]:
        """Get the hypothesis with highest evidence strength."""
        result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient_id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_all_signals(self, patient_id: UUID) -> list[ClinicalSignal]:
        """Get all signals for a patient."""
        result = await self.db.execute(
            select(ClinicalSignal)
            .where(ClinicalSignal.patient_id == patient_id)
            .order_by(ClinicalSignal.extracted_at.desc())
        )
        return list(result.scalars().all())

    async def _get_session_summary(self, patient_id: UUID) -> str:
        """Get summary of sessions for context."""
        from src.models.session import VoiceSession

        result = await self.db.execute(
            select(VoiceSession)
            .where(
                VoiceSession.patient_id == patient_id,
                VoiceSession.status == "completed",
            )
            .order_by(VoiceSession.ended_at.desc())
            .limit(5)
        )
        sessions = result.scalars().all()

        if not sessions:
            return "No completed sessions yet."

        lines = []
        for s in sessions:
            date_str = s.ended_at.strftime("%Y-%m-%d") if s.ended_at else "Unknown"
            duration = f"{s.duration_seconds // 60}min" if s.duration_seconds else "Unknown"
            summary = s.summary[:100] + "..." if s.summary and len(s.summary) > 100 else (s.summary or "No summary")
            lines.append(f"- {date_str} ({s.session_type}, {duration}): {summary}")

        return "\n".join(lines)

    def _summarize_signals(self, signals: list[ClinicalSignal]) -> str:
        """Create a summary of signals for the prompt."""
        if not signals:
            return "No signals extracted yet."

        # Group by domain
        by_domain: dict[str, list[ClinicalSignal]] = {}
        for signal in signals:
            domain = signal.maps_to_domain or "uncategorized"
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(signal)

        lines = []
        for domain, domain_signals in by_domain.items():
            lines.append(f"\n{domain.upper()} ({len(domain_signals)} signals):")
            # Show top 3 by intensity
            top_signals = sorted(domain_signals, key=lambda s: s.intensity, reverse=True)[:3]
            for s in top_signals:
                lines.append(f"  - [{s.clinical_significance}] {s.signal_name}: {s.evidence[:80]}...")

        return "\n".join(lines)
