"""
Post-Session Processing Pipeline

Orchestrates the full processing of a completed voice session:
1. Extract clinical signals from transcript (parallel with 4, 5)
2. Score assessment domains (depends on 1)
3. Update diagnostic hypotheses (depends on 1, 2)
4. Generate session summary (parallel with 1, 5)
5. Check for clinical concerns (parallel with 1, 4)

Optimized for parallel execution where possible to reduce total processing time.
"""

import asyncio
import logging
import time
from uuid import UUID
from datetime import datetime
from typing import Optional, Tuple, Any

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

        # ============================================================
        # PHASE 1: Run independent tasks in parallel
        # - Signal extraction (needed for phase 2)
        # - Concern detection (independent)
        # ============================================================
        signals = []
        concerns = None

        phase1_tasks = []
        task_names = []

        if extract_signals:
            phase1_tasks.append(
                self._extract_signals_safe(session_id, transcript, session.session_type)
            )
            task_names.append("signals")

        if check_concerns:
            phase1_tasks.append(
                self._detect_concerns_safe(session_id, transcript)
            )
            task_names.append("concerns")

        if phase1_tasks:
            logger.info(f"Phase 1: Running {len(phase1_tasks)} tasks in parallel: {task_names}")
            phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)

            # Process phase 1 results
            result_idx = 0
            if extract_signals:
                signals_result = phase1_results[result_idx]
                result_idx += 1
                if isinstance(signals_result, Exception):
                    logger.error(f"Signal extraction failed: {signals_result}")
                    result.errors.append(f"Signal extraction: {str(signals_result)}")
                else:
                    signals = signals_result or []
                    result.signals_extracted = len(signals)

            if check_concerns:
                concerns_result = phase1_results[result_idx]
                if isinstance(concerns_result, Exception):
                    logger.error(f"Concern detection failed: {concerns_result}")
                    result.errors.append(f"Concern detection: {str(concerns_result)}")
                else:
                    concerns = concerns_result

        # ============================================================
        # PHASE 2: Run dependent tasks sequentially, but summary in parallel
        # - Domain scoring (needs signals from phase 1)
        # - Hypothesis generation (needs signals + domain scores)
        # - Summary generation (can run in parallel, uses signals if available)
        # ============================================================
        phase2_tasks = []
        phase2_task_names = []

        # Summary can run in parallel with scoring/hypothesis since it only
        # optionally uses signals (which we now have)
        if generate_summary:
            phase2_tasks.append(
                self._generate_summary_safe(session, transcript, signals)
            )
            phase2_task_names.append("summary")

        # Sequential chain: scoring -> hypothesis (run as a single coroutine)
        if score_domains or update_hypotheses:
            phase2_tasks.append(
                self._scoring_and_hypothesis_chain(
                    session_id=session_id,
                    patient_id=session.patient_id,
                    signals=signals,
                    score_domains=score_domains,
                    update_hypotheses=update_hypotheses,
                )
            )
            phase2_task_names.append("scoring_chain")

        if phase2_tasks:
            logger.info(f"Phase 2: Running {len(phase2_tasks)} tasks in parallel: {phase2_task_names}")
            phase2_results = await asyncio.gather(*phase2_tasks, return_exceptions=True)

            # Process phase 2 results
            result_idx = 0
            if generate_summary:
                summary_result = phase2_results[result_idx]
                result_idx += 1
                if isinstance(summary_result, Exception):
                    logger.error(f"Summary generation failed: {summary_result}")
                    result.errors.append(f"Summary generation: {str(summary_result)}")
                else:
                    result.summary_generated = True

            if score_domains or update_hypotheses:
                chain_result = phase2_results[result_idx]
                if isinstance(chain_result, Exception):
                    logger.error(f"Scoring/hypothesis chain failed: {chain_result}")
                    result.errors.append(f"Scoring/hypothesis: {str(chain_result)}")
                else:
                    domains_scored, hypotheses_updated = chain_result
                    result.domains_scored = domains_scored
                    result.hypotheses_updated = hypotheses_updated

        # ============================================================
        # PHASE 3: Update summary with concerns (needs both summary and concerns)
        # ============================================================
        if concerns and result.summary_generated:
            try:
                concern_list = concerns.get("concerns", [])
                result.concerns_flagged = len(concern_list)
                await self._update_summary_with_concerns(session_id, concerns)
            except Exception as e:
                logger.error(f"Updating summary with concerns failed: {e}")
                result.errors.append(f"Concern update: {str(e)}")
        elif concerns:
            # Still count concerns even if summary wasn't generated
            concern_list = concerns.get("concerns", [])
            result.concerns_flagged = len(concern_list)

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

    # ================================================================
    # Helper methods for parallel execution
    # ================================================================

    async def _extract_signals_safe(
        self,
        session_id: UUID,
        transcript: str,
        session_type: str,
    ) -> list:
        """Extract signals with error handling for parallel execution."""
        return await self.extraction_service.extract_signals(
            session_id=session_id,
            transcript=transcript,
            session_type=session_type,
        )

    async def _detect_concerns_safe(
        self,
        session_id: UUID,
        transcript: str,
    ) -> dict:
        """Detect concerns with error handling for parallel execution."""
        return await self.extraction_service.detect_concerns(
            session_id=session_id,
            transcript=transcript,
        )

    async def _generate_summary_safe(
        self,
        session: VoiceSession,
        transcript: str,
        signals: list,
    ) -> SessionSummary:
        """Generate summary with error handling for parallel execution."""
        return await self._generate_and_store_summary(
            session=session,
            transcript=transcript,
            signals=signals,
        )

    async def _scoring_and_hypothesis_chain(
        self,
        session_id: UUID,
        patient_id: UUID,
        signals: list,
        score_domains: bool,
        update_hypotheses: bool,
    ) -> Tuple[int, bool]:
        """
        Run domain scoring and hypothesis generation sequentially.

        These must be sequential because hypothesis generation depends on
        domain scores being written to the database first.

        Returns:
            Tuple of (domains_scored_count, hypotheses_updated_bool)
        """
        domains_scored = 0
        hypotheses_updated = False

        # Step 1: Score domains (if enabled and we have signals)
        if score_domains and signals:
            scores = await self.scoring_service.score_domains(
                session_id=session_id,
                patient_id=patient_id,
                signals=signals,
            )
            domains_scored = len(scores)

        # Step 2: Generate hypotheses (depends on domain scores in DB)
        if update_hypotheses:
            await self.hypothesis_engine.generate_hypotheses(
                patient_id=patient_id,
                session_id=session_id,
            )
            hypotheses_updated = True

        return domains_scored, hypotheses_updated

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
