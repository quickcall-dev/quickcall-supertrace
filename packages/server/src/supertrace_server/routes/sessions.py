"""
Session API routes.

Provides endpoints for listing sessions, getting session details,
fetching session events, and exporting sessions.

Related: db/client.py (queries), export.py (export logic)
"""

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Response

from ..db import get_db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """List all sessions, most recent first."""
    db = await get_db()
    sessions = await db.get_sessions(limit=limit, offset=offset)
    return {"sessions": sessions, "count": len(sessions)}


def _slim_event(event: dict) -> dict:
    """Strip large data from event for initial load. Keep structure for display."""
    slim = {
        "id": event.get("id"),
        "session_id": event.get("session_id"),
        "event_type": event.get("event_type"),
        "timestamp": event.get("timestamp"),
        "created_at": event.get("created_at"),
    }

    data = event.get("data") or {}
    event_type = event.get("event_type")

    # For tool_use, keep tool_name and slim tool_input
    if event_type == "tool_use":
        slim["data"] = {
            "tool_name": data.get("tool_name"),
            "tool_input": _slim_tool_input(data.get("tool_input", {})),
            "tool_result": _slim_text(data.get("tool_result"), 500),
        }
    # For user_prompt, keep the prompt (can be at top level or in tool_input)
    elif event_type == "user_prompt":
        # Prompt can be at data.prompt or data.tool_input.prompt
        prompt = data.get("prompt") or data.get("tool_input", {}).get("prompt", "")
        images = data.get("images") or data.get("tool_input", {}).get("images", [])
        slim["data"] = {
            "prompt": prompt,
            "images": images or [],
            "promptIndex": data.get("promptIndex"),  # Preserve prompt number for display
        }
    # For assistant_stop, need to keep transcript for display but slim it down
    elif event_type == "assistant_stop":
        transcript = data.get("transcript", [])
        slimmed_transcript = _slim_transcript(transcript)
        slim["data"] = {
            "token_usage": data.get("token_usage"),
            "stop_reason": data.get("stop_reason"),
            "transcript": slimmed_transcript,
            "message": data.get("message"),  # Direct message from reimport
        }
    # For compact events
    elif event_type == "compact":
        slim["data"] = {
            "command": data.get("command"),
            "token_usage_before": data.get("token_usage_before"),
        }
    # For notification events
    elif event_type == "notification":
        slim["data"] = {
            "notification": data.get("notification"),
        }
    else:
        # For other events (session_start, session_end), keep data as-is (usually small)
        slim["data"] = data

    return slim


def _slim_transcript(transcript: list) -> list:
    """Slim down transcript, keeping only what's needed for display."""
    if not transcript:
        return []

    # Only keep the last assistant message for display
    slimmed = []
    for msg in reversed(transcript):
        if msg.get("type") == "assistant":
            message = msg.get("message", {})
            content = message.get("content", [])
            # Extract text content only, skip tool blocks
            slim_content = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    # Truncate very long text
                    if len(text) > 2000:
                        text = text[:2000] + f"... [{len(text) - 2000} more chars]"
                    slim_content.append({"type": "text", "text": text})
            if slim_content:
                slimmed.append({
                    "type": "assistant",
                    "message": {"content": slim_content}
                })
            break
    return slimmed


def _slim_tool_input(tool_input: dict) -> dict:
    """Slim down tool input, keeping essential fields."""
    if not tool_input:
        return {}

    slim = {}
    # Keep file paths
    for key in ["file_path", "path", "pattern", "command", "query", "url"]:
        if key in tool_input:
            slim[key] = _slim_text(tool_input[key], 200)

    # Slim content fields
    for key in ["content", "old_string", "new_string", "prompt"]:
        if key in tool_input:
            slim[key] = _slim_text(tool_input[key], 300)

    return slim


def _slim_text(text: Any, max_len: int = 200) -> Any:
    """Truncate text if too long."""
    if not isinstance(text, str):
        return text
    if len(text) <= max_len:
        return text
    return text[:max_len] + f"... [{len(text) - max_len} more chars]"


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    slim: bool = True,
    event_limit: int = 100,
) -> dict[str, Any]:
    """Get session details with events.

    Args:
        slim: If True (default), strip large data for faster initial load.
        event_limit: Max events to return (default 100). Use 0 for all.
    """
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get events from messages table (JSONL ingestion is the only data source)
    all_events = await db.get_messages_as_events(session_id, limit=10000)

    total_events = len(all_events)

    # Limit events for initial load (get most recent)
    if event_limit > 0 and len(all_events) > event_limit:
        events = all_events[-event_limit:]  # Get last N events (most recent)
    else:
        events = all_events

    # Optionally slim down events for initial load
    if slim:
        events = [_slim_event(e) for e in events]

    return {
        "session": session,
        "events": events,
        "total_events": total_events,
    }


@router.get("/{session_id}/events")
async def get_session_events(
    session_id: str,
    limit: int = 100,
    slim: bool = True,
    before_id: int | None = None,
) -> dict[str, Any]:
    """Get events for a session (paginated).

    Args:
        before_id: If provided, get events with id < before_id (for loading older events)
    """
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get events from messages table (JSONL ingestion is the only data source)
    all_events = await db.get_messages_as_events(session_id, limit=10000)

    # Filter to events before the given ID (for loading older events)
    if before_id is not None:
        events = [e for e in all_events if e.get("id", 0) < before_id]
        # Take the last `limit` events (most recent before the cutoff)
        events = events[-limit:] if len(events) > limit else events
    else:
        # No before_id, just return the last `limit` events
        events = all_events[-limit:] if len(all_events) > limit else all_events

    if slim:
        events = [_slim_event(e) for e in events]

    return {"events": events, "count": len(events)}


@router.get("/{session_id}/export")
async def export_session(session_id: str, format: str = "json") -> Response:
    """
    Export session in JSON or Markdown format.

    - format=json: Full data export
    - format=md: Human-readable markdown
    """
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    events = await db.get_messages_as_events(session_id, limit=10000)

    if format == "json":
        content = json.dumps({"session": session, "events": events}, indent=2)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={session_id}.json"},
        )

    elif format == "md":
        md_content = _export_markdown(session, events)
        return Response(
            content=md_content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={session_id}.md"},
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json' or 'md'")


def _export_markdown(session: dict, events: list[dict]) -> str:
    """Convert session and events to markdown format."""
    lines = [
        f"# Session: {session['id']}",
        "",
        f"**Project:** {session.get('project_path', 'N/A')}",
        f"**Started:** {session.get('started_at', 'N/A')}",
        f"**Ended:** {session.get('ended_at', 'N/A')}",
        "",
        "---",
        "",
    ]

    for event in events:
        event_type = event["event_type"]
        timestamp = event["timestamp"]
        data = event.get("data", {})

        lines.append(f"## [{timestamp}] {event_type}")
        lines.append("")

        if event_type == "user_prompt":
            prompt = data.get("tool_input", {}).get("prompt", "")
            lines.append(f"> {prompt}")

        elif event_type == "assistant_stop":
            transcript = data.get("transcript", [])
            if transcript:
                # Get last assistant message
                for msg in reversed(transcript):
                    if msg.get("type") == "assistant":
                        content = msg.get("message", {}).get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                lines.append(block.get("text", ""))
                        break

        elif event_type == "tool_use":
            tool_name = data.get("tool_name", "unknown")
            lines.append(f"**Tool:** `{tool_name}`")
            tool_input = data.get("tool_input", {})
            if tool_input:
                lines.append("```json")
                lines.append(json.dumps(tool_input, indent=2))
                lines.append("```")

        lines.append("")

    return "\n".join(lines)
