import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_clinician(client: AsyncClient):
    """Test creating a new clinician."""
    clinician_data = {
        "email": "jane.smith@clinic.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "license_number": "PSY123456",
        "specialty": "psychiatrist",
    }

    response = await client.post("/api/v1/clinicians", json=clinician_data)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "jane.smith@clinic.com"
    assert data["first_name"] == "Jane"
    assert data["specialty"] == "psychiatrist"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_clinicians(client: AsyncClient):
    """Test listing clinicians."""
    # Create a clinician first
    clinician_data = {
        "email": "dr.jones@clinic.com",
        "first_name": "Dr",
        "last_name": "Jones",
    }
    await client.post("/api/v1/clinicians", json=clinician_data)

    # List clinicians
    response = await client.get("/api/v1/clinicians")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_clinician(client: AsyncClient):
    """Test getting a clinician by ID."""
    # Create a clinician first
    clinician_data = {
        "email": "dr.wilson@clinic.com",
        "first_name": "Dr",
        "last_name": "Wilson",
    }
    create_response = await client.post("/api/v1/clinicians", json=clinician_data)
    clinician_id = create_response.json()["id"]

    # Get the clinician
    response = await client.get(f"/api/v1/clinicians/{clinician_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "dr.wilson@clinic.com"


@pytest.mark.asyncio
async def test_update_clinician(client: AsyncClient):
    """Test updating a clinician."""
    # Create a clinician first
    clinician_data = {
        "email": "dr.brown@clinic.com",
        "first_name": "Dr",
        "last_name": "Brown",
    }
    create_response = await client.post("/api/v1/clinicians", json=clinician_data)
    clinician_id = create_response.json()["id"]

    # Update the clinician
    update_data = {"specialty": "psychologist"}
    response = await client.put(f"/api/v1/clinicians/{clinician_id}", json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["specialty"] == "psychologist"


@pytest.mark.asyncio
async def test_delete_clinician(client: AsyncClient):
    """Test deleting a clinician."""
    # Create a clinician first
    clinician_data = {
        "email": "dr.temp@clinic.com",
        "first_name": "Temp",
        "last_name": "Doctor",
    }
    create_response = await client.post("/api/v1/clinicians", json=clinician_data)
    clinician_id = create_response.json()["id"]

    # Delete the clinician
    response = await client.delete(f"/api/v1/clinicians/{clinician_id}")
    assert response.status_code == 204

    # Verify clinician is deleted
    get_response = await client.get(f"/api/v1/clinicians/{clinician_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_clinician_not_found(client: AsyncClient):
    """Test getting a non-existent clinician."""
    fake_id = "00000000-0000-0000-0000-000000000999"
    response = await client.get(f"/api/v1/clinicians/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_email(client: AsyncClient):
    """Test creating clinician with duplicate email."""
    clinician_data = {
        "email": "duplicate@clinic.com",
        "first_name": "First",
        "last_name": "Clinician",
    }
    await client.post("/api/v1/clinicians", json=clinician_data)

    # Try to create another with same email
    response = await client.post("/api/v1/clinicians", json=clinician_data)
    assert response.status_code == 400
