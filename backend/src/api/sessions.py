from uuid import UUID
from typing import Optional
from datetime import datetime
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
from src.assessment.processing import SessionProcessor
from src.assessment.extraction import SignalExtractionService
from src.assessment.scoring import DomainScoringService

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


@router.get("/{session_id}/analysis")
async def get_session_analysis(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """
    Get the full analysis results for a session.

    Returns:
    - Processing status
    - Extracted clinical signals
    - Domain scores
    - Session summary
    - Diagnostic hypotheses
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
            detail="Not authorized to access this session",
        )

    # Get processing status
    processor = SessionProcessor(db)
    processing_status = await processor.get_processing_status(session_id)

    # Get signals
    extraction_service = SignalExtractionService(db)
    signals = await extraction_service.get_signals_for_session(session_id)

    # Get domain scores
    scoring_service = DomainScoringService(db)
    domain_scores = await scoring_service.get_scores_for_session(session_id)

    # Get session summary
    from sqlalchemy import select
    from src.models.assessment import SessionSummary
    summary_result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = summary_result.scalar_one_or_none()

    # Get hypotheses for patient
    from src.models.assessment import DiagnosticHypothesis
    hypotheses_result = await db.execute(
        select(DiagnosticHypothesis)
        .where(DiagnosticHypothesis.patient_id == session.patient_id)
        .order_by(DiagnosticHypothesis.evidence_strength.desc())
    )
    hypotheses = list(hypotheses_result.scalars().all())

    return {
        "session_id": str(session_id),
        "patient_id": str(session.patient_id),
        "processing_status": processing_status,
        "signals": [
            {
                "id": str(s.id),
                "signal_type": s.signal_type,
                "signal_name": s.signal_name,
                "evidence": s.evidence,
                "evidence_type": s.evidence_type,
                "reasoning": s.reasoning,
                "maps_to_domain": s.maps_to_domain,
                "intensity": s.intensity,
                "confidence": s.confidence,
                "clinical_significance": s.clinical_significance,
                "clinician_verified": s.clinician_verified,
            }
            for s in signals
        ],
        "domain_scores": [
            {
                "domain_code": d.domain_code,
                "domain_name": d.domain_name,
                "raw_score": d.raw_score,
                "normalized_score": d.normalized_score,
                "confidence": d.confidence,
                "evidence_count": d.evidence_count,
                "previous_score": d.previous_score,
                "score_change": d.score_change,
            }
            for d in domain_scores
        ],
        "summary": {
            "brief_summary": summary.brief_summary if summary else None,
            "detailed_summary": summary.detailed_summary if summary else None,
            "key_topics": summary.key_topics if summary else None,
            "emotional_tone": summary.emotional_tone if summary else None,
            "clinical_observations": summary.clinical_observations if summary else None,
            "follow_up_suggestions": summary.follow_up_suggestions if summary else None,
            "concerns": summary.concerns if summary else None,
        } if summary else None,
        "hypotheses": [
            {
                "id": str(h.id),
                "condition_code": h.condition_code,
                "condition_name": h.condition_name,
                "evidence_strength": h.evidence_strength,
                "uncertainty": h.uncertainty,
                "trend": h.trend,
                "supporting_signals": h.supporting_signals,
                "explanation": h.explanation,
            }
            for h in hypotheses
        ],
    }


@router.post("/{session_id}/analyze")
async def trigger_session_analysis(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """
    Manually trigger analysis for a completed session.

    Use this to re-run analysis or analyze a session that wasn't
    automatically processed.
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
            detail="Not authorized to access this session",
        )
    if session.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session not completed (status: {session.status})",
        )

    processor = SessionProcessor(db)
    result = await processor.process_session(session_id)

    return {
        "session_id": str(session_id),
        "result": result.to_dict(),
    }


@router.patch("/{session_id}/signals/{signal_id}/verify")
async def verify_signal(
    session_id: UUID,
    signal_id: UUID,
    verified: bool = True,
    clinician_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    clinician: Clinician = Depends(get_current_clinician),
):
    """
    Mark a signal as verified/rejected by clinician.

    This is how clinicians confirm or reject AI-extracted signals.
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
            detail="Not authorized to access this session",
        )

    from src.models.assessment import ClinicalSignal
    signal = await db.get(ClinicalSignal, signal_id)

    if not signal or signal.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found",
        )

    signal.clinician_verified = verified
    signal.clinician_notes = clinician_notes
    signal.verified_by = clinician.id
    signal.verified_at = datetime.utcnow() if verified else None

    await db.commit()
    await db.refresh(signal)

    return {
        "signal_id": str(signal_id),
        "verified": signal.clinician_verified,
        "notes": signal.clinician_notes,
    }
