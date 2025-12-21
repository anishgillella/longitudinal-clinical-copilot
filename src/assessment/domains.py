"""
Assessment Domain Definitions for Autism Spectrum Disorder

Based on DSM-5 criteria for ASD, these domains structure the clinical
assessment process. Each domain contains indicators to look for and
questions that help gather relevant information.

IMPORTANT: This system does NOT diagnose. It collects structured information
to assist clinicians in their assessment.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DomainCategory(str, Enum):
    """High-level categories from DSM-5 ASD criteria."""
    SOCIAL_COMMUNICATION = "social_communication"
    RESTRICTED_REPETITIVE = "restricted_repetitive"
    DEVELOPMENTAL = "developmental"
    FUNCTIONAL = "functional"


@dataclass
class AssessmentDomain:
    """Definition of an assessment domain."""
    code: str
    name: str
    category: DomainCategory
    description: str
    indicators: list[str]
    example_questions: list[str]
    weight: float = 1.0  # Relative importance in scoring

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "indicators": self.indicators,
            "example_questions": self.example_questions,
            "weight": self.weight,
        }


# =============================================================================
# AUTISM ASSESSMENT DOMAINS
# Based on DSM-5 Criteria
# =============================================================================

AUTISM_DOMAINS: list[AssessmentDomain] = [
    # -------------------------------------------------------------------------
    # SOCIAL COMMUNICATION & INTERACTION (Criterion A)
    # -------------------------------------------------------------------------
    AssessmentDomain(
        code="social_emotional_reciprocity",
        name="Social-Emotional Reciprocity",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Ability to engage in back-and-forth social interaction",
        indicators=[
            "Difficulty initiating social interactions",
            "Reduced sharing of interests, emotions, or affect",
            "Failure to respond to social overtures from others",
            "Difficulty with conversational turn-taking",
            "Atypical social approach behaviors",
            "One-sided conversations",
            "Reduced social smiling or emotional expression",
        ],
        example_questions=[
            "Can you tell me about your friendships? How do you usually meet new people?",
            "When something exciting happens to you, who do you share it with and how?",
            "How do you usually start conversations with others?",
            "What happens when someone tries to talk to you unexpectedly?",
            "Do you find it easy or difficult to keep a conversation going?",
        ],
    ),

    AssessmentDomain(
        code="nonverbal_communication",
        name="Nonverbal Communication",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Use and understanding of nonverbal cues in communication",
        indicators=[
            "Reduced or atypical eye contact",
            "Atypical facial expressions",
            "Unusual body language or gestures",
            "Difficulty understanding others' nonverbal cues",
            "Mismatch between verbal and nonverbal communication",
            "Limited use of gestures while speaking",
            "Difficulty reading facial expressions",
        ],
        example_questions=[
            "How comfortable do you feel making eye contact during conversations?",
            "Do people ever say you're hard to read or seem different?",
            "How do you know when someone is upset or happy without them telling you?",
            "Do you use hand gestures when you talk?",
            "Have you ever missed that someone was joking or being sarcastic?",
        ],
    ),

    AssessmentDomain(
        code="relationships",
        name="Developing and Maintaining Relationships",
        category=DomainCategory.SOCIAL_COMMUNICATION,
        description="Ability to form and sustain social relationships",
        indicators=[
            "Difficulty adjusting behavior to social contexts",
            "Challenges making or keeping friends",
            "Reduced interest in peers",
            "Preference for solitary activities",
            "Difficulty understanding social hierarchy",
            "Trouble maintaining friendships over time",
            "Not understanding unwritten social rules",
        ],
        example_questions=[
            "Tell me about your closest relationships. How long have they lasted?",
            "Do you prefer spending time alone or with others?",
            "How do you handle it when social situations don't go as expected?",
            "Have you found it easy or hard to make friends throughout your life?",
            "Do you have different 'versions' of yourself for different situations?",
        ],
    ),

    # -------------------------------------------------------------------------
    # RESTRICTED, REPETITIVE BEHAVIORS (Criterion B)
    # -------------------------------------------------------------------------
    AssessmentDomain(
        code="stereotyped_behaviors",
        name="Stereotyped or Repetitive Behaviors",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Presence of repetitive motor movements, speech, or object use",
        indicators=[
            "Motor stereotypies (hand flapping, rocking, spinning)",
            "Echolalia (repeating words or phrases)",
            "Scripted or formulaic speech",
            "Lining up objects",
            "Repetitive use of objects",
            "Idiosyncratic phrases",
            "Unusual movements when excited or stressed",
        ],
        example_questions=[
            "Are there any movements or sounds you find yourself doing repeatedly?",
            "Do you have any phrases or quotes you like to repeat?",
            "How do you typically arrange or organize your belongings?",
            "What do you do with your hands when you're excited or nervous?",
            "Do you ever find yourself repeating things others have said?",
        ],
    ),

    AssessmentDomain(
        code="insistence_sameness",
        name="Insistence on Sameness",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Inflexible adherence to routines or ritualized patterns",
        indicators=[
            "Distress at small changes",
            "Rigid thinking patterns",
            "Strong need for predictability",
            "Ritualized behaviors or routines",
            "Difficulty with transitions",
            "Same route, same food, same schedule",
            "Extreme distress when routines are disrupted",
        ],
        example_questions=[
            "How do you handle unexpected changes to your plans or routine?",
            "Do you have specific routines that are important to follow?",
            "What happens if something in your environment is different from usual?",
            "Do you eat the same foods regularly or prefer variety?",
            "How do you feel when plans change at the last minute?",
        ],
    ),

    AssessmentDomain(
        code="restricted_interests",
        name="Restricted Interests",
        category=DomainCategory.RESTRICTED_REPETITIVE,
        description="Highly focused, intense interests that may be unusual in intensity or focus",
        indicators=[
            "Intense preoccupation with specific topics",
            "Unusually deep knowledge in narrow areas",
            "Difficulty shifting focus from interests",
            "Interests in unusual topics or aspects of topics",
            "Collecting behaviors",
            "Talking extensively about interests regardless of listener response",
            "Strong attachment to specific objects",
        ],
        example_questions=[
            "What topics or activities are you most passionate about?",
            "How much time do you spend on your main interests each day?",
            "Do others comment on how much you know about certain topics?",
            "Have your interests changed over time or stayed fairly consistent?",
            "Do you find it hard to stop thinking about your interests?",
        ],
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
            "Visual fascination with lights or movement",
            "Sensitivity to food textures or tastes",
            "Overwhelm in busy or loud environments",
        ],
        example_questions=[
            "Are there any sounds, lights, or textures that bother you more than others?",
            "Do you notice things in your environment that others might miss?",
            "How do you react to unexpected loud noises or bright lights?",
            "Are there certain textures of food or clothing you avoid?",
            "Do you seek out specific sensory experiences (pressure, spinning, etc.)?",
        ],
    ),

    # -------------------------------------------------------------------------
    # DEVELOPMENTAL HISTORY
    # -------------------------------------------------------------------------
    AssessmentDomain(
        code="developmental_milestones",
        name="Developmental Milestones",
        category=DomainCategory.DEVELOPMENTAL,
        description="Early developmental history and milestone timing",
        indicators=[
            "Language development timing (early, late, unusual)",
            "Motor milestone timing",
            "Social smile and joint attention development",
            "Regression of previously acquired skills",
            "Early play patterns (solitary, parallel, interactive)",
            "Response to name as infant/toddler",
            "Early attachment patterns",
        ],
        example_questions=[
            "What do you know about when you started talking as a child?",
            "Were there ever skills you had that seemed to go away?",
            "What were you told about your early development?",
            "How did you play as a young child? Alone or with others?",
            "Did your parents ever have concerns about your development?",
        ],
        weight=0.8,  # Historical info, less certain
    ),

    # -------------------------------------------------------------------------
    # FUNCTIONAL IMPACT
    # -------------------------------------------------------------------------
    AssessmentDomain(
        code="daily_functioning",
        name="Daily Functioning",
        category=DomainCategory.FUNCTIONAL,
        description="Impact on daily life, independence, and adaptive functioning",
        indicators=[
            "Self-care abilities and challenges",
            "Employment or academic difficulties",
            "Need for support in daily activities",
            "Living situation and independence level",
            "Executive function challenges",
            "Time management difficulties",
            "Organization challenges",
        ],
        example_questions=[
            "How do you manage day-to-day tasks like cooking, cleaning, or appointments?",
            "What kinds of support, if any, do you find helpful?",
            "How has this affected your work or education?",
            "Do you live independently? What's that like for you?",
            "What's most challenging about managing daily life?",
        ],
        weight=0.7,  # Important context but not diagnostic
    ),

    AssessmentDomain(
        code="emotional_regulation",
        name="Emotional Regulation",
        category=DomainCategory.FUNCTIONAL,
        description="Ability to manage and express emotions appropriately",
        indicators=[
            "Meltdowns or shutdowns",
            "Difficulty identifying own emotions",
            "Intense emotional responses",
            "Delayed emotional processing",
            "Difficulty calming down once upset",
            "Alexithymia (trouble describing feelings)",
            "Emotional exhaustion from social situations",
        ],
        example_questions=[
            "How do you typically handle strong emotions like frustration or anxiety?",
            "Do you ever feel overwhelmed to the point of shutting down?",
            "Is it easy or difficult for you to know what you're feeling?",
            "How long does it take you to recover after a stressful situation?",
            "Do social situations leave you feeling drained?",
        ],
        weight=0.7,
    ),
]


def get_domain_by_code(code: str) -> Optional[AssessmentDomain]:
    """Get a domain by its code."""
    for domain in AUTISM_DOMAINS:
        if domain.code == code:
            return domain
    return None


def get_domains_by_category(category: DomainCategory) -> list[AssessmentDomain]:
    """Get all domains in a category."""
    return [d for d in AUTISM_DOMAINS if d.category == category]


def get_all_domain_codes() -> list[str]:
    """Get list of all domain codes."""
    return [d.code for d in AUTISM_DOMAINS]


def get_domains_for_prompt() -> str:
    """Format domains for inclusion in LLM prompts."""
    lines = []
    for domain in AUTISM_DOMAINS:
        lines.append(f"## {domain.name} ({domain.code})")
        lines.append(f"Category: {domain.category.value}")
        lines.append(f"Description: {domain.description}")
        lines.append("Indicators to look for:")
        for indicator in domain.indicators:
            lines.append(f"  - {indicator}")
        lines.append("")
    return "\n".join(lines)
