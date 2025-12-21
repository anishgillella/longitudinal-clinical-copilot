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
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vapi", tags=["VAPI Webhooks"])


def parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp from VAPI."""
    if not ts:
        return None
    try:
        # Handle various ISO formats
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except ValueError:
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
    event_type = payload.get("type", "")
    call_data = payload.get("call", {})
    call_id = call_data.get("id")

    logger.info(f"VAPI webhook received: {event_type} for call {call_id}")

    session_service = SessionService(db)

    try:
        match event_type:
            case "status-update":
                return await handle_status_update(session_service, payload)

            case "transcript":
                return await handle_transcript(session_service, payload)

            case "hang":
                return await handle_hang(session_service, payload)

            case "end-of-call-report":
                return await handle_end_of_call_report(session_service, payload)

            case "function-call":
                return await handle_function_call(session_service, payload)

            case "assistant-request":
                # We use pre-configured assistants, return empty to use default
                return {"assistant": None}

            case "speech-update":
                # Real-time speech detection - could be used for live features
                return {"status": "ok"}

            case _:
                logger.warning(f"Unhandled VAPI event type: {event_type}")
                return {"status": "ignored", "event": event_type}

    except Exception as e:
        logger.error(f"Error handling VAPI webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_status_update(service: SessionService, payload: dict) -> dict:
    """Handle call status update events."""
    call_data = payload.get("call", {})
    call_id = call_data.get("id")
    status = payload.get("status")

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    timestamp = parse_timestamp(payload.get("timestamp"))

    if status == "in-progress":
        # Call started
        await service.mark_session_started(
            vapi_call_id=call_id,
            started_at=timestamp or datetime.utcnow(),
        )
    elif status == "ended":
        # Call ended - this is also sent with hang event
        pass
    elif status == "forwarding":
        # Call being forwarded
        pass

    return {"status": "ok"}


async def handle_transcript(service: SessionService, payload: dict) -> dict:
    """Handle transcript events - store each transcript segment."""
    call_data = payload.get("call", {})
    call_id = call_data.get("id")
    transcript_data = payload.get("transcript", {})

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


async def handle_hang(service: SessionService, payload: dict) -> dict:
    """Handle call hang/end events."""
    call_data = payload.get("call", {})
    call_id = call_data.get("id")

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    timestamp = parse_timestamp(payload.get("timestamp"))
    ended_reason = payload.get("endedReason", "unknown")

    # Map VAPI ended reasons to our completion reasons
    completion_reason = _map_ended_reason(ended_reason)

    await service.mark_session_ended(
        vapi_call_id=call_id,
        ended_at=timestamp or datetime.utcnow(),
        completion_reason=completion_reason,
    )

    return {"status": "ok"}


async def handle_end_of_call_report(service: SessionService, payload: dict) -> dict:
    """Handle end-of-call report with summary and duration."""
    call_data = payload.get("call", {})
    call_id = call_data.get("id")

    if not call_id:
        return {"status": "ignored", "reason": "no call id"}

    # Extract useful data from the report
    duration_seconds = call_data.get("duration")  # Duration in seconds
    summary = payload.get("summary", "")
    recording_url = call_data.get("recordingUrl")

    # Update session with report data
    await service.update_session_from_report(
        vapi_call_id=call_id,
        duration_seconds=duration_seconds,
        summary=summary,
        recording_url=recording_url,
    )

    return {"status": "ok"}


async def handle_function_call(service: SessionService, payload: dict) -> dict:
    """
    Handle function calls from the VAPI assistant.

    Supported functions:
    - get_patient_context: Get relevant patient history
    - flag_concern: Flag something for clinician review
    - end_session: End the session early
    """
    call_data = payload.get("call", {})
    call_id = call_data.get("id")
    function_call = payload.get("functionCall", {})

    function_name = function_call.get("name")
    function_args = function_call.get("parameters", {})

    logger.info(f"Function call: {function_name} with args: {function_args}")

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
