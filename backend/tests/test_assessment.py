"""
Tests for Assessment API Endpoints

Tests the clinical assessment functionality including signals, scores, hypotheses, and processing.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime

from src.assessment.domains import AUTISM_DOMAINS, get_domain_by_code, DomainCategory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def patient_id(client: AsyncClient) -> str:
    """Create a patient and return its ID."""
    patient_data = {
        "first_name": "Assessment",
        "last_name": "TestPatient",
        "date_of_birth": "1995-06-15",
        "primary_concern": "Autism spectrum assessment",
    }
    response = await client.post("/api/v1/patients", json=patient_data)
    return response.json()["id"]


@pytest.fixture
async def session_id(client: AsyncClient, patient_id: str) -> str:
    """Create a completed session and return its ID."""
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    response = await client.post("/api/v1/sessions", json=session_data)
    return response.json()["id"]


# =============================================================================
# Domain Definition Tests
# =============================================================================

class TestDomainDefinitions:
    """Tests for autism assessment domain definitions."""

    def test_all_domains_exist(self):
        """Verify all expected domains are defined."""
        assert len(AUTISM_DOMAINS) >= 10, "Should have at least 10 autism assessment domains"

        # Check key domains exist
        expected_codes = [
            "social_emotional_reciprocity",
            "nonverbal_communication",
            "relationships",
            "stereotyped_movements",
            "insistence_sameness",
            "restricted_interests",
            "sensory_reactivity",
        ]

        actual_codes = [d.code for d in AUTISM_DOMAINS]
        for code in expected_codes:
            assert code in actual_codes, f"Missing domain: {code}"

    def test_domain_categories(self):
        """Verify domains have proper categories."""
        social_count = 0
        rrb_count = 0

        for domain in AUTISM_DOMAINS:
            assert domain.category in DomainCategory, f"Invalid category for {domain.code}"
            if domain.category == DomainCategory.SOCIAL_COMMUNICATION:
                social_count += 1
            elif domain.category == DomainCategory.RESTRICTED_REPETITIVE:
                rrb_count += 1

        # DSM-5 has 3 social communication and 4 RRB criteria
        assert social_count >= 3, "Should have at least 3 social communication domains"
        assert rrb_count >= 4, "Should have at least 4 RRB domains"

    def test_domain_indicators(self):
        """Verify all domains have indicators."""
        for domain in AUTISM_DOMAINS:
            assert domain.indicators, f"No indicators for {domain.code}"
            assert len(domain.indicators) >= 3, f"Need at least 3 indicators for {domain.code}"

    def test_domain_example_questions(self):
        """Verify all domains have example questions."""
        for domain in AUTISM_DOMAINS:
            assert domain.example_questions, f"No example questions for {domain.code}"
            assert len(domain.example_questions) >= 2, f"Need at least 2 questions for {domain.code}"

    def test_get_domain_by_code(self):
        """Test looking up domain by code."""
        domain = get_domain_by_code("social_emotional_reciprocity")
        assert domain is not None
        assert domain.name == "Social-Emotional Reciprocity"

        # Non-existent domain
        assert get_domain_by_code("nonexistent") is None


# =============================================================================
# Domain Reference Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_all_domains(client: AsyncClient):
    """Test getting all domain definitions."""
    response = await client.get("/api/v1/assessment/domains")
    assert response.status_code == 200

    data = response.json()
    assert "domains" in data
    assert "total" in data
    assert data["total"] >= 10

    # Check domain structure
    domain = data["domains"][0]
    assert "code" in domain
    assert "name" in domain
    assert "category" in domain
    assert "description" in domain
    assert "indicators" in domain
    assert "example_questions" in domain


@pytest.mark.asyncio
async def test_get_domain_details(client: AsyncClient):
    """Test getting a specific domain's details."""
    response = await client.get("/api/v1/assessment/domains/social_emotional_reciprocity")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == "social_emotional_reciprocity"
    assert data["name"] == "Social-Emotional Reciprocity"
    assert data["category"] == "social_communication"


@pytest.mark.asyncio
async def test_get_domain_not_found(client: AsyncClient):
    """Test getting a non-existent domain."""
    response = await client.get("/api/v1/assessment/domains/nonexistent_domain")
    assert response.status_code == 404


# =============================================================================
# Signal Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_session_signals_empty(client: AsyncClient, session_id: str):
    """Test getting signals for a session with no extractions."""
    response = await client.get(f"/api/v1/assessment/sessions/{session_id}/signals")
    assert response.status_code == 200

    data = response.json()
    assert data["signals"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_patient_signals_empty(client: AsyncClient, patient_id: str):
    """Test getting signals for a patient with no sessions."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/signals")
    assert response.status_code == 200

    data = response.json()
    assert data["signals"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_patient_signal_summary_empty(client: AsyncClient, patient_id: str):
    """Test getting signal summary for a patient with no signals."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/signals/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 0
    assert data["by_type"] == {}


# =============================================================================
# Domain Score Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_session_scores_empty(client: AsyncClient, session_id: str):
    """Test getting scores for a session with no scoring."""
    response = await client.get(f"/api/v1/assessment/sessions/{session_id}/scores")
    assert response.status_code == 200

    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_get_patient_latest_scores_empty(client: AsyncClient, patient_id: str):
    """Test getting latest scores for a patient with no sessions."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/scores/latest")
    assert response.status_code == 200

    data = response.json()
    assert data == {}


@pytest.mark.asyncio
async def test_get_patient_domains_overview_empty(client: AsyncClient, patient_id: str):
    """Test getting domains overview for a patient with no data."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/domains")
    assert response.status_code == 200

    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["domains"] == []


@pytest.mark.asyncio
async def test_get_domains_needing_exploration(client: AsyncClient, patient_id: str):
    """Test getting domains needing exploration."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/domains/exploration-needed")
    assert response.status_code == 200

    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["total_domains"] >= 10
    # With no data, all domains need exploration
    assert data["explored_domains"] == 0
    assert len(data["domains_needing_exploration"]) == data["total_domains"]


# =============================================================================
# Hypothesis Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_patient_hypotheses_empty(client: AsyncClient, patient_id: str):
    """Test getting hypotheses for a patient with no analysis."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/hypotheses")
    assert response.status_code == 200

    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_get_primary_hypothesis_none(client: AsyncClient, patient_id: str):
    """Test getting primary hypothesis when none exists."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/hypotheses/primary")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_get_hypothesis_history_not_found(client: AsyncClient):
    """Test getting history for non-existent hypothesis."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/assessment/hypotheses/{fake_id}/history")
    assert response.status_code == 404


# =============================================================================
# Session Summary Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_session_summary_none(client: AsyncClient, session_id: str):
    """Test getting summary for a session with no summary."""
    response = await client.get(f"/api/v1/assessment/sessions/{session_id}/summary")
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_get_patient_summaries_empty(client: AsyncClient, patient_id: str):
    """Test getting summaries for a patient with no sessions."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/summaries")
    assert response.status_code == 200

    data = response.json()
    assert data == []


# =============================================================================
# Processing Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_processing_status_new_session(client: AsyncClient, session_id: str):
    """Test getting processing status for a new session."""
    response = await client.get(f"/api/v1/assessment/sessions/{session_id}/processing-status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] in ["pending", "not_found"]


@pytest.mark.asyncio
async def test_get_processing_status_not_found(client: AsyncClient):
    """Test getting processing status for non-existent session."""
    fake_id = str(uuid4())
    response = await client.get(f"/api/v1/assessment/sessions/{fake_id}/processing-status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "not_found"


# =============================================================================
# Assessment Overview Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_patient_assessment_overview_empty(client: AsyncClient, patient_id: str):
    """Test getting assessment overview for a new patient."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/overview")
    assert response.status_code == 200

    data = response.json()
    assert data["patient_id"] == patient_id
    assert data["total_sessions"] == 0
    assert data["completed_sessions"] == 0
    assert data["total_signals"] == 0
    assert data["domains_with_data"] == 0
    assert data["current_hypotheses"] == []
    assert data["assessment_completeness"] == 0.0
    assert len(data["areas_needing_exploration"]) > 0


@pytest.mark.asyncio
async def test_get_patient_assessment_overview_with_session(client: AsyncClient, patient_id: str, session_id: str):
    """Test getting assessment overview with a session created."""
    response = await client.get(f"/api/v1/assessment/patients/{patient_id}/overview")
    assert response.status_code == 200

    data = response.json()
    assert data["patient_id"] == patient_id
    # Session is created but in pending status
    assert data["total_sessions"] == 1
    # Not completed yet
    assert data["completed_sessions"] == 0
