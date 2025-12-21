# REST API Specification

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.your-domain.com/api/v1
```

## Authentication

> **Local Development**: Authentication is disabled. All endpoints are open. Auth will be added in Phase 6 for production.

## Response Format

All responses follow this structure:

```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

Error responses:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## Clinician Endpoints

> **Note**: A default development clinician is auto-created on first request.

### List Clinicians

```http
GET /clinicians
```

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "00000000-0000-0000-0000-000000000001",
      "email": "dev@localhost",
      "first_name": "Development",
      "last_name": "Clinician",
      "specialty": "development",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Create Clinician

```http
POST /clinicians
```

**Request Body:**
```json
{
  "email": "clinician@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "license_number": "PSY123456",
  "specialty": "psychiatrist"
}
```

**Response:** `201 Created`

### Get Clinician

```http
GET /clinicians/{clinician_id}
```

**Response:** `200 OK`

---

## Patient Endpoints

### List Patients

```http
GET /patients
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status: `active`, `inactive`, `discharged` |
| search | string | Search by name |
| page | integer | Page number (default: 1) |
| limit | integer | Items per page (default: 20, max: 100) |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "first_name": "John",
      "last_name": "Doe",
      "date_of_birth": "1990-05-15",
      "status": "active",
      "intake_date": "2024-01-01",
      "session_count": 5,
      "last_session": "2024-01-10T14:30:00Z"
    }
  ],
  "meta": {
    "total": 42,
    "page": 1,
    "limit": 20,
    "pages": 3
  }
}
```

### Create Patient

```http
POST /patients
```

**Request Body:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-05-15",
  "gender": "male",
  "email": "john.doe@email.com",
  "phone": "+1234567890",
  "primary_concern": "Seeking assessment for autism spectrum",
  "referral_source": "Primary care physician"
}
```

**Response:** `201 Created`
```json
{
  "data": {
    "id": "uuid",
    "clinician_id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "email": "john.doe@email.com",
    "phone": "+1234567890",
    "primary_concern": "Seeking assessment for autism spectrum",
    "referral_source": "Primary care physician",
    "status": "active",
    "intake_date": "2024-01-15",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Get Patient

```http
GET /patients/{patient_id}
```

**Response:** `200 OK`
```json
{
  "data": {
    "id": "uuid",
    "clinician_id": "uuid",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "email": "john.doe@email.com",
    "phone": "+1234567890",
    "primary_concern": "Seeking assessment for autism spectrum",
    "referral_source": "Primary care physician",
    "status": "active",
    "intake_date": "2024-01-01",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### Update Patient

```http
PUT /patients/{patient_id}
```

**Request Body:**
```json
{
  "email": "john.new@email.com",
  "primary_concern": "Updated concern description"
}
```

**Response:** `200 OK`

### Delete Patient (Soft Delete)

```http
DELETE /patients/{patient_id}
```

**Response:** `204 No Content`

### Get Patient History

```http
GET /patients/{patient_id}/history
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| history_type | string | Filter: `medical`, `psychiatric`, `medication`, `life_event` |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "history_type": "medication",
      "title": "Started SSRI medication",
      "description": "Began fluoxetine 20mg daily",
      "occurred_at": "2023-06-15",
      "source": "clinician_entry",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Add History Entry

```http
POST /patients/{patient_id}/history
```

**Request Body:**
```json
{
  "history_type": "medication",
  "title": "Started SSRI medication",
  "description": "Began fluoxetine 20mg daily",
  "occurred_at": "2023-06-15"
}
```

**Response:** `201 Created`

---

## Session Endpoints

### Start Intake Session

```http
POST /sessions/intake
```

**Request Body:**
```json
{
  "patient_id": "uuid",
  "phone_number": "+1234567890",
  "additional_context": "Patient expressed interest in understanding their social challenges"
}
```

**Response:** `201 Created`
```json
{
  "data": {
    "id": "uuid",
    "patient_id": "uuid",
    "session_type": "intake",
    "status": "pending",
    "vapi_call_id": "vapi_123",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Start Check-in Session

```http
POST /sessions/checkin
```

**Request Body:**
```json
{
  "patient_id": "uuid",
  "phone_number": "+1234567890",
  "focus_areas": ["sleep patterns", "social interactions at work"]
}
```

**Response:** `201 Created`

### Get Session

```http
GET /sessions/{session_id}
```

**Response:** `200 OK`
```json
{
  "data": {
    "id": "uuid",
    "patient_id": "uuid",
    "clinician_id": "uuid",
    "session_type": "intake",
    "status": "completed",
    "started_at": "2024-01-15T10:30:00Z",
    "ended_at": "2024-01-15T11:00:00Z",
    "duration_seconds": 1800,
    "completion_reason": "completed"
  }
}
```

### Get Session Transcript

```http
GET /sessions/{session_id}/transcript
```

**Response:** `200 OK`
```json
{
  "data": {
    "session_id": "uuid",
    "entries": [
      {
        "role": "assistant",
        "content": "Hello John, thank you for taking the time...",
        "timestamp_ms": 0
      },
      {
        "role": "patient",
        "content": "Hi, thank you for having me...",
        "timestamp_ms": 5000
      }
    ],
    "total_entries": 45
  }
}
```

### List Patient Sessions

```http
GET /patients/{patient_id}/sessions
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| session_type | string | Filter: `intake`, `checkin`, `targeted_probe` |
| status | string | Filter: `pending`, `active`, `completed`, `failed` |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "session_type": "intake",
      "status": "completed",
      "started_at": "2024-01-15T10:30:00Z",
      "duration_seconds": 1800
    }
  ]
}
```

### Trigger Post-Session Processing

```http
POST /sessions/{session_id}/process
```

**Response:** `202 Accepted`
```json
{
  "data": {
    "processing_id": "uuid",
    "status": "queued"
  }
}
```

---

## Assessment Endpoints

### Get Patient Signals

```http
GET /patients/{patient_id}/signals
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| signal_type | string | Filter: `linguistic`, `behavioral`, `emotional` |
| session_id | uuid | Filter by session |
| significance | string | Filter: `low`, `moderate`, `high` |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "signal_type": "behavioral",
      "signal_name": "restricted_topic_focus",
      "evidence": "Patient spent 10 minutes discussing train schedules...",
      "intensity": 0.75,
      "confidence": 0.85,
      "maps_to_domain": "restricted_interests",
      "clinical_significance": "moderate",
      "extracted_at": "2024-01-15T11:05:00Z"
    }
  ]
}
```

### Get Domain Scores

```http
GET /patients/{patient_id}/domains
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| category | string | Filter: `social_communication`, `restricted_repetitive` |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "domain_code": "social_reciprocity",
      "domain_name": "Social-Emotional Reciprocity",
      "category": "social_communication",
      "latest_score": {
        "normalized_score": 0.65,
        "confidence": 0.78,
        "evidence_count": 12,
        "assessed_at": "2024-01-15T11:05:00Z"
      },
      "trend": {
        "direction": "stable",
        "change_30d": -0.02
      }
    }
  ]
}
```

### Get Hypotheses

```http
GET /patients/{patient_id}/hypotheses
```

**Response:** `200 OK`
```json
{
  "data": [
    {
      "condition_code": "asd_level_1",
      "condition_name": "Autism Spectrum Disorder - Level 1",
      "evidence_strength": 0.72,
      "uncertainty": 0.15,
      "confidence_band": {
        "low": 0.57,
        "high": 0.87
      },
      "trend": "increasing",
      "supporting_signals": 18,
      "contradicting_signals": 3,
      "explanation": "Evidence suggests significant challenges in social reciprocity...",
      "last_updated_at": "2024-01-15T11:05:00Z"
    }
  ]
}
```

### Get Hypothesis History

```http
GET /patients/{patient_id}/hypotheses/history
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| condition_code | string | Filter by condition |
| days | integer | Lookback period (default: 90) |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "condition_code": "asd_level_1",
      "history": [
        {
          "date": "2024-01-01",
          "evidence_strength": 0.45,
          "uncertainty": 0.25,
          "session_id": "uuid"
        },
        {
          "date": "2024-01-08",
          "evidence_strength": 0.58,
          "uncertainty": 0.20,
          "session_id": "uuid"
        }
      ]
    }
  ]
}
```

---

## Timeline Endpoints

### Get Patient Timeline

```http
GET /patients/{patient_id}/timeline
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| start_date | date | Start of range |
| end_date | date | End of range |
| event_type | string[] | Filter by types |
| significance | string | Minimum significance |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "date": "2024-01-15",
      "timestamp": "2024-01-15T10:30:00Z",
      "type": "session",
      "subtype": "intake",
      "title": "Initial Intake Session",
      "description": "Comprehensive intake session covering developmental history...",
      "significance": "high",
      "is_pinned": false,
      "session_id": "uuid"
    }
  ]
}
```

### Add Timeline Event

```http
POST /patients/{patient_id}/timeline/events
```

**Request Body:**
```json
{
  "event_type": "life_event",
  "event_subtype": "job_change",
  "title": "Started new job",
  "description": "Began position as software developer at tech company",
  "event_date": "2024-01-10",
  "significance": "high"
}
```

**Response:** `201 Created`

### Answer Temporal Question

```http
POST /patients/{patient_id}/temporal-query
```

**Request Body:**
```json
{
  "question": "When did sleep issues first appear?"
}
```

**Response:** `200 OK`
```json
{
  "data": {
    "answer": "Sleep difficulties were first mentioned in the session on January 8, 2024...",
    "evidence": [
      {
        "date": "2024-01-08",
        "event": "Check-in session",
        "relevance": "Patient first mentioned difficulty falling asleep"
      }
    ],
    "confidence": 0.85,
    "data_gaps": ["No information about sleep patterns before assessment began"]
  }
}
```

---

## Dashboard Endpoints

### Get Patient Overview

```http
GET /dashboard/patients/{patient_id}/overview
```

**Response:** `200 OK`
```json
{
  "data": {
    "patient": { ... },
    "status_summary": {
      "summary": "Patient has completed 5 sessions over 6 weeks. Evidence for ASD Level 1 has increased...",
      "last_updated": "2024-01-15",
      "alert_count": 2
    },
    "key_metrics": [
      {
        "id": "sessions",
        "label": "Sessions (30d)",
        "value": 3,
        "trend": "up",
        "context": "Check-ins and assessments"
      }
    ],
    "action_items": [
      {
        "type": "alert",
        "priority": "high",
        "title": "High significance signal detected",
        "action": "Review"
      }
    ],
    "current_hypotheses": [ ... ]
  }
}
```

### Get Domain Trends

```http
GET /dashboard/patients/{patient_id}/domain-trends
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| days | integer | Lookback period (default: 90) |

**Response:** `200 OK`
```json
{
  "data": {
    "domains": [
      {
        "code": "social_reciprocity",
        "name": "Social Reciprocity",
        "data": [
          {"date": "2024-01-01", "score": 0.6, "confidence": 0.7},
          {"date": "2024-01-15", "score": 0.55, "confidence": 0.75}
        ]
      }
    ]
  }
}
```

---

## Notes Endpoints

### Generate SOAP Note

```http
POST /sessions/{session_id}/notes/generate
```

**Response:** `201 Created`
```json
{
  "data": {
    "id": "uuid",
    "note_type": "soap",
    "subjective": "Patient reports ongoing challenges with...",
    "objective": "During the session, the following was observed...",
    "assessment": "Patterns consistent with social communication difficulties...",
    "plan": "1. Schedule follow-up in 2 weeks...",
    "ai_generated": true,
    "ai_suggestions": {
      "assessment": ["Consider exploring sensory sensitivities further"]
    },
    "status": "draft"
  }
}
```

### Update Note

```http
PUT /notes/{note_id}
```

**Request Body:**
```json
{
  "assessment": "Updated clinical assessment with additional observations..."
}
```

**Response:** `200 OK`

### Finalize Note

```http
POST /notes/{note_id}/finalize
```

**Response:** `200 OK`
```json
{
  "data": {
    "id": "uuid",
    "status": "final",
    "finalized_at": "2024-01-15T12:00:00Z"
  }
}
```

### Export Note

```http
GET /notes/{note_id}/export
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| format | string | Export format: `text`, `pdf`, `hl7`, `fhir` |

**Response:** `200 OK` with appropriate content type

---

## Alert Endpoints

### List Alerts

```http
GET /alerts
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter: `active`, `acknowledged`, `resolved`, `dismissed` |
| priority | string | Filter: `low`, `normal`, `high`, `urgent` |
| patient_id | uuid | Filter by patient |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "patient_id": "uuid",
      "patient_name": "John Doe",
      "alert_type": "high_signal",
      "priority": "high",
      "title": "High significance signal detected",
      "description": "Repetitive behavior pattern identified...",
      "status": "active",
      "created_at": "2024-01-15T11:05:00Z"
    }
  ]
}
```

### Acknowledge Alert

```http
POST /alerts/{alert_id}/acknowledge
```

**Response:** `200 OK`

### Resolve Alert

```http
POST /alerts/{alert_id}/resolve
```

**Request Body:**
```json
{
  "resolution_note": "Reviewed and discussed with patient in session"
}
```

**Response:** `200 OK`

---

## Rollup Endpoints

### Get Summary Rollups

```http
GET /patients/{patient_id}/rollups
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| rollup_type | string | Filter: `weekly`, `monthly`, `quarterly`, `yearly` |

**Response:** `200 OK`
```json
{
  "data": [
    {
      "id": "uuid",
      "rollup_type": "monthly",
      "period_start": "2024-01-01",
      "period_end": "2024-01-31",
      "summary": "This month included 4 sessions covering...",
      "session_count": 4,
      "total_duration_minutes": 120,
      "domain_trends": {
        "social_reciprocity": {
          "start_score": 0.6,
          "end_score": 0.55,
          "trend": "declining"
        }
      }
    }
  ]
}
```

### Generate Rollup

```http
POST /patients/{patient_id}/rollups/generate
```

**Request Body:**
```json
{
  "rollup_type": "monthly",
  "end_date": "2024-01-31"
}
```

**Response:** `201 Created`

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| UNAUTHORIZED | 401 | Invalid or missing token |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| VALIDATION_ERROR | 422 | Invalid request data |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |

---

## Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| General API | 100 requests/minute |
| Authentication | 5 requests/minute |
| Voice Sessions | 10 requests/hour |
| Data Exports | 10 requests/hour |
