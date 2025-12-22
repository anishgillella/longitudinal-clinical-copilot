"""
Memory Summarizer

Generates and manages compressed summaries of patient history.
Implements hierarchical summarization for efficient context management.
"""

import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.models.memory import MemorySummary, TimelineEvent
from src.models.session import VoiceSession
from src.models.assessment import SessionSummary, ClinicalSignal
from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import (
    MEMORY_SUMMARY_SYSTEM,
    MEMORY_SUMMARY_USER,
    LONGITUDINAL_ANALYSIS_SYSTEM,
    LONGITUDINAL_ANALYSIS_USER,
)

logger = logging.getLogger(__name__)


class MemorySummarizer:
    """Service for generating memory summaries."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def generate_session_summary(
        self,
        session_id: UUID,
        patient_id: UUID,
    ) -> MemorySummary:
        """
        Generate a memory summary for a single session.

        This is the most granular summary type.
        """
        # Get session
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get session summary
        summary_result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        session_summary = summary_result.scalar_one_or_none()

        # Get signals
        signals_result = await self.db.execute(
            select(ClinicalSignal).where(ClinicalSignal.session_id == session_id)
        )
        signals = list(signals_result.scalars().all())

        # Compile session data
        summary_text = self._compile_session_summary(session, session_summary, signals)

        # Create memory summary
        memory_summary = MemorySummary(
            patient_id=patient_id,
            summary_type="session",
            period_start=session.started_at or session.created_at,
            period_end=session.ended_at or datetime.utcnow(),
            summary_text=summary_text,
            key_observations=self._extract_key_observations(signals),
            topics_covered={"topics": session_summary.key_topics.get("topics", []) if session_summary and session_summary.key_topics else []},
            sessions_included=1,
            signals_included=len(signals),
            model_version=self.llm.model,
        )

        self.db.add(memory_summary)
        await self.db.commit()
        await self.db.refresh(memory_summary)

        logger.info(f"Generated session memory summary for session {session_id}")
        return memory_summary

    async def generate_period_summary(
        self,
        patient_id: UUID,
        summary_type: str,  # weekly, monthly, quarterly
        period_start: datetime,
        period_end: datetime,
    ) -> MemorySummary:
        """
        Generate a summary for a time period.

        Compresses multiple session summaries into a period summary.
        """
        # Get all session summaries in the period
        session_summaries = await self._get_session_summaries_in_period(
            patient_id, period_start, period_end
        )

        if not session_summaries:
            # No sessions, create minimal summary
            return await self._create_empty_period_summary(
                patient_id, summary_type, period_start, period_end
            )

        # Get timeline events in the period
        events = await self._get_timeline_events_in_period(
            patient_id, period_start, period_end
        )

        # Use LLM to generate compressed summary
        summary_text = await self._generate_period_summary_with_llm(
            summary_type, session_summaries, events
        )

        # Extract structured data
        key_observations = self._extract_period_observations(session_summaries, events)
        domain_progress = await self._calculate_domain_progress(patient_id, period_start, period_end)
        concerns = self._extract_period_concerns(session_summaries)
        topics = self._extract_period_topics(session_summaries)

        memory_summary = MemorySummary(
            patient_id=patient_id,
            summary_type=summary_type,
            period_start=period_start,
            period_end=period_end,
            summary_text=summary_text,
            key_observations={"observations": key_observations},
            domain_progress=domain_progress,
            concerns_raised={"concerns": concerns},
            topics_covered={"topics": topics},
            sessions_included=len(session_summaries),
            signals_included=sum(s.get("signal_count", 0) for s in session_summaries),
            model_version=self.llm.model,
        )

        self.db.add(memory_summary)
        await self.db.commit()
        await self.db.refresh(memory_summary)

        logger.info(f"Generated {summary_type} memory summary for patient {patient_id}")
        return memory_summary

    async def generate_longitudinal_analysis(
        self,
        patient_id: UUID,
        days: int = 90,
    ) -> dict:
        """
        Generate a longitudinal analysis of patient progress.

        Returns comprehensive analysis of trajectory over time.
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        # Gather all data
        session_summaries = await self._get_session_summaries_in_period(
            patient_id, period_start, period_end
        )
        events = await self._get_timeline_events_in_period(
            patient_id, period_start, period_end
        )

        if len(session_summaries) < 2:
            return {
                "patient_id": str(patient_id),
                "analysis_period_days": days,
                "overall_trajectory": "insufficient_data",
                "confidence": 0.0,
                "domain_trajectories": {},
                "milestones_achieved": [],
                "areas_of_concern": [],
                "recommended_focus_areas": [],
                "sessions_analyzed": len(session_summaries),
                "signals_analyzed": 0,
                "data_completeness": 0.0,
            }

        # Get domain score history
        domain_progress = await self._calculate_domain_progress(patient_id, period_start, period_end)

        # Use LLM for analysis
        analysis = await self._generate_longitudinal_analysis_with_llm(
            session_summaries, events, domain_progress
        )

        return {
            "patient_id": str(patient_id),
            "analysis_period_days": days,
            "overall_trajectory": analysis.get("overall_trajectory", "stable"),
            "confidence": analysis.get("confidence", 0.5),
            "domain_trajectories": domain_progress,
            "milestones_achieved": analysis.get("milestones", []),
            "areas_of_concern": analysis.get("concerns", []),
            "recommended_focus_areas": analysis.get("recommendations", []),
            "sessions_analyzed": len(session_summaries),
            "signals_analyzed": sum(s.get("signal_count", 0) for s in session_summaries),
            "data_completeness": min(len(session_summaries) / 10, 1.0),  # 10 sessions = 100%
        }

    async def get_memory_summaries(
        self,
        patient_id: UUID,
        summary_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemorySummary]:
        """Get memory summaries for a patient."""
        query = select(MemorySummary).where(MemorySummary.patient_id == patient_id)

        if summary_type:
            query = query.where(MemorySummary.summary_type == summary_type)

        query = query.order_by(MemorySummary.period_end.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_compressed_history(
        self,
        patient_id: UUID,
        max_tokens: int = 2000,
    ) -> str:
        """
        Get compressed patient history optimized for token budget.

        Uses hierarchical summaries to stay within token limits.
        """
        sections = []
        remaining_tokens = max_tokens

        # Get overall summary if available
        overall_result = await self.db.execute(
            select(MemorySummary)
            .where(
                MemorySummary.patient_id == patient_id,
                MemorySummary.summary_type == "overall",
            )
            .order_by(MemorySummary.period_end.desc())
            .limit(1)
        )
        overall = overall_result.scalar_one_or_none()

        if overall:
            sections.append(f"OVERALL: {overall.summary_text}")
            remaining_tokens -= len(overall.summary_text) // 4

        # Get recent session summaries
        if remaining_tokens > 500:
            session_result = await self.db.execute(
                select(MemorySummary)
                .where(
                    MemorySummary.patient_id == patient_id,
                    MemorySummary.summary_type == "session",
                )
                .order_by(MemorySummary.period_end.desc())
                .limit(3)
            )
            sessions = session_result.scalars().all()

            for s in sessions:
                if remaining_tokens > 200:
                    sections.append(f"SESSION ({s.period_end.strftime('%Y-%m-%d')}): {s.summary_text}")
                    remaining_tokens -= len(s.summary_text) // 4

        return "\n\n".join(sections)

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _compile_session_summary(
        self,
        session: VoiceSession,
        session_summary: Optional[SessionSummary],
        signals: list[ClinicalSignal],
    ) -> str:
        """Compile a session into a summary text."""
        parts = []

        # Basic info
        date_str = session.ended_at.strftime("%Y-%m-%d") if session.ended_at else "Unknown"
        duration = f"{(session.duration_seconds or 0) // 60} minutes"
        parts.append(f"{session.session_type.title()} session on {date_str} ({duration})")

        # Summary
        if session_summary:
            parts.append(session_summary.brief_summary)
        elif session.summary:
            parts.append(session.summary)

        # Key signals
        high_signals = [s for s in signals if s.clinical_significance == "high"]
        if high_signals:
            signal_texts = [f"- {s.signal_name}" for s in high_signals[:3]]
            parts.append("Key observations:\n" + "\n".join(signal_texts))

        return " ".join(parts)

    def _extract_key_observations(self, signals: list[ClinicalSignal]) -> dict:
        """Extract key observations from signals."""
        observations = []
        for s in sorted(signals, key=lambda x: x.intensity, reverse=True)[:5]:
            observations.append({
                "signal": s.signal_name,
                "domain": s.maps_to_domain,
                "significance": s.clinical_significance,
            })
        return {"observations": observations}

    async def _get_session_summaries_in_period(
        self,
        patient_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict]:
        """Get session summary data for a period."""
        result = await self.db.execute(
            select(VoiceSession, SessionSummary)
            .outerjoin(SessionSummary, VoiceSession.id == SessionSummary.session_id)
            .where(
                VoiceSession.patient_id == patient_id,
                VoiceSession.status == "completed",
                VoiceSession.ended_at >= period_start,
                VoiceSession.ended_at <= period_end,
            )
            .order_by(VoiceSession.ended_at)
        )
        rows = result.all()

        summaries = []
        for session, summary in rows:
            # Count signals
            signal_result = await self.db.execute(
                select(ClinicalSignal).where(ClinicalSignal.session_id == session.id)
            )
            signals = list(signal_result.scalars().all())

            summaries.append({
                "date": session.ended_at.isoformat(),
                "type": session.session_type,
                "summary": summary.brief_summary if summary else session.summary or "No summary",
                "topics": summary.key_topics.get("topics", []) if summary and summary.key_topics else [],
                "concerns": summary.concerns if summary else [],
                "signal_count": len(signals),
            })

        return summaries

    async def _get_timeline_events_in_period(
        self,
        patient_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> list[dict]:
        """Get timeline events for a period."""
        result = await self.db.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.patient_id == patient_id,
                TimelineEvent.occurred_at >= period_start,
                TimelineEvent.occurred_at <= period_end,
            )
            .order_by(TimelineEvent.occurred_at)
        )
        events = result.scalars().all()

        return [
            {
                "date": e.occurred_at.isoformat(),
                "type": e.event_type,
                "title": e.title,
                "description": e.description,
                "significance": e.significance,
            }
            for e in events
        ]

    async def _generate_period_summary_with_llm(
        self,
        summary_type: str,
        session_summaries: list[dict],
        events: list[dict],
    ) -> str:
        """Use LLM to generate period summary."""
        sessions_text = "\n".join([
            f"- {s['date'][:10]} ({s['type']}): {s['summary'][:150]}"
            for s in session_summaries
        ])

        events_text = "\n".join([
            f"- {e['date'][:10]} [{e['type']}]: {e['title']}"
            for e in events[:10]
        ])

        user_prompt = MEMORY_SUMMARY_USER.format(
            summary_type=summary_type,
            sessions_text=sessions_text,
            events_text=events_text or "No notable events",
            session_count=len(session_summaries),
        )

        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": MEMORY_SUMMARY_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return result.get("summary", "Summary generation failed")
        except Exception as e:
            logger.error(f"LLM summary generation failed: {e}")
            return f"Summary of {len(session_summaries)} sessions from this {summary_type} period."

    async def _generate_longitudinal_analysis_with_llm(
        self,
        session_summaries: list[dict],
        events: list[dict],
        domain_progress: dict,
    ) -> dict:
        """Use LLM to generate longitudinal analysis."""
        sessions_text = "\n".join([
            f"- {s['date'][:10]}: {s['summary'][:100]}"
            for s in session_summaries
        ])

        user_prompt = LONGITUDINAL_ANALYSIS_USER.format(
            sessions_text=sessions_text,
            domain_progress=str(domain_progress),
            event_count=len(events),
        )

        try:
            return await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": LONGITUDINAL_ANALYSIS_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "overall_trajectory": "unknown",
                "confidence": 0.0,
                "milestones": [],
                "concerns": [],
                "recommendations": [],
            }

    async def _calculate_domain_progress(
        self,
        patient_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """Calculate domain score progress over period."""
        from src.models.assessment import AssessmentDomainScore

        result = await self.db.execute(
            select(AssessmentDomainScore)
            .where(
                AssessmentDomainScore.patient_id == patient_id,
                AssessmentDomainScore.assessed_at >= period_start,
                AssessmentDomainScore.assessed_at <= period_end,
            )
            .order_by(AssessmentDomainScore.domain_code, AssessmentDomainScore.assessed_at)
        )
        scores = result.scalars().all()

        # Group by domain
        by_domain: dict = {}
        for score in scores:
            if score.domain_code not in by_domain:
                by_domain[score.domain_code] = []
            by_domain[score.domain_code].append(score)

        # Calculate progress
        progress = {}
        for domain, domain_scores in by_domain.items():
            if len(domain_scores) >= 2:
                first = domain_scores[0].normalized_score
                last = domain_scores[-1].normalized_score
                change = last - first

                if abs(change) < 0.05:
                    trajectory = "stable"
                elif change > 0:
                    trajectory = "improving"
                else:
                    trajectory = "declining"

                progress[domain] = {
                    "trajectory": trajectory,
                    "change": change,
                    "sessions": len(domain_scores),
                    "latest_score": last,
                }

        return progress

    async def _create_empty_period_summary(
        self,
        patient_id: UUID,
        summary_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> MemorySummary:
        """Create an empty summary for a period with no sessions."""
        memory_summary = MemorySummary(
            patient_id=patient_id,
            summary_type=summary_type,
            period_start=period_start,
            period_end=period_end,
            summary_text=f"No sessions completed during this {summary_type} period.",
            sessions_included=0,
            signals_included=0,
        )

        self.db.add(memory_summary)
        await self.db.commit()
        await self.db.refresh(memory_summary)
        return memory_summary

    def _extract_period_observations(
        self,
        session_summaries: list[dict],
        events: list[dict],
    ) -> list[str]:
        """Extract key observations from a period."""
        observations = []

        # From high-significance events
        for event in events:
            if event.get("significance") in ["high", "critical"]:
                observations.append(event["title"])

        return observations[:10]

    def _extract_period_concerns(self, session_summaries: list[dict]) -> list[str]:
        """Extract concerns from session summaries."""
        concerns = []
        for s in session_summaries:
            session_concerns = s.get("concerns", [])
            if isinstance(session_concerns, list):
                for c in session_concerns:
                    if isinstance(c, str):
                        concerns.append(c)
                    elif isinstance(c, dict):
                        concerns.append(c.get("description", str(c)))
        return list(set(concerns))[:5]

    def _extract_period_topics(self, session_summaries: list[dict]) -> list[str]:
        """Extract unique topics from session summaries."""
        topics = []
        for s in session_summaries:
            topics.extend(s.get("topics", []))
        return list(set(topics))[:10]
