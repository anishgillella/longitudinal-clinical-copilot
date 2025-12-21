# Phase 3: Clinical Assessment Engine

## Objective

Build the clinical assessment engine for autism spectrum disorder (ASD), including structured screening protocols, LLM-based analysis via OpenRouter, clinical signal extraction, and probabilistic hypothesis generation.

## Prerequisites

- Phase 2 completed (VAPI integration, session management)
- OpenRouter account with API key
- Understanding of ASD clinical assessment tools

## Clinical Background: Autism Assessment

### Standard Assessment Tools (Informing Our Approach)

| Tool | Full Name | Purpose | Format |
|------|-----------|---------|--------|
| ADOS-2 | Autism Diagnostic Observation Schedule | Gold standard observation | Structured activities |
| ADI-R | Autism Diagnostic Interview - Revised | Caregiver interview | Semi-structured |
| SRS-2 | Social Responsiveness Scale | Social behavior screening | Questionnaire |
| SCQ | Social Communication Questionnaire | Screening | Parent questionnaire |
| M-CHAT-R | Modified Checklist for Autism in Toddlers | Early screening | Checklist |

**Our system does NOT replace these tools** but uses their domains to structure voice-based information gathering.

### DSM-5 ASD Criteria Domains

1. **Social Communication & Interaction**
   - Social-emotional reciprocity
   - Nonverbal communication
   - Relationships

2. **Restricted, Repetitive Behaviors**
   - Stereotyped movements, speech, or object use
   - Insistence on sameness
   - Restricted interests
   - Sensory sensitivities

## Deliverables

### 3.1 Extended Project Structure

```
src/
├── assessment/                  # Clinical assessment engine
│   ├── __init__.py
│   ├── domains.py               # Assessment domain definitions
│   ├── protocols/               # Screening protocols
│   │   ├── __init__.py
│   │   ├── autism.py            # Autism-specific protocol
│   │   └── base.py              # Base protocol class
│   ├── scoring.py               # Signal scoring engine
│   └── hypothesis.py            # Hypothesis generation
│
├── llm/                         # LLM integration
│   ├── __init__.py
│   ├── openrouter.py            # OpenRouter client
│   ├── prompts/                 # Prompt templates
│   │   ├── __init__.py
│   │   ├── extraction.py        # Signal extraction prompts
│   │   ├── summary.py           # Session summary prompts
│   │   └── hypothesis.py        # Hypothesis generation prompts
│   └── chains.py                # LLM processing chains
│
├── signals/                     # Clinical signal extraction
│   ├── __init__.py
│   ├── linguistic.py            # Language pattern analysis
│   ├── behavioral.py            # Behavioral marker extraction
│   └── temporal.py              # Temporal pattern detection
│
└── models/
    ├── assessment.py            # Assessment domain scores (new)
    ├── hypothesis.py            # Hypothesis tracking (new)
    └── signal.py                # Clinical signals (new)
```

### 3.2 Database Schema Extensions

```sql
-- Assessment domains and scores
CREATE TABLE assessment_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Domain identification
    domain_code VARCHAR(50) NOT NULL,  -- e.g., 'social_reciprocity', 'repetitive_behaviors'
    domain_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),  -- 'social_communication', 'restricted_repetitive'

    -- Scoring
    raw_score FLOAT,           -- Domain-specific score
    normalized_score FLOAT,    -- 0-1 normalized
    confidence FLOAT,          -- Model confidence 0-1
    evidence_count INTEGER,    -- Number of evidence points

    -- Metadata
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    model_version VARCHAR(50),

    UNIQUE(session_id, domain_code)
);

-- Clinical signals extracted from sessions
CREATE TABLE clinical_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES voice_sessions(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Signal identification
    signal_type VARCHAR(50) NOT NULL,  -- 'linguistic', 'behavioral', 'emotional'
    signal_name VARCHAR(100) NOT NULL, -- e.g., 'echolalia', 'flat_affect', 'restricted_topic'

    -- Evidence
    evidence TEXT NOT NULL,            -- Quote or description
    transcript_offset_start INTEGER,   -- Position in transcript
    transcript_offset_end INTEGER,

    -- Scoring
    intensity FLOAT,                   -- Signal strength 0-1
    confidence FLOAT,                  -- Extraction confidence

    -- Clinical mapping
    maps_to_domain VARCHAR(50),        -- Which assessment domain
    clinical_significance VARCHAR(20), -- 'low', 'moderate', 'high'

    -- Metadata
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Diagnostic hypotheses
CREATE TABLE diagnostic_hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,

    -- Hypothesis
    condition_code VARCHAR(50) NOT NULL,  -- e.g., 'asd_level_1', 'asd_level_2'
    condition_name VARCHAR(255) NOT NULL,

    -- Evidence
    evidence_strength FLOAT NOT NULL,     -- 0-1, how strong is the evidence
    uncertainty FLOAT NOT NULL,           -- 0-1, model uncertainty
    supporting_signals INTEGER,           -- Count of supporting signals
    contradicting_signals INTEGER,        -- Count of contradicting signals

    -- Temporal tracking
    first_indicated_at TIMESTAMP WITH TIME ZONE,
    last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trend VARCHAR(20),                    -- 'increasing', 'stable', 'decreasing'

    -- Model info
    model_version VARCHAR(50),
    explanation TEXT,                     -- Why this hypothesis

    UNIQUE(patient_id, condition_code)
);

-- Hypothesis history for temporal tracking
CREATE TABLE hypothesis_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id UUID REFERENCES diagnostic_hypotheses(id) ON DELETE CASCADE,
    session_id UUID REFERENCES voice_sessions(id),

    -- Snapshot
    evidence_strength FLOAT NOT NULL,
    uncertainty FLOAT NOT NULL,
    delta_from_previous FLOAT,

    -- Metadata
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_domains_patient ON assessment_domains(patient_id);
CREATE INDEX idx_domains_session ON assessment_domains(session_id);
CREATE INDEX idx_signals_patient ON clinical_signals(patient_id);
CREATE INDEX idx_signals_type ON clinical_signals(signal_type);
CREATE INDEX idx_hypotheses_patient ON diagnostic_hypotheses(patient_id);
CREATE INDEX idx_hypothesis_history ON hypothesis_history(hypothesis_id);
```

### 3.3 OpenRouter Client

```python
# src/llm/openrouter.py
import httpx
from typing import Optional, AsyncGenerator
from src.config import get_settings

class OpenRouterClient:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://clinical-copilot.com",
            "X-Title": "Longitudinal Clinical Copilot"
        }

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: Optional[dict] = None
    ) -> dict:
        """Generate a completion from OpenRouter."""
        payload = {
            "model": model or self.settings.openrouter_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def complete_json(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> dict:
        """Generate a JSON-structured completion."""
        result = await self.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        import json
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    async def stream(
        self,
        messages: list[dict],
        model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from OpenRouter."""
        payload = {
            "model": model or self.settings.openrouter_model,
            "messages": messages,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data != "[DONE]":
                            import json
                            chunk = json.loads(data)
                            if chunk["choices"][0].get("delta", {}).get("content"):
                                yield chunk["choices"][0]["delta"]["content"]
```

### 3.4 Assessment Domain Definitions

```python
# src/assessment/domains.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional

class DomainCategory(str, Enum):
    SOCIAL_COMMUNICATION = "social_communication"
    RESTRICTED_REPETITIVE = "restricted_repetitive"
    DEVELOPMENTAL = "developmental"
    FUNCTIONAL = "functional"

@dataclass
class AssessmentDomain:
    code: str
    name: str
    category: DomainCategory
    description: str
    indicators: list[str]
    questions: list[str]
    weight: float = 1.0

# Autism Assessment Domains based on DSM-5 criteria
AUTISM_DOMAINS = [
    # Social Communication & Interaction
    AssessmentDomain(
        code="social_emotional_reciprocity",
        name="Social-Emotional Reciprocity",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Ability to engage in back-and-forth social interaction",
        indicators=[
            "Difficulty initiating social interactions",
            "Reduced sharing of interests or emotions",
            "Failure to respond to social overtures",
            "Difficulty with conversational turn-taking",
            "Atypical social approach behaviors"
        ],
        questions=[
            "Can you tell me about your friendships? How do you usually meet new people?",
            "When something exciting happens to you, who do you share it with and how?",
            "How do you usually start conversations with others?",
            "What happens when someone tries to talk to you unexpectedly?"
        ]
    ),
    AssessmentDomain(
        code="nonverbal_communication",
        name="Nonverbal Communication",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Use and understanding of nonverbal cues",
        indicators=[
            "Reduced eye contact",
            "Atypical facial expressions",
            "Unusual body language or gestures",
            "Difficulty understanding others' nonverbal cues",
            "Mismatch between verbal and nonverbal communication"
        ],
        questions=[
            "How comfortable do you feel making eye contact during conversations?",
            "Do people ever say you're hard to read or seem different?",
            "How do you know when someone is upset or happy without them telling you?"
        ]
    ),
    AssessmentDomain(
        code="relationships",
        name="Developing and Maintaining Relationships",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Ability to form and sustain social relationships",
        indicators=[
            "Difficulty adjusting behavior to social contexts",
            "Challenges making friends",
            "Reduced interest in peers",
            "Preference for solitary activities",
            "Difficulty understanding social hierarchy"
        ],
        questions=[
            "Tell me about your closest relationships. How long have they lasted?",
            "Do you prefer spending time alone or with others?",
            "How do you handle it when social situations don't go as expected?"
        ]
    ),

    # Restricted, Repetitive Behaviors
    AssessmentDomain(
        code="stereotyped_behaviors",
        name="Stereotyped or Repetitive Behaviors",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Presence of repetitive motor movements, speech, or object use",
        indicators=[
            "Motor stereotypies (hand flapping, rocking)",
            "Echolalia or scripted speech",
            "Lining up objects",
            "Repetitive use of objects",
            "Idiosyncratic phrases"
        ],
        questions=[
            "Are there any movements or sounds you find yourself doing repeatedly?",
            "Do you have any phrases or quotes you like to repeat?",
            "How do you typically arrange or organize your belongings?"
        ]
    ),
    AssessmentDomain(
        code="insistence_sameness",
        name="Insistence on Sameness",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Inflexible adherence to routines or ritualized patterns",
        indicators=[
            "Distress at small changes",
            "Rigid thinking patterns",
            "Need for predictability",
            "Ritualized behaviors",
            "Difficulty with transitions"
        ],
        questions=[
            "How do you handle unexpected changes to your plans or routine?",
            "Do you have specific routines that are important to follow?",
            "What happens if something in your environment is different from usual?"
        ]
    ),
    AssessmentDomain(
        code="restricted_interests",
        name="Restricted Interests",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Highly fixated, intense interests that are abnormal in intensity or focus",
        indicators=[
            "Intense preoccupation with specific topics",
            "Unusually deep knowledge in narrow areas",
            "Difficulty shifting focus from interests",
            "Interest in unusual topics",
            "Collecting behaviors"
        ],
        questions=[
            "What topics or activities are you most passionate about?",
            "How much time do you spend on your main interests?",
            "Do others comment on how much you know about certain topics?"
        ]
    ),
    AssessmentDomain(
        code="sensory_processing",
        name="Sensory Processing",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Hyper- or hypo-reactivity to sensory input",
        indicators=[
            "Sensitivity to sounds, lights, or textures",
            "Unusual sensory seeking behaviors",
            "Apparent indifference to temperature or pain",
            "Adverse response to specific sounds or textures",
            "Visual fascination with lights or movement"
        ],
        questions=[
            "Are there any sounds, lights, or textures that bother you more than others?",
            "Do you notice things in your environment that others might miss?",
            "How do you react to unexpected loud noises or bright lights?"
        ]
    ),

    # Developmental History
    AssessmentDomain(
        code="developmental_milestones",
        name="Developmental Milestones",
        category=DomainCategory.DEVELOPMENTAL,
        description="Early developmental history and milestones",
        indicators=[
            "Language development timing",
            "Motor milestone timing",
            "Social smile and joint attention",
            "Regression of skills",
            "Early play patterns"
        ],
        questions=[
            "What do you know about when you started talking as a child?",
            "Were there ever skills you had that seemed to go away?",
            "What were you told about your early development?"
        ],
        weight=0.8
    ),

    # Functional Impact
    AssessmentDomain(
        code="daily_functioning",
        name="Daily Functioning",
        category=DomainCategory.FUNCTIONAL,
        description="Impact on daily life and independence",
        indicators=[
            "Self-care abilities",
            "Employment or academic challenges",
            "Need for support in daily activities",
            "Living situation independence",
            "Executive function challenges"
        ],
        questions=[
            "How do you manage day-to-day tasks like cooking, cleaning, or appointments?",
            "What kinds of support, if any, do you find helpful?",
            "How has this affected your work or education?"
        ],
        weight=0.7
    )
]

def get_domain_by_code(code: str) -> Optional[AssessmentDomain]:
    """Get domain by code."""
    for domain in AUTISM_DOMAINS:
        if domain.code == code:
            return domain
    return None

def get_domains_by_category(category: DomainCategory) -> list[AssessmentDomain]:
    """Get all domains in a category."""
    return [d for d in AUTISM_DOMAINS if d.category == category]
```

### 3.5 Signal Extraction Prompts

```python
# src/llm/prompts/extraction.py

SIGNAL_EXTRACTION_SYSTEM = """You are a clinical signal extraction system for autism spectrum assessment.
Your role is to identify clinically relevant signals from patient transcripts.

You must:
1. Identify specific behaviors, patterns, or statements that are clinically meaningful
2. Map each signal to the appropriate assessment domain
3. Rate the intensity and your confidence in each signal
4. Provide exact quotes as evidence

You must NOT:
1. Make diagnostic conclusions
2. Interpret beyond what is explicitly stated
3. Assume the presence of behaviors not mentioned
4. Add clinical judgment - only extract observable signals

Output Format: JSON
{
    "signals": [
        {
            "signal_type": "linguistic|behavioral|emotional",
            "signal_name": "specific signal name",
            "evidence": "exact quote or description",
            "intensity": 0.0-1.0,
            "confidence": 0.0-1.0,
            "maps_to_domain": "domain_code",
            "clinical_significance": "low|moderate|high"
        }
    ],
    "domain_observations": {
        "domain_code": {
            "observed": true/false,
            "evidence_summary": "brief summary",
            "notable_quotes": ["quote1", "quote2"]
        }
    }
}"""

SIGNAL_EXTRACTION_USER = """Analyze the following transcript for clinically relevant signals related to autism spectrum assessment.

Patient Information:
- Name: {patient_name}
- Age: {patient_age}
- Session Type: {session_type}

Assessment Domains to Consider:
{domains_list}

Transcript:
{transcript}

Extract all clinically relevant signals and map them to the appropriate domains."""

LINGUISTIC_ANALYSIS_SYSTEM = """You are a linguistic pattern analyzer for clinical assessment.
Analyze speech patterns for features relevant to autism spectrum assessment.

Look for:
1. Echolalia (immediate or delayed)
2. Pronoun reversal
3. Scripted or formulaic speech
4. Unusual prosody descriptions (if mentioned)
5. Pedantic or formal speech patterns
6. Literal interpretation of language
7. Difficulty with idioms or figurative language
8. Topic perseveration
9. One-sided conversation patterns

Output as JSON with specific examples."""

BEHAVIORAL_MARKER_SYSTEM = """You are a behavioral marker extraction system for clinical assessment.
Identify behavioral patterns described in the transcript.

Look for mentions of:
1. Repetitive behaviors or movements
2. Routine adherence and flexibility
3. Special interests (intensity and breadth)
4. Sensory experiences (seeking or avoiding)
5. Social interaction patterns
6. Coping strategies
7. Emotional regulation approaches
8. Daily living activities

Output as JSON with specific quotes as evidence."""
```

### 3.6 Hypothesis Generation

```python
# src/assessment/hypothesis.py
from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime
from src.llm.openrouter import OpenRouterClient
from src.assessment.domains import AUTISM_DOMAINS

@dataclass
class HypothesisResult:
    condition_code: str
    condition_name: str
    evidence_strength: float
    uncertainty: float
    supporting_signals: int
    contradicting_signals: int
    explanation: str
    key_evidence: list[str]

HYPOTHESIS_GENERATION_PROMPT = """You are a clinical hypothesis generation system for autism spectrum assessment.
Based on the accumulated evidence, generate probability estimates for ASD.

CRITICAL RULES:
1. You generate HYPOTHESES, not diagnoses
2. Always express uncertainty
3. Consider differential explanations
4. Weight evidence appropriately
5. Note contradicting evidence

ASD Levels (if ASD hypothesis is supported):
- Level 1: Requiring support (mild)
- Level 2: Requiring substantial support (moderate)
- Level 3: Requiring very substantial support (severe)

Input: Accumulated signals and domain scores from all sessions

Output Format: JSON
{
    "hypotheses": [
        {
            "condition_code": "asd_level_1|asd_level_2|asd_level_3|no_asd|uncertain",
            "condition_name": "Full name",
            "evidence_strength": 0.0-1.0,
            "uncertainty": 0.0-1.0,
            "supporting_signals": count,
            "contradicting_signals": count,
            "explanation": "Clear explanation of reasoning",
            "key_evidence": ["evidence point 1", "evidence point 2"]
        }
    ],
    "differential_considerations": [
        "Other conditions to consider and why"
    ],
    "data_gaps": [
        "Areas where more information would help"
    ],
    "clinical_notes": "Any important observations for the clinician"
}"""

class HypothesisEngine:
    def __init__(self):
        self.llm = OpenRouterClient()

    async def generate_hypotheses(
        self,
        patient_id: UUID,
        accumulated_signals: list[dict],
        domain_scores: list[dict],
        session_summaries: list[str]
    ) -> dict:
        """Generate diagnostic hypotheses based on accumulated evidence."""

        # Prepare evidence summary
        evidence_text = self._format_evidence(
            accumulated_signals, domain_scores, session_summaries
        )

        messages = [
            {"role": "system", "content": HYPOTHESIS_GENERATION_PROMPT},
            {"role": "user", "content": f"""
Generate hypotheses for patient assessment based on the following evidence:

DOMAIN SCORES:
{self._format_domain_scores(domain_scores)}

CLINICAL SIGNALS ({len(accumulated_signals)} total):
{self._format_signals(accumulated_signals)}

SESSION SUMMARIES:
{chr(10).join(session_summaries)}

Generate probabilistic hypotheses with appropriate uncertainty.
"""}
        ]

        result = await self.llm.complete_json(messages, temperature=0.2)
        return result

    def _format_domain_scores(self, scores: list[dict]) -> str:
        lines = []
        for score in scores:
            lines.append(
                f"- {score['domain_name']}: {score['normalized_score']:.2f} "
                f"(confidence: {score['confidence']:.2f})"
            )
        return "\n".join(lines)

    def _format_signals(self, signals: list[dict]) -> str:
        lines = []
        for signal in signals[:50]:  # Limit for context
            lines.append(
                f"- [{signal['signal_type']}] {signal['signal_name']}: "
                f"\"{signal['evidence'][:100]}...\" "
                f"(intensity: {signal['intensity']:.2f})"
            )
        return "\n".join(lines)

    def _format_evidence(
        self,
        signals: list[dict],
        scores: list[dict],
        summaries: list[str]
    ) -> str:
        return f"""
Domain Scores: {len(scores)} domains assessed
Clinical Signals: {len(signals)} signals extracted
Sessions Analyzed: {len(summaries)} sessions
"""
```

### 3.7 Post-Session Processing Pipeline

```python
# src/services/processing_service.py
from uuid import UUID
from src.llm.openrouter import OpenRouterClient
from src.assessment.hypothesis import HypothesisEngine
from src.services.transcript_service import TranscriptService
from src.services.signal_service import SignalService
from src.services.domain_service import DomainService

class PostSessionProcessor:
    def __init__(self, db):
        self.db = db
        self.llm = OpenRouterClient()
        self.hypothesis_engine = HypothesisEngine()
        self.transcript_service = TranscriptService(db)
        self.signal_service = SignalService(db)
        self.domain_service = DomainService(db)

    async def process_session(self, session_id: UUID) -> dict:
        """
        Full post-session processing pipeline.

        Steps:
        1. Retrieve transcript
        2. Extract clinical signals
        3. Score assessment domains
        4. Update patient hypotheses
        5. Generate session summary
        6. Flag concerns for clinician
        """
        results = {
            "session_id": session_id,
            "signals_extracted": 0,
            "domains_scored": 0,
            "hypotheses_updated": False,
            "concerns_flagged": []
        }

        # Step 1: Get transcript
        transcript = await self.transcript_service.get_full_transcript(session_id)
        session = await self.get_session(session_id)

        # Step 2: Extract signals
        signals = await self._extract_signals(session, transcript)
        await self.signal_service.store_signals(session_id, signals)
        results["signals_extracted"] = len(signals)

        # Step 3: Score domains
        domain_scores = await self._score_domains(session, signals)
        await self.domain_service.store_scores(session_id, domain_scores)
        results["domains_scored"] = len(domain_scores)

        # Step 4: Update hypotheses
        all_signals = await self.signal_service.get_patient_signals(session.patient_id)
        all_scores = await self.domain_service.get_patient_scores(session.patient_id)
        summaries = await self.get_session_summaries(session.patient_id)

        hypotheses = await self.hypothesis_engine.generate_hypotheses(
            session.patient_id, all_signals, all_scores, summaries
        )
        await self._update_hypotheses(session.patient_id, hypotheses)
        results["hypotheses_updated"] = True

        # Step 5: Generate summary
        summary = await self._generate_summary(session, transcript, signals)
        await self.store_session_summary(session_id, summary)

        # Step 6: Check for concerns
        concerns = self._identify_concerns(signals, hypotheses)
        if concerns:
            await self.flag_concerns(session_id, concerns)
            results["concerns_flagged"] = concerns

        return results

    async def _extract_signals(self, session, transcript: str) -> list[dict]:
        """Extract clinical signals from transcript."""
        from src.llm.prompts.extraction import (
            SIGNAL_EXTRACTION_SYSTEM, SIGNAL_EXTRACTION_USER
        )
        from src.assessment.domains import AUTISM_DOMAINS

        domains_text = "\n".join([
            f"- {d.code}: {d.description}"
            for d in AUTISM_DOMAINS
        ])

        messages = [
            {"role": "system", "content": SIGNAL_EXTRACTION_SYSTEM},
            {"role": "user", "content": SIGNAL_EXTRACTION_USER.format(
                patient_name=session.patient.first_name,
                patient_age=self._calculate_age(session.patient.date_of_birth),
                session_type=session.session_type,
                domains_list=domains_text,
                transcript=transcript
            )}
        ]

        result = await self.llm.complete_json(messages)
        return result.get("signals", [])

    async def _score_domains(self, session, signals: list[dict]) -> list[dict]:
        """Score assessment domains based on extracted signals."""
        from src.assessment.domains import AUTISM_DOMAINS

        domain_scores = []
        for domain in AUTISM_DOMAINS:
            # Get signals mapped to this domain
            domain_signals = [
                s for s in signals
                if s.get("maps_to_domain") == domain.code
            ]

            if domain_signals:
                # Calculate aggregate score
                avg_intensity = sum(s["intensity"] for s in domain_signals) / len(domain_signals)
                avg_confidence = sum(s["confidence"] for s in domain_signals) / len(domain_signals)

                domain_scores.append({
                    "domain_code": domain.code,
                    "domain_name": domain.name,
                    "category": domain.category.value,
                    "raw_score": avg_intensity,
                    "normalized_score": avg_intensity,  # Already 0-1
                    "confidence": avg_confidence,
                    "evidence_count": len(domain_signals)
                })

        return domain_scores

    def _identify_concerns(self, signals: list[dict], hypotheses: dict) -> list[dict]:
        """Identify concerns requiring clinician attention."""
        concerns = []

        # High significance signals
        for signal in signals:
            if signal.get("clinical_significance") == "high":
                concerns.append({
                    "type": "high_significance_signal",
                    "signal": signal["signal_name"],
                    "evidence": signal["evidence"],
                    "priority": "high"
                })

        # Sudden changes in hypothesis
        for hyp in hypotheses.get("hypotheses", []):
            if hyp.get("evidence_strength", 0) > 0.7:
                concerns.append({
                    "type": "strong_hypothesis",
                    "condition": hyp["condition_name"],
                    "strength": hyp["evidence_strength"],
                    "priority": "medium"
                })

        return concerns
```

### 3.8 API Endpoints (Phase 3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/patients/{id}/signals` | Get patient's clinical signals |
| GET | `/api/v1/patients/{id}/domains` | Get domain assessment scores |
| GET | `/api/v1/patients/{id}/hypotheses` | Get current hypotheses |
| GET | `/api/v1/patients/{id}/hypotheses/history` | Get hypothesis history |
| POST | `/api/v1/sessions/{id}/process` | Trigger post-session processing |
| GET | `/api/v1/sessions/{id}/summary` | Get session summary |
| GET | `/api/v1/sessions/{id}/signals` | Get signals from session |

### 3.9 Configuration

```bash
# .env additions for Phase 3
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=google/gemini-2.5-flash

# Optional: Model for specific tasks
OPENROUTER_EXTRACTION_MODEL=google/gemini-2.5-flash
OPENROUTER_HYPOTHESIS_MODEL=google/gemini-2.5-flash
```

## Acceptance Criteria

- [ ] OpenRouter client implemented and tested
- [ ] All autism assessment domains defined
- [ ] Signal extraction prompts working
- [ ] Post-session processing pipeline complete
- [ ] Domain scoring implemented
- [ ] Hypothesis generation working
- [ ] Hypothesis history tracked over time
- [ ] Clinical concerns flagging implemented
- [ ] Session summaries generated
- [ ] API endpoints functioning

## Clinical Safety Checks

1. **Never display hypotheses as diagnoses** - always label as "evidence patterns"
2. **Always show uncertainty** - confidence bands required
3. **Temporal context required** - show when evidence was collected
4. **Clinician override** - allow manual corrections
5. **Audit trail** - log all hypothesis changes

## Next Phase

Once Phase 3 is complete, proceed to [Phase 4: Longitudinal Memory & Context](./phase-4-memory.md).
