from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.clinician import Clinician
from src.api.deps import get_current_clinician
from src.schemas.session import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    SessionTranscriptResponse,
    TranscriptEntry,
)
from src.services.session_service import SessionService
from src.services.patient_service import PatientService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """
    Create a new voice session for a patient.

    After creating the session, use the session ID to link with VAPI
    when the call starts.
    """
    # Verify patient exists and belongs to clinician
    patient_service = PatientService(db)
    patient = await patient_service.get_by_id(data.patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )
    if patient.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create session for this patient",
        )

    session_service = SessionService(db)
    session = await session_service.create_session(data, clinician_id=clinician.id)
    return session


@router.get("", response_model=list[SessionListResponse])
async def list_sessions(
    patient_id: Optional[UUID] = Query(None, description="Filter by patient ID"),
    session_type: Optional[str] = Query(None, description="Filter by session type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """List sessions, optionally filtered."""
    session_service = SessionService(db)

    if patient_id:
        # Verify patient belongs to clinician
        patient_service = PatientService(db)
        patient = await patient_service.get_by_id(patient_id)
        if not patient or patient.clinician_id != clinician.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )
        sessions = await session_service.get_sessions_for_patient(
            patient_id=patient_id,
            session_type=session_type,
            status=status,
        )
    else:
        # Get all sessions for clinician's patients
        from sqlalchemy import select
        from src.models.session import VoiceSession

        query = select(VoiceSession).where(VoiceSession.clinician_id == clinician.id)
        if session_type:
            query = query.where(VoiceSession.session_type == session_type)
        if status:
            query = query.where(VoiceSession.status == status)
        query = query.order_by(VoiceSession.created_at.desc())

        result = await db.execute(query)
        sessions = list(result.scalars().all())

    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Get a session by ID."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return session


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Update a session."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this session",
        )

    updated = await session_service.update_session(session_id, data)
    return updated


@router.post("/{session_id}/link/{vapi_call_id}", response_model=SessionResponse)
async def link_vapi_call(
    session_id: UUID,
    vapi_call_id: str,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """
    Link a VAPI call ID to a session.

    Call this when the VAPI call starts to associate it with the session.
    """
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this session",
        )

    updated = await session_service.link_vapi_call(session_id, vapi_call_id)
    return updated


@router.get("/{session_id}/transcript", response_model=SessionTranscriptResponse)
async def get_session_transcript(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Get the full transcript for a session."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    transcripts = await session_service.get_transcripts(session_id)

    return SessionTranscriptResponse(
        session_id=session_id,
        entries=[TranscriptEntry.model_validate(t) for t in transcripts],
        total_entries=len(transcripts),
    )


@router.get("/{session_id}/transcript/text")
async def get_session_transcript_text(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Get the transcript as formatted text."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    text = await session_service.get_full_transcript_text(session_id)

    return {"session_id": str(session_id), "transcript": text}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """Delete a session."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session.clinician_id != clinician.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this session",
        )

    await session_service.delete_session(session_id)
