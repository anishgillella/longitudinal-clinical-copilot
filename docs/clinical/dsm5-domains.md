# DSM-5 Autism Spectrum Disorder Criteria

This document explains the DSM-5 diagnostic criteria for Autism Spectrum Disorder (ASD) and how our system maps clinical observations to these domains.

## Overview

The DSM-5 (Diagnostic and Statistical Manual of Mental Disorders, 5th Edition) defines autism through two main categories:

1. **Domain A**: Persistent deficits in social communication and social interaction
2. **Domain B**: Restricted, repetitive patterns of behavior, interests, or activities

For an ASD diagnosis:
- **All 3 criteria in Domain A** must be met
- **At least 2 of 4 criteria in Domain B** must be met
- Symptoms must be present in early developmental period
- Symptoms must cause clinically significant impairment
- Not better explained by intellectual disability or global developmental delay

## Domain A: Social Communication & Interaction

All three must be present (currently or by history):

### A1: Social-Emotional Reciprocity

**Clinical Definition**: Deficits in social-emotional reciprocity, ranging from abnormal social approach and failure of normal back-and-forth conversation, to reduced sharing of interests, emotions, or affect, to failure to initiate or respond to social interactions.

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Difficulty with back-and-forth conversation | "He talks AT people, not with them" |
| Reduced sharing of interests | "She never comes to show us things she's excited about" |
| Failure to respond to social bids | "When other kids wave, he doesn't wave back" |
| Atypical social approaches | "She just walks up and starts talking about trains" |
| One-sided conversations | "He can talk for 30 minutes without asking any questions" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "reduced_social_reciprocity",
  "evidence": "Mother reports child talks extensively about dinosaurs without noticing listener's disinterest",
  "maps_to_domain": "A1",
  "intensity": 0.7,
  "confidence": 0.8
}
```

### A2: Nonverbal Communication

**Clinical Definition**: Deficits in nonverbal communicative behaviors used for social interaction, ranging from poorly integrated verbal and nonverbal communication, to abnormalities in eye contact and body language, to deficits in understanding and use of gestures, to a total lack of facial expressions and nonverbal communication.

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Reduced or atypical eye contact | "He looks at my forehead, not my eyes" |
| Limited use of gestures | "She doesn't point to show us things" |
| Flat or unusual facial expressions | "His face doesn't change even when excited" |
| Difficulty reading others' expressions | "He can't tell when I'm upset" |
| Mismatch between verbal and nonverbal | "Says he's fine while clearly distressed" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "atypical_eye_contact",
  "evidence": "Parent states 'He has always avoided looking at people's faces, even as a baby'",
  "maps_to_domain": "A2",
  "intensity": 0.8,
  "confidence": 0.9
}
```

### A3: Relationships

**Clinical Definition**: Deficits in developing, maintaining, and understanding relationships, ranging from difficulties adjusting behavior to suit various social contexts, to difficulties in sharing imaginative play or in making friends, to absence of interest in peers.

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Difficulty making friends | "He's never been invited to a birthday party" |
| Preference for solitary play | "She plays alone, even when other kids are around" |
| Challenges with imaginative play | "He lines up toys but doesn't pretend with them" |
| Difficulty adjusting to social contexts | "Uses the same volume whether at library or playground" |
| Limited interest in peers | "He prefers adults or much younger children" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "difficulty_maintaining_friendships",
  "evidence": "Mother describes how child had one friend in 2nd grade but 'the friendship just faded' and child didn't seem to notice or care",
  "maps_to_domain": "A3",
  "intensity": 0.6,
  "confidence": 0.7
}
```

## Domain B: Restricted, Repetitive Behaviors

At least 2 of 4 must be present (currently or by history):

### B1: Stereotyped or Repetitive Behaviors

**Clinical Definition**: Stereotyped or repetitive motor movements, use of objects, or speech (e.g., simple motor stereotypies, lining up toys or flipping objects, echolalia, idiosyncratic phrases).

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Motor stereotypies | "Hand flapping when excited" |
| Echolalia | "Repeats what you just said back to you" |
| Object stereotypies | "Spins wheels for extended periods" |
| Repetitive object use | "Lines up all his cars by color every day" |
| Scripted/idiosyncratic speech | "Uses movie quotes as responses" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "motor_stereotypy",
  "evidence": "Father describes 'hand flapping whenever he gets excited, like when his favorite show comes on'",
  "maps_to_domain": "B1",
  "intensity": 0.7,
  "confidence": 0.9
}
```

### B2: Insistence on Sameness

**Clinical Definition**: Insistence on sameness, inflexible adherence to routines, or ritualized patterns of verbal or nonverbal behavior (e.g., extreme distress at small changes, difficulties with transitions, rigid thinking patterns, greeting rituals, need to take same route or eat same food every day).

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Distress at changes | "Complete meltdown when we took a different route" |
| Rigid routines | "Must eat breakfast foods in exact same order" |
| Ritualized behaviors | "Has to touch the doorframe three times" |
| Difficulty with transitions | "Takes 30 minutes to get out the door" |
| Rigid thinking | "If the rule says X, there are no exceptions" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "distress_at_routine_changes",
  "evidence": "Parent reports 'When they moved his desk at school, he couldn't focus all day and came home crying'",
  "maps_to_domain": "B2",
  "intensity": 0.8,
  "confidence": 0.85
}
```

### B3: Restricted Interests

**Clinical Definition**: Highly restricted, fixated interests that are abnormal in intensity or focus (e.g., strong attachment to or preoccupation with unusual objects, excessively circumscribed or perseverative interests).

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Intense focused interests | "Knows every train model from every year" |
| Unusual interest topics | "Obsessed with vacuum cleaners since age 3" |
| Difficulty shifting from interests | "Can only talk about Minecraft" |
| Preoccupation with parts of objects | "More interested in wheels than the car itself" |
| Collecting/cataloging behaviors | "Has documented every license plate in our town" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "behavioral",
  "signal_name": "circumscribed_interest",
  "evidence": "Child has encyclopedic knowledge of World War II aircraft and 'brings every conversation back to planes somehow'",
  "maps_to_domain": "B3",
  "intensity": 0.75,
  "confidence": 0.8
}
```

### B4: Sensory Processing

**Clinical Definition**: Hyper- or hyporeactivity to sensory input or unusual interest in sensory aspects of the environment (e.g., apparent indifference to pain/temperature, adverse response to specific sounds or textures, excessive smelling or touching of objects, visual fascination with lights or movement).

**What to Look For**:
| Indicator | Example in Transcript |
|-----------|----------------------|
| Sound sensitivity | "Covers ears during fire drills" |
| Texture aversions | "Only wears certain fabrics" |
| Pain insensitivity | "Didn't cry when he broke his arm" |
| Visual seeking | "Stares at spinning objects" |
| Smell/taste sensitivity | "Gags at certain food smells" |

**Signal Extraction Examples**:
```json
{
  "signal_type": "sensory",
  "signal_name": "auditory_hypersensitivity",
  "evidence": "Mother describes 'He can hear the refrigerator hum from upstairs and it bothers him. Cafeteria is impossible.'",
  "maps_to_domain": "B4",
  "intensity": 0.8,
  "confidence": 0.9
}
```

## Severity Levels

Once ASD is diagnosed, severity is specified for each domain:

| Level | Description | Support Needs |
|-------|-------------|---------------|
| **Level 1** | "Requiring support" | Noticeable impairments, can function with minimal support |
| **Level 2** | "Requiring substantial support" | Marked deficits, need regular support |
| **Level 3** | "Requiring very substantial support" | Severe deficits, need extensive support |

## How Our System Uses This

### Signal Extraction
When the LLM analyzes a transcript, it looks for statements that map to these domains:

```
Transcript: "She lines up her dolls by height every morning
            and gets upset if anyone moves them."

Extracted Signal:
├── Domain: B1 (Stereotyped behaviors) - lining up objects
├── Domain: B2 (Insistence on sameness) - upset at change
├── Intensity: 0.7 (moderate-high)
└── Evidence: Direct parent quote
```

### Domain Scoring
Signals accumulate into domain scores over multiple sessions:

```
Patient: Alex Thompson
Sessions: 5

Domain Scores:
├── A1 (Social Reciprocity):     0.65 (8 signals)
├── A2 (Nonverbal):              0.45 (4 signals)
├── A3 (Relationships):          0.55 (6 signals)
├── B1 (Stereotyped):            0.70 (7 signals)
├── B2 (Sameness):               0.80 (9 signals)  ← Highest
├── B3 (Restricted Interests):   0.60 (5 signals)
└── B4 (Sensory):                0.75 (8 signals)
```

### Hypothesis Generation
Based on accumulated evidence, the system generates probabilistic hypotheses:

```
Hypothesis: ASD Level 1
├── Evidence Strength: 72%
├── Uncertainty: 18%
├── Supporting Signals: 34
├── Contradicting Signals: 5
└── Recommendation: Continue assessment, focus on A2 domain
```

## Important Notes

1. **This system does not diagnose** - It supports clinician decision-making
2. **Clinician review required** - All AI extractions must be confirmed
3. **Context matters** - Same behavior may mean different things
4. **Developmental history** - Early symptoms are important even if not current
5. **Rule out other conditions** - Differential diagnosis is essential

## References

- American Psychiatric Association. (2013). Diagnostic and statistical manual of mental disorders (5th ed.)
- Lord, C., et al. (2012). Autism Diagnostic Observation Schedule, Second Edition (ADOS-2)
- Rutter, M., Le Couteur, A., & Lord, C. (2003). Autism Diagnostic Interview-Revised (ADI-R)
