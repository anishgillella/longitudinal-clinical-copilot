# Phase 4: Longitudinal Memory & Context

## Objective

Build the longitudinal memory system that maintains patient context across months or years, enables cross-session reasoning, constructs patient timelines, and detects patterns over time.

## Prerequisites

- Phase 3 completed (clinical assessment engine, signal extraction)
- Understanding of temporal data patterns
- PostgreSQL with proper indexing for time-series queries

## Core Concept: Mental Health Longitudinal Memory Graph

The memory system operates in layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    QUERY LAYER                               │
│    "What changed after medication X?" / "Pattern since..."  │
├─────────────────────────────────────────────────────────────┤
│                 TEMPORAL REASONING                           │
│         Trend Detection • Anomaly Detection • Deltas         │
├─────────────────────────────────────────────────────────────┤
│                 SEMANTIC SUMMARIES                           │
│      Session Summaries • Monthly Rollups • Yearly Snapshots │
├─────────────────────────────────────────────────────────────┤
│                  DERIVED FEATURES                            │
│    Emotion Embeddings • Symptom Scores • Behavioral Markers │
├─────────────────────────────────────────────────────────────┤
│                    RAW DATA                                  │
│           Audio Recordings • Full Transcripts                │
└─────────────────────────────────────────────────────────────┘
```

## Deliverables

### 4.1 Extended Project Structure

```
src/
├── memory/                      # Longitudinal memory system
│   ├── __init__.py
│   ├── timeline.py              # Timeline construction
│   ├── context.py               # Context retrieval
│   ├── patterns.py              # Pattern detection
│   ├── embeddings.py            # Semantic embeddings
│   └── rollups.py               # Summary rollups
│
├── temporal/                    # Temporal reasoning
│   ├── __init__.py
│   ├── trends.py                # Trend detection
│   ├── anomalies.py             # Anomaly detection
│   ├── deltas.py                # Change detection
│   └── windows.py               # Time window utilities
│
└── models/
    ├── timeline.py              # Timeline events (new)
    ├── embedding.py             # Embeddings storage (new)
    └── rollup.py                # Summary rollups (new)
```

### 4.2 Database Schema Extensions

```sql
-- Patient timeline events
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Event timing
    event_date DATE NOT NULL,
    event_timestamp TIMESTAMP WITH TIME ZONE,

    -- Event classification
    event_type VARCHAR(50) NOT NULL,
    -- Types: 'session', 'symptom_change', 'medication', 'life_event',
    --        'milestone', 'clinician_note', 'hypothesis_change'

    event_subtype VARCHAR(50),
    title VARCHAR(255) NOT NULL,
    description TEXT,

    -- Importance
    significance VARCHAR(20) DEFAULT 'normal',  -- low, normal, high, critical
    is_pinned BOOLEAN DEFAULT FALSE,  -- Clinician-pinned for reference

    -- Linked data
    session_id UUID REFERENCES voice_sessions(id),
    source_type VARCHAR(50),  -- 'ai_extracted', 'clinician_entry', 'patient_reported'
    source_id UUID,  -- Reference to source record

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES clinicians(id)
);

-- Semantic embeddings for similarity search
CREATE TABLE semantic_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Source
    source_type VARCHAR(50) NOT NULL,  -- 'session_summary', 'signal', 'note'
    source_id UUID NOT NULL,
    content_hash VARCHAR(64),  -- For deduplication

    -- Embedding
    embedding vector(1536),  -- OpenAI embedding dimension
    model_version VARCHAR(50),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Session summaries (hierarchical)
CREATE TABLE session_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Content
    summary_type VARCHAR(20) NOT NULL,  -- 'brief', 'detailed', 'clinical'
    content TEXT NOT NULL,

    -- Key extractions
    key_topics JSONB,  -- ["topic1", "topic2"]
    emotional_tone VARCHAR(50),
    notable_quotes JSONB,  -- ["quote1", "quote2"]

    -- Clinical
    clinical_observations TEXT,
    follow_up_suggestions JSONB,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50)
);

-- Periodic rollups (weekly, monthly, yearly)
CREATE TABLE summary_rollups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Period
    rollup_type VARCHAR(20) NOT NULL,  -- 'weekly', 'monthly', 'quarterly', 'yearly'
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Content
    summary TEXT NOT NULL,

    -- Metrics for the period
    session_count INTEGER,
    total_duration_minutes INTEGER,

    -- Trend data
    domain_trends JSONB,
    -- {domain_code: {start_score, end_score, trend: 'improving'|'stable'|'declining'}}

    hypothesis_changes JSONB,
    -- [{condition, previous_strength, current_strength, direction}]

    -- Key events
    significant_events JSONB,
    -- [{date, type, description}]

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cross-session patterns
CREATE TABLE detected_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Pattern info
    pattern_type VARCHAR(50) NOT NULL,
    -- Types: 'recurring_theme', 'behavioral_cycle', 'trigger_response',
    --        'symptom_progression', 'communication_pattern'

    pattern_name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Evidence
    first_detected_at TIMESTAMP WITH TIME ZONE,
    occurrence_count INTEGER DEFAULT 1,
    supporting_sessions JSONB,  -- [session_id, session_id, ...]
    evidence_snippets JSONB,    -- [{session_id, quote, timestamp}]

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    confidence FLOAT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for temporal queries
CREATE INDEX idx_timeline_patient_date ON timeline_events(patient_id, event_date DESC);
CREATE INDEX idx_timeline_type ON timeline_events(event_type);
CREATE INDEX idx_embeddings_patient ON semantic_embeddings(patient_id);
CREATE INDEX idx_summaries_session ON session_summaries(session_id);
CREATE INDEX idx_rollups_patient_period ON summary_rollups(patient_id, period_start);
CREATE INDEX idx_patterns_patient ON detected_patterns(patient_id);

-- Enable vector similarity search (requires pgvector extension)
CREATE INDEX idx_embeddings_vector ON semantic_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### 4.3 Timeline Construction

```python
# src/memory/timeline.py
from uuid import UUID
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.models.timeline import TimelineEvent
from src.models.session import VoiceSession
from src.models.hypothesis import DiagnosticHypothesis

class TimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_patient_timeline(
        self,
        patient_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_types: Optional[list[str]] = None
    ) -> list[dict]:
        """
        Build comprehensive patient timeline.

        Aggregates:
        - Voice sessions
        - Symptom changes
        - Medication changes
        - Life events
        - Hypothesis changes
        - Clinician notes
        """
        query = select(TimelineEvent).where(
            TimelineEvent.patient_id == patient_id
        ).order_by(TimelineEvent.event_date.desc())

        if start_date:
            query = query.where(TimelineEvent.event_date >= start_date)
        if end_date:
            query = query.where(TimelineEvent.event_date <= end_date)
        if event_types:
            query = query.where(TimelineEvent.event_type.in_(event_types))

        result = await self.db.execute(query)
        events = result.scalars().all()

        return [self._format_event(e) for e in events]

    async def add_session_to_timeline(
        self,
        session_id: UUID,
        patient_id: UUID,
        summary: str,
        key_topics: list[str],
        significance: str = "normal"
    ):
        """Add a completed session to the timeline."""
        session = await self.db.get(VoiceSession, session_id)

        event = TimelineEvent(
            patient_id=patient_id,
            event_date=session.started_at.date(),
            event_timestamp=session.started_at,
            event_type="session",
            event_subtype=session.session_type,
            title=f"{session.session_type.title()} Session",
            description=summary,
            significance=significance,
            session_id=session_id,
            source_type="ai_extracted"
        )

        self.db.add(event)
        await self.db.commit()
        return event

    async def add_hypothesis_change_to_timeline(
        self,
        patient_id: UUID,
        hypothesis: DiagnosticHypothesis,
        previous_strength: float,
        session_id: Optional[UUID] = None
    ):
        """Record significant hypothesis changes in timeline."""
        delta = hypothesis.evidence_strength - previous_strength
        direction = "increased" if delta > 0 else "decreased"
        significance = "high" if abs(delta) > 0.2 else "normal"

        event = TimelineEvent(
            patient_id=patient_id,
            event_date=date.today(),
            event_timestamp=datetime.utcnow(),
            event_type="hypothesis_change",
            event_subtype=hypothesis.condition_code,
            title=f"{hypothesis.condition_name} evidence {direction}",
            description=(
                f"Evidence strength changed from {previous_strength:.2f} to "
                f"{hypothesis.evidence_strength:.2f} ({delta:+.2f})"
            ),
            significance=significance,
            session_id=session_id,
            source_type="ai_extracted"
        )

        self.db.add(event)
        await self.db.commit()

    async def add_life_event(
        self,
        patient_id: UUID,
        event_date: date,
        title: str,
        description: str,
        event_subtype: str = "general",
        clinician_id: Optional[UUID] = None
    ):
        """Add clinician-entered or patient-reported life event."""
        event = TimelineEvent(
            patient_id=patient_id,
            event_date=event_date,
            event_type="life_event",
            event_subtype=event_subtype,
            title=title,
            description=description,
            source_type="clinician_entry" if clinician_id else "patient_reported",
            created_by=clinician_id
        )

        self.db.add(event)
        await self.db.commit()
        return event

    async def get_context_window(
        self,
        patient_id: UUID,
        reference_date: date,
        days_before: int = 30,
        days_after: int = 0
    ) -> list[dict]:
        """Get timeline events within a context window around a date."""
        start = reference_date - timedelta(days=days_before)
        end = reference_date + timedelta(days=days_after)

        return await self.build_patient_timeline(
            patient_id, start_date=start, end_date=end
        )

    def _format_event(self, event: TimelineEvent) -> dict:
        return {
            "id": str(event.id),
            "date": event.event_date.isoformat(),
            "timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
            "type": event.event_type,
            "subtype": event.event_subtype,
            "title": event.title,
            "description": event.description,
            "significance": event.significance,
            "is_pinned": event.is_pinned,
            "session_id": str(event.session_id) if event.session_id else None
        }
```

### 4.4 Context Retrieval System

```python
# src/memory/context.py
from uuid import UUID
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.memory.timeline import TimelineService
from src.memory.embeddings import EmbeddingService
from src.llm.openrouter import OpenRouterClient

class ContextRetriever:
    """
    Retrieves relevant context for a patient interaction.

    Uses multiple strategies:
    1. Temporal: Recent sessions and events
    2. Semantic: Similar past discussions
    3. Clinical: Relevant signals and hypotheses
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.timeline = TimelineService(db)
        self.embeddings = EmbeddingService(db)
        self.llm = OpenRouterClient()

    async def get_session_context(
        self,
        patient_id: UUID,
        session_type: str,
        focus_areas: Optional[list[str]] = None
    ) -> dict:
        """
        Get comprehensive context for starting a new session.

        Returns context optimized for the voice agent.
        """
        context = {
            "patient_summary": await self._get_patient_summary(patient_id),
            "recent_sessions": await self._get_recent_sessions(patient_id, limit=3),
            "current_hypotheses": await self._get_current_hypotheses(patient_id),
            "active_patterns": await self._get_active_patterns(patient_id),
            "recent_changes": await self._get_recent_changes(patient_id),
            "suggested_topics": []
        }

        # Add focus-area specific context
        if focus_areas:
            context["focus_context"] = await self._get_focus_context(
                patient_id, focus_areas
            )

        # Generate suggested topics based on context
        context["suggested_topics"] = await self._generate_topic_suggestions(context)

        return context

    async def _get_patient_summary(self, patient_id: UUID) -> dict:
        """Get current patient summary."""
        # Get most recent monthly rollup
        from src.models.rollup import SummaryRollup
        from sqlalchemy import select

        query = select(SummaryRollup).where(
            SummaryRollup.patient_id == patient_id,
            SummaryRollup.rollup_type == "monthly"
        ).order_by(SummaryRollup.period_end.desc()).limit(1)

        result = await self.db.execute(query)
        rollup = result.scalar_one_or_none()

        if rollup:
            return {
                "summary": rollup.summary,
                "period": f"{rollup.period_start} to {rollup.period_end}",
                "session_count": rollup.session_count,
                "domain_trends": rollup.domain_trends
            }

        return {"summary": "No summary available yet."}

    async def _get_recent_sessions(self, patient_id: UUID, limit: int = 3) -> list:
        """Get summaries of recent sessions."""
        from src.models.session import VoiceSession
        from src.models.summary import SessionSummary
        from sqlalchemy import select

        query = select(VoiceSession, SessionSummary).join(
            SessionSummary, VoiceSession.id == SessionSummary.session_id
        ).where(
            VoiceSession.patient_id == patient_id,
            VoiceSession.status == "completed"
        ).order_by(VoiceSession.ended_at.desc()).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "date": session.ended_at.date().isoformat(),
                "type": session.session_type,
                "summary": summary.content,
                "key_topics": summary.key_topics,
                "emotional_tone": summary.emotional_tone
            }
            for session, summary in rows
        ]

    async def _get_current_hypotheses(self, patient_id: UUID) -> list:
        """Get current diagnostic hypotheses."""
        from src.models.hypothesis import DiagnosticHypothesis
        from sqlalchemy import select

        query = select(DiagnosticHypothesis).where(
            DiagnosticHypothesis.patient_id == patient_id
        ).order_by(DiagnosticHypothesis.evidence_strength.desc())

        result = await self.db.execute(query)
        hypotheses = result.scalars().all()

        return [
            {
                "condition": h.condition_name,
                "evidence_strength": h.evidence_strength,
                "uncertainty": h.uncertainty,
                "trend": h.trend,
                "explanation": h.explanation
            }
            for h in hypotheses
        ]

    async def _get_active_patterns(self, patient_id: UUID) -> list:
        """Get active detected patterns."""
        from src.models.pattern import DetectedPattern
        from sqlalchemy import select

        query = select(DetectedPattern).where(
            DetectedPattern.patient_id == patient_id,
            DetectedPattern.is_active == True
        ).order_by(DetectedPattern.occurrence_count.desc())

        result = await self.db.execute(query)
        patterns = result.scalars().all()

        return [
            {
                "type": p.pattern_type,
                "name": p.pattern_name,
                "description": p.description,
                "occurrences": p.occurrence_count,
                "confidence": p.confidence
            }
            for p in patterns
        ]

    async def _get_recent_changes(self, patient_id: UUID, days: int = 14) -> list:
        """Get significant changes in the last N days."""
        start_date = date.today() - timedelta(days=days)

        events = await self.timeline.build_patient_timeline(
            patient_id,
            start_date=start_date,
            event_types=["hypothesis_change", "symptom_change", "life_event"]
        )

        return [e for e in events if e["significance"] in ["high", "critical"]]

    async def _get_focus_context(
        self,
        patient_id: UUID,
        focus_areas: list[str]
    ) -> dict:
        """Get context specific to focus areas."""
        focus_context = {}

        for area in focus_areas:
            # Get semantically similar past discussions
            similar = await self.embeddings.find_similar(
                patient_id=patient_id,
                query_text=area,
                limit=3
            )
            focus_context[area] = similar

        return focus_context

    async def _generate_topic_suggestions(self, context: dict) -> list[str]:
        """Generate suggested topics based on context."""
        prompt = f"""Based on this patient context, suggest 3-5 topics to explore in the next session.

Recent Sessions:
{context.get('recent_sessions', [])}

Current Hypotheses:
{context.get('current_hypotheses', [])}

Active Patterns:
{context.get('active_patterns', [])}

Recent Changes:
{context.get('recent_changes', [])}

Suggest topics that:
1. Follow up on important previous discussions
2. Explore areas with high uncertainty
3. Investigate notable patterns
4. Address any concerning changes

Return as a JSON list of strings."""

        result = await self.llm.complete_json([
            {"role": "user", "content": prompt}
        ])

        return result.get("topics", [])

    async def answer_temporal_question(
        self,
        patient_id: UUID,
        question: str
    ) -> dict:
        """
        Answer a temporal question about the patient.

        Examples:
        - "When did sleep issues first appear?"
        - "What changed after starting medication X?"
        - "How has social behavior evolved over the last 3 months?"
        """
        # Get relevant context
        timeline = await self.timeline.build_patient_timeline(patient_id)
        hypotheses = await self._get_current_hypotheses(patient_id)
        patterns = await self._get_active_patterns(patient_id)

        prompt = f"""Answer this question about the patient's history:

Question: {question}

Timeline Events:
{timeline[:50]}  # Limit for context

Current Hypotheses:
{hypotheses}

Detected Patterns:
{patterns}

Provide a clear, evidence-based answer. Cite specific dates and sessions where relevant.
If the information is not available, say so clearly.

Return as JSON:
{{
    "answer": "...",
    "evidence": [
        {{"date": "...", "event": "...", "relevance": "..."}}
    ],
    "confidence": 0.0-1.0,
    "data_gaps": ["areas where more info would help"]
}}"""

        return await self.llm.complete_json([
            {"role": "user", "content": prompt}
        ])
```

### 4.5 Pattern Detection

```python
# src/memory/patterns.py
from uuid import UUID
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from src.models.pattern import DetectedPattern
from src.llm.openrouter import OpenRouterClient

class PatternDetector:
    """
    Detects recurring patterns across sessions.

    Pattern types:
    - recurring_theme: Topics that come up repeatedly
    - behavioral_cycle: Cyclical behavioral patterns
    - trigger_response: Consistent trigger-response relationships
    - symptom_progression: How symptoms evolve over time
    - communication_pattern: Consistent speech/interaction patterns
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def detect_patterns(
        self,
        patient_id: UUID,
        new_session_id: UUID,
        session_signals: list[dict],
        session_summary: str
    ) -> list[dict]:
        """
        Detect patterns after a new session.

        Compares new session against historical data.
        """
        # Get existing patterns
        existing_patterns = await self._get_existing_patterns(patient_id)

        # Get historical context
        from src.memory.context import ContextRetriever
        context = ContextRetriever(self.db)
        recent_sessions = await context._get_recent_sessions(patient_id, limit=10)

        # Detect new patterns and update existing ones
        detected = await self._analyze_for_patterns(
            patient_id=patient_id,
            new_session_id=new_session_id,
            new_signals=session_signals,
            new_summary=session_summary,
            historical_sessions=recent_sessions,
            existing_patterns=existing_patterns
        )

        # Save detected patterns
        for pattern in detected:
            await self._save_pattern(patient_id, new_session_id, pattern)

        return detected

    async def _analyze_for_patterns(
        self,
        patient_id: UUID,
        new_session_id: UUID,
        new_signals: list[dict],
        new_summary: str,
        historical_sessions: list[dict],
        existing_patterns: list[dict]
    ) -> list[dict]:
        """Use LLM to analyze for patterns."""

        prompt = f"""Analyze this patient's sessions for recurring patterns.

NEW SESSION:
Summary: {new_summary}
Signals: {new_signals}

HISTORICAL SESSIONS:
{historical_sessions}

EXISTING PATTERNS:
{existing_patterns}

Look for:
1. recurring_theme: Topics, concerns, or subjects that appear repeatedly
2. behavioral_cycle: Patterns in behavior that follow cycles (weekly, seasonal, etc.)
3. trigger_response: Consistent reactions to specific situations or stimuli
4. symptom_progression: How specific symptoms are changing over time
5. communication_pattern: Consistent ways of communicating or interacting

For each pattern found, determine:
- Is this a new pattern or an update to an existing one?
- How confident are we in this pattern?
- What is the evidence?

Return as JSON:
{{
    "new_patterns": [
        {{
            "pattern_type": "...",
            "pattern_name": "descriptive name",
            "description": "detailed description",
            "evidence_snippets": ["quote1", "quote2"],
            "confidence": 0.0-1.0
        }}
    ],
    "updated_patterns": [
        {{
            "existing_pattern_id": "...",
            "new_evidence": "...",
            "confidence_change": +/-0.0
        }}
    ]
}}"""

        return await self.llm.complete_json([
            {"role": "system", "content": "You are a clinical pattern detection system."},
            {"role": "user", "content": prompt}
        ])

    async def _save_pattern(
        self,
        patient_id: UUID,
        session_id: UUID,
        pattern_data: dict
    ):
        """Save or update a detected pattern."""
        if "existing_pattern_id" in pattern_data:
            # Update existing pattern
            await self.db.execute(
                update(DetectedPattern)
                .where(DetectedPattern.id == pattern_data["existing_pattern_id"])
                .values(
                    occurrence_count=DetectedPattern.occurrence_count + 1,
                    last_seen_at=datetime.utcnow(),
                    confidence=pattern_data.get("new_confidence")
                )
            )
        else:
            # Create new pattern
            pattern = DetectedPattern(
                patient_id=patient_id,
                pattern_type=pattern_data["pattern_type"],
                pattern_name=pattern_data["pattern_name"],
                description=pattern_data["description"],
                first_detected_at=datetime.utcnow(),
                occurrence_count=1,
                supporting_sessions=[str(session_id)],
                evidence_snippets=pattern_data.get("evidence_snippets", []),
                confidence=pattern_data.get("confidence", 0.5)
            )
            self.db.add(pattern)

        await self.db.commit()

    async def _get_existing_patterns(self, patient_id: UUID) -> list[dict]:
        """Get existing patterns for a patient."""
        query = select(DetectedPattern).where(
            DetectedPattern.patient_id == patient_id,
            DetectedPattern.is_active == True
        )

        result = await self.db.execute(query)
        patterns = result.scalars().all()

        return [
            {
                "id": str(p.id),
                "type": p.pattern_type,
                "name": p.pattern_name,
                "description": p.description,
                "occurrences": p.occurrence_count,
                "confidence": p.confidence
            }
            for p in patterns
        ]
```

### 4.6 Summary Rollups

```python
# src/memory/rollups.py
from uuid import UUID
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.models.rollup import SummaryRollup
from src.models.session import VoiceSession
from src.models.hypothesis import HypothesisHistory
from src.llm.openrouter import OpenRouterClient

class RollupService:
    """
    Generates periodic summary rollups for patients.

    Rollup types:
    - weekly: Last 7 days
    - monthly: Last 30 days
    - quarterly: Last 90 days
    - yearly: Last 365 days
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def generate_rollup(
        self,
        patient_id: UUID,
        rollup_type: str,
        end_date: Optional[date] = None
    ) -> SummaryRollup:
        """Generate a summary rollup for a patient."""
        end_date = end_date or date.today()

        period_days = {
            "weekly": 7,
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365
        }

        start_date = end_date - timedelta(days=period_days[rollup_type])

        # Gather data for the period
        sessions = await self._get_period_sessions(patient_id, start_date, end_date)
        domain_trends = await self._calculate_domain_trends(patient_id, start_date, end_date)
        hypothesis_changes = await self._get_hypothesis_changes(patient_id, start_date, end_date)
        significant_events = await self._get_significant_events(patient_id, start_date, end_date)

        # Generate summary using LLM
        summary = await self._generate_summary_text(
            rollup_type=rollup_type,
            period=(start_date, end_date),
            sessions=sessions,
            domain_trends=domain_trends,
            hypothesis_changes=hypothesis_changes,
            significant_events=significant_events
        )

        # Create rollup record
        rollup = SummaryRollup(
            patient_id=patient_id,
            rollup_type=rollup_type,
            period_start=start_date,
            period_end=end_date,
            summary=summary,
            session_count=len(sessions),
            total_duration_minutes=sum(s.duration_seconds or 0 for s in sessions) // 60,
            domain_trends=domain_trends,
            hypothesis_changes=hypothesis_changes,
            significant_events=significant_events
        )

        self.db.add(rollup)
        await self.db.commit()
        await self.db.refresh(rollup)

        return rollup

    async def _calculate_domain_trends(
        self,
        patient_id: UUID,
        start_date: date,
        end_date: date
    ) -> dict:
        """Calculate how domain scores changed over the period."""
        from src.models.assessment import AssessmentDomain as DomainScore

        # Get first and last scores for each domain in the period
        # Implementation depends on exact schema

        trends = {}
        # For each domain, calculate:
        # - start_score: first score in period
        # - end_score: last score in period
        # - trend: 'improving', 'stable', 'declining'

        return trends

    async def _generate_summary_text(
        self,
        rollup_type: str,
        period: tuple,
        sessions: list,
        domain_trends: dict,
        hypothesis_changes: list,
        significant_events: list
    ) -> str:
        """Generate human-readable summary."""
        prompt = f"""Generate a clinical summary for this {rollup_type} period ({period[0]} to {period[1]}).

Sessions: {len(sessions)} sessions

Domain Trends:
{domain_trends}

Hypothesis Changes:
{hypothesis_changes}

Significant Events:
{significant_events}

Write a clear, professional summary that:
1. Highlights key developments
2. Notes any concerning trends
3. Summarizes progress in assessment areas
4. Identifies areas needing attention

Keep it concise but comprehensive. This will be read by clinicians."""

        result = await self.llm.complete([
            {"role": "system", "content": "You are a clinical documentation assistant."},
            {"role": "user", "content": prompt}
        ])

        return result["choices"][0]["message"]["content"]

    async def get_comparison(
        self,
        patient_id: UUID,
        rollup_type: str
    ) -> dict:
        """Compare current period to previous period."""
        current = await self._get_latest_rollup(patient_id, rollup_type)

        query = select(SummaryRollup).where(
            SummaryRollup.patient_id == patient_id,
            SummaryRollup.rollup_type == rollup_type,
            SummaryRollup.period_end < current.period_start
        ).order_by(SummaryRollup.period_end.desc()).limit(1)

        result = await self.db.execute(query)
        previous = result.scalar_one_or_none()

        if not previous:
            return {"current": current, "previous": None, "comparison": None}

        # Compare metrics
        comparison = {
            "session_count_change": current.session_count - previous.session_count,
            "duration_change": current.total_duration_minutes - previous.total_duration_minutes,
            "domain_comparisons": self._compare_domains(
                current.domain_trends, previous.domain_trends
            )
        }

        return {
            "current": current,
            "previous": previous,
            "comparison": comparison
        }
```

### 4.7 API Endpoints (Phase 4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patients/{id}/timeline` | Get patient timeline |
| POST | `/api/v1/patients/{id}/timeline/events` | Add timeline event |
| GET | `/api/v1/patients/{id}/context` | Get session context |
| GET | `/api/v1/patients/{id}/patterns` | Get detected patterns |
| POST | `/api/v1/patients/{id}/temporal-query` | Answer temporal question |
| GET | `/api/v1/patients/{id}/rollups` | Get summary rollups |
| POST | `/api/v1/patients/{id}/rollups/generate` | Generate new rollup |
| GET | `/api/v1/patients/{id}/rollups/{type}/compare` | Compare rollup periods |

### 4.8 Context for Voice Agent

```python
# src/vapi/context_provider.py
from uuid import UUID
from src.memory.context import ContextRetriever

async def get_voice_agent_context(
    patient_id: UUID,
    session_type: str,
    db
) -> str:
    """
    Generate context string for VAPI voice agent.

    This is injected into the system prompt to give the agent
    awareness of patient history.
    """
    retriever = ContextRetriever(db)
    context = await retriever.get_session_context(patient_id, session_type)

    context_parts = []

    # Patient summary
    if context.get("patient_summary"):
        context_parts.append(f"PATIENT CONTEXT:\n{context['patient_summary'].get('summary', '')}")

    # Recent sessions
    if context.get("recent_sessions"):
        recent = context["recent_sessions"][:2]
        sessions_text = "\n".join([
            f"- {s['date']}: {s['summary'][:200]}..."
            for s in recent
        ])
        context_parts.append(f"RECENT SESSIONS:\n{sessions_text}")

    # Current patterns
    if context.get("active_patterns"):
        patterns = context["active_patterns"][:3]
        patterns_text = "\n".join([
            f"- {p['name']}: {p['description'][:100]}"
            for p in patterns
        ])
        context_parts.append(f"NOTABLE PATTERNS:\n{patterns_text}")

    # Suggested topics
    if context.get("suggested_topics"):
        topics = ", ".join(context["suggested_topics"][:5])
        context_parts.append(f"SUGGESTED TOPICS TO EXPLORE: {topics}")

    return "\n\n".join(context_parts)
```

## Acceptance Criteria

- [ ] Timeline construction working
- [ ] Timeline events added for all session types
- [ ] Context retrieval returning relevant history
- [ ] Pattern detection identifying recurring themes
- [ ] Summary rollups generating correctly
- [ ] Temporal question answering functional
- [ ] Semantic embeddings stored and searchable
- [ ] Voice agent receiving patient context
- [ ] API endpoints for timeline and patterns
- [ ] Period comparison working

## Next Phase

Once Phase 4 is complete, proceed to [Phase 5: Analytics & Clinician Dashboard](./phase-5-analytics.md).
