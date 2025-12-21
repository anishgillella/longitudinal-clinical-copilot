"""
Report Generation Service

Generates clinical reports for patients.
"""

import logging
from uuid import UUID
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.assessment import (
    ClinicalSignal,
    AssessmentDomainScore,
    DiagnosticHypothesis,
    SessionSummary,
)
from src.models.analytics import PatientReport
from src.models.memory import TimelineEvent, MemorySummary
from src.llm.openrouter import OpenRouterClient
from src.assessment.domains import AUTISM_DOMAINS

logger = logging.getLogger(__name__)


# Report generation prompts
REPORT_SYSTEM_PROMPT = """You are a clinical report writer for autism spectrum assessments.

Your reports should:
1. Be professional and objective
2. Use clinical language appropriate for medical records
3. Focus on observations and patterns, NOT diagnoses
4. Present evidence-based findings
5. Include appropriate uncertainty language
6. Be structured and easy to read

CRITICAL: This is a HYPOTHESIS REPORT, not a diagnostic report.
Frame all findings as patterns for clinical consideration."""

REPORT_USER_PROMPT = """Generate a {report_type} report for this patient assessment.

PATIENT INFORMATION:
{patient_info}

SESSION HISTORY ({session_count} sessions):
{session_summaries}

DOMAIN SCORES:
{domain_scores}

HYPOTHESES:
{hypotheses}

TIMELINE EVENTS:
{timeline_events}

Generate a comprehensive report with:
1. executive_summary: 2-3 paragraph overview
2. assessment_overview: Summary of the assessment process
3. domain_analysis: Analysis of each scored domain
4. hypothesis_discussion: Discussion of current hypotheses
5. behavioral_observations: Key behavioral patterns observed
6. recommendations: Clinical recommendations
7. next_steps: Suggested next steps

Return as JSON:
{{
    "executive_summary": "...",
    "assessment_overview": "...",
    "domain_analysis": {{
        "domain_code": {{"analysis": "...", "evidence_summary": "..."}}
    }},
    "hypothesis_discussion": "...",
    "behavioral_observations": "...",
    "recommendations": ["rec1", "rec2"],
    "next_steps": ["step1", "step2"]
}}"""


class ReportService:
    """Service for generating patient reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def generate_report(
        self,
        patient_id: UUID,
        report_type: str,
        clinician_id: Optional[UUID] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        title: Optional[str] = None,
    ) -> PatientReport:
        """
        Generate a comprehensive patient report.

        Args:
            patient_id: The patient ID
            report_type: Type of report (progress, assessment_summary, full_assessment)
            clinician_id: Optional clinician generating the report
            period_start: Optional start of reporting period
            period_end: Optional end of reporting period
            title: Optional custom title

        Returns:
            Generated PatientReport
        """
        # Get patient
        patient = await self.db.get(Patient, patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Set defaults
        report_date = date.today()
        if not period_end:
            period_end = report_date
        if not period_start:
            period_start = period_end - timedelta(days=90)

        if not title:
            title = self._generate_title(report_type, patient, report_date)

        # Gather all data
        patient_info = self._format_patient_info(patient)
        session_data = await self._get_session_data(patient_id, period_start, period_end)
        domain_scores = await self._get_domain_scores(patient_id)
        hypotheses = await self._get_hypotheses(patient_id)
        timeline_events = await self._get_timeline_events(patient_id, period_start, period_end)

        # Generate report content using LLM
        report_content = await self._generate_report_content(
            report_type=report_type,
            patient_info=patient_info,
            session_data=session_data,
            domain_scores=domain_scores,
            hypotheses=hypotheses,
            timeline_events=timeline_events,
        )

        # Create report
        report = PatientReport(
            patient_id=patient_id,
            clinician_id=clinician_id,
            report_type=report_type,
            title=title,
            report_date=report_date,
            period_start=period_start,
            period_end=period_end,
            executive_summary=report_content.get("executive_summary", ""),
            detailed_content=report_content,
            sessions_included=session_data["count"],
            signals_analyzed=session_data["signal_count"],
            domain_scores_snapshot={"scores": domain_scores},
            hypotheses_snapshot={"hypotheses": hypotheses},
            clinical_impressions=report_content.get("hypothesis_discussion"),
            recommendations={"items": report_content.get("recommendations", [])},
            status="draft",
            model_version=self.llm.model,
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"Generated {report_type} report for patient {patient_id}")
        return report

    async def get_reports(
        self,
        patient_id: UUID,
        report_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10,
    ) -> list[PatientReport]:
        """Get reports for a patient."""
        query = select(PatientReport).where(PatientReport.patient_id == patient_id)

        if report_type:
            query = query.where(PatientReport.report_type == report_type)
        if status:
            query = query.where(PatientReport.status == status)

        query = query.order_by(PatientReport.report_date.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_report(self, report_id: UUID) -> Optional[PatientReport]:
        """Get a specific report."""
        return await self.db.get(PatientReport, report_id)

    async def finalize_report(
        self,
        report_id: UUID,
        clinician_id: UUID,
        clinical_impressions: Optional[str] = None,
    ) -> Optional[PatientReport]:
        """Finalize a report."""
        report = await self.db.get(PatientReport, report_id)
        if not report:
            return None

        if clinical_impressions:
            report.clinical_impressions = clinical_impressions

        report.status = "finalized"
        report.finalized_at = datetime.utcnow()
        report.finalized_by = clinician_id

        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"Finalized report {report_id}")
        return report

    async def export_report(
        self,
        report_id: UUID,
        format: str = "json",
    ) -> dict:
        """Export a report in the specified format."""
        report = await self.db.get(PatientReport, report_id)
        if not report:
            return {"error": "Report not found"}

        # Update export tracking
        report.last_exported_at = datetime.utcnow()
        report.export_format = format
        await self.db.commit()

        if format == "json":
            return self._export_as_json(report)
        elif format == "text":
            return self._export_as_text(report)
        else:
            return {"error": f"Unsupported format: {format}"}

    # ==========================================================================
    # Private Helper Methods
    # ==========================================================================

    def _generate_title(
        self,
        report_type: str,
        patient: Patient,
        report_date: date,
    ) -> str:
        """Generate a default report title."""
        type_names = {
            "progress": "Progress Report",
            "assessment_summary": "Assessment Summary",
            "full_assessment": "Comprehensive Assessment Report",
            "session_notes": "Session Notes",
        }
        type_name = type_names.get(report_type, "Report")
        return f"{type_name} - {patient.first_name} {patient.last_name} - {report_date.strftime('%B %Y')}"

    def _format_patient_info(self, patient: Patient) -> str:
        """Format patient information for the prompt."""
        today = date.today()
        age = today.year - patient.date_of_birth.year

        return f"""Name: {patient.first_name} {patient.last_name}
Age: {age} years
Gender: {patient.gender or 'Not specified'}
Primary Concern: {patient.primary_concern or 'Not specified'}
Intake Date: {patient.intake_date.strftime('%Y-%m-%d') if patient.intake_date else 'Not recorded'}"""

    async def _get_session_data(
        self,
        patient_id: UUID,
        period_start: date,
        period_end: date,
    ) -> dict:
        """Get session data for the report period."""
        # Get sessions
        session_result = await self.db.execute(
            select(VoiceSession)
            .where(
                VoiceSession.patient_id == patient_id,
                VoiceSession.status == "completed",
                func.date(VoiceSession.ended_at) >= period_start,
                func.date(VoiceSession.ended_at) <= period_end,
            )
            .order_by(VoiceSession.ended_at)
        )
        sessions = list(session_result.scalars().all())

        # Get summaries
        summaries = []
        signal_count = 0
        for session in sessions:
            summary_result = await self.db.execute(
                select(SessionSummary).where(SessionSummary.session_id == session.id)
            )
            summary = summary_result.scalar_one_or_none()

            # Count signals
            signal_result = await self.db.execute(
                select(func.count(ClinicalSignal.id)).where(
                    ClinicalSignal.session_id == session.id
                )
            )
            session_signals = signal_result.scalar() or 0
            signal_count += session_signals

            summaries.append({
                "date": session.ended_at.strftime("%Y-%m-%d") if session.ended_at else "Unknown",
                "type": session.session_type,
                "duration_minutes": (session.duration_seconds or 0) // 60,
                "summary": summary.brief_summary if summary else session.summary or "No summary",
                "signals_extracted": session_signals,
            })

        return {
            "count": len(sessions),
            "signal_count": signal_count,
            "summaries": summaries,
        }

    async def _get_domain_scores(self, patient_id: UUID) -> list[dict]:
        """Get latest domain scores."""
        from src.assessment.scoring import DomainScoringService
        scoring_service = DomainScoringService(self.db)
        scores = await scoring_service.get_latest_scores_for_patient(patient_id)

        return [
            {
                "domain_code": code,
                "domain_name": score.domain_name,
                "score": score.normalized_score,
                "confidence": score.confidence,
                "evidence_count": score.evidence_count,
            }
            for code, score in scores.items()
        ]

    async def _get_hypotheses(self, patient_id: UUID) -> list[dict]:
        """Get current hypotheses."""
        result = await self.db.execute(
            select(DiagnosticHypothesis)
            .where(DiagnosticHypothesis.patient_id == patient_id)
            .order_by(DiagnosticHypothesis.evidence_strength.desc())
        )
        hypotheses = result.scalars().all()

        return [
            {
                "condition_code": h.condition_code,
                "condition_name": h.condition_name,
                "evidence_strength": h.evidence_strength,
                "uncertainty": h.uncertainty,
                "trend": h.trend,
                "explanation": h.explanation,
            }
            for h in hypotheses
        ]

    async def _get_timeline_events(
        self,
        patient_id: UUID,
        period_start: date,
        period_end: date,
    ) -> list[dict]:
        """Get timeline events for the period."""
        result = await self.db.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.patient_id == patient_id,
                func.date(TimelineEvent.occurred_at) >= period_start,
                func.date(TimelineEvent.occurred_at) <= period_end,
            )
            .order_by(TimelineEvent.occurred_at)
        )
        events = result.scalars().all()

        return [
            {
                "date": e.occurred_at.strftime("%Y-%m-%d"),
                "type": e.event_type,
                "title": e.title,
                "description": e.description[:200] if len(e.description) > 200 else e.description,
                "significance": e.significance,
            }
            for e in events
        ]

    async def _generate_report_content(
        self,
        report_type: str,
        patient_info: str,
        session_data: dict,
        domain_scores: list[dict],
        hypotheses: list[dict],
        timeline_events: list[dict],
    ) -> dict:
        """Use LLM to generate report content."""
        # Format data for prompt
        session_summaries = "\n".join([
            f"- {s['date']} ({s['type']}, {s['duration_minutes']}min): {s['summary']}"
            for s in session_data["summaries"]
        ]) or "No sessions in this period"

        domain_text = "\n".join([
            f"- {d['domain_name']}: Score {d['score']:.2f} (confidence: {d['confidence']:.2f})"
            for d in domain_scores
        ]) or "No domain scores available"

        hypothesis_text = "\n".join([
            f"- {h['condition_name']}: Strength {h['evidence_strength']:.2f}, Trend: {h['trend'] or 'N/A'}"
            for h in hypotheses
        ]) or "No hypotheses generated yet"

        event_text = "\n".join([
            f"- {e['date']} [{e['type']}]: {e['title']}"
            for e in timeline_events[:10]
        ]) or "No notable events"

        user_prompt = REPORT_USER_PROMPT.format(
            report_type=report_type,
            patient_info=patient_info,
            session_count=session_data["count"],
            session_summaries=session_summaries,
            domain_scores=domain_text,
            hypotheses=hypothesis_text,
            timeline_events=event_text,
        )

        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return result
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                "executive_summary": "Report generation failed. Please try again.",
                "recommendations": [],
                "next_steps": [],
            }

    def _export_as_json(self, report: PatientReport) -> dict:
        """Export report as JSON."""
        return {
            "report_id": str(report.id),
            "patient_id": str(report.patient_id),
            "report_type": report.report_type,
            "title": report.title,
            "report_date": report.report_date.isoformat(),
            "period": {
                "start": report.period_start.isoformat() if report.period_start else None,
                "end": report.period_end.isoformat() if report.period_end else None,
            },
            "executive_summary": report.executive_summary,
            "content": report.detailed_content,
            "domain_scores": report.domain_scores_snapshot,
            "hypotheses": report.hypotheses_snapshot,
            "clinical_impressions": report.clinical_impressions,
            "recommendations": report.recommendations,
            "status": report.status,
            "generated_at": report.created_at.isoformat(),
            "finalized_at": report.finalized_at.isoformat() if report.finalized_at else None,
        }

    def _export_as_text(self, report: PatientReport) -> dict:
        """Export report as formatted text."""
        lines = [
            f"{'=' * 60}",
            f"{report.title}",
            f"{'=' * 60}",
            f"Report Date: {report.report_date.strftime('%B %d, %Y')}",
            f"Status: {report.status.upper()}",
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            report.executive_summary or "No summary available",
            "",
        ]

        if report.detailed_content:
            content = report.detailed_content
            if content.get("assessment_overview"):
                lines.extend([
                    "ASSESSMENT OVERVIEW",
                    "-" * 40,
                    content["assessment_overview"],
                    "",
                ])

            if content.get("behavioral_observations"):
                lines.extend([
                    "BEHAVIORAL OBSERVATIONS",
                    "-" * 40,
                    content["behavioral_observations"],
                    "",
                ])

        if report.clinical_impressions:
            lines.extend([
                "CLINICAL IMPRESSIONS",
                "-" * 40,
                report.clinical_impressions,
                "",
            ])

        if report.recommendations and report.recommendations.get("items"):
            lines.extend([
                "RECOMMENDATIONS",
                "-" * 40,
            ])
            for i, rec in enumerate(report.recommendations["items"], 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        return {
            "content": "\n".join(lines),
            "format": "text",
        }
