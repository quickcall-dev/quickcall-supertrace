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


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get session details with all events (no limit)."""
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all events - no truncation
    events = await db.get_events(session_id, limit=10000)

    return {"session": session, "events": events}


@router.get("/{session_id}/events")
async def get_session_events(
    session_id: str, limit: int = 100, offset: int = 0
) -> dict[str, Any]:
    """Get events for a session (paginated)."""
    db = await get_db()

    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    events = await db.get_events(session_id, limit=limit, offset=offset)

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

    events = await db.get_events(session_id, limit=10000)

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
