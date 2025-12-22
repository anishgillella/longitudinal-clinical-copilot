import pytest
from httpx import AsyncClient
from uuid import UUID, uuid4
from datetime import datetime


@pytest.fixture
async def patient_id(client: AsyncClient) -> str:
    """Create a patient and return its ID."""
    patient_data = {
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "primary_concern": "Autism assessment",
    }
    response = await client.post("/api/v1/patients", json=patient_data)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient, patient_id: str):
    """Test creating a new voice session."""
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }

    response = await client.post("/api/v1/sessions", json=session_data)
    assert response.status_code == 201

    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["session_type"] == "intake"
    assert data["status"] == "pending"
    assert data["vapi_assistant_id"] == "test-assistant-123"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_session_with_schedule(client: AsyncClient, patient_id: str):
    """Test creating a scheduled session."""
    scheduled_time = "2024-12-25T10:00:00Z"
    session_data = {
        "patient_id": patient_id,
        "session_type": "checkin",
        "vapi_assistant_id": "test-assistant-123",
        "scheduled_at": scheduled_time,
    }

    response = await client.post("/api/v1/sessions", json=session_data)
    assert response.status_code == 201

    data = response.json()
    assert data["session_type"] == "checkin"
    assert data["scheduled_at"] is not None


@pytest.mark.asyncio
async def test_create_session_patient_not_found(client: AsyncClient):
    """Test creating a session for non-existent patient."""
    fake_patient_id = str(uuid4())
    session_data = {
        "patient_id": fake_patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }

    response = await client.post("/api/v1/sessions", json=session_data)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient, patient_id: str):
    """Test listing sessions."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    await client.post("/api/v1/sessions", json=session_data)

    # List all sessions
    response = await client.get("/api/v1/sessions")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_sessions_by_patient(client: AsyncClient, patient_id: str):
    """Test listing sessions filtered by patient."""
    # Create sessions
    for session_type in ["intake", "checkin"]:
        session_data = {
            "patient_id": patient_id,
            "session_type": session_type,
            "vapi_assistant_id": "test-assistant-123",
        }
        await client.post("/api/v1/sessions", json=session_data)

    # List by patient
    response = await client.get(f"/api/v1/sessions?patient_id={patient_id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_sessions_by_type(client: AsyncClient, patient_id: str):
    """Test listing sessions filtered by type."""
    # Create sessions
    for session_type in ["intake", "checkin", "checkin"]:
        session_data = {
            "patient_id": patient_id,
            "session_type": session_type,
            "vapi_assistant_id": "test-assistant-123",
        }
        await client.post("/api/v1/sessions", json=session_data)

    # List by type
    response = await client.get(f"/api/v1/sessions?patient_id={patient_id}&session_type=checkin")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert all(s["session_type"] == "checkin" for s in data)


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient, patient_id: str):
    """Test getting a session by ID."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    create_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = create_response.json()["id"]

    # Get the session
    response = await client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == session_id
    assert data["session_type"] == "intake"


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient):
    """Test getting a non-existent session."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/sessions/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_session(client: AsyncClient, patient_id: str):
    """Test updating a session."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    create_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = create_response.json()["id"]

    # Update the session
    update_data = {
        "summary": "Patient discussed social challenges at work",
        "key_topics": ["social_interaction", "workplace"],
    }
    response = await client.put(f"/api/v1/sessions/{session_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["summary"] == "Patient discussed social challenges at work"


@pytest.mark.asyncio
async def test_link_vapi_call(client: AsyncClient, patient_id: str):
    """Test linking a VAPI call ID to a session."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    create_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = create_response.json()["id"]

    # Link VAPI call
    vapi_call_id = "vapi-call-abc123"
    response = await client.post(f"/api/v1/sessions/{session_id}/link/{vapi_call_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["vapi_call_id"] == vapi_call_id
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_empty_transcript(client: AsyncClient, patient_id: str):
    """Test getting transcript for a session with no transcripts."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    create_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = create_response.json()["id"]

    # Get transcript
    response = await client.get(f"/api/v1/sessions/{session_id}/transcript")
    assert response.status_code == 200

    data = response.json()
    assert data["session_id"] == session_id
    assert data["entries"] == []
    assert data["total_entries"] == 0


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient, patient_id: str):
    """Test deleting a session."""
    # Create a session
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    create_response = await client.post("/api/v1/sessions", json=session_data)
    session_id = create_response.json()["id"]

    # Delete the session
    response = await client.delete(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 204

    # Verify deleted
    get_response = await client.get(f"/api/v1/sessions/{session_id}")
    assert get_response.status_code == 404
