"""
Tests for Longitudinal Memory API Endpoints

Tests the memory, timeline, context, and summarization functionality.
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
async def patient_id(client: AsyncClient) -> str:
    """Create a patient and return its ID."""
    patient_data = {
        "first_name": "Memory",
        "last_name": "TestPatient",
        "date_of_birth": "2012-03-15",
        "primary_concern": "Social communication difficulties",
    }
    response = await client.post("/api/v1/patients", json=patient_data)
    return response.json()["id"]


@pytest.fixture
async def session_id(client: AsyncClient, patient_id: str) -> str:
    """Create a session and return its ID."""
    session_data = {
        "patient_id": patient_id,
        "session_type": "intake",
        "vapi_assistant_id": "test-assistant-123",
    }
    response = await client.post("/api/v1/sessions", json=session_data)
    return response.json()["id"]


# =============================================================================
# Timeline Event Tests
# =============================================================================

class TestTimelineEvents:
    """Tests for timeline event endpoints."""

    @pytest.mark.asyncio
    async def test_add_timeline_event(self, client: AsyncClient, patient_id: str):
        """Test adding a timeline event."""
        event_data = {
            "event_type": "observation",
            "category": "social",
            "title": "Difficulty with peer interactions",
            "description": "Patient described challenges making friends at school.",
            "occurred_at": datetime.utcnow().isoformat(),
            "significance": "moderate",
            "source": "session_extraction",
            "confidence": 0.85,
        }

        response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json=event_data
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["event_type"] == "observation"
        assert data["category"] == "social"
        assert data["title"] == "Difficulty with peer interactions"
        assert data["significance"] == "moderate"

    @pytest.mark.asyncio
    async def test_get_patient_timeline_empty(self, client: AsyncClient, patient_id: str):
        """Test getting empty timeline."""
        response = await client.get(f"/api/v1/memory/patients/{patient_id}/timeline")
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["events"] == []
        assert data["total_events"] == 0

    @pytest.mark.asyncio
    async def test_get_patient_timeline_with_events(self, client: AsyncClient, patient_id: str):
        """Test getting timeline with events."""
        # Add multiple events
        for i in range(3):
            event_data = {
                "event_type": "observation",
                "category": "social",
                "title": f"Test Event {i}",
                "description": f"Description for event {i}",
                "occurred_at": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "significance": "moderate",
            }
            await client.post(
                f"/api/v1/memory/patients/{patient_id}/timeline",
                json=event_data
            )

        response = await client.get(f"/api/v1/memory/patients/{patient_id}/timeline")
        assert response.status_code == 200

        data = response.json()
        assert data["total_events"] == 3
        assert len(data["events"]) == 3

    @pytest.mark.asyncio
    async def test_get_timeline_with_filters(self, client: AsyncClient, patient_id: str):
        """Test filtering timeline events."""
        # Add events of different types
        await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json={
                "event_type": "observation",
                "category": "social",
                "title": "Social observation",
                "description": "Test",
                "occurred_at": datetime.utcnow().isoformat(),
                "significance": "moderate",
            }
        )
        await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json={
                "event_type": "concern",
                "category": "emotional",
                "title": "Emotional concern",
                "description": "Test",
                "occurred_at": datetime.utcnow().isoformat(),
                "significance": "high",
            }
        )

        # Filter by event_type
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline?event_type=observation"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(e["event_type"] == "observation" for e in data["events"])

        # Filter by significance
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline?significance=high"
        )
        assert response.status_code == 200
        data = response.json()
        assert all(e["significance"] == "high" for e in data["events"])

    @pytest.mark.asyncio
    async def test_get_timeline_summary(self, client: AsyncClient, patient_id: str):
        """Test getting timeline summary statistics."""
        # Add some events
        await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json={
                "event_type": "observation",
                "category": "social",
                "title": "Test",
                "description": "Test",
                "occurred_at": datetime.utcnow().isoformat(),
                "significance": "moderate",
            }
        )

        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline/summary"
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_events" in data
        assert "by_category" in data
        assert "by_significance" in data

    @pytest.mark.asyncio
    async def test_update_timeline_event(self, client: AsyncClient, patient_id: str):
        """Test updating a timeline event."""
        # Create event
        create_response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json={
                "event_type": "observation",
                "category": "social",
                "title": "Original Title",
                "description": "Original description",
                "occurred_at": datetime.utcnow().isoformat(),
                "significance": "low",
            }
        )
        event_id = create_response.json()["id"]

        # Update event
        response = await client.patch(
            f"/api/v1/memory/timeline/{event_id}",
            json={
                "title": "Updated Title",
                "significance": "high",
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["significance"] == "high"

    @pytest.mark.asyncio
    async def test_delete_timeline_event(self, client: AsyncClient, patient_id: str):
        """Test deleting a timeline event."""
        # Create event
        create_response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/timeline",
            json={
                "event_type": "observation",
                "category": "social",
                "title": "To Delete",
                "description": "Test",
                "occurred_at": datetime.utcnow().isoformat(),
                "significance": "low",
            }
        )
        event_id = create_response.json()["id"]

        # Delete event
        response = await client.delete(f"/api/v1/memory/timeline/{event_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"


# =============================================================================
# Conversation Thread Tests
# =============================================================================

class TestConversationThreads:
    """Tests for conversation thread endpoints."""

    @pytest.mark.asyncio
    async def test_create_thread(self, client: AsyncClient, patient_id: str):
        """Test creating a conversation thread."""
        thread_data = {
            "thread_topic": "School difficulties",
            "category": "social",
            "summary": "Patient has been discussing challenges at school.",
            "first_mentioned_at": datetime.utcnow().isoformat(),
            "clinical_relevance": "high",
        }

        response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/threads",
            json=thread_data
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["thread_topic"] == "School difficulties"
        assert data["status"] == "active"
        assert data["mention_count"] == 1

    @pytest.mark.asyncio
    async def test_get_patient_threads_empty(self, client: AsyncClient, patient_id: str):
        """Test getting threads for patient with none."""
        response = await client.get(f"/api/v1/memory/patients/{patient_id}/threads")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_patient_threads(self, client: AsyncClient, patient_id: str):
        """Test getting conversation threads."""
        # Create threads
        for i in range(3):
            await client.post(
                f"/api/v1/memory/patients/{patient_id}/threads",
                json={
                    "thread_topic": f"Topic {i}",
                    "category": "social",
                    "summary": f"Summary {i}",
                    "first_mentioned_at": datetime.utcnow().isoformat(),
                }
            )

        response = await client.get(f"/api/v1/memory/patients/{patient_id}/threads")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.asyncio
    async def test_update_thread(self, client: AsyncClient, patient_id: str):
        """Test updating a thread."""
        # Create thread
        create_response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/threads",
            json={
                "thread_topic": "Test Topic",
                "category": "social",
                "summary": "Original summary",
                "first_mentioned_at": datetime.utcnow().isoformat(),
            }
        )
        thread_id = create_response.json()["id"]

        # Update thread
        response = await client.patch(
            f"/api/v1/memory/threads/{thread_id}",
            json={
                "summary": "Updated summary",
                "follow_up_needed": True,
                "follow_up_notes": "Need to discuss more next session",
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["summary"] == "Updated summary"
        assert data["follow_up_needed"] is True
        assert data["follow_up_notes"] == "Need to discuss more next session"

    @pytest.mark.asyncio
    async def test_resolve_thread(self, client: AsyncClient, patient_id: str):
        """Test resolving a thread."""
        # Create thread
        create_response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/threads",
            json={
                "thread_topic": "To Resolve",
                "category": "social",
                "summary": "Test",
                "first_mentioned_at": datetime.utcnow().isoformat(),
            }
        )
        thread_id = create_response.json()["id"]

        # Resolve thread
        response = await client.post(
            f"/api/v1/memory/threads/{thread_id}/resolve",
            params={"resolution_notes": "Issue addressed"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_get_threads_needing_followup(self, client: AsyncClient, patient_id: str):
        """Test getting threads that need follow-up."""
        # Create thread needing follow-up
        create_response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/threads",
            json={
                "thread_topic": "Needs Follow-up",
                "category": "social",
                "summary": "Test",
                "first_mentioned_at": datetime.utcnow().isoformat(),
            }
        )
        thread_id = create_response.json()["id"]

        # Mark as needing follow-up
        await client.patch(
            f"/api/v1/memory/threads/{thread_id}",
            json={"follow_up_needed": True}
        )

        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/threads/follow-up"
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1


# =============================================================================
# Context Tests
# =============================================================================

class TestContext:
    """Tests for context retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_patient_context(self, client: AsyncClient, patient_id: str):
        """Test getting patient context."""
        response = await client.post(f"/api/v1/memory/patients/{patient_id}/context")
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert "context_text" in data
        assert "token_count" in data
        assert "patient_info" in data

    @pytest.mark.asyncio
    async def test_get_patient_context_with_options(self, client: AsyncClient, patient_id: str):
        """Test getting context with custom options."""
        request_data = {
            "patient_id": patient_id,
            "session_type": "intake",
            "max_tokens": 1000,
            "include_hypotheses": False,
            "include_domain_scores": True,
            "include_recent_events": True,
            "recent_events_days": 14,
        }

        response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/context",
            json=request_data
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id

    @pytest.mark.asyncio
    async def test_get_session_context_injection(
        self, client: AsyncClient, patient_id: str, session_id: str
    ):
        """Test getting context for VAPI session injection."""
        response = await client.post(
            f"/api/v1/memory/sessions/{session_id}/context-injection",
            params={
                "patient_id": patient_id,
                "session_type": "checkin",
            }
        )
        assert response.status_code == 200

        data = response.json()
        assert data["session_id"] == session_id
        assert data["patient_id"] == patient_id
        assert "system_context" in data
        assert "opening_context" in data
        assert "exploration_topics" in data

    @pytest.mark.asyncio
    async def test_create_context_snapshot(self, client: AsyncClient, patient_id: str):
        """Test creating a context snapshot."""
        response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/snapshots",
            params={"snapshot_type": "pre_session"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["snapshot_type"] == "pre_session"
        assert "context_text" in data

    @pytest.mark.asyncio
    async def test_get_latest_snapshot_none(self, client: AsyncClient, patient_id: str):
        """Test getting latest snapshot when none exists."""
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/snapshots/latest"
        )
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, client: AsyncClient, patient_id: str):
        """Test getting latest snapshot after creating one."""
        # Create snapshot
        await client.post(
            f"/api/v1/memory/patients/{patient_id}/snapshots",
            params={"snapshot_type": "pre_session"}
        )

        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/snapshots/latest"
        )
        assert response.status_code == 200
        assert response.json() is not None
        assert response.json()["patient_id"] == patient_id


# =============================================================================
# Memory Summary Tests
# =============================================================================

class TestMemorySummaries:
    """Tests for memory summary endpoints."""

    @pytest.mark.asyncio
    async def test_get_memory_summaries_empty(self, client: AsyncClient, patient_id: str):
        """Test getting summaries when none exist."""
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/summaries"
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_get_compressed_history(self, client: AsyncClient, patient_id: str):
        """Test getting compressed history."""
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/history/compressed",
            params={"max_tokens": 1000}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert "compressed_history" in data
        assert "approximate_tokens" in data


# =============================================================================
# Longitudinal Analysis Tests
# =============================================================================

class TestLongitudinalAnalysis:
    """Tests for longitudinal analysis endpoints."""

    @pytest.mark.asyncio
    async def test_get_longitudinal_analysis_insufficient_data(
        self, client: AsyncClient, patient_id: str
    ):
        """Test analysis with insufficient data."""
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/analysis",
            params={"days": 30}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["overall_trajectory"] == "insufficient_data"
        assert data["sessions_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_get_trajectory_summary(self, client: AsyncClient, patient_id: str):
        """Test getting trajectory summary."""
        response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/trajectory",
            params={"days": 30}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["patient_id"] == patient_id
        assert "trajectory" in data
        assert "confidence" in data
        assert "sessions_analyzed" in data


# =============================================================================
# Integration Tests
# =============================================================================

class TestMemoryIntegration:
    """Integration tests for memory functionality."""

    @pytest.mark.asyncio
    async def test_full_timeline_workflow(self, client: AsyncClient, patient_id: str):
        """Test complete timeline workflow."""
        # 1. Add multiple events
        events_created = []
        for i in range(5):
            response = await client.post(
                f"/api/v1/memory/patients/{patient_id}/timeline",
                json={
                    "event_type": "observation" if i % 2 == 0 else "disclosure",
                    "category": "social" if i % 2 == 0 else "emotional",
                    "title": f"Event {i}",
                    "description": f"Description {i}",
                    "occurred_at": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                    "significance": "moderate" if i < 3 else "high",
                }
            )
            events_created.append(response.json())

        # 2. Get timeline
        timeline_response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline"
        )
        assert timeline_response.json()["total_events"] == 5

        # 3. Get summary
        summary_response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline/summary"
        )
        summary = summary_response.json()
        assert summary["total_events"] == 5
        assert "social" in summary["by_category"]
        assert "emotional" in summary["by_category"]

        # 4. Update an event
        await client.patch(
            f"/api/v1/memory/timeline/{events_created[0]['id']}",
            json={"significance": "critical"}
        )

        # 5. Delete an event
        await client.delete(f"/api/v1/memory/timeline/{events_created[-1]['id']}")

        # 6. Verify final state
        final_response = await client.get(
            f"/api/v1/memory/patients/{patient_id}/timeline"
        )
        assert final_response.json()["total_events"] == 4

    @pytest.mark.asyncio
    async def test_context_with_threads(self, client: AsyncClient, patient_id: str):
        """Test context includes thread information."""
        # Create a thread
        await client.post(
            f"/api/v1/memory/patients/{patient_id}/threads",
            json={
                "thread_topic": "Important Topic",
                "category": "social",
                "summary": "This is an important ongoing discussion.",
                "first_mentioned_at": datetime.utcnow().isoformat(),
                "clinical_relevance": "high",
            }
        )

        # Get context
        response = await client.post(
            f"/api/v1/memory/patients/{patient_id}/context"
        )
        data = response.json()

        # Verify threads are included
        assert "active_threads" in data
