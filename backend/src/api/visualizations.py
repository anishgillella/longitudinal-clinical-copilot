"""
Visualization API Endpoints

Provides endpoints for generating chart data and visualizations
for clinical analytics dashboards.
"""

import logging
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models.assessment import ClinicalSignal, AssessmentDomainScore, DiagnosticHypothesis
from src.models.session import VoiceSession
from src.schemas.llm_outputs import (
    AnalyticsDashboardData,
    DomainRadarData,
    SignalDistributionData,
    HypothesisComparisonData,
    ChartDataPoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualizations", tags=["visualizations"])


# =============================================================================
# CHART COLOR SCHEMES
# =============================================================================

DOMAIN_COLORS = {
    "social_emotional_reciprocity": "#FF6B6B",
    "nonverbal_communication": "#4ECDC4",
    "relationships": "#45B7D1",
    "stereotyped_behaviors": "#96CEB4",
    "insistence_on_sameness": "#FFEAA7",
    "restricted_interests": "#DDA0DD",
    "sensory_reactivity": "#98D8C8",
    "emotional_regulation": "#F7DC6F",
}

SIGNIFICANCE_COLORS = {
    "high": "#E74C3C",
    "moderate": "#F39C12",
    "low": "#27AE60",
}

DSM5_COLORS = {
    "A1": "#3498DB",
    "A2": "#2ECC71",
    "A3": "#9B59B6",
    "B1": "#E74C3C",
    "B2": "#F39C12",
    "B3": "#1ABC9C",
    "B4": "#E91E63",
}


# =============================================================================
# DASHBOARD DATA ENDPOINT
# =============================================================================

@router.get("/dashboard/{session_id}", response_model=AnalyticsDashboardData)
async def get_dashboard_data(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsDashboardData:
    """
    Get complete dashboard data for a session.

    Returns all chart data and summary metrics for the analytics dashboard.
    """
    # Get session
    session = await db.get(VoiceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get signals
    signals_result = await db.execute(
        select(ClinicalSignal)
        .where(ClinicalSignal.session_id == session_id)
    )
    signals = list(signals_result.scalars().all())

    # Get domain scores
    scores_result = await db.execute(
        select(AssessmentDomainScore)
        .where(AssessmentDomainScore.session_id == session_id)
    )
    domain_scores = list(scores_result.scalars().all())

    # Get hypotheses
    hypotheses_result = await db.execute(
        select(DiagnosticHypothesis)
        .where(DiagnosticHypothesis.patient_id == session.patient_id)
        .order_by(DiagnosticHypothesis.evidence_strength.desc())
    )
    hypotheses = list(hypotheses_result.scalars().all())

    # Build dashboard data
    dashboard = AnalyticsDashboardData(
        session_id=str(session_id),
        patient_id=str(session.patient_id),
        total_signals=len(signals),
        high_significance_signals=len([s for s in signals if s.clinical_significance == "high"]),
        domains_scored=len(domain_scores),
        average_domain_score=sum(d.normalized_score for d in domain_scores) / len(domain_scores) if domain_scores else 0.0,
    )

    # Primary hypothesis
    if hypotheses:
        primary = hypotheses[0]
        dashboard.primary_hypothesis = primary.condition_name
        dashboard.primary_hypothesis_strength = primary.evidence_strength

    # Domain radar chart data
    if domain_scores:
        dashboard.domain_radar = DomainRadarData(
            labels=[d.domain_name or d.domain_code for d in domain_scores],
            values=[d.normalized_score for d in domain_scores],
            confidence=[d.confidence for d in domain_scores],
        )

    # Signal distribution data
    dashboard.signal_distribution = _build_signal_distribution(signals)

    # Hypothesis comparison data
    if hypotheses:
        dashboard.hypothesis_comparison = HypothesisComparisonData(
            hypotheses=[h.condition_name for h in hypotheses[:5]],
            evidence_strength=[h.evidence_strength for h in hypotheses[:5]],
            uncertainty=[h.uncertainty for h in hypotheses[:5]],
            supporting_count=[h.supporting_signals for h in hypotheses[:5]],
        )

    # DSM-5 coverage
    dsm5_coverage = {}
    for signal in signals:
        if signal.dsm5_criteria:
            criterion = signal.dsm5_criteria
            dsm5_coverage[criterion] = dsm5_coverage.get(criterion, 0) + 1

    dashboard.dsm5_coverage_summary = dsm5_coverage
    dashboard.dsm5_gaps = [
        c for c in ["A1", "A2", "A3", "B1", "B2", "B3", "B4"]
        if c not in dsm5_coverage
    ]

    return dashboard


def _build_signal_distribution(signals: list[ClinicalSignal]) -> SignalDistributionData:
    """Build signal distribution data for charts."""
    by_type = {}
    by_significance = {}
    by_dsm5 = {}
    by_evidence = {}

    for signal in signals:
        # By type
        sig_type = signal.signal_type or "unknown"
        by_type[sig_type] = by_type.get(sig_type, 0) + 1

        # By significance
        sig = signal.clinical_significance or "moderate"
        by_significance[sig] = by_significance.get(sig, 0) + 1

        # By DSM-5 criterion
        if signal.dsm5_criteria:
            by_dsm5[signal.dsm5_criteria] = by_dsm5.get(signal.dsm5_criteria, 0) + 1

        # By evidence type
        ev_type = signal.evidence_type or "inferred"
        by_evidence[ev_type] = by_evidence.get(ev_type, 0) + 1

    return SignalDistributionData(
        by_type=by_type,
        by_significance=by_significance,
        by_dsm5_criterion=by_dsm5,
        by_evidence_type=by_evidence,
    )


# =============================================================================
# INDIVIDUAL CHART ENDPOINTS
# =============================================================================

@router.get("/domain-radar/{session_id}")
async def get_domain_radar_chart(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get domain radar chart data.

    Returns data formatted for Chart.js radar chart.
    """
    scores_result = await db.execute(
        select(AssessmentDomainScore)
        .where(AssessmentDomainScore.session_id == session_id)
        .order_by(AssessmentDomainScore.domain_code)
    )
    domain_scores = list(scores_result.scalars().all())

    if not domain_scores:
        return {"labels": [], "datasets": []}

    labels = [d.domain_name or d.domain_code for d in domain_scores]
    scores = [d.normalized_score for d in domain_scores]
    confidence = [d.confidence for d in domain_scores]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Evidence Strength",
                "data": scores,
                "backgroundColor": "rgba(54, 162, 235, 0.2)",
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderWidth": 2,
            },
            {
                "label": "Confidence",
                "data": confidence,
                "backgroundColor": "rgba(255, 99, 132, 0.2)",
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 2,
            },
        ],
    }


@router.get("/signal-distribution/{session_id}")
async def get_signal_distribution_chart(
    session_id: UUID,
    chart_type: str = "type",  # type, significance, dsm5, evidence
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get signal distribution chart data.

    Args:
        session_id: The session ID
        chart_type: What to group by (type, significance, dsm5, evidence)

    Returns data formatted for Chart.js pie/doughnut chart.
    """
    signals_result = await db.execute(
        select(ClinicalSignal)
        .where(ClinicalSignal.session_id == session_id)
    )
    signals = list(signals_result.scalars().all())

    distribution = _build_signal_distribution(signals)

    if chart_type == "type":
        data = distribution.by_type
        colors = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40"]
    elif chart_type == "significance":
        data = distribution.by_significance
        colors = [SIGNIFICANCE_COLORS.get(k, "#999") for k in data.keys()]
    elif chart_type == "dsm5":
        data = distribution.by_dsm5_criterion
        colors = [DSM5_COLORS.get(k, "#999") for k in data.keys()]
    else:  # evidence
        data = distribution.by_evidence_type
        colors = ["#2ECC71", "#3498DB", "#E74C3C"]

    labels = list(data.keys())
    values = list(data.values())

    return {
        "labels": labels,
        "datasets": [{
            "data": values,
            "backgroundColor": colors[:len(labels)],
        }],
    }


@router.get("/hypothesis-comparison/{patient_id}")
async def get_hypothesis_comparison_chart(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get hypothesis comparison bar chart data.

    Returns data formatted for Chart.js horizontal bar chart.
    """
    hypotheses_result = await db.execute(
        select(DiagnosticHypothesis)
        .where(DiagnosticHypothesis.patient_id == patient_id)
        .order_by(DiagnosticHypothesis.evidence_strength.desc())
        .limit(5)
    )
    hypotheses = list(hypotheses_result.scalars().all())

    if not hypotheses:
        return {"labels": [], "datasets": []}

    labels = [h.condition_name for h in hypotheses]
    strength = [h.evidence_strength for h in hypotheses]
    uncertainty = [h.uncertainty for h in hypotheses]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Evidence Strength",
                "data": strength,
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
            },
            {
                "label": "Uncertainty",
                "data": uncertainty,
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
            },
        ],
    }


@router.get("/dsm5-coverage/{patient_id}")
async def get_dsm5_coverage_chart(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get DSM-5 criteria coverage chart.

    Returns data showing evidence coverage for each DSM-5 criterion.
    """
    signals_result = await db.execute(
        select(ClinicalSignal)
        .where(ClinicalSignal.patient_id == patient_id)
    )
    signals = list(signals_result.scalars().all())

    # Count signals per criterion
    criteria = ["A1", "A2", "A3", "B1", "B2", "B3", "B4"]
    counts = {c: 0 for c in criteria}

    for signal in signals:
        if signal.dsm5_criteria and signal.dsm5_criteria in counts:
            counts[signal.dsm5_criteria] += 1

    criterion_labels = {
        "A1": "Social-Emotional Reciprocity",
        "A2": "Nonverbal Communication",
        "A3": "Relationships",
        "B1": "Stereotyped Behaviors",
        "B2": "Insistence on Sameness",
        "B3": "Restricted Interests",
        "B4": "Sensory Reactivity",
    }

    return {
        "labels": [criterion_labels.get(c, c) for c in criteria],
        "datasets": [{
            "label": "Evidence Count",
            "data": [counts[c] for c in criteria],
            "backgroundColor": [DSM5_COLORS.get(c, "#999") for c in criteria],
        }],
        "coverage_summary": {
            "total_criteria": 7,
            "criteria_with_evidence": len([c for c in criteria if counts[c] > 0]),
            "gaps": [c for c in criteria if counts[c] == 0],
        },
    }


@router.get("/signal-timeline/{session_id}")
async def get_signal_timeline(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get signal extraction timeline.

    Returns signals organized by their position in the transcript.
    """
    signals_result = await db.execute(
        select(ClinicalSignal)
        .where(ClinicalSignal.session_id == session_id)
        .order_by(ClinicalSignal.transcript_line)
    )
    signals = list(signals_result.scalars().all())

    timeline_data = []
    for signal in signals:
        timeline_data.append({
            "id": str(signal.id),
            "line": signal.transcript_line or 0,
            "name": signal.signal_name,
            "type": signal.signal_type,
            "significance": signal.clinical_significance,
            "dsm5": signal.dsm5_criteria,
            "confidence": signal.confidence,
            "evidence": signal.evidence[:100] + "..." if len(signal.evidence) > 100 else signal.evidence,
        })

    return {
        "signals": timeline_data,
        "total": len(timeline_data),
    }


# =============================================================================
# LONGITUDINAL CHARTS
# =============================================================================

@router.get("/domain-progress/{patient_id}/{domain_code}")
async def get_domain_progress_chart(
    patient_id: UUID,
    domain_code: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get domain progress over time.

    Returns time-series data for a specific domain.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    scores_result = await db.execute(
        select(AssessmentDomainScore)
        .where(
            AssessmentDomainScore.patient_id == patient_id,
            AssessmentDomainScore.domain_code == domain_code,
            AssessmentDomainScore.assessed_at >= cutoff,
        )
        .order_by(AssessmentDomainScore.assessed_at)
    )
    scores = list(scores_result.scalars().all())

    if not scores:
        return {"labels": [], "datasets": []}

    labels = [s.assessed_at.strftime("%Y-%m-%d") for s in scores]
    values = [s.normalized_score for s in scores]
    confidence = [s.confidence for s in scores]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": f"{domain_code} Score",
                "data": values,
                "borderColor": "rgba(54, 162, 235, 1)",
                "fill": False,
            },
            {
                "label": "Confidence",
                "data": confidence,
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderDash": [5, 5],
                "fill": False,
            },
        ],
    }


@router.get("/hypothesis-history/{patient_id}/{condition_code}")
async def get_hypothesis_history_chart(
    patient_id: UUID,
    condition_code: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get hypothesis evidence strength history.

    Returns time-series data for a specific hypothesis.
    """
    from src.models.assessment import HypothesisHistory

    # Get hypothesis
    hyp_result = await db.execute(
        select(DiagnosticHypothesis)
        .where(
            DiagnosticHypothesis.patient_id == patient_id,
            DiagnosticHypothesis.condition_code == condition_code,
        )
    )
    hypothesis = hyp_result.scalar_one_or_none()

    if not hypothesis:
        return {"labels": [], "datasets": []}

    # Get history
    history_result = await db.execute(
        select(HypothesisHistory)
        .where(HypothesisHistory.hypothesis_id == hypothesis.id)
        .order_by(HypothesisHistory.recorded_at)
    )
    history = list(history_result.scalars().all())

    if not history:
        return {"labels": [], "datasets": []}

    labels = [h.recorded_at.strftime("%Y-%m-%d %H:%M") for h in history]
    strength = [h.evidence_strength for h in history]
    uncertainty = [h.uncertainty for h in history]

    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Evidence Strength",
                "data": strength,
                "borderColor": "rgba(54, 162, 235, 1)",
                "fill": False,
            },
            {
                "label": "Uncertainty",
                "data": uncertainty,
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderDash": [5, 5],
                "fill": False,
            },
        ],
        "trend": hypothesis.trend,
    }


@router.get("/session-comparison/{patient_id}")
async def get_session_comparison_chart(
    patient_id: UUID,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Compare signal extraction across sessions.

    Returns data comparing multiple sessions.
    """
    # Get recent sessions
    sessions_result = await db.execute(
        select(VoiceSession)
        .where(
            VoiceSession.patient_id == patient_id,
            VoiceSession.status == "completed",
        )
        .order_by(VoiceSession.ended_at.desc())
        .limit(limit)
    )
    sessions = list(sessions_result.scalars().all())

    if not sessions:
        return {"labels": [], "datasets": []}

    # Get signal counts per session
    session_data = []
    for session in reversed(sessions):  # Chronological order
        signals_result = await db.execute(
            select(func.count(ClinicalSignal.id))
            .where(ClinicalSignal.session_id == session.id)
        )
        signal_count = signals_result.scalar() or 0

        high_sig_result = await db.execute(
            select(func.count(ClinicalSignal.id))
            .where(
                ClinicalSignal.session_id == session.id,
                ClinicalSignal.clinical_significance == "high",
            )
        )
        high_sig_count = high_sig_result.scalar() or 0

        session_data.append({
            "date": session.ended_at.strftime("%Y-%m-%d") if session.ended_at else "Unknown",
            "type": session.session_type,
            "total_signals": signal_count,
            "high_significance": high_sig_count,
        })

    return {
        "labels": [s["date"] for s in session_data],
        "datasets": [
            {
                "label": "Total Signals",
                "data": [s["total_signals"] for s in session_data],
                "backgroundColor": "rgba(54, 162, 235, 0.8)",
            },
            {
                "label": "High Significance",
                "data": [s["high_significance"] for s in session_data],
                "backgroundColor": "rgba(255, 99, 132, 0.8)",
            },
        ],
    }
