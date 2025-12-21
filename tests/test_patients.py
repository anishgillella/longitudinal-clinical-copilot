import pytest
from httpx import AsyncClient
from uuid import UUID


@pytest.mark.asyncio
async def test_create_patient(client: AsyncClient):
    """Test creating a new patient."""
    patient_data = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "email": "john.doe@example.com",
        "primary_concern": "Assessment for autism spectrum",
    }

    response = await client.post("/api/v1/patients", json=patient_data)
    assert response.status_code == 201

    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["status"] == "active"
    assert "id" in data
    assert "clinician_id" in data


@pytest.mark.asyncio
async def test_list_patients(client: AsyncClient):
    """Test listing patients."""
    # Create a patient first
    patient_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "date_of_birth": "1985-03-20",
    }
    await client.post("/api/v1/patients", json=patient_data)

    # List patients
    response = await client.get("/api/v1/patients")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_patient(client: AsyncClient):
    """Test getting a patient by ID."""
    # Create a patient first
    patient_data = {
        "first_name": "Bob",
        "last_name": "Johnson",
        "date_of_birth": "1975-11-30",
    }
    create_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = create_response.json()["id"]

    # Get the patient
    response = await client.get(f"/api/v1/patients/{patient_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["first_name"] == "Bob"
    assert data["last_name"] == "Johnson"


@pytest.mark.asyncio
async def test_update_patient(client: AsyncClient):
    """Test updating a patient."""
    # Create a patient first
    patient_data = {
        "first_name": "Alice",
        "last_name": "Williams",
        "date_of_birth": "1995-07-10",
    }
    create_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = create_response.json()["id"]

    # Update the patient
    update_data = {"primary_concern": "Updated concern"}
    response = await client.put(f"/api/v1/patients/{patient_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["primary_concern"] == "Updated concern"


@pytest.mark.asyncio
async def test_delete_patient(client: AsyncClient):
    """Test soft deleting a patient."""
    # Create a patient first
    patient_data = {
        "first_name": "Charlie",
        "last_name": "Brown",
        "date_of_birth": "2000-01-01",
    }
    create_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = create_response.json()["id"]

    # Delete the patient
    response = await client.delete(f"/api/v1/patients/{patient_id}")
    assert response.status_code == 204

    # Verify patient is discharged
    get_response = await client.get(f"/api/v1/patients/{patient_id}")
    assert get_response.json()["status"] == "discharged"


@pytest.mark.asyncio
async def test_patient_not_found(client: AsyncClient):
    """Test getting a non-existent patient."""
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = await client.get(f"/api/v1/patients/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_patient_history(client: AsyncClient):
    """Test adding history to a patient."""
    # Create a patient first
    patient_data = {
        "first_name": "David",
        "last_name": "Lee",
        "date_of_birth": "1988-09-25",
    }
    create_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = create_response.json()["id"]

    # Add history
    history_data = {
        "history_type": "medical",
        "title": "Previous diagnosis",
        "description": "ADHD diagnosed in childhood",
        "occurred_at": "2000-05-15",
    }
    response = await client.post(f"/api/v1/patients/{patient_id}/history", json=history_data)
    assert response.status_code == 201

    data = response.json()
    assert data["title"] == "Previous diagnosis"
    assert data["history_type"] == "medical"


@pytest.mark.asyncio
async def test_get_patient_history(client: AsyncClient):
    """Test getting patient history."""
    # Create a patient and add history
    patient_data = {
        "first_name": "Eve",
        "last_name": "Taylor",
        "date_of_birth": "1992-12-05",
    }
    create_response = await client.post("/api/v1/patients", json=patient_data)
    patient_id = create_response.json()["id"]

    history_data = {
        "history_type": "psychiatric",
        "title": "Anxiety treatment",
        "description": "Received therapy for anxiety",
    }
    await client.post(f"/api/v1/patients/{patient_id}/history", json=history_data)

    # Get history
    response = await client.get(f"/api/v1/patients/{patient_id}/history")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
