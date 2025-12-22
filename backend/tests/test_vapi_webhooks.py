import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
async def session_with_vapi_id(client: AsyncClient) -> tuple[str, str]:
    """Create a patient, session, and link a VAPI call ID."""
    # Create patient
    patient_data = {
        "first_name": "Webhook",
        "last_name": "Test",
        "date_of_birth": "1985-06-15",
    }
    patient_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = patient_response.json()["id"]

    # Create session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    session_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = session_response.json()["id"]

    # Link VAPI call
    vapi_call_id = f"vapi-{uuid4().hex[:8]}"
    await client.post(f"/api/v1/sessions/{session_id}/link/{vapi_call_id}")

    return session_id, vapi_call_id


@pytest.mark.asyncio
async def test_webhook_status_update_in_progress(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling status-update webhook for call start."""
    session_id, vapi_call_id = session_with_vapi_id

    payload = {
        "type": "status-update",
        "status": "in-progress",
        "call": {"id": vapi_call_id},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    # Verify session updated
    session_response = await client.get(f"/api/v1/sessions/{session_id}")
    session = session_response.json()
    assert session["status"] == "active"
    assert session["started_at"] is not None


@pytest.mark.asyncio
async def test_webhook_transcript(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling transcript webhook."""
    session_id, vapi_call_id = session_with_vapi_id

    # Send first transcript
    payload1 = {
        "type": "transcript",
        "call": {"id": vapi_call_id},
        "transcript": {
            "role": "assistant",
            "text": "Hello, how are you feeling today?",
            "timestamp": 0,
        },
    }
    response1 = await client.post("/api/v1/vapi/webhook", json=payload1)
    assert response1.status_code == 200

    # Send second transcript
    payload2 = {
        "type": "transcript",
        "call": {"id": vapi_call_id},
        "transcript": {
            "role": "user",
            "text": "I'm feeling okay, a bit anxious.",
            "timestamp": 5000,
        },
    }
    response2 = await client.post("/api/v1/vapi/webhook", json=payload2)
    assert response2.status_code == 200

    # Verify transcripts stored
    transcript_response = await client.get(f"/api/v1/sessions/{session_id}/transcript")
    transcript = transcript_response.json()
    assert transcript["total_entries"] == 2
    assert transcript["entries"][0]["role"] == "assistant"
    assert transcript["entries"][0]["content"] == "Hello, how are you feeling today?"
    assert transcript["entries"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_webhook_hang(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling hang/end call webhook."""
    session_id, vapi_call_id = session_with_vapi_id

    # First start the call
    start_payload = {
        "type": "status-update",
        "status": "in-progress",
        "call": {"id": vapi_call_id},
        "timestamp": "2024-01-15T10:00:00Z",
    }
    await client.post("/api/v1/vapi/webhook", json=start_payload)

    # Then end it
    hang_payload = {
        "type": "hang",
        "call": {"id": vapi_call_id},
        "endedReason": "assistant-ended-call",
        "timestamp": "2024-01-15T10:30:00Z",
    }

    response = await client.post("/api/v1/vapi/webhook", json=hang_payload)
    assert response.status_code == 200

    # Verify session ended
    session_response = await client.get(f"/api/v1/sessions/{session_id}")
    session = session_response.json()
    assert session["status"] == "completed"
    assert session["ended_at"] is not None
    assert session["completion_reason"] == "completed"


@pytest.mark.asyncio
async def test_webhook_end_of_call_report(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling end-of-call-report webhook."""
    session_id, vapi_call_id = session_with_vapi_id

    payload = {
        "type": "end-of-call-report",
        "call": {
            "id": vapi_call_id,
            "duration": 1800,  # 30 minutes
            "recordingUrl": "https://vapi.ai/recordings/abc123.mp3",
        },
        "summary": "Patient discussed challenges with social interactions at work.",
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200

    # Verify session updated
    session_response = await client.get(f"/api/v1/sessions/{session_id}")
    session = session_response.json()
    assert session["duration_seconds"] == 1800
    assert session["summary"] == "Patient discussed challenges with social interactions at work."


@pytest.mark.asyncio
async def test_webhook_function_call_get_context(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling function-call webhook for get_patient_context."""
    session_id, vapi_call_id = session_with_vapi_id

    payload = {
        "type": "function-call",
        "call": {"id": vapi_call_id},
        "functionCall": {
            "name": "get_patient_context",
            "parameters": {},
        },
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "result" in data
    assert "patient_name" in data["result"]


@pytest.mark.asyncio
async def test_webhook_function_call_flag_concern(client: AsyncClient, session_with_vapi_id: tuple):
    """Test handling function-call webhook for flag_concern."""
    session_id, vapi_call_id = session_with_vapi_id

    payload = {
        "type": "function-call",
        "call": {"id": vapi_call_id},
        "functionCall": {
            "name": "flag_concern",
            "parameters": {
                "concern": "Patient mentioned feeling hopeless",
                "severity": "high",
            },
        },
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["result"]["flagged"] is True

    # Verify concern stored in session
    session_response = await client.get(f"/api/v1/sessions/{session_id}")
    session = session_response.json()
    assert "concerns" in session["key_topics"]
    assert len(session["key_topics"]["concerns"]) == 1
    assert session["key_topics"]["concerns"][0]["severity"] == "high"


@pytest.mark.asyncio
async def test_webhook_unknown_event(client: AsyncClient):
    """Test handling unknown webhook event type."""
    payload = {
        "type": "unknown-event-type",
        "call": {"id": "some-call-id"},
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ignored"


@pytest.mark.asyncio
async def test_webhook_no_call_id(client: AsyncClient):
    """Test handling webhook with missing call ID."""
    payload = {
        "type": "transcript",
        "transcript": {
            "role": "user",
            "text": "Hello",
        },
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


@pytest.mark.asyncio
async def test_webhook_assistant_request(client: AsyncClient):
    """Test handling assistant-request webhook."""
    payload = {
        "type": "assistant-request",
        "call": {"id": "new-call-id"},
    }

    response = await client.post("/api/v1/vapi/webhook", json=payload)
    assert response.status_code == 200

    data = response.json()
    # We use pre-configured assistants, so return None
    assert data["assistant"] is None


@pytest.mark.asyncio
async def test_full_session_lifecycle(client: AsyncClient):
    """Test complete session lifecycle via webhooks."""
    # 1. Create patient
    patient_response = await client.post(
        "/api/v1/patients",
        json={
            "first_name": "Lifecycle",
            "last_name": "Test",
            "date_of_birth": "1992-03-20",
            "primary_concern": "Assessment for autism spectrum",
        },
    )
    patient_id = patient_response.json()["id"]

    # 2. Create session
    session_response = await client.post(
        "/api/v1/sessions",
        json={
            "patient_id": patient_id,
            "session_type": "intake",
            "vapi_assistant_id": "autism-intake-assistant",
        },
    )
    session_id = session_response.json()["id"]

    # 3. Link VAPI call (simulating call initiation)
    vapi_call_id = "lifecycle-test-call-123"
    await client.post(f"/api/v1/sessions/{session_id}/link/{vapi_call_id}")

    # 4. Call starts
    await client.post(
        "/api/v1/vapi/webhook",
        json={
            "type": "status-update",
            "status": "in-progress",
            "call": {"id": vapi_call_id},
            "timestamp": "2024-01-15T10:00:00Z",
        },
    )

    # 5. Transcripts come in
    transcripts = [
        ("assistant", "Hello, thank you for joining. How are you today?", 0),
        ("user", "Hi, I'm doing alright. A bit nervous.", 3000),
        ("assistant", "That's completely understandable. Let's take this at your pace.", 6000),
        ("user", "I've always had trouble with social situations.", 10000),
    ]

    for role, text, ts in transcripts:
        await client.post(
            "/api/v1/vapi/webhook",
            json={
                "type": "transcript",
                "call": {"id": vapi_call_id},
                "transcript": {"role": role, "text": text, "timestamp": ts},
            },
        )

    # 6. Function call to flag concern
    await client.post(
        "/api/v1/vapi/webhook",
        json={
            "type": "function-call",
            "call": {"id": vapi_call_id},
            "functionCall": {
                "name": "flag_concern",
                "parameters": {"concern": "Social anxiety mentioned", "severity": "moderate"},
            },
        },
    )

    # 7. Call ends
    await client.post(
        "/api/v1/vapi/webhook",
        json={
            "type": "hang",
            "call": {"id": vapi_call_id},
            "endedReason": "assistant-ended-call",
            "timestamp": "2024-01-15T10:30:00Z",
        },
    )

    # 8. End of call report
    await client.post(
        "/api/v1/vapi/webhook",
        json={
            "type": "end-of-call-report",
            "call": {
                "id": vapi_call_id,
                "duration": 1800,
                "recordingUrl": "https://vapi.ai/recordings/lifecycle-test.mp3",
            },
            "summary": "Initial intake session. Patient discussed social challenges.",
        },
    )

    # 9. Verify final state
    final_session = await client.get(f"/api/v1/sessions/{session_id}")
    session = final_session.json()

    assert session["status"] == "completed"
    assert session["duration_seconds"] == 1800
    assert session["summary"] == "Initial intake session. Patient discussed social challenges."
    assert "concerns" in session["key_topics"]

    # Verify transcript
    transcript_response = await client.get(f"/api/v1/sessions/{session_id}/transcript")
    transcript = transcript_response.json()
    assert transcript["total_entries"] == 4

    # Verify formatted text transcript
    text_response = await client.get(f"/api/v1/sessions/{session_id}/transcript/text")
    text = text_response.json()["transcript"]
    assert "Hello, thank you for joining" in text
    assert "trouble with social situations" in text
