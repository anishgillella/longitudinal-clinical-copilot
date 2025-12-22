"""
Signal Extraction Service

Extracts clinical signals from session transcripts using LLM analysis.
"""

import logging
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import (
    SIGNAL_EXTRACTION_SYSTEM,
    SIGNAL_EXTRACTION_USER,
    CONCERN_DETECTION_SYSTEM,
    CONCERN_DETECTION_USER,
)
from src.assessment.domains import AUTISM_DOMAINS, get_domains_for_prompt
from src.models.assessment import ClinicalSignal
from src.models.session import VoiceSession

logger = logging.getLogger(__name__)


class SignalExtractionService:
    """Service for extracting clinical signals from transcripts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def extract_signals(
        self,
        session_id: UUID,
        transcript: str,
        session_type: str = "intake",
    ) -> list[ClinicalSignal]:
        """
        Extract clinical signals from a session transcript.

        Args:
            session_id: The session ID
            transcript: Full transcript text
            session_type: Type of session (intake, checkin, etc.)

        Returns:
            List of extracted ClinicalSignal objects
        """
        # Get session for patient_id
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Prepare prompt
        domains_text = get_domains_for_prompt()

        user_prompt = SIGNAL_EXTRACTION_USER.format(
            session_type=session_type,
            domains_text=domains_text,
            transcript=transcript,
        )

        # Call LLM
        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": SIGNAL_EXTRACTION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Lower for more consistent extraction
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise

        # Parse and store signals
        signals = []
        for signal_data in result.get("signals", []):
            signal = ClinicalSignal(
                session_id=session_id,
                patient_id=session.patient_id,
                signal_type=signal_data.get("signal_type", "behavioral"),
                signal_name=signal_data.get("signal_name", "Unknown"),
                evidence=signal_data.get("evidence", ""),
                evidence_type=signal_data.get("evidence_type", "inferred"),
                reasoning=signal_data.get("reasoning"),
                transcript_line=signal_data.get("transcript_line"),
                intensity=float(signal_data.get("intensity", 0.5)),
                confidence=float(signal_data.get("confidence", 0.5)),
                maps_to_domain=signal_data.get("maps_to_domain"),
                clinical_significance=signal_data.get("clinical_significance", "moderate"),
                extracted_at=datetime.utcnow(),
                model_version=self.llm.model,
            )
            self.db.add(signal)
            signals.append(signal)

        await self.db.commit()

        # Refresh to get IDs
        for signal in signals:
            await self.db.refresh(signal)

        logger.info(f"Extracted {len(signals)} signals from session {session_id}")
        return signals

    async def detect_concerns(
        self,
        session_id: UUID,
        transcript: str,
    ) -> dict:
        """
        Detect clinical concerns requiring attention.

        Returns:
            Dict with concerns and safety assessment
        """
        user_prompt = CONCERN_DETECTION_USER.format(transcript=transcript)

        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": CONCERN_DETECTION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Very low for safety-critical
            )
        except Exception as e:
            logger.error(f"Concern detection failed: {e}")
            # Return safe default on error
            return {
                "concerns": [],
                "overall_safety_assessment": "review",
                "notes": f"Error during analysis: {str(e)}",
            }

        return result

    async def get_signals_for_session(self, session_id: UUID) -> list[ClinicalSignal]:
        """Get all signals extracted from a session."""
        result = await self.db.execute(
            select(ClinicalSignal)
            .where(ClinicalSignal.session_id == session_id)
            .order_by(ClinicalSignal.extracted_at)
        )
        return list(result.scalars().all())

    async def get_signals_for_patient(
        self,
        patient_id: UUID,
        signal_type: Optional[str] = None,
        domain: Optional[str] = None,
        significance: Optional[str] = None,
    ) -> list[ClinicalSignal]:
        """Get all signals for a patient with optional filters."""
        query = select(ClinicalSignal).where(ClinicalSignal.patient_id == patient_id)

        if signal_type:
            query = query.where(ClinicalSignal.signal_type == signal_type)
        if domain:
            query = query.where(ClinicalSignal.maps_to_domain == domain)
        if significance:
            query = query.where(ClinicalSignal.clinical_significance == significance)

        query = query.order_by(ClinicalSignal.extracted_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_signal_summary(self, patient_id: UUID) -> dict:
        """Get summary statistics of signals for a patient."""
        signals = await self.get_signals_for_patient(patient_id)

        by_type = {}
        by_domain = {}
        by_significance = {}

        for signal in signals:
            by_type[signal.signal_type] = by_type.get(signal.signal_type, 0) + 1
            if signal.maps_to_domain:
                by_domain[signal.maps_to_domain] = by_domain.get(signal.maps_to_domain, 0) + 1
            by_significance[signal.clinical_significance] = (
                by_significance.get(signal.clinical_significance, 0) + 1
            )

        return {
            "total": len(signals),
            "by_type": by_type,
            "by_domain": by_domain,
            "by_significance": by_significance,
        }
