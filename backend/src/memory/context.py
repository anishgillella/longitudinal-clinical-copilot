"""
Context Retrieval Service

Compiles patient context for session injection.
Manages what information the voice agent receives about a patient.
"""

import logging
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.assessment import (
    DiagnosticHypothesis,
    SessionSummary,
    ClinicalSignal,
)
from src.models.memory import (
    TimelineEvent,
    MemorySummary,
    ContextSnapshot,
    ConversationThread,
)
from src.assessment.scoring import DomainScoringService
from src.assessment.hypothesis import HypothesisEngine
from src.schemas.memory import PatientContext

logger = logging.getLogger(__name__)


class ContextService:
    """Service for compiling and managing patient context."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scoring_service = DomainScoringService(db)
        self.hypothesis_engine = HypothesisEngine(db)

    async def get_patient_context(
        self,
        patient_id: UUID,
        session_type: str = "checkin",
        max_tokens: int = 2000,
        include_hypotheses: bool = True,
        include_domain_scores: bool = True,
        include_recent_events: bool = True,
        recent_events_days: int = 30,
    ) -> PatientContext:
        """
        Compile comprehensive patient context for session injection.

        Args:
            patient_id: The patient ID
            session_type: Type of upcoming session (intake, checkin, assessment)
            max_tokens: Approximate token limit for context
            include_hypotheses: Whether to include diagnostic hypotheses
            include_domain_scores: Whether to include domain scores
            include_recent_events: Whether to include timeline events
            recent_events_days: How many days of recent events to include

        Returns:
            PatientContext with compiled information
        """
        # Gather all context components
        patient_info = await self._get_patient_info(patient_id)
        session_history = await self._get_session_history(patient_id)
        assessment_data = await self._get_assessment_data(
            patient_id, include_hypotheses, include_domain_scores
        )
        recent_timeline = await self._get_recent_timeline(
            patient_id, recent_events_days
        ) if include_recent_events else []
        active_threads = await self._get_active_threads(patient_id)
        exploration_priorities = await self._get_exploration_priorities(patient_id)

        # Compile context text
        context_text = self._compile_context_text(
            patient_info=patient_info,
            session_history=session_history,
            assessment_data=assessment_data,
            recent_timeline=recent_timeline,
            active_threads=active_threads,
            exploration_priorities=exploration_priorities,
            session_type=session_type,
            max_tokens=max_tokens,
        )

        # Estimate token count (rough approximation: 4 chars = 1 token)
        token_count = len(context_text) // 4

        return PatientContext(
            patient_id=patient_id,
            context_text=context_text,
            token_count=token_count,
            patient_info=patient_info,
            session_history=session_history,
            current_assessment=assessment_data,
            recent_timeline=recent_timeline,
            active_threads=active_threads,
            exploration_priorities=exploration_priorities,
            generated_at=datetime.utcnow(),
        )

    async def create_snapshot(
        self,
        patient_id: UUID,
        session_id: Optional[UUID] = None,
        snapshot_type: str = "pre_session",
    ) -> ContextSnapshot:
        """
        Create and store a context snapshot.

        Snapshots preserve the context state at a point in time.
        """
        context = await self.get_patient_context(patient_id)

        snapshot = ContextSnapshot(
            patient_id=patient_id,
            session_id=session_id,
            snapshot_type=snapshot_type,
            context_text=context.context_text,
            patient_summary=context.patient_info,
            recent_observations={"observations": context.recent_timeline},
            current_hypotheses={"hypotheses": context.current_assessment.get("hypotheses", [])},
            domain_status=context.current_assessment.get("domain_scores", {}),
            exploration_priorities={"priorities": context.exploration_priorities},
            token_count=context.token_count,
            model_version="1.0",
        )

        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(f"Created context snapshot for patient {patient_id}")
        return snapshot

    async def get_latest_snapshot(
        self,
        patient_id: UUID,
    ) -> Optional[ContextSnapshot]:
        """Get the most recent context snapshot for a patient."""
        result = await self.db.execute(
            select(ContextSnapshot)
            .where(ContextSnapshot.patient_id == patient_id)
            .order_by(ContextSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_session_context_injection(
        self,
        patient_id: UUID,
        session_id: UUID,
        session_type: str = "checkin",
    ) -> dict:
        """
        Get context specifically formatted for VAPI session injection.

        Returns system prompt additions and conversation guidelines.
        """
        context = await self.get_patient_context(
            patient_id=patient_id,
            session_type=session_type,
        )

        # Build system context
        system_context = self._build_system_context(context, session_type)

        # Build opening context
        opening_context = self._build_opening_context(context, session_type)

        # Get follow-up items
        follow_up_items = await self._get_follow_up_items(patient_id)

        # Get sensitive topics to avoid
        sensitive_topics = await self._get_sensitive_topics(patient_id)

        return {
            "session_id": str(session_id),
            "patient_id": str(patient_id),
            "system_context": system_context,
            "opening_context": opening_context,
            "exploration_topics": context.exploration_priorities,
            "sensitive_topics": sensitive_topics,
            "follow_up_items": follow_up_items,
        }

    async def get_vapi_template_variables(
        self,
        patient_id: UUID,
        session_id: UUID,
        interview_mode: str = "parent",
    ) -> dict:
        """
        Get structured variables for VAPI prompt template injection.

        These variables populate the VAPI prompt template's {{variable}} placeholders.

        Args:
            patient_id: The patient ID
            session_id: The session ID
            interview_mode: Who is being interviewed (parent, teen, adult)

        Returns:
            Dictionary of template variables for VAPI prompt injection
        """
        # Get patient info
        patient_info = await self._get_patient_info(patient_id)
        session_history = await self._get_session_history(patient_id)

        # Get clinical gaps (domains needing more evidence)
        missing_information = await self._get_dsm5_gaps(patient_id)

        # Get focus areas for this session
        focus_areas = await self._get_exploration_priorities(patient_id)

        # Get previous session summary
        previous_session_summary = ""
        if session_history.get("recent_sessions"):
            recent = session_history["recent_sessions"][0]
            previous_session_summary = recent.get("summary", "")

        # Determine interviewee booleans
        interviewee_is_parent = interview_mode == "parent"
        interviewee_is_teen = interview_mode == "teen"
        interviewee_is_adult = interview_mode == "adult"

        return {
            # Core identifiers
            "session_id": str(session_id),
            "patient_id": str(patient_id),

            # Interviewee type variables
            "interviewee_type": interview_mode,
            "interviewee_is_parent": interviewee_is_parent,
            "interviewee_is_teen": interviewee_is_teen,
            "interviewee_is_adult": interviewee_is_adult,

            # Patient information
            "patient_name": patient_info.get("first_name", "the patient"),
            "patient_full_name": patient_info.get("name", ""),
            "patient_age": patient_info.get("age", 0),
            "patient_gender": patient_info.get("gender", ""),
            "primary_concern": patient_info.get("primary_concern", ""),

            # Session context
            "total_sessions": session_history.get("completed_sessions", 0),
            "is_first_session": session_history.get("completed_sessions", 0) == 0,
            "previous_session_summary": previous_session_summary,

            # Clinical focus
            "focus_areas": focus_areas,
            "focus_areas_text": ", ".join(focus_areas) if focus_areas else "general assessment",
            "missing_information": missing_information,
            "missing_domains_text": ", ".join(missing_information) if missing_information else "none identified",

            # Behavioral adaptations
            "use_concrete_language": interviewee_is_teen,
            "use_parent_perspective": interviewee_is_parent,
        }

    async def _get_dsm5_gaps(self, patient_id: UUID) -> list[str]:
        """
        Identify DSM-5 domains with insufficient evidence.

        Returns list of domain names that need more exploration.
        """
        # Get domain scores
        scores = await self.scoring_service.get_latest_scores_for_patient(patient_id)

        # Identify domains with low confidence or insufficient signals
        gaps = []
        for code, score in scores.items():
            # Consider it a gap if confidence is below threshold
            if score.confidence < 0.5:
                gaps.append(score.domain_name)

        # Also get domains that haven't been scored yet
        exploration_priorities = await self.scoring_service.get_domains_needing_exploration(patient_id)
        for domain in exploration_priorities:
            if domain not in gaps:
                gaps.append(domain)

        return gaps[:5]  # Return top 5 gaps

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    async def _get_patient_info(self, patient_id: UUID) -> dict:
        """Get basic patient information."""
        patient = await self.db.get(Patient, patient_id)
        if not patient:
            return {}

        # Calculate age
        today = datetime.utcnow().date()
        age = today.year - patient.date_of_birth.year
        if today.month < patient.date_of_birth.month or (
            today.month == patient.date_of_birth.month and today.day < patient.date_of_birth.day
        ):
            age -= 1

        return {
            "name": f"{patient.first_name} {patient.last_name}",
            "first_name": patient.first_name,
            "age": age,
            "gender": patient.gender,
            "primary_concern": patient.primary_concern,
            "intake_date": patient.intake_date.isoformat() if patient.intake_date else None,
            "status": patient.status,
        }

    async def _get_session_history(self, patient_id: UUID) -> dict:
        """Get summary of session history."""
        # Count sessions
        count_result = await self.db.execute(
            select(
                func.count(VoiceSession.id).label("total"),
                func.count(VoiceSession.id).filter(VoiceSession.status == "completed").label("completed"),
            )
            .where(VoiceSession.patient_id == patient_id)
        )
        counts = count_result.one()

        # Get recent sessions
        recent_result = await self.db.execute(
            select(VoiceSession)
            .where(
                VoiceSession.patient_id == patient_id,
                VoiceSession.status == "completed",
            )
            .order_by(VoiceSession.ended_at.desc())
            .limit(5)
        )
        recent_sessions = recent_result.scalars().all()

        # Get summaries for recent sessions
        session_summaries = []
        for session in recent_sessions:
            summary_result = await self.db.execute(
                select(SessionSummary).where(SessionSummary.session_id == session.id)
            )
            summary = summary_result.scalar_one_or_none()

            session_summaries.append({
                "date": session.ended_at.isoformat() if session.ended_at else None,
                "type": session.session_type,
                "duration_minutes": (session.duration_seconds or 0) // 60,
                "summary": summary.brief_summary if summary else session.summary,
            })

        return {
            "total_sessions": counts.total,
            "completed_sessions": counts.completed,
            "recent_sessions": session_summaries,
        }

    async def _get_assessment_data(
        self,
        patient_id: UUID,
        include_hypotheses: bool,
        include_domain_scores: bool,
    ) -> dict:
        """Get current assessment data."""
        data = {}

        if include_hypotheses:
            hypotheses = await self.hypothesis_engine.get_hypotheses_for_patient(patient_id)
            data["hypotheses"] = [
                {
                    "condition": h.condition_name,
                    "code": h.condition_code,
                    "strength": h.evidence_strength,
                    "uncertainty": h.uncertainty,
                    "trend": h.trend,
                }
                for h in hypotheses[:5]  # Limit to top 5
            ]

        if include_domain_scores:
            scores = await self.scoring_service.get_latest_scores_for_patient(patient_id)
            data["domain_scores"] = {
                code: {
                    "name": score.domain_name,
                    "score": score.normalized_score,
                    "confidence": score.confidence,
                }
                for code, score in scores.items()
            }

        return data

    async def _get_recent_timeline(
        self,
        patient_id: UUID,
        days: int,
    ) -> list[dict]:
        """Get recent timeline events."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.patient_id == patient_id,
                TimelineEvent.occurred_at >= cutoff,
            )
            .order_by(TimelineEvent.occurred_at.desc())
            .limit(10)
        )
        events = result.scalars().all()

        return [
            {
                "date": e.occurred_at.isoformat(),
                "type": e.event_type,
                "category": e.category,
                "title": e.title,
                "description": e.description[:200] if len(e.description) > 200 else e.description,
                "significance": e.significance,
            }
            for e in events
        ]

    async def _get_active_threads(self, patient_id: UUID) -> list[dict]:
        """Get active conversation threads."""
        result = await self.db.execute(
            select(ConversationThread)
            .where(
                ConversationThread.patient_id == patient_id,
                ConversationThread.status == "active",
            )
            .order_by(ConversationThread.last_discussed_at.desc())
            .limit(5)
        )
        threads = result.scalars().all()

        return [
            {
                "topic": t.thread_topic,
                "category": t.category,
                "summary": t.summary,
                "last_discussed": t.last_discussed_at.isoformat(),
                "mention_count": t.mention_count,
                "follow_up_needed": t.follow_up_needed,
            }
            for t in threads
        ]

    async def _get_exploration_priorities(self, patient_id: UUID) -> list[str]:
        """Get domains/topics that need more exploration."""
        priorities = await self.scoring_service.get_domains_needing_exploration(patient_id)
        return priorities[:5]  # Top 5 priorities

    async def _get_follow_up_items(self, patient_id: UUID) -> list[dict]:
        """Get items that need follow-up from previous sessions."""
        result = await self.db.execute(
            select(ConversationThread)
            .where(
                ConversationThread.patient_id == patient_id,
                ConversationThread.follow_up_needed == True,
                ConversationThread.status == "active",
            )
            .limit(5)
        )
        threads = result.scalars().all()

        return [
            {
                "topic": t.thread_topic,
                "notes": t.follow_up_notes,
                "last_discussed": t.last_discussed_at.isoformat(),
            }
            for t in threads
        ]

    async def _get_sensitive_topics(self, patient_id: UUID) -> list[str]:
        """Get topics that should be handled with care."""
        # Look for high-significance concerns
        result = await self.db.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.patient_id == patient_id,
                TimelineEvent.event_type == "concern",
                TimelineEvent.significance.in_(["high", "critical"]),
            )
            .order_by(TimelineEvent.occurred_at.desc())
            .limit(5)
        )
        concerns = result.scalars().all()

        return [c.title for c in concerns]

    def _compile_context_text(
        self,
        patient_info: dict,
        session_history: dict,
        assessment_data: dict,
        recent_timeline: list[dict],
        active_threads: list[dict],
        exploration_priorities: list[str],
        session_type: str,
        max_tokens: int,
    ) -> str:
        """Compile all context into a formatted text string."""
        sections = []

        # Patient info
        if patient_info:
            sections.append(
                f"PATIENT: {patient_info.get('name', 'Unknown')}, "
                f"{patient_info.get('age', 'Unknown')} years old\n"
                f"Primary concern: {patient_info.get('primary_concern', 'Not specified')}"
            )

        # Session history
        if session_history:
            sections.append(
                f"SESSION HISTORY: {session_history.get('completed_sessions', 0)} completed sessions"
            )
            if session_history.get('recent_sessions'):
                recent = session_history['recent_sessions'][0]
                sections.append(
                    f"Last session ({recent.get('type', 'unknown')}, {recent.get('date', 'unknown')[:10]}): "
                    f"{recent.get('summary', 'No summary')[:150]}..."
                )

        # Current assessment
        if assessment_data.get('hypotheses'):
            top_hyp = assessment_data['hypotheses'][0]
            sections.append(
                f"CURRENT HYPOTHESIS: {top_hyp['condition']} "
                f"(strength: {top_hyp['strength']:.0%}, trend: {top_hyp.get('trend', 'stable')})"
            )

        # Exploration priorities
        if exploration_priorities:
            sections.append(
                f"AREAS TO EXPLORE: {', '.join(exploration_priorities[:3])}"
            )

        # Active threads
        if active_threads:
            thread_topics = [t['topic'] for t in active_threads[:3]]
            sections.append(
                f"ONGOING TOPICS: {', '.join(thread_topics)}"
            )

        # Recent events
        if recent_timeline:
            high_significance = [e for e in recent_timeline if e['significance'] in ['high', 'critical']]
            if high_significance:
                event = high_significance[0]
                sections.append(
                    f"RECENT NOTE: {event['title']} ({event['date'][:10]})"
                )

        return "\n\n".join(sections)

    def _build_system_context(self, context: PatientContext, session_type: str) -> str:
        """Build system prompt context for VAPI."""
        parts = [
            f"This is a {session_type} session with {context.patient_info.get('first_name', 'the patient')}.",
            context.context_text,
        ]

        if context.exploration_priorities:
            parts.append(
                f"During this session, try to explore: {', '.join(context.exploration_priorities[:3])}"
            )

        return "\n\n".join(parts)

    def _build_opening_context(self, context: PatientContext, session_type: str) -> str:
        """Build opening message context."""
        first_name = context.patient_info.get('first_name', '')

        if session_type == "intake":
            return f"This is the first session with {first_name}. Focus on building rapport and understanding their primary concerns."

        if context.active_threads:
            thread = context.active_threads[0]
            return f"Last time, you discussed {thread['topic']}. Consider following up on this topic."

        return f"Continue building on previous conversations with {first_name}."
