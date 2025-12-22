"""
Longitudinal Memory API Endpoints

Endpoints for managing patient timeline, context, and memory summaries.
"""

from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.memory import (
    TimelineEvent,
    MemorySummary,
    ContextSnapshot,
    ConversationThread,
)
from src.schemas.memory import (
    TimelineEventCreate,
    TimelineEventUpdate,
    TimelineEventResponse,
    TimelineResponse,
    MemorySummaryResponse,
    ContextSnapshotResponse,
    ConversationThreadCreate,
    ConversationThreadUpdate,
    ConversationThreadResponse,
    ContextRequest,
    PatientContext,
    LongitudinalProgress,
)
from src.memory.timeline import TimelineService
from src.memory.context import ContextService
from src.memory.summarizer import MemorySummarizer

router = APIRouter(prefix="/memory", tags=["memory"])


# =============================================================================
# Timeline Event Endpoints
# =============================================================================

@router.post("/patients/{patient_id}/timeline", response_model=TimelineEventResponse)
async def add_timeline_event(
    patient_id: UUID,
    event: TimelineEventCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new event to the patient's timeline."""
    timeline_service = TimelineService(db)
    created = await timeline_service.add_event(
        patient_id=patient_id,
        event_type=event.event_type.value,
        category=event.category.value,
        title=event.title,
        description=event.description,
        occurred_at=event.occurred_at,
        significance=event.significance.value,
        duration_context=event.duration_context,
        impact_domains=event.impact_domains,
        source=event.source,
        confidence=event.confidence,
        evidence_quotes=event.evidence_quotes,
        related_signal_ids=event.related_signal_ids,
    )
    return TimelineEventResponse.model_validate(created)


@router.get("/patients/{patient_id}/timeline", response_model=TimelineResponse)
async def get_patient_timeline(
    patient_id: UUID,
    days: int | None = None,
    event_type: str | None = None,
    category: str | None = None,
    significance: str | None = None,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get the patient's timeline with optional filters."""
    timeline_service = TimelineService(db)
    events = await timeline_service.get_timeline(
        patient_id=patient_id,
        days=days,
        event_type=event_type,
        category=category,
        significance=significance,
        limit=limit,
    )

    summary = await timeline_service.get_timeline_summary(patient_id)

    return TimelineResponse(
        patient_id=patient_id,
        events=[TimelineEventResponse.model_validate(e) for e in events],
        total_events=summary["total_events"],
        date_range=summary["date_range"],
        events_by_category=summary["by_category"],
        events_by_significance=summary["by_significance"],
    )


@router.get("/patients/{patient_id}/timeline/summary")
async def get_timeline_summary(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics for the patient's timeline."""
    timeline_service = TimelineService(db)
    return await timeline_service.get_timeline_summary(patient_id)


@router.post("/sessions/{session_id}/extract-events")
async def extract_session_events(
    session_id: UUID,
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Extract timeline events from a completed session."""
    timeline_service = TimelineService(db)
    events = await timeline_service.extract_events_from_session(
        session_id=session_id,
        patient_id=patient_id,
    )
    return {
        "session_id": str(session_id),
        "events_extracted": len(events),
        "events": [TimelineEventResponse.model_validate(e) for e in events],
    }


@router.patch("/timeline/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(
    event_id: UUID,
    update: TimelineEventUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a timeline event."""
    event = await db.get(TimelineEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if update.title is not None:
        event.title = update.title
    if update.description is not None:
        event.description = update.description
    if update.significance is not None:
        event.significance = update.significance.value
    if update.duration_context is not None:
        event.duration_context = update.duration_context

    await db.commit()
    await db.refresh(event)
    return TimelineEventResponse.model_validate(event)


@router.delete("/timeline/{event_id}")
async def delete_timeline_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a timeline event."""
    event = await db.get(TimelineEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    await db.delete(event)
    await db.commit()
    return {"status": "deleted", "event_id": str(event_id)}


# =============================================================================
# Conversation Thread Endpoints
# =============================================================================

@router.post("/patients/{patient_id}/threads", response_model=ConversationThreadResponse)
async def create_thread(
    patient_id: UUID,
    thread: ConversationThreadCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation thread."""
    timeline_service = TimelineService(db)
    created = await timeline_service.create_thread(
        patient_id=patient_id,
        thread_topic=thread.thread_topic,
        category=thread.category,
        summary=thread.summary,
        first_mentioned_at=thread.first_mentioned_at,
        clinical_relevance=thread.clinical_relevance,
    )
    return ConversationThreadResponse.model_validate(created)


@router.get("/patients/{patient_id}/threads", response_model=list[ConversationThreadResponse])
async def get_patient_threads(
    patient_id: UUID,
    status: str | None = "active",
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation threads for a patient."""
    timeline_service = TimelineService(db)
    if status == "active":
        threads = await timeline_service.get_active_threads(patient_id, limit)
    else:
        # Get all threads
        from sqlalchemy import select
        result = await db.execute(
            select(ConversationThread)
            .where(ConversationThread.patient_id == patient_id)
            .order_by(ConversationThread.last_discussed_at.desc())
            .limit(limit)
        )
        threads = list(result.scalars().all())

    return [ConversationThreadResponse.model_validate(t) for t in threads]


@router.get("/patients/{patient_id}/threads/follow-up", response_model=list[ConversationThreadResponse])
async def get_threads_needing_followup(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get threads that need follow-up."""
    timeline_service = TimelineService(db)
    threads = await timeline_service.get_threads_needing_followup(patient_id)
    return [ConversationThreadResponse.model_validate(t) for t in threads]


@router.patch("/threads/{thread_id}", response_model=ConversationThreadResponse)
async def update_thread(
    thread_id: UUID,
    update: ConversationThreadUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation thread."""
    thread = await db.get(ConversationThread, thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if update.summary is not None:
        thread.summary = update.summary
    if update.status is not None:
        thread.status = update.status.value
    if update.clinical_relevance is not None:
        thread.clinical_relevance = update.clinical_relevance
    if update.follow_up_needed is not None:
        thread.follow_up_needed = update.follow_up_needed
    if update.follow_up_notes is not None:
        thread.follow_up_notes = update.follow_up_notes

    await db.commit()
    await db.refresh(thread)
    return ConversationThreadResponse.model_validate(thread)


@router.post("/threads/{thread_id}/resolve", response_model=ConversationThreadResponse)
async def resolve_thread(
    thread_id: UUID,
    resolution_notes: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Mark a thread as resolved."""
    timeline_service = TimelineService(db)
    thread = await timeline_service.resolve_thread(thread_id, resolution_notes)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ConversationThreadResponse.model_validate(thread)


# =============================================================================
# Context Endpoints
# =============================================================================

@router.post("/patients/{patient_id}/context", response_model=PatientContext)
async def get_patient_context(
    patient_id: UUID,
    request: ContextRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get compiled patient context for session injection."""
    context_service = ContextService(db)

    if request:
        context = await context_service.get_patient_context(
            patient_id=patient_id,
            session_type=request.session_type,
            max_tokens=request.max_tokens,
            include_hypotheses=request.include_hypotheses,
            include_domain_scores=request.include_domain_scores,
            include_recent_events=request.include_recent_events,
            recent_events_days=request.recent_events_days,
        )
    else:
        context = await context_service.get_patient_context(patient_id)

    return context


@router.post("/sessions/{session_id}/context-injection")
async def get_session_context_injection(
    session_id: UUID,
    patient_id: UUID,
    session_type: str = "checkin",
    db: AsyncSession = Depends(get_db),
):
    """Get context formatted for VAPI session injection."""
    context_service = ContextService(db)
    return await context_service.get_session_context_injection(
        patient_id=patient_id,
        session_id=session_id,
        session_type=session_type,
    )


@router.post("/patients/{patient_id}/snapshots", response_model=ContextSnapshotResponse)
async def create_context_snapshot(
    patient_id: UUID,
    session_id: UUID | None = None,
    snapshot_type: str = "pre_session",
    db: AsyncSession = Depends(get_db),
):
    """Create and store a context snapshot."""
    context_service = ContextService(db)
    snapshot = await context_service.create_snapshot(
        patient_id=patient_id,
        session_id=session_id,
        snapshot_type=snapshot_type,
    )
    return ContextSnapshotResponse.model_validate(snapshot)


@router.get("/patients/{patient_id}/snapshots/latest", response_model=ContextSnapshotResponse | None)
async def get_latest_snapshot(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent context snapshot."""
    context_service = ContextService(db)
    snapshot = await context_service.get_latest_snapshot(patient_id)
    if snapshot:
        return ContextSnapshotResponse.model_validate(snapshot)
    return None


# =============================================================================
# Memory Summary Endpoints
# =============================================================================

@router.post("/sessions/{session_id}/summarize", response_model=MemorySummaryResponse)
async def generate_session_summary(
    session_id: UUID,
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate a memory summary for a session."""
    summarizer = MemorySummarizer(db)
    summary = await summarizer.generate_session_summary(session_id, patient_id)
    return MemorySummaryResponse.model_validate(summary)


@router.post("/patients/{patient_id}/summaries/period", response_model=MemorySummaryResponse)
async def generate_period_summary(
    patient_id: UUID,
    summary_type: str,  # weekly, monthly, quarterly
    period_start: datetime,
    period_end: datetime,
    db: AsyncSession = Depends(get_db),
):
    """Generate a summary for a time period."""
    if summary_type not in ["weekly", "monthly", "quarterly", "overall"]:
        raise HTTPException(
            status_code=400,
            detail="summary_type must be one of: weekly, monthly, quarterly, overall"
        )

    summarizer = MemorySummarizer(db)
    summary = await summarizer.generate_period_summary(
        patient_id=patient_id,
        summary_type=summary_type,
        period_start=period_start,
        period_end=period_end,
    )
    return MemorySummaryResponse.model_validate(summary)


@router.get("/patients/{patient_id}/summaries", response_model=list[MemorySummaryResponse])
async def get_memory_summaries(
    patient_id: UUID,
    summary_type: str | None = None,
    limit: int = Query(default=10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get memory summaries for a patient."""
    summarizer = MemorySummarizer(db)
    summaries = await summarizer.get_memory_summaries(
        patient_id=patient_id,
        summary_type=summary_type,
        limit=limit,
    )
    return [MemorySummaryResponse.model_validate(s) for s in summaries]


@router.get("/patients/{patient_id}/history/compressed")
async def get_compressed_history(
    patient_id: UUID,
    max_tokens: int = Query(default=2000, ge=500, le=8000),
    db: AsyncSession = Depends(get_db),
):
    """Get compressed patient history optimized for token budget."""
    summarizer = MemorySummarizer(db)
    history = await summarizer.get_compressed_history(patient_id, max_tokens)
    return {
        "patient_id": str(patient_id),
        "compressed_history": history,
        "approximate_tokens": len(history) // 4,
    }


# =============================================================================
# Longitudinal Analysis Endpoints
# =============================================================================

@router.get("/patients/{patient_id}/analysis", response_model=LongitudinalProgress)
async def get_longitudinal_analysis(
    patient_id: UUID,
    days: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get longitudinal analysis of patient progress."""
    summarizer = MemorySummarizer(db)
    analysis = await summarizer.generate_longitudinal_analysis(patient_id, days)
    return LongitudinalProgress(**analysis)


@router.get("/patients/{patient_id}/trajectory")
async def get_trajectory_summary(
    patient_id: UUID,
    days: int = Query(default=30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
):
    """Get a quick summary of patient trajectory."""
    summarizer = MemorySummarizer(db)
    analysis = await summarizer.generate_longitudinal_analysis(patient_id, days)

    return {
        "patient_id": str(patient_id),
        "period_days": days,
        "trajectory": analysis.get("overall_trajectory", "insufficient_data"),
        "confidence": analysis.get("confidence", 0.0),
        "sessions_analyzed": analysis.get("sessions_analyzed", 0),
        "key_areas": analysis.get("recommended_focus_areas", [])[:3],
    }
