from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.models.session import VoiceSession, Transcript, AudioRecording
from src.models.patient import Patient
from src.schemas.session import SessionCreate, SessionUpdate


class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Session CRUD operations
    async def create_session(
        self,
        data: SessionCreate,
        clinician_id: UUID,
    ) -> VoiceSession:
        """Create a new voice session."""
        session = VoiceSession(
            patient_id=data.patient_id,
            clinician_id=clinician_id,
            vapi_assistant_id=data.vapi_assistant_id,
            session_type=data.session_type.value,
            status="pending",
            scheduled_at=data.scheduled_at,
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID) -> Optional[VoiceSession]:
        """Get a session by ID."""
        return await self.db.get(VoiceSession, session_id)

    async def get_session_by_vapi_id(self, vapi_call_id: str) -> Optional[VoiceSession]:
        """Get a session by VAPI call ID."""
        result = await self.db.execute(
            select(VoiceSession).where(VoiceSession.vapi_call_id == vapi_call_id)
        )
        return result.scalar_one_or_none()

    async def get_sessions_for_patient(
        self,
        patient_id: UUID,
        session_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[VoiceSession]:
        """Get all sessions for a patient."""
        query = select(VoiceSession).where(VoiceSession.patient_id == patient_id)

        if session_type:
            query = query.where(VoiceSession.session_type == session_type)
        if status:
            query = query.where(VoiceSession.status == status)

        query = query.order_by(VoiceSession.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_session(
        self,
        session_id: UUID,
        data: SessionUpdate,
    ) -> Optional[VoiceSession]:
        """Update a session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "key_topics" and value:
                value = {"topics": value}  # Store as dict
            setattr(session, field, value)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def link_vapi_call(
        self,
        session_id: UUID,
        vapi_call_id: str,
    ) -> Optional[VoiceSession]:
        """Link a VAPI call ID to a session."""
        session = await self.get_session(session_id)
        if not session:
            return None

        session.vapi_call_id = vapi_call_id
        session.status = "active"
        await self.db.commit()
        await self.db.refresh(session)
        return session

    # Session lifecycle methods (called from webhooks)
    async def mark_session_started(
        self,
        vapi_call_id: str,
        started_at: datetime,
    ) -> Optional[VoiceSession]:
        """Mark a session as started."""
        session = await self.get_session_by_vapi_id(vapi_call_id)
        if not session:
            return None

        session.status = "active"
        session.started_at = started_at
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def mark_session_ended(
        self,
        vapi_call_id: str,
        ended_at: datetime,
        completion_reason: str,
    ) -> Optional[VoiceSession]:
        """Mark a session as ended."""
        session = await self.get_session_by_vapi_id(vapi_call_id)
        if not session:
            return None

        session.status = "completed"
        session.ended_at = ended_at
        session.completion_reason = completion_reason

        # Calculate duration if we have start time
        if session.started_at:
            duration = (ended_at - session.started_at).total_seconds()
            session.duration_seconds = int(duration)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def update_session_from_report(
        self,
        vapi_call_id: str,
        duration_seconds: Optional[int] = None,
        summary: Optional[str] = None,
        recording_url: Optional[str] = None,
    ) -> Optional[VoiceSession]:
        """Update session with end-of-call report data."""
        session = await self.get_session_by_vapi_id(vapi_call_id)
        if not session:
            return None

        if duration_seconds:
            session.duration_seconds = duration_seconds
        if summary:
            session.summary = summary

        # Store recording URL if provided
        if recording_url:
            # Check if audio recording exists
            existing = await self.db.execute(
                select(AudioRecording).where(AudioRecording.session_id == session.id)
            )
            audio = existing.scalar_one_or_none()

            if audio:
                audio.file_path = recording_url
            else:
                audio = AudioRecording(
                    session_id=session.id,
                    storage_type="vapi",
                    file_path=recording_url,
                    duration_seconds=duration_seconds,
                )
                self.db.add(audio)

        await self.db.commit()
        await self.db.refresh(session)
        return session

    # Transcript methods
    async def add_transcript(
        self,
        vapi_call_id: str,
        role: str,
        content: str,
        timestamp_ms: Optional[int] = None,
    ) -> Optional[Transcript]:
        """Add a transcript entry to a session."""
        session = await self.get_session_by_vapi_id(vapi_call_id)
        if not session:
            return None

        transcript = Transcript(
            session_id=session.id,
            role=role,
            content=content,
            timestamp_ms=timestamp_ms,
        )
        self.db.add(transcript)
        await self.db.commit()
        await self.db.refresh(transcript)
        return transcript

    async def get_transcripts(self, session_id: UUID) -> list[Transcript]:
        """Get all transcripts for a session."""
        result = await self.db.execute(
            select(Transcript)
            .where(Transcript.session_id == session_id)
            .order_by(Transcript.timestamp_ms.asc().nullslast(), Transcript.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_full_transcript_text(self, session_id: UUID) -> str:
        """Get the full transcript as formatted text."""
        transcripts = await self.get_transcripts(session_id)
        lines = []
        for t in transcripts:
            role_label = "Assistant" if t.role == "assistant" else "Patient"
            lines.append(f"{role_label}: {t.content}")
        return "\n\n".join(lines)

    # Patient context for assistant
    async def get_patient_context_for_session(self, session_id: UUID) -> dict:
        """Get patient context for use by the voice assistant."""
        session = await self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        # Get patient with history
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.history))
            .where(Patient.id == session.patient_id)
        )
        patient = result.scalar_one_or_none()

        if not patient:
            return {"error": "Patient not found"}

        # Get previous sessions
        prev_sessions = await self.get_sessions_for_patient(
            patient_id=patient.id,
            status="completed",
        )

        # Build context
        context = {
            "patient_name": f"{patient.first_name} {patient.last_name}",
            "primary_concern": patient.primary_concern or "Not specified",
            "previous_sessions": len(prev_sessions),
            "history": [
                {
                    "type": h.history_type,
                    "title": h.title,
                    "description": h.description,
                    "date": h.occurred_at.isoformat() if h.occurred_at else None,
                }
                for h in (patient.history or [])[:5]  # Last 5 history items
            ],
        }

        # Add summary from last session if available
        if prev_sessions:
            last_session = prev_sessions[0]
            if last_session.summary:
                context["last_session_summary"] = last_session.summary
            if last_session.key_topics:
                context["last_session_topics"] = last_session.key_topics.get("topics", [])

        return context

    # Concern flagging
    async def flag_concern(
        self,
        vapi_call_id: str,
        concern: str,
        severity: str,
    ) -> bool:
        """Flag a concern during a session."""
        session = await self.get_session_by_vapi_id(vapi_call_id)
        if not session:
            return False

        # For now, store in key_topics. In Phase 5, this will create alerts.
        current_topics = session.key_topics or {}
        concerns = current_topics.get("concerns", [])
        concerns.append({
            "concern": concern,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        })
        current_topics["concerns"] = concerns
        session.key_topics = current_topics

        await self.db.commit()
        return True

    # Delete session
    async def delete_session(self, session_id: UUID) -> bool:
        """Delete a session."""
        session = await self.get_session(session_id)
        if not session:
            return False

        await self.db.delete(session)
        await self.db.commit()
        return True
