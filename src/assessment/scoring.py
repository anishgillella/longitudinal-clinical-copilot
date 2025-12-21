"""
Domain Scoring Service

Scores assessment domains based on extracted signals.
"""

import logging
import json
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import DOMAIN_SCORING_SYSTEM, DOMAIN_SCORING_USER
from src.assessment.domains import AUTISM_DOMAINS, get_domain_by_code, get_domains_for_prompt
from src.models.assessment import ClinicalSignal, AssessmentDomainScore

logger = logging.getLogger(__name__)


class DomainScoringService:
    """Service for scoring assessment domains."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def score_domains(
        self,
        session_id: UUID,
        patient_id: UUID,
        signals: list[ClinicalSignal],
    ) -> list[AssessmentDomainScore]:
        """
        Score assessment domains based on signals from a session.

        Args:
            session_id: The session being scored
            patient_id: The patient ID
            signals: List of signals extracted from the session

        Returns:
            List of domain scores
        """
        if not signals:
            logger.info(f"No signals to score for session {session_id}")
            return []

        # Prepare signals for prompt
        signals_json = json.dumps([
            {
                "type": s.signal_type,
                "name": s.signal_name,
                "evidence": s.evidence[:200],  # Truncate for prompt
                "intensity": s.intensity,
                "confidence": s.confidence,
                "domain": s.maps_to_domain,
                "significance": s.clinical_significance,
            }
            for s in signals
        ], indent=2)

        domains_text = get_domains_for_prompt()

        user_prompt = DOMAIN_SCORING_USER.format(
            signals_json=signals_json,
            domains_text=domains_text,
        )

        # Call LLM
        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": DOMAIN_SCORING_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception as e:
            logger.error(f"Domain scoring failed: {e}")
            raise

        # Parse and store scores
        scores = []
        for score_data in result.get("domain_scores", []):
            domain_code = score_data.get("domain_code")
            domain = get_domain_by_code(domain_code)

            if not domain:
                logger.warning(f"Unknown domain code: {domain_code}")
                continue

            raw_score = float(score_data.get("raw_score", 0.0))

            score = AssessmentDomainScore(
                session_id=session_id,
                patient_id=patient_id,
                domain_code=domain_code,
                domain_name=domain.name,
                category=domain.category.value,
                raw_score=raw_score,
                normalized_score=raw_score,  # Already 0-1
                confidence=float(score_data.get("confidence", 0.5)),
                evidence_count=int(score_data.get("evidence_count", 0)),
                key_evidence=score_data.get("key_evidence"),
                assessed_at=datetime.utcnow(),
                model_version=self.llm.model,
            )
            self.db.add(score)
            scores.append(score)

        await self.db.commit()

        for score in scores:
            await self.db.refresh(score)

        logger.info(f"Scored {len(scores)} domains for session {session_id}")
        return scores

    async def get_scores_for_session(self, session_id: UUID) -> list[AssessmentDomainScore]:
        """Get all domain scores for a session."""
        result = await self.db.execute(
            select(AssessmentDomainScore)
            .where(AssessmentDomainScore.session_id == session_id)
            .order_by(AssessmentDomainScore.domain_code)
        )
        return list(result.scalars().all())

    async def get_latest_scores_for_patient(
        self,
        patient_id: UUID,
    ) -> dict[str, AssessmentDomainScore]:
        """
        Get the most recent score for each domain for a patient.

        Returns:
            Dict mapping domain_code to latest score
        """
        # Subquery to get max assessed_at for each domain
        subquery = (
            select(
                AssessmentDomainScore.domain_code,
                func.max(AssessmentDomainScore.assessed_at).label("max_assessed"),
            )
            .where(AssessmentDomainScore.patient_id == patient_id)
            .group_by(AssessmentDomainScore.domain_code)
            .subquery()
        )

        # Get scores matching the max dates
        query = (
            select(AssessmentDomainScore)
            .join(
                subquery,
                (AssessmentDomainScore.domain_code == subquery.c.domain_code)
                & (AssessmentDomainScore.assessed_at == subquery.c.max_assessed),
            )
            .where(AssessmentDomainScore.patient_id == patient_id)
        )

        result = await self.db.execute(query)
        scores = result.scalars().all()

        return {score.domain_code: score for score in scores}

    async def get_domain_history(
        self,
        patient_id: UUID,
        domain_code: str,
        days: int = 90,
    ) -> list[AssessmentDomainScore]:
        """Get historical scores for a domain."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(AssessmentDomainScore)
            .where(
                AssessmentDomainScore.patient_id == patient_id,
                AssessmentDomainScore.domain_code == domain_code,
                AssessmentDomainScore.assessed_at >= cutoff,
            )
            .order_by(AssessmentDomainScore.assessed_at)
        )
        return list(result.scalars().all())

    async def calculate_domain_trend(
        self,
        patient_id: UUID,
        domain_code: str,
        days: int = 30,
    ) -> Optional[dict]:
        """
        Calculate trend for a domain over the specified period.

        Returns:
            Dict with trend direction and change, or None if insufficient data
        """
        history = await self.get_domain_history(patient_id, domain_code, days)

        if len(history) < 2:
            return None

        first_score = history[0].normalized_score
        last_score = history[-1].normalized_score
        change = last_score - first_score

        if abs(change) < 0.05:
            trend = "stable"
        elif change > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "trend": trend,
            "change": change,
            "first_score": first_score,
            "last_score": last_score,
            "data_points": len(history),
        }

    async def get_domains_needing_exploration(
        self,
        patient_id: UUID,
    ) -> list[str]:
        """
        Identify domains that need more data.

        Returns domains with:
        - No scores yet
        - Low confidence scores
        - High uncertainty
        """
        latest_scores = await self.get_latest_scores_for_patient(patient_id)

        # All possible domains
        all_domains = [d.code for d in AUTISM_DOMAINS]

        # Domains needing exploration
        needs_exploration = []

        for domain_code in all_domains:
            if domain_code not in latest_scores:
                # No data at all
                needs_exploration.append(domain_code)
            elif latest_scores[domain_code].confidence < 0.5:
                # Low confidence
                needs_exploration.append(domain_code)

        return needs_exploration
