"""
Post-Session Processing Pipeline

Orchestrates the full processing of a completed voice session:
1. Extract clinical signals from transcript
2. Score assessment domains
3. Update diagnostic hypotheses
4. Generate session summary
5. Check for clinical concerns
"""

import logging
import time
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.session import VoiceSession, Transcript
from src.models.assessment import SessionSummary, ClinicalSignal, AssessmentDomainScore
from src.assessment.extraction import SignalExtractionService
from src.assessment.scoring import DomainScoringService
from src.assessment.hypothesis import HypothesisEngine
from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import SESSION_SUMMARY_SYSTEM, SESSION_SUMMARY_USER

logger = logging.getLogger(__name__)


class ProcessingResult:
    """Result of session processing."""

    def __init__(self, session_id: UUID):
        self.session_id = session_id
        self.status = "pending"
        self.signals_extracted = 0
        self.domains_scored = 0
        self.hypotheses_updated = False
        self.summary_generated = False
        self.concerns_flagged = 0
        self.processing_time_ms = 0
        self.errors: list[str] = []

    def to_dict(self) -> dict:
        return {
            "session_id": str(self.session_id),
            "status": self.status,
            "signals_extracted": self.signals_extracted,
            "domains_scored": self.domains_scored,
            "hypotheses_updated": self.hypotheses_updated,
            "summary_generated": self.summary_generated,
            "concerns_flagged": self.concerns_flagged,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
        }


class SessionProcessor:
    """Orchestrates post-session processing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()
        self.extraction_service = SignalExtractionService(db)
        self.scoring_service = DomainScoringService(db)
        self.hypothesis_engine = HypothesisEngine(db)

    async def process_session(
        self,
        session_id: UUID,
        extract_signals: bool = True,
        score_domains: bool = True,
        update_hypotheses: bool = True,
        generate_summary: bool = True,
        check_concerns: bool = True,
    ) -> ProcessingResult:
        """
        Process a completed session through the full pipeline.

        Args:
            session_id: The session to process
            extract_signals: Whether to extract clinical signals
            score_domains: Whether to score assessment domains
            update_hypotheses: Whether to update diagnostic hypotheses
            generate_summary: Whether to generate session summary
            check_concerns: Whether to check for clinical concerns

        Returns:
            ProcessingResult with details of what was processed
        """
        start_time = time.time()
        result = ProcessingResult(session_id)

        # Get session and transcript
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            result.status = "failed"
            result.errors.append("Session not found")
            return result

        if session.status != "completed":
            result.status = "failed"
            result.errors.append(f"Session not completed (status: {session.status})")
            return result

        transcript = await self._get_transcript_text(session_id)
        if not transcript:
            result.status = "failed"
            result.errors.append("No transcript found")
            return result

        # Step 1: Extract signals
        signals = []
        if extract_signals:
            try:
                signals = await self.extraction_service.extract_signals(
                    session_id=session_id,
                    transcript=transcript,
                    session_type=session.session_type,
                )
                result.signals_extracted = len(signals)
            except Exception as e:
                logger.error(f"Signal extraction failed: {e}")
                result.errors.append(f"Signal extraction: {str(e)}")

        # Step 2: Score domains
        if score_domains and signals:
            try:
                scores = await self.scoring_service.score_domains(
                    session_id=session_id,
                    patient_id=session.patient_id,
                    signals=signals,
                )
                result.domains_scored = len(scores)
            except Exception as e:
                logger.error(f"Domain scoring failed: {e}")
                result.errors.append(f"Domain scoring: {str(e)}")

        # Step 3: Update hypotheses
        if update_hypotheses:
            try:
                await self.hypothesis_engine.generate_hypotheses(
                    patient_id=session.patient_id,
                    session_id=session_id,
                )
                result.hypotheses_updated = True
            except Exception as e:
                logger.error(f"Hypothesis generation failed: {e}")
                result.errors.append(f"Hypothesis generation: {str(e)}")

        # Step 4: Generate summary
        if generate_summary:
            try:
                await self._generate_and_store_summary(
                    session=session,
                    transcript=transcript,
                    signals=signals,
                )
                result.summary_generated = True
            except Exception as e:
                logger.error(f"Summary generation failed: {e}")
                result.errors.append(f"Summary generation: {str(e)}")

        # Step 5: Check concerns
        if check_concerns:
            try:
                concerns = await self.extraction_service.detect_concerns(
                    session_id=session_id,
                    transcript=transcript,
                )
                concern_list = concerns.get("concerns", [])
                result.concerns_flagged = len(concern_list)

                # Update session summary with concerns
                await self._update_summary_with_concerns(session_id, concerns)
            except Exception as e:
                logger.error(f"Concern detection failed: {e}")
                result.errors.append(f"Concern detection: {str(e)}")

        # Calculate processing time
        result.processing_time_ms = int((time.time() - start_time) * 1000)

        # Determine final status
        if result.errors:
            result.status = "partial" if result.signals_extracted > 0 else "failed"
        else:
            result.status = "completed"

        logger.info(
            f"Session {session_id} processed: {result.signals_extracted} signals, "
            f"{result.domains_scored} domains, {result.processing_time_ms}ms"
        )

        return result

    async def _get_transcript_text(self, session_id: UUID) -> Optional[str]:
        """Get transcript as formatted text."""
        result = await self.db.execute(
            select(Transcript)
            .where(Transcript.session_id == session_id)
            .order_by(Transcript.timestamp_ms.asc().nullslast(), Transcript.created_at.asc())
        )
        transcripts = result.scalars().all()

        if not transcripts:
            return None

        lines = []
        for t in transcripts:
            role_label = "Assistant" if t.role == "assistant" else "Patient"
            lines.append(f"{role_label}: {t.content}")

        return "\n\n".join(lines)

    async def _generate_and_store_summary(
        self,
        session: VoiceSession,
        transcript: str,
        signals: list,
    ) -> SessionSummary:
        """Generate and store session summary."""
        # Prepare signals summary
        signals_summary = ""
        if signals:
            signals_summary = "\n".join([
                f"- {s.signal_name} ({s.signal_type}): {s.evidence[:100]}"
                for s in signals[:10]  # Limit for prompt
            ])

        duration_minutes = (session.duration_seconds or 0) // 60

        user_prompt = SESSION_SUMMARY_USER.format(
            session_type=session.session_type,
            duration_minutes=duration_minutes,
            transcript=transcript,
            signals_summary=signals_summary or "No signals extracted",
        )

        result = await self.llm.complete_json(
            messages=[
                {"role": "system", "content": SESSION_SUMMARY_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

        # Check for existing summary
        existing = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session.id)
        )
        summary = existing.scalar_one_or_none()

        if summary:
            # Update existing
            summary.brief_summary = result.get("brief_summary", "")
            summary.detailed_summary = result.get("detailed_summary")
            summary.key_topics = {"topics": result.get("key_topics", [])}
            summary.emotional_tone = result.get("emotional_tone")
            summary.notable_quotes = {"quotes": result.get("notable_quotes", [])}
            summary.clinical_observations = result.get("clinical_observations")
            summary.follow_up_suggestions = {"suggestions": result.get("follow_up_suggestions", [])}
        else:
            # Create new
            summary = SessionSummary(
                session_id=session.id,
                patient_id=session.patient_id,
                brief_summary=result.get("brief_summary", ""),
                detailed_summary=result.get("detailed_summary"),
                key_topics={"topics": result.get("key_topics", [])},
                emotional_tone=result.get("emotional_tone"),
                notable_quotes={"quotes": result.get("notable_quotes", [])},
                clinical_observations=result.get("clinical_observations"),
                follow_up_suggestions={"suggestions": result.get("follow_up_suggestions", [])},
                model_version=self.llm.model,
            )
            self.db.add(summary)

        await self.db.commit()
        await self.db.refresh(summary)

        # Also update session's summary field
        session.summary = result.get("brief_summary", "")
        session.key_topics = {"topics": result.get("key_topics", [])}
        await self.db.commit()

        return summary

    async def _update_summary_with_concerns(
        self,
        session_id: UUID,
        concerns: dict,
    ):
        """Update session summary with detected concerns."""
        result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        summary = result.scalar_one_or_none()

        if summary:
            summary.concerns = concerns.get("concerns", [])
            summary.safety_assessment = concerns.get("overall_safety_assessment", "safe")
            await self.db.commit()

    async def get_processing_status(self, session_id: UUID) -> dict:
        """Get the processing status of a session."""
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            return {"status": "not_found"}

        # Check what has been processed
        signals_result = await self.db.execute(
            select(ClinicalSignal).where(ClinicalSignal.session_id == session_id).limit(1)
        )
        has_signals = signals_result.scalar_one_or_none() is not None

        scores_result = await self.db.execute(
            select(AssessmentDomainScore).where(AssessmentDomainScore.session_id == session_id).limit(1)
        )
        has_scores = scores_result.scalar_one_or_none() is not None

        summary_result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        has_summary = summary_result.scalar_one_or_none() is not None

        return {
            "status": "processed" if (has_signals and has_summary) else "pending",
            "has_signals": has_signals,
            "has_domain_scores": has_scores,
            "has_summary": has_summary,
        }
