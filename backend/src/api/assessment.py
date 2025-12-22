"""
Assessment API Endpoints

Endpoints for clinical assessment data: signals, domain scores, hypotheses, and processing.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.session import VoiceSession
from src.models.assessment import (
    ClinicalSignal,
    AssessmentDomainScore,
    DiagnosticHypothesis,
    HypothesisHistory,
    SessionSummary,
)
from src.schemas.assessment import (
    ClinicalSignalResponse,
    SignalListResponse,
    DomainScoreResponse,
    DomainScoreWithTrend,
    DomainOverview,
    HypothesisResponse,
    HypothesisHistoryEntry,
    HypothesisWithHistory,
    HypothesisDetailResponse,
    SessionSummaryResponse,
    ProcessingRequest,
    ProcessingResult,
    PatientAssessmentOverview,
)
from src.assessment.extraction import SignalExtractionService
from src.assessment.scoring import DomainScoringService
from src.assessment.hypothesis import HypothesisEngine
from src.assessment.processing import SessionProcessor
from src.assessment.domains import AUTISM_DOMAINS

router = APIRouter(prefix="/assessment", tags=["assessment"])


# =============================================================================
# Signal Endpoints
# =============================================================================

@router.get("/sessions/{session_id}/signals", response_model=SignalListResponse)
async def get_session_signals(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all clinical signals extracted from a session."""
    extraction_service = SignalExtractionService(db)
    signals = await extraction_service.get_signals_for_session(session_id)

    # Calculate summary stats
    by_type = {}
    by_significance = {}
    for signal in signals:
        by_type[signal.signal_type] = by_type.get(signal.signal_type, 0) + 1
        by_significance[signal.clinical_significance] = (
            by_significance.get(signal.clinical_significance, 0) + 1
        )

    return SignalListResponse(
        signals=[ClinicalSignalResponse.model_validate(s) for s in signals],
        total=len(signals),
        by_type=by_type,
        by_significance=by_significance,
    )


@router.get("/patients/{patient_id}/signals", response_model=SignalListResponse)
async def get_patient_signals(
    patient_id: UUID,
    signal_type: str | None = None,
    domain: str | None = None,
    significance: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all clinical signals for a patient with optional filters."""
    extraction_service = SignalExtractionService(db)
    signals = await extraction_service.get_signals_for_patient(
        patient_id=patient_id,
        signal_type=signal_type,
        domain=domain,
        significance=significance,
    )

    # Calculate summary stats
    by_type = {}
    by_significance = {}
    for signal in signals:
        by_type[signal.signal_type] = by_type.get(signal.signal_type, 0) + 1
        by_significance[signal.clinical_significance] = (
            by_significance.get(signal.clinical_significance, 0) + 1
        )

    return SignalListResponse(
        signals=[ClinicalSignalResponse.model_validate(s) for s in signals],
        total=len(signals),
        by_type=by_type,
        by_significance=by_significance,
    )


@router.get("/patients/{patient_id}/signals/summary")
async def get_patient_signal_summary(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics of signals for a patient."""
    extraction_service = SignalExtractionService(db)
    return await extraction_service.get_signal_summary(patient_id)


# =============================================================================
# Domain Score Endpoints
# =============================================================================

@router.get("/sessions/{session_id}/scores", response_model=list[DomainScoreResponse])
async def get_session_scores(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all domain scores for a session."""
    scoring_service = DomainScoringService(db)
    scores = await scoring_service.get_scores_for_session(session_id)
    return [DomainScoreResponse.model_validate(s) for s in scores]


@router.get("/patients/{patient_id}/scores/latest")
async def get_patient_latest_scores(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent score for each domain for a patient."""
    scoring_service = DomainScoringService(db)
    scores = await scoring_service.get_latest_scores_for_patient(patient_id)
    return {
        domain: DomainScoreResponse.model_validate(score)
        for domain, score in scores.items()
    }


@router.get("/patients/{patient_id}/domains", response_model=DomainOverview)
async def get_patient_domains_overview(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get overview of all domains with trends for a patient."""
    scoring_service = DomainScoringService(db)
    latest_scores = await scoring_service.get_latest_scores_for_patient(patient_id)

    domains_with_trends = []
    last_updated = None

    for domain_code, score in latest_scores.items():
        trend_data = await scoring_service.calculate_domain_trend(patient_id, domain_code)

        # Get history for sparkline
        history = await scoring_service.get_domain_history(patient_id, domain_code, days=90)
        history_points = [
            {"date": h.assessed_at.isoformat(), "score": h.normalized_score}
            for h in history
        ]

        domains_with_trends.append(DomainScoreWithTrend(
            domain_code=score.domain_code,
            domain_name=score.domain_name,
            category=score.category,
            current_score=score.normalized_score,
            confidence=score.confidence,
            evidence_count=score.evidence_count,
            trend=trend_data["trend"] if trend_data else None,
            change_30d=trend_data["change"] if trend_data else None,
            history=history_points,
        ))

        if last_updated is None or score.assessed_at > last_updated:
            last_updated = score.assessed_at

    return DomainOverview(
        patient_id=patient_id,
        domains=domains_with_trends,
        last_updated=last_updated,
    )


@router.get("/patients/{patient_id}/domains/{domain_code}/history")
async def get_domain_history(
    patient_id: UUID,
    domain_code: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db),
):
    """Get historical scores for a specific domain."""
    scoring_service = DomainScoringService(db)
    history = await scoring_service.get_domain_history(patient_id, domain_code, days)
    return {
        "domain_code": domain_code,
        "history": [DomainScoreResponse.model_validate(h) for h in history],
        "trend": await scoring_service.calculate_domain_trend(patient_id, domain_code, days),
    }


@router.get("/patients/{patient_id}/domains/exploration-needed")
async def get_domains_needing_exploration(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get list of domains that need more data collection."""
    scoring_service = DomainScoringService(db)
    domains = await scoring_service.get_domains_needing_exploration(patient_id)

    # Get domain details
    domain_details = []
    for code in domains:
        domain_info = next((d for d in AUTISM_DOMAINS if d.code == code), None)
        if domain_info:
            domain_details.append({
                "code": code,
                "name": domain_info.name,
                "category": domain_info.category.value,
                "description": domain_info.description,
                "example_questions": domain_info.example_questions[:3],
            })

    return {
        "patient_id": str(patient_id),
        "domains_needing_exploration": domain_details,
        "total_domains": len(AUTISM_DOMAINS),
        "explored_domains": len(AUTISM_DOMAINS) - len(domains),
    }


# =============================================================================
# Hypothesis Endpoints
# =============================================================================

@router.get("/patients/{patient_id}/hypotheses", response_model=list[HypothesisResponse])
async def get_patient_hypotheses(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all diagnostic hypotheses for a patient."""
    hypothesis_engine = HypothesisEngine(db)
    hypotheses = await hypothesis_engine.get_hypotheses_for_patient(patient_id)
    return [HypothesisResponse.from_orm_with_bounds(h) for h in hypotheses]


@router.get("/patients/{patient_id}/hypotheses/primary", response_model=HypothesisResponse | None)
async def get_primary_hypothesis(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the hypothesis with highest evidence strength."""
    hypothesis_engine = HypothesisEngine(db)
    hypothesis = await hypothesis_engine.get_primary_hypothesis(patient_id)
    if hypothesis:
        return HypothesisResponse.from_orm_with_bounds(hypothesis)
    return None


@router.get("/hypotheses/{hypothesis_id}/history", response_model=HypothesisWithHistory)
async def get_hypothesis_with_history(
    hypothesis_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a hypothesis with its full history."""
    hypothesis_engine = HypothesisEngine(db)

    # Get hypothesis
    result = await db.execute(
        select(DiagnosticHypothesis).where(DiagnosticHypothesis.id == hypothesis_id)
    )
    hypothesis = result.scalar_one_or_none()

    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    # Get history
    history = await hypothesis_engine.get_hypothesis_history(hypothesis_id)

    history_entries = [
        HypothesisHistoryEntry(
            date=h.recorded_at,
            evidence_strength=h.evidence_strength,
            uncertainty=h.uncertainty,
            delta=h.delta_from_previous,
            session_id=h.session_id,
        )
        for h in history
    ]

    return HypothesisWithHistory(
        hypothesis=HypothesisResponse.from_orm_with_bounds(hypothesis),
        history=history_entries,
    )


@router.post("/patients/{patient_id}/hypotheses/regenerate", response_model=list[HypothesisResponse])
async def regenerate_hypotheses(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate hypotheses based on all accumulated evidence."""
    hypothesis_engine = HypothesisEngine(db)
    hypotheses = await hypothesis_engine.generate_hypotheses(patient_id)
    return [HypothesisResponse.from_orm_with_bounds(h) for h in hypotheses]


@router.get("/hypotheses/{hypothesis_id}/detail", response_model=HypothesisDetailResponse)
async def get_hypothesis_detail(
    hypothesis_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed hypothesis with linked evidence and related signals.

    This endpoint returns:
    - Full hypothesis data with explanation and limitations
    - Supporting evidence with links to source signals
    - Contradicting evidence with reasoning
    - All related clinical signals for deep-linking to transcripts
    """
    # Get hypothesis
    result = await db.execute(
        select(DiagnosticHypothesis).where(DiagnosticHypothesis.id == hypothesis_id)
    )
    hypothesis = result.scalar_one_or_none()

    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    # Get all signals for this patient to enable deep-linking
    extraction_service = SignalExtractionService(db)
    all_signals = await extraction_service.get_signals_for_patient(hypothesis.patient_id)

    # Filter to signals that are referenced in evidence
    signal_ids = set()
    if hypothesis.supporting_evidence and "points" in hypothesis.supporting_evidence:
        for point in hypothesis.supporting_evidence["points"]:
            if isinstance(point, dict) and point.get("signal_id"):
                signal_ids.add(point["signal_id"])

    # Include signals that match by name if IDs aren't available
    related_signals = []
    for signal in all_signals:
        if str(signal.id) in signal_ids:
            related_signals.append(signal)
        elif hypothesis.supporting_evidence:
            # Check if signal name appears in any evidence
            for point in hypothesis.supporting_evidence.get("points", []):
                if isinstance(point, dict):
                    if point.get("signal_name") == signal.signal_name:
                        related_signals.append(signal)
                        break

    return HypothesisDetailResponse.from_hypothesis_with_signals(
        hypothesis=hypothesis,
        related_signals=related_signals,
    )


@router.get("/signals/{signal_id}", response_model=ClinicalSignalResponse)
async def get_signal_detail(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details for a specific clinical signal, including transcript context."""
    result = await db.execute(
        select(ClinicalSignal).where(ClinicalSignal.id == signal_id)
    )
    signal = result.scalar_one_or_none()

    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    return ClinicalSignalResponse.model_validate(signal)


# =============================================================================
# Session Summary Endpoints
# =============================================================================

@router.get("/sessions/{session_id}/summary", response_model=SessionSummaryResponse | None)
async def get_session_summary(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the summary for a session."""
    result = await db.execute(
        select(SessionSummary).where(SessionSummary.session_id == session_id)
    )
    summary = result.scalar_one_or_none()

    if summary:
        return SessionSummaryResponse.model_validate(summary)
    return None


@router.get("/patients/{patient_id}/summaries", response_model=list[SessionSummaryResponse])
async def get_patient_summaries(
    patient_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get recent session summaries for a patient."""
    result = await db.execute(
        select(SessionSummary)
        .where(SessionSummary.patient_id == patient_id)
        .order_by(SessionSummary.created_at.desc())
        .limit(limit)
    )
    summaries = result.scalars().all()
    return [SessionSummaryResponse.model_validate(s) for s in summaries]


# =============================================================================
# Processing Endpoints
# =============================================================================

@router.post("/process", response_model=ProcessingResult)
async def process_session(
    request: ProcessingRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process a completed session through the full assessment pipeline."""
    processor = SessionProcessor(db)
    result = await processor.process_session(
        session_id=request.session_id,
        extract_signals=request.extract_signals,
        score_domains=request.score_domains,
        update_hypotheses=request.update_hypotheses,
        generate_summary=request.generate_summary,
        check_concerns=request.check_concerns,
    )
    return ProcessingResult(**result.to_dict())


@router.post("/process/background")
async def process_session_background(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Queue a session for background processing."""
    # For now, just return acknowledgment
    # In production, this would use Celery or similar
    background_tasks.add_task(
        process_session_task,
        request.session_id,
        request.extract_signals,
        request.score_domains,
        request.update_hypotheses,
        request.generate_summary,
        request.check_concerns,
    )

    return {
        "status": "queued",
        "session_id": str(request.session_id),
        "message": "Session processing has been queued",
    }


async def process_session_task(
    session_id: UUID,
    extract_signals: bool,
    score_domains: bool,
    update_hypotheses: bool,
    generate_summary: bool,
    check_concerns: bool,
):
    """Background task for processing a session."""
    from src.database import async_session_maker

    async with async_session_maker() as db:
        processor = SessionProcessor(db)
        await processor.process_session(
            session_id=session_id,
            extract_signals=extract_signals,
            score_domains=score_domains,
            update_hypotheses=update_hypotheses,
            generate_summary=generate_summary,
            check_concerns=check_concerns,
        )


@router.get("/sessions/{session_id}/processing-status")
async def get_processing_status(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the processing status of a session."""
    processor = SessionProcessor(db)
    return await processor.get_processing_status(session_id)


# =============================================================================
# Assessment Overview Endpoints
# =============================================================================

@router.get("/patients/{patient_id}/overview", response_model=PatientAssessmentOverview)
async def get_patient_assessment_overview(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive assessment overview for a patient."""
    # Count sessions
    session_result = await db.execute(
        select(
            func.count(VoiceSession.id).label("total"),
            func.count(VoiceSession.id).filter(VoiceSession.status == "completed").label("completed"),
        ).where(VoiceSession.patient_id == patient_id)
    )
    session_counts = session_result.one()

    # Count signals
    signal_result = await db.execute(
        select(func.count(ClinicalSignal.id))
        .where(ClinicalSignal.patient_id == patient_id)
    )
    total_signals = signal_result.scalar() or 0

    # Get latest scores
    scoring_service = DomainScoringService(db)
    latest_scores = await scoring_service.get_latest_scores_for_patient(patient_id)
    domains_with_data = len(latest_scores)

    # Get hypotheses
    hypothesis_engine = HypothesisEngine(db)
    hypotheses = await hypothesis_engine.get_hypotheses_for_patient(patient_id)

    # Get domains needing exploration
    areas_needing = await scoring_service.get_domains_needing_exploration(patient_id)

    # Get last session date
    last_session_result = await db.execute(
        select(VoiceSession.ended_at)
        .where(VoiceSession.patient_id == patient_id, VoiceSession.status == "completed")
        .order_by(VoiceSession.ended_at.desc())
        .limit(1)
    )
    last_session_date = last_session_result.scalar()

    # Calculate assessment completeness
    total_domains = len(AUTISM_DOMAINS)
    completeness = domains_with_data / total_domains if total_domains > 0 else 0.0

    return PatientAssessmentOverview(
        patient_id=patient_id,
        total_sessions=session_counts.total,
        completed_sessions=session_counts.completed,
        total_signals=total_signals,
        domains_with_data=domains_with_data,
        current_hypotheses=[HypothesisResponse.from_orm_with_bounds(h) for h in hypotheses],
        last_session_date=last_session_date,
        assessment_completeness=completeness,
        areas_needing_exploration=areas_needing,
    )


# =============================================================================
# Domain Reference Endpoints
# =============================================================================

@router.get("/domains")
async def get_all_domains():
    """Get all assessment domains and their definitions."""
    return {
        "domains": [
            {
                "code": d.code,
                "name": d.name,
                "category": d.category.value,
                "description": d.description,
                "indicators": d.indicators,
                "example_questions": d.example_questions,
            }
            for d in AUTISM_DOMAINS
        ],
        "total": len(AUTISM_DOMAINS),
    }


@router.get("/domains/{domain_code}")
async def get_domain_details(domain_code: str):
    """Get details for a specific domain."""
    domain = next((d for d in AUTISM_DOMAINS if d.code == domain_code), None)

    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_code}' not found")

    return {
        "code": domain.code,
        "name": domain.name,
        "category": domain.category.value,
        "description": domain.description,
        "indicators": domain.indicators,
        "example_questions": domain.example_questions,
    }
