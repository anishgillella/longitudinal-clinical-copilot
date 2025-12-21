"""
Analytics API Endpoints

Endpoints for dashboards, reports, metrics, and analytics.
"""

from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.api.deps import get_current_clinician
from src.models.clinician import Clinician
from src.models.analytics import PatientReport, AssessmentProgress
from src.schemas.analytics import (
    DashboardData,
    PatientListResponse,
    ReportCreate,
    ReportResponse,
    ReportListItem,
    AssessmentProgressResponse,
    AssessmentProgressUpdate,
    ClinicianStats,
    SystemStats,
    TimeSeriesData,
    TimeSeriesDataPoint,
)
from src.analytics.metrics import MetricsService
from src.analytics.dashboard import DashboardService
from src.analytics.reports import ReportService
from src.analytics.progress import ProgressService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard(
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get clinician dashboard with all metrics and data."""
    dashboard_service = DashboardService(db)
    return await dashboard_service.get_dashboard(clinician.id)


@router.get("/dashboard/patients", response_model=PatientListResponse)
async def get_patient_list(
    status: str | None = None,
    assessment_status: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of patients for the clinician."""
    dashboard_service = DashboardService(db)
    result = await dashboard_service.get_patient_list(
        clinician_id=clinician.id,
        status=status,
        assessment_status=assessment_status,
        search=search,
        page=page,
        page_size=page_size,
    )
    return PatientListResponse(**result)


@router.get("/dashboard/attention-needed")
async def get_patients_needing_attention(
    limit: int = Query(default=10, ge=1, le=50),
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get patients that need clinician attention."""
    dashboard_service = DashboardService(db)
    patients = await dashboard_service.get_patients_needing_attention(
        clinician.id, limit
    )
    return {"patients": patients}


# =============================================================================
# Metrics Endpoints
# =============================================================================

@router.get("/metrics")
async def get_clinician_metrics(
    as_of_date: date | None = None,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get metrics for the current clinician."""
    metrics_service = MetricsService(db)
    return await metrics_service.get_clinician_metrics(clinician.id, as_of_date)


@router.get("/metrics/stats", response_model=ClinicianStats)
async def get_clinician_stats(
    period_days: int = Query(default=30, ge=7, le=365),
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed statistics for the clinician."""
    metrics_service = MetricsService(db)
    stats = await metrics_service.get_clinician_stats(clinician.id, period_days)
    return ClinicianStats(**stats)


@router.get("/metrics/system", response_model=SystemStats)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get system-wide statistics."""
    metrics_service = MetricsService(db)
    stats = await metrics_service.get_system_stats()
    return SystemStats(**stats)


@router.get("/metrics/timeseries/{metric}", response_model=TimeSeriesData)
async def get_time_series(
    metric: str,
    period_days: int = Query(default=30, ge=7, le=90),
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Get time series data for a metric."""
    if metric not in ["sessions", "signals"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metric: {metric}. Valid options: sessions, signals"
        )

    metrics_service = MetricsService(db)
    data = await metrics_service.get_time_series(clinician.id, metric, period_days)

    return TimeSeriesData(
        metric_name=metric,
        data_points=[TimeSeriesDataPoint(**d) for d in data],
        period_start=date.today().replace(day=1),
        period_end=date.today(),
    )


@router.post("/metrics/snapshot")
async def create_dashboard_snapshot(
    snapshot_date: date | None = None,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Create a dashboard metrics snapshot."""
    metrics_service = MetricsService(db)
    snapshot = await metrics_service.create_dashboard_snapshot(
        clinician.id, snapshot_date
    )
    return {
        "snapshot_id": str(snapshot.id),
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "created": True,
    }


# =============================================================================
# Report Endpoints
# =============================================================================

@router.post("/patients/{patient_id}/reports", response_model=ReportResponse)
async def generate_report(
    patient_id: UUID,
    request: ReportCreate,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report for a patient."""
    report_service = ReportService(db)
    report = await report_service.generate_report(
        patient_id=patient_id,
        report_type=request.report_type.value,
        clinician_id=clinician.id,
        period_start=request.period_start,
        period_end=request.period_end,
        title=request.title,
    )
    return ReportResponse.model_validate(report)


@router.get("/patients/{patient_id}/reports", response_model=list[ReportListItem])
async def get_patient_reports(
    patient_id: UUID,
    report_type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get reports for a patient."""
    report_service = ReportService(db)
    reports = await report_service.get_reports(
        patient_id=patient_id,
        report_type=report_type,
        status=status,
        limit=limit,
    )
    return [
        ReportListItem(
            id=r.id,
            report_type=r.report_type,
            title=r.title,
            report_date=r.report_date,
            status=r.status,
            created_at=r.created_at,
        )
        for r in reports
    ]


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report."""
    report_service = ReportService(db)
    report = await report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/finalize", response_model=ReportResponse)
async def finalize_report(
    report_id: UUID,
    clinical_impressions: str | None = None,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Finalize a report."""
    report_service = ReportService(db)
    report = await report_service.finalize_report(
        report_id=report_id,
        clinician_id=clinician.id,
        clinical_impressions=clinical_impressions,
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportResponse.model_validate(report)


@router.post("/reports/{report_id}/export")
async def export_report(
    report_id: UUID,
    format: str = Query(default="json", pattern="^(json|text)$"),
    db: AsyncSession = Depends(get_db),
):
    """Export a report."""
    report_service = ReportService(db)
    return await report_service.export_report(report_id, format)


# =============================================================================
# Assessment Progress Endpoints
# =============================================================================

@router.get("/patients/{patient_id}/progress", response_model=AssessmentProgressResponse)
async def get_assessment_progress(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get assessment progress for a patient."""
    progress_service = ProgressService(db)
    details = await progress_service.get_progress_details(patient_id)
    return AssessmentProgressResponse(**details)


@router.post("/patients/{patient_id}/progress/update", response_model=AssessmentProgressResponse)
async def update_assessment_progress(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Recalculate and update assessment progress."""
    progress_service = ProgressService(db)
    await progress_service.update_progress(patient_id)
    details = await progress_service.get_progress_details(patient_id)
    return AssessmentProgressResponse(**details)


@router.patch("/patients/{patient_id}/progress")
async def patch_assessment_progress(
    patient_id: UUID,
    update: AssessmentProgressUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Manually update progress settings."""
    progress_service = ProgressService(db)

    if update.status:
        await progress_service.set_status(patient_id, update.status.value)

    if update.next_session_recommended:
        await progress_service.schedule_next_session(
            patient_id, update.next_session_recommended
        )

    details = await progress_service.get_progress_details(patient_id)
    return AssessmentProgressResponse(**details)


# =============================================================================
# Analytics Events Endpoints
# =============================================================================

@router.post("/events")
async def log_analytics_event(
    event_type: str,
    event_category: str,
    patient_id: UUID | None = None,
    session_id: UUID | None = None,
    event_data: dict | None = None,
    clinician: Clinician = Depends(get_current_clinician),
    db: AsyncSession = Depends(get_db),
):
    """Log an analytics event."""
    metrics_service = MetricsService(db)
    event = await metrics_service.log_event(
        event_type=event_type,
        event_category=event_category,
        clinician_id=clinician.id,
        patient_id=patient_id,
        session_id=session_id,
        event_data=event_data,
    )
    return {
        "event_id": str(event.id),
        "logged": True,
    }
