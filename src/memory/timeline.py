"""
Timeline Service

Manages patient timeline events - discrete observations and events over time.
"""

import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.memory import TimelineEvent, ConversationThread
from src.models.assessment import ClinicalSignal, SessionSummary
from src.models.session import VoiceSession

logger = logging.getLogger(__name__)


class TimelineService:
    """Service for managing patient timeline events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_event(
        self,
        patient_id: UUID,
        event_type: str,
        category: str,
        title: str,
        description: str,
        occurred_at: datetime,
        session_id: Optional[UUID] = None,
        significance: str = "moderate",
        duration_context: Optional[str] = None,
        impact_domains: Optional[list[str]] = None,
        source: str = "session_extraction",
        confidence: float = 0.8,
        evidence_quotes: Optional[list[str]] = None,
        related_signal_ids: Optional[list[str]] = None,
    ) -> TimelineEvent:
        """Add a new event to the patient's timeline."""
        event = TimelineEvent(
            patient_id=patient_id,
            session_id=session_id,
            event_type=event_type,
            category=category,
            title=title,
            description=description,
            occurred_at=occurred_at,
            duration_context=duration_context,
            significance=significance,
            impact_domains={"domains": impact_domains} if impact_domains else None,
            source=source,
            confidence=confidence,
            evidence_quotes={"quotes": evidence_quotes} if evidence_quotes else None,
            related_signal_ids={"signal_ids": related_signal_ids} if related_signal_ids else None,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        logger.info(f"Added timeline event '{title}' for patient {patient_id}")
        return event

    async def get_timeline(
        self,
        patient_id: UUID,
        days: Optional[int] = None,
        event_type: Optional[str] = None,
        category: Optional[str] = None,
        significance: Optional[str] = None,
        limit: int = 100,
    ) -> list[TimelineEvent]:
        """Get timeline events for a patient with optional filters."""
        query = select(TimelineEvent).where(TimelineEvent.patient_id == patient_id)

        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(TimelineEvent.occurred_at >= cutoff)

        if event_type:
            query = query.where(TimelineEvent.event_type == event_type)

        if category:
            query = query.where(TimelineEvent.category == category)

        if significance:
            query = query.where(TimelineEvent.significance == significance)

        query = query.order_by(TimelineEvent.occurred_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_timeline_summary(self, patient_id: UUID) -> dict:
        """Get summary statistics of the patient's timeline."""
        # Count by category
        category_result = await self.db.execute(
            select(
                TimelineEvent.category,
                func.count(TimelineEvent.id).label("count")
            )
            .where(TimelineEvent.patient_id == patient_id)
            .group_by(TimelineEvent.category)
        )
        by_category = {row.category: row.count for row in category_result}

        # Count by significance
        significance_result = await self.db.execute(
            select(
                TimelineEvent.significance,
                func.count(TimelineEvent.id).label("count")
            )
            .where(TimelineEvent.patient_id == patient_id)
            .group_by(TimelineEvent.significance)
        )
        by_significance = {row.significance: row.count for row in significance_result}

        # Total and date range
        stats_result = await self.db.execute(
            select(
                func.count(TimelineEvent.id).label("total"),
                func.min(TimelineEvent.occurred_at).label("earliest"),
                func.max(TimelineEvent.occurred_at).label("latest"),
            )
            .where(TimelineEvent.patient_id == patient_id)
        )
        stats = stats_result.one()

        return {
            "total_events": stats.total,
            "date_range": {
                "start": stats.earliest.isoformat() if stats.earliest else None,
                "end": stats.latest.isoformat() if stats.latest else None,
            },
            "by_category": by_category,
            "by_significance": by_significance,
        }

    async def extract_events_from_session(
        self,
        session_id: UUID,
        patient_id: UUID,
    ) -> list[TimelineEvent]:
        """
        Extract timeline events from a completed session.

        Uses session signals and summary to identify discrete events.
        """
        # Get session summary
        summary_result = await self.db.execute(
            select(SessionSummary).where(SessionSummary.session_id == session_id)
        )
        summary = summary_result.scalar_one_or_none()

        # Get session signals
        signals_result = await self.db.execute(
            select(ClinicalSignal)
            .where(ClinicalSignal.session_id == session_id)
            .order_by(ClinicalSignal.intensity.desc())
        )
        signals = list(signals_result.scalars().all())

        # Get session for timing info
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            return []

        session_time = session.ended_at or session.started_at or datetime.utcnow()
        events = []

        # Create events from high-significance signals
        high_signals = [s for s in signals if s.clinical_significance == "high"]
        for signal in high_signals[:5]:  # Limit to top 5
            event = await self.add_event(
                patient_id=patient_id,
                session_id=session_id,
                event_type="observation",
                category=self._signal_type_to_category(signal.signal_type),
                title=signal.signal_name,
                description=signal.evidence,
                occurred_at=session_time,
                significance="high",
                impact_domains=[signal.maps_to_domain] if signal.maps_to_domain else None,
                source="session_extraction",
                confidence=signal.confidence,
                related_signal_ids=[str(signal.id)],
            )
            events.append(event)

        # Create event from concerns if any
        if summary and summary.concerns:
            concerns = summary.concerns if isinstance(summary.concerns, list) else summary.concerns.get("concerns", [])
            for concern in concerns:
                concern_text = concern if isinstance(concern, str) else concern.get("description", str(concern))
                event = await self.add_event(
                    patient_id=patient_id,
                    session_id=session_id,
                    event_type="concern",
                    category="emotional",
                    title="Clinical Concern Flagged",
                    description=concern_text,
                    occurred_at=session_time,
                    significance="high",
                    source="session_extraction",
                    confidence=0.9,
                )
                events.append(event)

        logger.info(f"Extracted {len(events)} timeline events from session {session_id}")
        return events

    def _signal_type_to_category(self, signal_type: str) -> str:
        """Map signal type to timeline category."""
        mapping = {
            "linguistic": "communication",
            "behavioral": "behavioral",
            "emotional": "emotional",
            "social": "social",
            "cognitive": "cognitive",
            "sensory": "sensory",
        }
        return mapping.get(signal_type, "behavioral")

    # ==========================================================================
    # Conversation Thread Management
    # ==========================================================================

    async def create_thread(
        self,
        patient_id: UUID,
        thread_topic: str,
        category: str,
        summary: str,
        first_mentioned_at: datetime,
        clinical_relevance: str = "moderate",
    ) -> ConversationThread:
        """Create a new conversation thread."""
        thread = ConversationThread(
            patient_id=patient_id,
            thread_topic=thread_topic,
            category=category,
            summary=summary,
            first_mentioned_at=first_mentioned_at,
            last_discussed_at=first_mentioned_at,
            clinical_relevance=clinical_relevance,
        )
        self.db.add(thread)
        await self.db.commit()
        await self.db.refresh(thread)

        logger.info(f"Created conversation thread '{thread_topic}' for patient {patient_id}")
        return thread

    async def update_thread(
        self,
        thread_id: UUID,
        session_id: UUID,
        session_summary: str,
    ) -> Optional[ConversationThread]:
        """Update a thread with new session mention."""
        thread = await self.db.get(ConversationThread, thread_id)
        if not thread:
            return None

        # Update mention tracking
        mentions = thread.session_mentions or {"sessions": []}
        mentions["sessions"].append({
            "id": str(session_id),
            "date": datetime.utcnow().isoformat(),
            "summary": session_summary,
        })

        thread.session_mentions = mentions
        thread.last_discussed_at = datetime.utcnow()
        thread.mention_count += 1

        await self.db.commit()
        await self.db.refresh(thread)
        return thread

    async def get_active_threads(
        self,
        patient_id: UUID,
        limit: int = 10,
    ) -> list[ConversationThread]:
        """Get active conversation threads for a patient."""
        result = await self.db.execute(
            select(ConversationThread)
            .where(
                ConversationThread.patient_id == patient_id,
                ConversationThread.status == "active",
            )
            .order_by(ConversationThread.last_discussed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_threads_needing_followup(
        self,
        patient_id: UUID,
    ) -> list[ConversationThread]:
        """Get threads that need follow-up."""
        result = await self.db.execute(
            select(ConversationThread)
            .where(
                ConversationThread.patient_id == patient_id,
                ConversationThread.follow_up_needed == True,
                ConversationThread.status == "active",
            )
            .order_by(ConversationThread.clinical_relevance.desc())
        )
        return list(result.scalars().all())

    async def resolve_thread(
        self,
        thread_id: UUID,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ConversationThread]:
        """Mark a thread as resolved."""
        thread = await self.db.get(ConversationThread, thread_id)
        if not thread:
            return None

        thread.status = "resolved"
        if resolution_notes:
            thread.follow_up_notes = resolution_notes

        await self.db.commit()
        await self.db.refresh(thread)
        return thread
