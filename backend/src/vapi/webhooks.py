"""
VAPI Webhook Handlers

Handles incoming webhooks from VAPI for voice call events.

Event types:
- assistant-request: VAPI requesting assistant config (we use pre-configured assistant)
- status-update: Call status changes
- speech-update: Real-time speech detection
- transcript: Final transcript segments
- hang: Call ended
- function-call: Assistant requesting a function call
- end-of-call-report: Final call summary

Server URL (ngrok for dev):
https://sustentacular-giada-chunkily.ngrok-free.dev/api/v1/vapi/webhook
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.database import get_db
from src.services.session_service import SessionService
from src.memory.context import ContextService
from src.assessment.processing import SessionProcessor
from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/vapi", tags=["VAPI Webhooks"])


# =============================================================================
# Request/Response Models for VAPI Functions
# =============================================================================

class GetContextRequest(BaseModel):
    """Request to get patient context."""
    patient_id: str
    session_id: Optional[str] = None


class FlagConcernRequest(BaseModel):
    """Request to flag a clinical concern."""
    concern_type: str  # safety, distress, urgent, note
    description: str
    session_id: Optional[str] = None


class EndSessionRequest(BaseModel):
    """Request to end a session."""
    reason: str  # completed, patient_request, distress, technical
    summary: Optional[str] = None
    session_id: Optional[str] = None


def parse_timestamp(ts) -> Optional[datetime]:
    """Parse timestamp from VAPI - handles both ISO strings and millisecond integers."""
    if ts is None:
        return None
    try:
        # Handle integer timestamps (milliseconds since epoch)
        if isinstance(ts, (int, float)):
            # Use timezone-aware UTC datetime
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        # Handle ISO string formats
        if isinstance(ts, str):
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        return None
    except (ValueError, OSError):
        return None


@router.post("/webhook")
async def handle_vapi_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_vapi_secret: Optional[str] = Header(None, alias="x-vapi-secret"),
):
    """
    Handle all VAPI webhook events.

    VAPI sends various events during the call lifecycle.
    We handle the ones relevant for our use case.
    """
    payload = await request.json()

    # VAPI wraps data in "message" for server-url webhooks
    message = payload.get("message", payload)
    event_type = message.get("type", "")
    call_data = message.get("call", {})
    call_id = call_data.get("id") if call_data else None

    # Only log important events, skip noisy ones
    if event_type in ("status-update", "end-of-call-report", "function-call"):
        logger.info(f"VAPI webhook: type={event_type}, call_id={call_id}")

    session_service = SessionService(db)

    try:
        match event_type:
            case "status-update":
                return await handle_status_update(session_service, payload, db)

            case "transcript":
                # Silently store transcript without logging each segment
                return await handle_transcript(session_service, payload)

            case "hang":
                return await handle_hang(session_service, payload)

            case "end-of-call-report":
                return await handle_end_of_call_report(session_service, payload, db)

            case "function-call":
                return await handle_function_call(session_service, payload)

            case "assistant-request":
                # We use pre-configured assistants, return empty to use default
                return {"assistant": None}

            case "speech-update":
                # Real-time speech detection - silently acknowledge
                return {"status": "ok"}

            case "conversation-update":
                # Store conversation updates (contains full conversation history)
                return await handle_conversation_update(session_service, payload)

            case _:
                logger.debug(f"Unhandled VAPI event type: {event_type}")
                return {"status": "ignored", "event": event_type}

    except Exception as e:
        logger.error(f"Error handling VAPI webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_status_update(service: SessionService, payload: dict, db: AsyncSession) -> dict:
    """Handle call status update events."""
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")
    status = message.get("status")
    ended_reason = message.get("endedReason")

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    timestamp = parse_timestamp(message.get("timestamp"))

    if status == "in-progress":
        # Call started
        await service.mark_session_started(
            vapi_call_id=call_id,
            started_at=timestamp or datetime.now(timezone.utc),
        )
    elif status == "ended":
        # Call ended - mark session as completed
        completion_reason = _map_ended_reason(ended_reason or "unknown")

        session = await service.mark_session_ended(
            vapi_call_id=call_id,
            ended_at=timestamp or datetime.now(timezone.utc),
            completion_reason=completion_reason,
        )

        # Trigger analysis if session exists and hasn't been processed yet
        # This is a fallback in case end-of-call-report doesn't arrive
        if session and session.status == "completed":
            try:
                processor = SessionProcessor(db)
                # Check if already processed
                from sqlalchemy import select
                from src.models.assessment import ClinicalSignal
                existing = await db.execute(
                    select(ClinicalSignal).where(ClinicalSignal.session_id == session.id).limit(1)
                )
                if not existing.scalar_one_or_none():
                    logger.info(f"Starting analysis for session {session.id}")
                    result = await processor.process_session(session.id)
                    logger.info(f"Analysis complete: {result.signals_extracted} signals")
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
    elif status == "forwarding":
        # Call being forwarded
        pass

    return {"status": "ok"}


async def handle_transcript(service: SessionService, payload: dict) -> dict:
    """Handle transcript events - store each transcript segment."""
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")
    transcript_data = message.get("transcript", {})

    if not call_id or not transcript_data:
        return {"status": "ignored", "reason": "missing data"}

    role = transcript_data.get("role", "user")
    text = transcript_data.get("text", "")
    timestamp_ms = transcript_data.get("timestamp")

    if text:
        await service.add_transcript(
            vapi_call_id=call_id,
            role=role,
            content=text,
            timestamp_ms=timestamp_ms,
        )

    return {"status": "ok"}


async def handle_conversation_update(service: SessionService, payload: dict) -> dict:
    """Handle conversation-update events - extract and store transcripts."""
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")
    conversation = message.get("conversation", [])

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    # Get session to check what we've already stored
    session = await service.get_session_by_vapi_id(call_id)
    if not session:
        return {"status": "ignored", "reason": "session not found"}

    # Get existing transcript count to avoid duplicates
    existing_transcripts = await service.get_transcripts(session.id)
    existing_count = len(existing_transcripts)

    # conversation is a list like:
    # [{"role": "system", "content": "..."}, {"role": "assistant", "content": "..."}, {"role": "user", "content": "..."}]
    # Skip system messages and only store new ones
    non_system = [msg for msg in conversation if msg.get("role") != "system"]

    # Only add transcripts that are new (beyond what we've stored)
    new_messages = non_system[existing_count:]

    for i, msg in enumerate(new_messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            await service.add_transcript(
                vapi_call_id=call_id,
                role=role,
                content=content,
                timestamp_ms=message.get("timestamp"),
            )

    return {"status": "ok", "new_messages": len(new_messages)}


async def handle_hang(service: SessionService, payload: dict) -> dict:
    """Handle call hang/end events."""
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    timestamp = parse_timestamp(message.get("timestamp"))
    ended_reason = message.get("endedReason", "unknown")

    # Map VAPI ended reasons to our completion reasons
    completion_reason = _map_ended_reason(ended_reason)

    await service.mark_session_ended(
        vapi_call_id=call_id,
        ended_at=timestamp or datetime.now(timezone.utc),
        completion_reason=completion_reason,
    )

    return {"status": "ok"}


async def handle_end_of_call_report(service: SessionService, payload: dict, db: AsyncSession) -> dict:
    """Handle end-of-call report with summary and duration, then trigger analysis."""
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")

    if not call_id:
        logger.warning("end-of-call-report received without call ID")
        return {"status": "ignored", "reason": "no call id"}

    # Extract useful data from the report
    duration_seconds = call_data.get("duration")  # Duration in seconds
    summary = message.get("summary", "")
    recording_url = call_data.get("recordingUrl")

    # Update session with report data
    session = await service.update_session_from_report(
        vapi_call_id=call_id,
        duration_seconds=duration_seconds,
        summary=summary,
        recording_url=recording_url,
    )

    if not session:
        logger.warning(f"end-of-call-report: No session found for call {call_id}")
        return {"status": "ignored", "reason": "session not found"}

    # Ensure session is marked as completed (in case hang event hasn't arrived yet)
    if session.status != "completed":
        await service.mark_session_ended(
            vapi_call_id=call_id,
            ended_at=datetime.now(timezone.utc),
            completion_reason="completed",
        )
        await db.refresh(session)

    # Trigger post-session analysis pipeline
    try:
        processor = SessionProcessor(db)
        result = await processor.process_session(session.id)
        logger.info(f"Analysis complete: {result.signals_extracted} signals, {result.domains_scored} domains")
        return {"status": "ok", "analysis": result.to_dict()}
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"status": "ok", "analysis_error": str(e)}


async def handle_function_call(service: SessionService, payload: dict) -> dict:
    """
    Handle function calls from the VAPI assistant.

    Supported functions:
    - get_patient_context: Get relevant patient history
    - flag_concern: Flag something for clinician review
    - end_session: End the session early
    """
    # Extract from message wrapper (VAPI wraps server-url webhook data)
    message = payload.get("message", payload)
    call_data = message.get("call", {})
    call_id = call_data.get("id")
    function_call = message.get("functionCall", {})

    function_name = function_call.get("name")
    function_args = function_call.get("parameters", {})

    logger.debug(f"Function call: {function_name}")

    match function_name:
        case "get_patient_context":
            # Get patient context for the assistant
            session = await service.get_session_by_vapi_id(call_id)
            if session:
                context = await service.get_patient_context_for_session(session.id)
                return {"result": context}
            return {"result": {"error": "Session not found"}}

        case "flag_concern":
            # Flag a concern for clinician review
            concern = function_args.get("concern", "")
            severity = function_args.get("severity", "low")
            await service.flag_concern(
                vapi_call_id=call_id,
                concern=concern,
                severity=severity,
            )
            return {"result": {"flagged": True}}

        case "end_session":
            # Assistant wants to end the session
            reason = function_args.get("reason", "assistant_requested")
            return {"result": {"end_call": True, "reason": reason}}

        case _:
            logger.warning(f"Unknown function call: {function_name}")
            return {"result": {"error": f"Unknown function: {function_name}"}}


def _map_ended_reason(vapi_reason: str) -> str:
    """Map VAPI ended reasons to our completion reasons."""
    reason_map = {
        "assistant-ended-call": "completed",
        "customer-ended-call": "patient_hangup",
        "assistant-error": "error",
        "customer-did-not-answer": "no_answer",
        "silence-timed-out": "silence",
        "max-duration-reached": "timeout",
        "voicemail": "voicemail",
    }
    return reason_map.get(vapi_reason, vapi_reason)


# =============================================================================
# VAPI Function Endpoints (for Server-Side Tools)
# =============================================================================

@router.post("/functions/get-context")
async def vapi_get_context(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get patient context for the VAPI assistant.

    Called by VAPI when the assistant needs patient context.
    Returns context formatted for injection into the conversation.
    """
    try:
        payload = await request.json()
        logger.debug("VAPI get-context request")

        # Extract from VAPI function call format
        message = payload.get("message", {})
        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})
        call_data = payload.get("call", {})

        patient_id = parameters.get("patient_id")
        session_id = parameters.get("session_id")
        call_id = call_data.get("id")

        if not patient_id:
            return {
                "results": [
                    {
                        "toolCallId": function_call.get("id"),
                        "result": "No patient ID provided"
                    }
                ]
            }

        # Get session to retrieve interview_mode
        session_service = SessionService(db)
        session = None
        interview_mode = "parent"

        if call_id:
            session = await session_service.get_session_by_vapi_id(call_id)
            if session:
                interview_mode = getattr(session, "interview_mode", "parent")
                session_id = str(session.id)

        # Get structured template variables
        context_service = ContextService(db)
        template_vars = await context_service.get_vapi_template_variables(
            patient_id=UUID(patient_id),
            session_id=UUID(session_id) if session_id else UUID(patient_id),
            interview_mode=interview_mode,
        )

        # Also get the text context for backwards compatibility
        context = await context_service.get_patient_context(
            patient_id=UUID(patient_id),
            session_type="checkin",
        )

        # Combine structured variables with context text
        result = {
            "context_text": context.context_text,
            "variables": template_vars,
        }

        return {
            "results": [
                {
                    "toolCallId": function_call.get("id"),
                    "result": result
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in get-context: {e}")
        return {
            "results": [
                {
                    "toolCallId": "",
                    "result": f"Error retrieving context: {str(e)}"
                }
            ]
        }


@router.post("/functions/get-template-variables")
async def vapi_get_template_variables(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get structured template variables for VAPI prompt injection.

    Called by VAPI to populate prompt template placeholders like:
    - {{interviewee_type}}
    - {{patient_name}}
    - {{previous_session_summary}}
    - {{focus_areas_text}}
    - {{missing_domains_text}}

    Returns all variables needed by the VAPI prompt template.
    """
    try:
        payload = await request.json()
        logger.debug("VAPI get-template-variables request")

        # Extract from VAPI function call format
        message = payload.get("message", {})
        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})
        call_data = payload.get("call", {})

        patient_id = parameters.get("patient_id")
        session_id = parameters.get("session_id")
        call_id = call_data.get("id")

        if not patient_id:
            return {
                "results": [
                    {
                        "toolCallId": function_call.get("id"),
                        "result": {"error": "No patient ID provided"}
                    }
                ]
            }

        # Get session to retrieve interview_mode
        session_service = SessionService(db)
        session = None
        interview_mode = "parent"

        if call_id:
            session = await session_service.get_session_by_vapi_id(call_id)
            if session:
                interview_mode = getattr(session, "interview_mode", "parent")
                session_id = str(session.id)

        # Get structured template variables
        context_service = ContextService(db)
        template_vars = await context_service.get_vapi_template_variables(
            patient_id=UUID(patient_id),
            session_id=UUID(session_id) if session_id else UUID(patient_id),
            interview_mode=interview_mode,
        )

        return {
            "results": [
                {
                    "toolCallId": function_call.get("id"),
                    "result": template_vars
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in get-template-variables: {e}")
        return {
            "results": [
                {
                    "toolCallId": "",
                    "result": {"error": f"Error retrieving variables: {str(e)}"}
                }
            ]
        }


@router.post("/functions/flag-concern")
async def vapi_flag_concern(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Flag a clinical concern from the VAPI assistant.

    Called when the assistant detects something requiring clinician attention.
    """
    try:
        payload = await request.json()
        logger.debug("VAPI flag-concern request")

        message = payload.get("message", {})
        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})
        call_data = payload.get("call", {})

        concern_type = parameters.get("concern_type", "note")
        description = parameters.get("description", "")
        call_id = call_data.get("id")

        # Get session and flag concern
        session_service = SessionService(db)
        if call_id:
            await session_service.flag_concern(
                vapi_call_id=call_id,
                concern=description,
                severity=concern_type,
            )

        logger.warning(f"Concern flagged: [{concern_type}] {description}")

        return {
            "results": [
                {
                    "toolCallId": function_call.get("id"),
                    "result": f"Concern flagged successfully. The clinician will be notified."
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in flag-concern: {e}")
        return {
            "results": [
                {
                    "toolCallId": "",
                    "result": f"Concern noted but there was an error logging it: {str(e)}"
                }
            ]
        }


@router.post("/functions/end-session")
async def vapi_end_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    End the session from the VAPI assistant.

    Called when the assistant determines the session should end.
    """
    try:
        payload = await request.json()
        logger.debug("VAPI end-session request")

        message = payload.get("message", {})
        function_call = message.get("functionCall", {})
        parameters = function_call.get("parameters", {})
        call_data = payload.get("call", {})

        reason = parameters.get("reason", "completed")
        summary = parameters.get("summary", "")
        call_id = call_data.get("id")

        logger.debug(f"Session ending: reason={reason}")

        # Return signal to VAPI to end the call
        return {
            "results": [
                {
                    "toolCallId": function_call.get("id"),
                    "result": "Ending session now. Goodbye!"
                }
            ]
        }

    except Exception as e:
        logger.error(f"Error in end-session: {e}")
        return {
            "results": [
                {
                    "toolCallId": "",
                    "result": "Ending session."
                }
            ]
        }


# =============================================================================
# VAPI Configuration Helper Endpoint
# =============================================================================

@router.get("/config")
async def get_vapi_config():
    """
    Get VAPI configuration details for setting up the assistant.

    Returns the webhook URLs and configuration needed for VAPI console.
    """
    base_url = settings.webhook_base_url

    return {
        "server_url": f"{base_url}/api/v1/vapi/webhook",
        "functions": {
            "get_patient_context": {
                "url": f"{base_url}/api/v1/vapi/functions/get-context",
                "description": "Retrieve context about the patient from previous sessions"
            },
            "get_template_variables": {
                "url": f"{base_url}/api/v1/vapi/functions/get-template-variables",
                "description": "Get structured variables for prompt template (interviewee_type, patient_name, focus_areas, etc.)"
            },
            "flag_concern": {
                "url": f"{base_url}/api/v1/vapi/functions/flag-concern",
                "description": "Flag a clinical concern that needs immediate attention"
            },
            "end_session": {
                "url": f"{base_url}/api/v1/vapi/functions/end-session",
                "description": "Gracefully end the session"
            }
        },
        "environment": {
            "debug": settings.debug,
            "backend_port": settings.backend_port,
            "ngrok_url": settings.ngrok_url,
        }
    }
