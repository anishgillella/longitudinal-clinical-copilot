# Phase 5: Analytics & Clinician Dashboard

## Objective

Build the clinician-facing analytics dashboard with visualizations, structured clinical notes, hypothesis tracking, and actionable insights.

## Prerequisites

- Phase 4 completed (longitudinal memory, pattern detection)
- Understanding of clinical documentation requirements
- Frontend framework selection (recommended: React with TypeScript)

## Design Principles

1. **Clinician time is precious** - Show the most important information first
2. **No false certainty** - Always display confidence intervals and uncertainty
3. **Temporal context required** - Show when evidence was collected
4. **Actionable over informational** - Prioritize what needs attention
5. **Editable and auditable** - Allow corrections with full audit trail

## Deliverables

### 5.1 Dashboard Information Architecture

```
Clinician Dashboard
│
├── Patient List View
│   ├── Search & filters
│   ├── Priority indicators (needs attention)
│   └── Quick stats (sessions, last contact)
│
├── Patient Detail View
│   ├── Overview Tab
│   │   ├── Current status summary
│   │   ├── Key metrics (3-5 cards)
│   │   ├── Recent activity timeline
│   │   └── Action items / alerts
│   │
│   ├── Timeline Tab
│   │   ├── Visual timeline (zoomable)
│   │   ├── Event filtering
│   │   └── Add event functionality
│   │
│   ├── Sessions Tab
│   │   ├── Session list
│   │   ├── Session detail with transcript
│   │   ├── Signal highlights
│   │   └── Clinical notes
│   │
│   ├── Assessment Tab
│   │   ├── Domain score visualization
│   │   ├── Trend charts
│   │   ├── Hypothesis tracking
│   │   └── Evidence browser
│   │
│   └── Notes Tab
│       ├── Clinical notes (SOAP/DAP)
│       ├── Progress notes
│       └── Export for EHR
│
└── Analytics View
    ├── Cohort overview
    ├── Workload metrics
    └── Outcome tracking
```

### 5.2 Extended Project Structure

```
src/
├── dashboard/                   # Dashboard backend
│   ├── __init__.py
│   ├── views.py                 # Dashboard view aggregations
│   ├── notes.py                 # Clinical note generation
│   ├── exports.py               # Data exports
│   └── alerts.py                # Alert generation
│
├── api/
│   ├── dashboard.py             # Dashboard endpoints
│   └── notes.py                 # Notes endpoints
│
└── models/
    ├── clinical_note.py         # Clinical notes model
    └── alert.py                 # Alerts model

# Frontend (separate repo or monorepo)
frontend/
├── src/
│   ├── components/
│   │   ├── common/              # Shared components
│   │   ├── charts/              # Visualization components
│   │   ├── timeline/            # Timeline components
│   │   └── notes/               # Note editor components
│   │
│   ├── pages/
│   │   ├── PatientList/
│   │   ├── PatientDetail/
│   │   └── Analytics/
│   │
│   ├── hooks/                   # Custom React hooks
│   ├── services/                # API services
│   └── types/                   # TypeScript types
│
├── package.json
└── tsconfig.json
```

### 5.3 Database Schema Extensions

```sql
-- Clinical notes
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    session_id UUID REFERENCES voice_sessions(id),

    -- Note type
    note_type VARCHAR(20) NOT NULL,  -- 'soap', 'dap', 'progress', 'intake', 'discharge'

    -- SOAP format
    subjective TEXT,
    objective TEXT,
    assessment TEXT,
    plan TEXT,

    -- General content (for non-SOAP notes)
    content TEXT,

    -- AI-assisted
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_suggestions JSONB,  -- AI-provided suggestions for each section

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft, final, amended
    finalized_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Note amendments (for audit trail)
CREATE TABLE note_amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID REFERENCES clinical_notes(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),

    -- Change tracking
    field_changed VARCHAR(50),
    previous_value TEXT,
    new_value TEXT,
    reason TEXT,

    -- Metadata
    amended_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clinician alerts
CREATE TABLE clinician_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    clinician_id UUID REFERENCES clinicians(id),
    session_id UUID REFERENCES voice_sessions(id),

    -- Alert info
    alert_type VARCHAR(50) NOT NULL,
    -- Types: 'high_signal', 'hypothesis_change', 'pattern_detected',
    --        'follow_up_due', 'data_gap', 'anomaly'

    priority VARCHAR(20) DEFAULT 'normal',  -- low, normal, high, urgent
    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Linked evidence
    evidence JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active, acknowledged, resolved, dismissed
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dashboard preferences
CREATE TABLE clinician_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinician_id UUID REFERENCES clinicians(id) UNIQUE,

    -- Display preferences
    default_view VARCHAR(50) DEFAULT 'overview',
    timeline_zoom VARCHAR(20) DEFAULT 'month',
    chart_preferences JSONB,

    -- Notification preferences
    email_alerts BOOLEAN DEFAULT TRUE,
    alert_threshold VARCHAR(20) DEFAULT 'normal',  -- low, normal, high (minimum priority to notify)

    -- Note preferences
    default_note_type VARCHAR(20) DEFAULT 'soap',

    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_notes_patient ON clinical_notes(patient_id);
CREATE INDEX idx_notes_session ON clinical_notes(session_id);
CREATE INDEX idx_alerts_clinician ON clinician_alerts(clinician_id);
CREATE INDEX idx_alerts_status ON clinician_alerts(status);
CREATE INDEX idx_alerts_priority ON clinician_alerts(priority);
```

### 5.4 Dashboard View Aggregations

```python
# src/dashboard/views.py
from uuid import UUID
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.patient import Patient
from src.models.session import VoiceSession
from src.models.hypothesis import DiagnosticHypothesis
from src.models.alert import ClinicianAlert

class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patient_overview(self, patient_id: UUID) -> dict:
        """
        Get comprehensive patient overview for dashboard.

        This is the first thing a clinician sees when opening a patient.
        """
        patient = await self.db.get(Patient, patient_id)

        return {
            "patient": self._format_patient(patient),
            "status_summary": await self._get_status_summary(patient_id),
            "key_metrics": await self._get_key_metrics(patient_id),
            "recent_activity": await self._get_recent_activity(patient_id),
            "action_items": await self._get_action_items(patient_id),
            "current_hypotheses": await self._get_hypothesis_cards(patient_id)
        }

    async def _get_status_summary(self, patient_id: UUID) -> dict:
        """Generate natural language status summary."""
        # Get latest data
        last_session = await self._get_last_session(patient_id)
        active_alerts = await self._get_active_alerts_count(patient_id)
        hypothesis_trend = await self._get_hypothesis_trend(patient_id)

        from src.llm.openrouter import OpenRouterClient
        llm = OpenRouterClient()

        result = await llm.complete([
            {"role": "system", "content": "Generate a brief 2-3 sentence clinical status summary."},
            {"role": "user", "content": f"""
Last session: {last_session}
Active alerts: {active_alerts}
Hypothesis trends: {hypothesis_trend}

Write a brief, professional summary of current status."""}
        ])

        return {
            "summary": result["choices"][0]["message"]["content"],
            "last_updated": last_session.get("date") if last_session else None,
            "alert_count": active_alerts
        }

    async def _get_key_metrics(self, patient_id: UUID) -> list[dict]:
        """
        Get 4-6 key metrics for dashboard cards.

        Each metric shows current value, trend, and context.
        """
        metrics = []

        # Sessions this month
        session_count = await self._count_sessions_in_period(patient_id, days=30)
        metrics.append({
            "id": "sessions",
            "label": "Sessions (30d)",
            "value": session_count,
            "trend": await self._get_session_trend(patient_id),
            "context": "Check-ins and assessments"
        })

        # Engagement
        avg_duration = await self._get_avg_session_duration(patient_id, days=30)
        metrics.append({
            "id": "engagement",
            "label": "Avg Session",
            "value": f"{avg_duration} min",
            "trend": None,
            "context": "Average session duration"
        })

        # Primary hypothesis strength
        primary_hyp = await self._get_primary_hypothesis(patient_id)
        if primary_hyp:
            metrics.append({
                "id": "primary_hypothesis",
                "label": primary_hyp["condition_name"],
                "value": f"{primary_hyp['evidence_strength']:.0%}",
                "trend": primary_hyp["trend"],
                "context": f"Evidence strength (±{primary_hyp['uncertainty']:.0%})"
            })

        # Domain with biggest change
        biggest_change = await self._get_biggest_domain_change(patient_id, days=30)
        if biggest_change:
            metrics.append({
                "id": "domain_change",
                "label": biggest_change["domain_name"],
                "value": f"{biggest_change['delta']:+.0%}",
                "trend": "up" if biggest_change["delta"] > 0 else "down",
                "context": "Largest change in 30 days"
            })

        return metrics

    async def _get_action_items(self, patient_id: UUID) -> list[dict]:
        """
        Get prioritized action items for the clinician.

        Things that need attention or follow-up.
        """
        items = []

        # Active alerts
        alerts = await self._get_active_alerts(patient_id, limit=5)
        for alert in alerts:
            items.append({
                "type": "alert",
                "priority": alert.priority,
                "title": alert.title,
                "description": alert.description,
                "action": "Review",
                "link": f"/patients/{patient_id}/alerts/{alert.id}"
            })

        # Pending note reviews
        pending_notes = await self._get_pending_notes(patient_id)
        if pending_notes:
            items.append({
                "type": "notes",
                "priority": "normal",
                "title": f"{len(pending_notes)} notes pending review",
                "description": "AI-generated notes awaiting finalization",
                "action": "Review notes",
                "link": f"/patients/{patient_id}/notes"
            })

        # Overdue follow-up
        days_since_session = await self._get_days_since_last_session(patient_id)
        if days_since_session > 14:
            items.append({
                "type": "follow_up",
                "priority": "high" if days_since_session > 30 else "normal",
                "title": f"No session in {days_since_session} days",
                "description": "Consider scheduling a check-in",
                "action": "Schedule session",
                "link": f"/patients/{patient_id}/sessions/new"
            })

        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
        items.sort(key=lambda x: priority_order.get(x["priority"], 2))

        return items

    async def _get_hypothesis_cards(self, patient_id: UUID) -> list[dict]:
        """
        Get hypothesis information formatted for dashboard cards.

        Shows current strength, uncertainty band, and trend.
        """
        query = select(DiagnosticHypothesis).where(
            DiagnosticHypothesis.patient_id == patient_id
        ).order_by(DiagnosticHypothesis.evidence_strength.desc())

        result = await self.db.execute(query)
        hypotheses = result.scalars().all()

        cards = []
        for h in hypotheses:
            cards.append({
                "condition_code": h.condition_code,
                "condition_name": h.condition_name,
                "evidence_strength": h.evidence_strength,
                "uncertainty": h.uncertainty,
                "confidence_low": max(0, h.evidence_strength - h.uncertainty),
                "confidence_high": min(1, h.evidence_strength + h.uncertainty),
                "trend": h.trend,
                "supporting_signals": h.supporting_signals,
                "contradicting_signals": h.contradicting_signals,
                "last_updated": h.last_updated_at.isoformat(),
                "explanation": h.explanation
            })

        return cards

    async def get_patient_list(
        self,
        clinician_id: UUID,
        sort_by: str = "last_activity",
        filter_status: str = None
    ) -> list[dict]:
        """
        Get patient list for clinician dashboard.

        Includes priority indicators and quick stats.
        """
        query = select(Patient).where(
            Patient.clinician_id == clinician_id
        )

        if filter_status:
            query = query.where(Patient.status == filter_status)

        result = await self.db.execute(query)
        patients = result.scalars().all()

        patient_list = []
        for patient in patients:
            # Get quick stats
            alert_count = await self._get_active_alerts_count(patient.id)
            last_session = await self._get_last_session_date(patient.id)
            session_count = await self._count_sessions_in_period(patient.id, days=30)

            patient_list.append({
                "id": str(patient.id),
                "name": f"{patient.first_name} {patient.last_name}",
                "status": patient.status,
                "intake_date": patient.intake_date.isoformat() if patient.intake_date else None,
                "last_session": last_session.isoformat() if last_session else None,
                "sessions_30d": session_count,
                "alert_count": alert_count,
                "needs_attention": alert_count > 0 or (last_session and (date.today() - last_session).days > 14)
            })

        # Sort
        if sort_by == "last_activity":
            patient_list.sort(key=lambda x: x["last_session"] or "", reverse=True)
        elif sort_by == "alerts":
            patient_list.sort(key=lambda x: x["alert_count"], reverse=True)
        elif sort_by == "name":
            patient_list.sort(key=lambda x: x["name"])

        return patient_list
```

### 5.5 Clinical Note Generation

```python
# src/dashboard/notes.py
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.clinical_note import ClinicalNote
from src.models.session import VoiceSession
from src.llm.openrouter import OpenRouterClient

class ClinicalNoteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def generate_soap_note(
        self,
        session_id: UUID,
        clinician_id: UUID
    ) -> ClinicalNote:
        """
        Generate a SOAP note from a session.

        SOAP = Subjective, Objective, Assessment, Plan
        """
        # Get session data
        session = await self.db.get(VoiceSession, session_id)
        transcript = await self._get_transcript(session_id)
        signals = await self._get_session_signals(session_id)
        summary = await self._get_session_summary(session_id)

        # Generate each section
        sections = await self._generate_soap_sections(
            session=session,
            transcript=transcript,
            signals=signals,
            summary=summary
        )

        # Create note
        note = ClinicalNote(
            patient_id=session.patient_id,
            clinician_id=clinician_id,
            session_id=session_id,
            note_type="soap",
            subjective=sections["subjective"],
            objective=sections["objective"],
            assessment=sections["assessment"],
            plan=sections["plan"],
            ai_generated=True,
            ai_suggestions=sections.get("suggestions"),
            status="draft"
        )

        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)

        return note

    async def _generate_soap_sections(
        self,
        session,
        transcript: str,
        signals: list,
        summary: str
    ) -> dict:
        """Generate each SOAP section using LLM."""

        prompt = f"""Generate a clinical SOAP note from this voice session.

SESSION TYPE: {session.session_type}
DURATION: {session.duration_seconds // 60} minutes

TRANSCRIPT:
{transcript[:5000]}  # Truncate for context limits

EXTRACTED SIGNALS:
{signals}

SESSION SUMMARY:
{summary}

Generate each SOAP section following clinical documentation standards:

SUBJECTIVE: Patient's reported symptoms, concerns, and experiences in their own words. Include relevant quotes.

OBJECTIVE: Observable findings, extracted signals, behavioral observations. Be specific and measurable where possible.

ASSESSMENT: Clinical interpretation of findings. Note patterns, changes from baseline, and areas of concern. Do NOT make diagnoses - use phrases like "pattern consistent with..." or "evidence suggestive of...".

PLAN: Recommended next steps, follow-up items, areas to explore in future sessions.

Return as JSON:
{{
    "subjective": "...",
    "objective": "...",
    "assessment": "...",
    "plan": "...",
    "suggestions": {{
        "subjective": ["alternative phrasing or additions"],
        "objective": ["additional observations to consider"],
        "assessment": ["other interpretations to consider"],
        "plan": ["additional recommendations"]
    }}
}}"""

        return await self.llm.complete_json([
            {"role": "system", "content": "You are a clinical documentation assistant. Generate professional, accurate clinical notes."},
            {"role": "user", "content": prompt}
        ])

    async def finalize_note(
        self,
        note_id: UUID,
        clinician_id: UUID,
        edits: dict = None
    ) -> ClinicalNote:
        """Finalize a clinical note after clinician review."""
        note = await self.db.get(ClinicalNote, note_id)

        # Apply edits if provided
        if edits:
            for field, value in edits.items():
                if hasattr(note, field) and getattr(note, field) != value:
                    # Record amendment
                    await self._record_amendment(
                        note_id=note_id,
                        clinician_id=clinician_id,
                        field=field,
                        previous=getattr(note, field),
                        new=value
                    )
                    setattr(note, field, value)

        note.status = "final"
        note.finalized_at = datetime.utcnow()
        await self.db.commit()

        return note

    async def export_for_ehr(
        self,
        note_id: UUID,
        format: str = "text"
    ) -> str:
        """Export note in format suitable for EHR integration."""
        note = await self.db.get(ClinicalNote, note_id)

        if format == "text":
            return self._format_as_text(note)
        elif format == "hl7":
            return self._format_as_hl7(note)
        elif format == "fhir":
            return self._format_as_fhir(note)

    def _format_as_text(self, note: ClinicalNote) -> str:
        """Format note as plain text."""
        return f"""CLINICAL NOTE
Date: {note.created_at.strftime('%Y-%m-%d %H:%M')}
Type: {note.note_type.upper()}
Status: {note.status}

SUBJECTIVE:
{note.subjective}

OBJECTIVE:
{note.objective}

ASSESSMENT:
{note.assessment}

PLAN:
{note.plan}
"""
```

### 5.6 Alert Generation

```python
# src/dashboard/alerts.py
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.alert import ClinicianAlert

class AlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_alert(
        self,
        patient_id: UUID,
        clinician_id: UUID,
        alert_type: str,
        title: str,
        description: str,
        priority: str = "normal",
        session_id: UUID = None,
        evidence: dict = None
    ) -> ClinicianAlert:
        """Create a new alert for clinician review."""
        alert = ClinicianAlert(
            patient_id=patient_id,
            clinician_id=clinician_id,
            session_id=session_id,
            alert_type=alert_type,
            priority=priority,
            title=title,
            description=description,
            evidence=evidence,
            status="active"
        )

        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)

        # Send notification if high priority
        if priority in ["high", "urgent"]:
            await self._send_notification(alert)

        return alert

    async def generate_session_alerts(
        self,
        session_id: UUID,
        signals: list[dict],
        hypotheses: dict
    ) -> list[ClinicianAlert]:
        """Generate alerts from session analysis."""
        alerts = []

        # High significance signals
        for signal in signals:
            if signal.get("clinical_significance") == "high":
                alert = await self.create_alert(
                    patient_id=signal["patient_id"],
                    clinician_id=signal["clinician_id"],
                    alert_type="high_signal",
                    title=f"High significance: {signal['signal_name']}",
                    description=f"Detected during session: {signal['evidence'][:200]}",
                    priority="high",
                    session_id=session_id,
                    evidence={"signal": signal}
                )
                alerts.append(alert)

        # Hypothesis threshold crossed
        for hyp in hypotheses.get("hypotheses", []):
            if hyp.get("evidence_strength", 0) > 0.7:
                alert = await self.create_alert(
                    patient_id=hypotheses["patient_id"],
                    clinician_id=hypotheses["clinician_id"],
                    alert_type="hypothesis_change",
                    title=f"Strong evidence for {hyp['condition_name']}",
                    description=hyp.get("explanation", "Evidence threshold exceeded"),
                    priority="normal",
                    session_id=session_id,
                    evidence={"hypothesis": hyp}
                )
                alerts.append(alert)

        # Data gaps identified
        for gap in hypotheses.get("data_gaps", []):
            alert = await self.create_alert(
                patient_id=hypotheses["patient_id"],
                clinician_id=hypotheses["clinician_id"],
                alert_type="data_gap",
                title=f"More information needed: {gap}",
                description=f"Consider exploring this area in the next session",
                priority="low",
                session_id=session_id
            )
            alerts.append(alert)

        return alerts

    async def acknowledge_alert(
        self,
        alert_id: UUID,
        clinician_id: UUID
    ):
        """Mark alert as acknowledged."""
        alert = await self.db.get(ClinicianAlert, alert_id)
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        await self.db.commit()

    async def resolve_alert(
        self,
        alert_id: UUID,
        clinician_id: UUID,
        resolution_note: str = None
    ):
        """Mark alert as resolved."""
        alert = await self.db.get(ClinicianAlert, alert_id)
        alert.status = "resolved"
        alert.resolved_at = datetime.utcnow()
        if resolution_note:
            alert.evidence = {
                **(alert.evidence or {}),
                "resolution_note": resolution_note
            }
        await self.db.commit()
```

### 5.7 Visualization Data Endpoints

```python
# src/api/dashboard.py
from fastapi import APIRouter, Depends
from uuid import UUID
from src.dashboard.views import DashboardService
from src.api.deps import get_db, get_current_clinician

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/patients")
async def get_patient_list(
    sort_by: str = "last_activity",
    filter_status: str = None,
    db = Depends(get_db),
    clinician = Depends(get_current_clinician)
):
    """Get patient list for dashboard."""
    service = DashboardService(db)
    return await service.get_patient_list(
        clinician_id=clinician.id,
        sort_by=sort_by,
        filter_status=filter_status
    )

@router.get("/patients/{patient_id}/overview")
async def get_patient_overview(
    patient_id: UUID,
    db = Depends(get_db),
    clinician = Depends(get_current_clinician)
):
    """Get patient overview for dashboard."""
    service = DashboardService(db)
    return await service.get_patient_overview(patient_id)

@router.get("/patients/{patient_id}/domain-trends")
async def get_domain_trends(
    patient_id: UUID,
    days: int = 90,
    db = Depends(get_db)
):
    """
    Get domain score trends for charting.

    Returns time-series data for each domain.
    """
    # Return format optimized for chart libraries
    return {
        "domains": [
            {
                "code": "social_reciprocity",
                "name": "Social Reciprocity",
                "data": [
                    {"date": "2024-01-01", "score": 0.6, "confidence": 0.7},
                    {"date": "2024-01-15", "score": 0.55, "confidence": 0.75},
                    # ...
                ]
            }
        ]
    }

@router.get("/patients/{patient_id}/hypothesis-history")
async def get_hypothesis_history(
    patient_id: UUID,
    condition_code: str = None,
    db = Depends(get_db)
):
    """
    Get hypothesis strength over time.

    Returns time-series data for hypothesis tracking.
    """
    return {
        "hypotheses": [
            {
                "condition_code": "asd_level_1",
                "condition_name": "ASD Level 1",
                "data": [
                    {
                        "date": "2024-01-01",
                        "strength": 0.4,
                        "uncertainty": 0.3,
                        "session_id": "..."
                    }
                ]
            }
        ]
    }

@router.get("/patients/{patient_id}/session-frequency")
async def get_session_frequency(
    patient_id: UUID,
    period: str = "month",  # week, month, quarter
    db = Depends(get_db)
):
    """Get session frequency data for charting."""
    return {
        "periods": [
            {"label": "Jan 2024", "count": 4, "total_minutes": 120},
            {"label": "Feb 2024", "count": 3, "total_minutes": 90}
        ]
    }
```

### 5.8 API Endpoints (Phase 5)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/dashboard/patients` | List clinician's patients |
| GET | `/api/v1/dashboard/patients/{id}/overview` | Patient overview |
| GET | `/api/v1/dashboard/patients/{id}/domain-trends` | Domain score trends |
| GET | `/api/v1/dashboard/patients/{id}/hypothesis-history` | Hypothesis history |
| GET | `/api/v1/patients/{id}/notes` | List clinical notes |
| POST | `/api/v1/sessions/{id}/notes/generate` | Generate SOAP note |
| PUT | `/api/v1/notes/{id}` | Update note |
| POST | `/api/v1/notes/{id}/finalize` | Finalize note |
| GET | `/api/v1/notes/{id}/export` | Export for EHR |
| GET | `/api/v1/alerts` | List clinician alerts |
| POST | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| POST | `/api/v1/alerts/{id}/resolve` | Resolve alert |

### 5.9 Frontend Component Specifications

```typescript
// frontend/src/types/dashboard.ts

export interface PatientOverview {
  patient: Patient;
  statusSummary: {
    summary: string;
    lastUpdated: string | null;
    alertCount: number;
  };
  keyMetrics: MetricCard[];
  recentActivity: TimelineEvent[];
  actionItems: ActionItem[];
  currentHypotheses: HypothesisCard[];
}

export interface MetricCard {
  id: string;
  label: string;
  value: string | number;
  trend: 'up' | 'down' | 'stable' | null;
  context: string;
}

export interface HypothesisCard {
  conditionCode: string;
  conditionName: string;
  evidenceStrength: number;  // 0-1
  uncertainty: number;       // 0-1
  confidenceLow: number;
  confidenceHigh: number;
  trend: 'increasing' | 'stable' | 'decreasing';
  supportingSignals: number;
  contradictingSignals: number;
  lastUpdated: string;
  explanation: string;
}

export interface ActionItem {
  type: 'alert' | 'notes' | 'follow_up';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  title: string;
  description: string;
  action: string;
  link: string;
}

// Chart data types
export interface DomainTrendData {
  domains: {
    code: string;
    name: string;
    data: {
      date: string;
      score: number;
      confidence: number;
    }[];
  }[];
}

export interface HypothesisHistoryData {
  hypotheses: {
    conditionCode: string;
    conditionName: string;
    data: {
      date: string;
      strength: number;
      uncertainty: number;
      sessionId: string;
    }[];
  }[];
}
```

### 5.10 Key Visualization Components

```typescript
// Hypothesis Gauge Component
// Shows evidence strength with uncertainty band

interface HypothesisGaugeProps {
  conditionName: string;
  strength: number;      // 0-1, center of gauge
  uncertainty: number;   // 0-1, width of uncertainty band
  trend: 'increasing' | 'stable' | 'decreasing';
}

// Timeline Component
// Zoomable, filterable patient timeline

interface TimelineProps {
  events: TimelineEvent[];
  onEventClick: (event: TimelineEvent) => void;
  zoomLevel: 'week' | 'month' | 'quarter' | 'year';
  filters: {
    eventTypes: string[];
    significanceThreshold: 'low' | 'normal' | 'high';
  };
}

// Domain Radar Chart
// Shows current scores across all domains

interface DomainRadarProps {
  domains: {
    code: string;
    name: string;
    score: number;
    previousScore?: number;  // For comparison
  }[];
}

// Trend Sparkline
// Small inline trend indicator

interface SparklineProps {
  data: number[];
  trend: 'up' | 'down' | 'stable';
  width: number;
  height: number;
}
```

## Acceptance Criteria

- [ ] Patient list view with filtering and sorting
- [ ] Patient overview dashboard rendering
- [ ] Key metrics cards displaying correctly
- [ ] Action items prioritized and linked
- [ ] Hypothesis cards with uncertainty bands
- [ ] Domain trend charts working
- [ ] Timeline visualization zoomable/filterable
- [ ] SOAP note generation from sessions
- [ ] Note editing and finalization flow
- [ ] Note export for EHR integration
- [ ] Alert system generating notifications
- [ ] Alert acknowledgment and resolution

## UX Guidelines

1. **First 30 seconds**: Clinician should understand patient status immediately
2. **Uncertainty is visible**: Never hide confidence intervals
3. **Evidence accessible**: Click through to see supporting data
4. **Editable everywhere**: AI-generated content is always editable
5. **Audit visible**: Show who changed what and when
6. **Mobile-responsive**: Basic functionality on tablets

## Next Phase

Once Phase 5 is complete, proceed to [Phase 6: Production Readiness](./phase-6-production.md).
