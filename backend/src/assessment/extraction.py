"""
Signal Extraction Service

Extracts clinical signals from session transcripts using LLM analysis.
Provides deep analytics including:
- Quote-level evidence extraction
- DSM-5 criteria mapping
- Clinical gap identification
- Differential considerations
"""

import logging
from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.llm.openrouter import OpenRouterClient
from src.llm.prompts import (
    SIGNAL_EXTRACTION_SYSTEM,
    SIGNAL_EXTRACTION_USER,
    CONCERN_DETECTION_SYSTEM,
    CONCERN_DETECTION_USER,
)
from src.assessment.domains import AUTISM_DOMAINS, get_domains_for_prompt
from src.models.assessment import ClinicalSignal, AssessmentDomainScore
from src.models.session import VoiceSession

logger = logging.getLogger(__name__)


# DSM-5 Autism Criteria Reference
DSM5_AUTISM_CRITERIA = {
    "A": {
        "name": "Social Communication and Interaction",
        "criteria": {
            "A1": "Deficits in social-emotional reciprocity",
            "A2": "Deficits in nonverbal communicative behaviors",
            "A3": "Deficits in developing, maintaining, and understanding relationships",
        }
    },
    "B": {
        "name": "Restricted, Repetitive Patterns",
        "criteria": {
            "B1": "Stereotyped or repetitive motor movements, use of objects, or speech",
            "B2": "Insistence on sameness, inflexible adherence to routines",
            "B3": "Highly restricted, fixated interests abnormal in intensity or focus",
            "B4": "Hyper- or hyporeactivity to sensory input",
        }
    }
}


def get_dsm5_criteria_for_prompt() -> str:
    """Format DSM-5 criteria for LLM prompt."""
    lines = ["DSM-5 Autism Spectrum Disorder Criteria:"]
    for category, data in DSM5_AUTISM_CRITERIA.items():
        lines.append(f"\nCriterion {category}: {data['name']}")
        for code, description in data['criteria'].items():
            lines.append(f"  - {code}: {description}")
    return "\n".join(lines)


class SignalExtractionService:
    """Service for extracting clinical signals from transcripts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = OpenRouterClient()

    async def extract_signals(
        self,
        session_id: UUID,
        transcript: str,
        session_type: str = "intake",
    ) -> list[ClinicalSignal]:
        """
        Extract clinical signals from a session transcript.

        Args:
            session_id: The session ID
            transcript: Full transcript text
            session_type: Type of session (intake, checkin, etc.)

        Returns:
            List of extracted ClinicalSignal objects
        """
        # Get session for patient_id
        session = await self.db.get(VoiceSession, session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Prepare prompt with DSM-5 criteria
        domains_text = get_domains_for_prompt()
        dsm5_text = get_dsm5_criteria_for_prompt()

        user_prompt = SIGNAL_EXTRACTION_USER.format(
            session_type=session_type,
            domains_text=domains_text,
            transcript=transcript,
        )

        # Enhance prompt with DSM-5 mapping instructions
        enhanced_prompt = f"""{user_prompt}

{dsm5_text}

ADDITIONAL EXTRACTION REQUIREMENTS:
1. For each signal, include the specific DSM-5 criterion code (A1, A2, A3, B1, B2, B3, B4) if applicable
2. Extract verbatim quotes from the patient where possible
3. Include the context around each quote
4. Map signals to specific criteria, not just domains
"""

        # Call LLM
        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": SIGNAL_EXTRACTION_SYSTEM},
                    {"role": "user", "content": enhanced_prompt},
                ],
                temperature=0.2,  # Lower for more consistent extraction
            )
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise

        # Parse and store signals with enhanced fields
        signals = []
        for signal_data in result.get("signals", []):
            signal = ClinicalSignal(
                session_id=session_id,
                patient_id=session.patient_id,
                signal_type=signal_data.get("signal_type", "behavioral"),
                signal_name=signal_data.get("signal_name", "Unknown"),
                evidence=signal_data.get("evidence", ""),
                evidence_type=signal_data.get("evidence_type", "inferred"),
                reasoning=signal_data.get("reasoning"),
                transcript_line=signal_data.get("transcript_line"),
                transcript_offset_start=signal_data.get("transcript_offset_start"),
                transcript_offset_end=signal_data.get("transcript_offset_end"),
                intensity=float(signal_data.get("intensity", 0.5)),
                confidence=float(signal_data.get("confidence", 0.5)),
                maps_to_domain=signal_data.get("maps_to_domain"),
                dsm5_criteria=signal_data.get("dsm5_criteria"),
                clinical_significance=signal_data.get("clinical_significance", "moderate"),
                verbatim_quote=signal_data.get("verbatim_quote"),
                quote_context=signal_data.get("quote_context"),
                extracted_at=datetime.utcnow(),
                model_version=self.llm.model,
            )
            self.db.add(signal)
            signals.append(signal)

        await self.db.commit()

        # Refresh to get IDs
        for signal in signals:
            await self.db.refresh(signal)

        logger.info(f"Extracted {len(signals)} signals from session {session_id}")
        return signals

    async def detect_concerns(
        self,
        session_id: UUID,
        transcript: str,
    ) -> dict:
        """
        Detect clinical concerns requiring attention.

        Returns:
            Dict with concerns and safety assessment
        """
        user_prompt = CONCERN_DETECTION_USER.format(transcript=transcript)

        try:
            result = await self.llm.complete_json(
                messages=[
                    {"role": "system", "content": CONCERN_DETECTION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,  # Very low for safety-critical
            )
        except Exception as e:
            logger.error(f"Concern detection failed: {e}")
            # Return safe default on error
            return {
                "concerns": [],
                "overall_safety_assessment": "review",
                "notes": f"Error during analysis: {str(e)}",
            }

        return result

    async def get_signals_for_session(self, session_id: UUID) -> list[ClinicalSignal]:
        """Get all signals extracted from a session."""
        result = await self.db.execute(
            select(ClinicalSignal)
            .where(ClinicalSignal.session_id == session_id)
            .order_by(ClinicalSignal.extracted_at)
        )
        return list(result.scalars().all())

    async def get_signals_for_patient(
        self,
        patient_id: UUID,
        signal_type: Optional[str] = None,
        domain: Optional[str] = None,
        significance: Optional[str] = None,
    ) -> list[ClinicalSignal]:
        """Get all signals for a patient with optional filters."""
        query = select(ClinicalSignal).where(ClinicalSignal.patient_id == patient_id)

        if signal_type:
            query = query.where(ClinicalSignal.signal_type == signal_type)
        if domain:
            query = query.where(ClinicalSignal.maps_to_domain == domain)
        if significance:
            query = query.where(ClinicalSignal.clinical_significance == significance)

        query = query.order_by(ClinicalSignal.extracted_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_signal_summary(self, patient_id: UUID) -> dict:
        """Get summary statistics of signals for a patient."""
        signals = await self.get_signals_for_patient(patient_id)

        by_type = {}
        by_domain = {}
        by_significance = {}

        for signal in signals:
            by_type[signal.signal_type] = by_type.get(signal.signal_type, 0) + 1
            if signal.maps_to_domain:
                by_domain[signal.maps_to_domain] = by_domain.get(signal.maps_to_domain, 0) + 1
            by_significance[signal.clinical_significance] = (
                by_significance.get(signal.clinical_significance, 0) + 1
            )

        return {
            "total": len(signals),
            "by_type": by_type,
            "by_domain": by_domain,
            "by_significance": by_significance,
        }

    async def identify_clinical_gaps(self, patient_id: UUID) -> dict:
        """
        Identify DSM-5 domains/criteria with insufficient evidence.

        Returns:
            Dictionary with gaps categorized by severity
        """
        # Get all signals for patient
        signals = await self.get_signals_for_patient(patient_id)

        # Count signals per DSM-5 criterion
        criteria_coverage = {
            "A1": [], "A2": [], "A3": [],
            "B1": [], "B2": [], "B3": [], "B4": []
        }

        for signal in signals:
            if signal.dsm5_criteria and signal.dsm5_criteria in criteria_coverage:
                criteria_coverage[signal.dsm5_criteria].append({
                    "signal_id": str(signal.id),
                    "signal_name": signal.signal_name,
                    "confidence": signal.confidence,
                    "significance": signal.clinical_significance,
                })

        # Identify gaps
        gaps = {
            "no_evidence": [],  # Criteria with no signals
            "low_confidence": [],  # Criteria with only low-confidence signals
            "needs_confirmation": [],  # Criteria that need more evidence
        }

        for criterion, signals_list in criteria_coverage.items():
            criterion_info = self._get_criterion_info(criterion)

            if not signals_list:
                gaps["no_evidence"].append({
                    "criterion": criterion,
                    "description": criterion_info,
                    "recommendation": f"Explore behaviors related to {criterion_info}",
                })
            else:
                avg_confidence = sum(s["confidence"] for s in signals_list) / len(signals_list)
                high_significance = any(s["significance"] == "high" for s in signals_list)

                if avg_confidence < 0.5:
                    gaps["low_confidence"].append({
                        "criterion": criterion,
                        "description": criterion_info,
                        "signal_count": len(signals_list),
                        "avg_confidence": avg_confidence,
                        "recommendation": f"Gather more specific examples for {criterion}",
                    })
                elif not high_significance and len(signals_list) < 3:
                    gaps["needs_confirmation"].append({
                        "criterion": criterion,
                        "description": criterion_info,
                        "signal_count": len(signals_list),
                        "recommendation": f"Look for additional evidence for {criterion}",
                    })

        return {
            "gaps": gaps,
            "coverage_summary": {
                criterion: len(signals_list)
                for criterion, signals_list in criteria_coverage.items()
            },
            "total_criteria": 7,
            "criteria_with_evidence": sum(1 for s in criteria_coverage.values() if s),
        }

    async def get_differential_considerations(self, patient_id: UUID) -> dict:
        """
        Identify signals that might support differential diagnoses.

        Returns:
            Dictionary with potential differentials and supporting evidence
        """
        signals = await self.get_signals_for_patient(patient_id)

        # Define differential conditions and their characteristic patterns
        differentials = {
            "anxiety_disorder": {
                "name": "Anxiety Disorder",
                "patterns": ["avoidance", "worry", "fear", "panic", "social anxiety"],
                "signals": [],
            },
            "adhd": {
                "name": "ADHD",
                "patterns": ["attention", "hyperactivity", "impulsivity", "distractibility", "focus"],
                "signals": [],
            },
            "social_communication_disorder": {
                "name": "Social (Pragmatic) Communication Disorder",
                "patterns": ["pragmatic", "conversation", "social context", "inference"],
                "signals": [],
            },
            "intellectual_disability": {
                "name": "Intellectual Disability",
                "patterns": ["learning", "cognitive", "adaptive", "academic"],
                "signals": [],
            },
            "language_disorder": {
                "name": "Language Disorder",
                "patterns": ["language", "speech", "expression", "comprehension"],
                "signals": [],
            },
        }

        # Match signals to potential differentials
        for signal in signals:
            signal_text = f"{signal.signal_name} {signal.evidence} {signal.reasoning or ''}".lower()

            for condition, data in differentials.items():
                for pattern in data["patterns"]:
                    if pattern in signal_text:
                        data["signals"].append({
                            "signal_id": str(signal.id),
                            "signal_name": signal.signal_name,
                            "evidence": signal.evidence[:200],
                            "pattern_matched": pattern,
                        })
                        break

        # Calculate relevance scores
        considerations = []
        for condition, data in differentials.items():
            if data["signals"]:
                considerations.append({
                    "condition": data["name"],
                    "code": condition,
                    "signal_count": len(data["signals"]),
                    "supporting_signals": data["signals"][:5],  # Top 5
                    "note": f"Consider ruling out {data['name']} based on {len(data['signals'])} related signals",
                })

        return {
            "differential_considerations": sorted(
                considerations, key=lambda x: x["signal_count"], reverse=True
            ),
            "total_signals_analyzed": len(signals),
        }

    async def get_evidence_by_criterion(self, patient_id: UUID) -> dict:
        """
        Get all evidence organized by DSM-5 criterion.

        Useful for clinical review and report generation.
        """
        signals = await self.get_signals_for_patient(patient_id)

        # Organize by criterion
        by_criterion = {}
        for criterion in ["A1", "A2", "A3", "B1", "B2", "B3", "B4"]:
            by_criterion[criterion] = {
                "description": self._get_criterion_info(criterion),
                "signals": [],
                "verbatim_quotes": [],
            }

        for signal in signals:
            if signal.dsm5_criteria and signal.dsm5_criteria in by_criterion:
                criterion_data = by_criterion[signal.dsm5_criteria]
                criterion_data["signals"].append({
                    "id": str(signal.id),
                    "name": signal.signal_name,
                    "evidence": signal.evidence,
                    "evidence_type": signal.evidence_type,
                    "confidence": signal.confidence,
                    "significance": signal.clinical_significance,
                    "verified": signal.clinician_verified,
                })

                if signal.verbatim_quote:
                    criterion_data["verbatim_quotes"].append({
                        "quote": signal.verbatim_quote,
                        "context": signal.quote_context,
                        "signal_name": signal.signal_name,
                    })

        return by_criterion

    def _get_criterion_info(self, criterion: str) -> str:
        """Get description for a DSM-5 criterion code."""
        for category, data in DSM5_AUTISM_CRITERIA.items():
            if criterion in data["criteria"]:
                return data["criteria"][criterion]
        return f"Unknown criterion: {criterion}"
