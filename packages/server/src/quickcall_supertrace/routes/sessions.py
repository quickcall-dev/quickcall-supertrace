"""
Session API routes.

Provides endpoints for listing sessions, getting session details,
fetching session events, exporting sessions, and context window tracking.

Related: db/client.py (queries), export.py (export logic), ws/broadcast.py (WebSocket)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..db import get_db
from ..ws import manager

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# =============================================================================
# Context Window Tracking Models
# =============================================================================

class ContextUpdateRequest(BaseModel):
    """
    Request body for POST /api/sessions/{session_id}/context.

    Expected payload from Claude Code hooks:
    {
        "used_percentage": 42.5,
        "remaining_percentage": 57.5,
        "context_window_size": 200000,
        "total_input_tokens": 85000,
        "total_output_tokens": 15000
    }
    """
    used_percentage: float = Field(..., ge=0, le=100, description="Percentage of context window used (0-100)")
    remaining_percentage: float = Field(default=None, ge=0, le=100, description="Percentage remaining")
    context_window_size: int = Field(default=200000, gt=0, description="Max context window size")
    total_input_tokens: int = Field(default=0, ge=0, description="Total input tokens consumed")
    total_output_tokens: int = Field(default=0, ge=0, description="Total output tokens generated")
    cache_read_tokens: int = Field(default=0, ge=0, description="Cache read tokens (optional)")
    cache_create_tokens: int = Field(default=0, ge=0, description="Cache creation tokens (optional)")
    model: str | None = Field(default=None, description="Model identifier (optional)")
    cost_usd: float | None = Field(default=None, ge=0, description="Cumulative session cost in USD")


class ContextResponse(BaseModel):
    """Response model for context window data."""
    id: int
    session_id: str
    timestamp: str
    used_percentage: float
    remaining_percentage: float
    context_window_size: int
    total_input_tokens: int
    total_output_tokens: int
    cache_read_tokens: int
    cache_create_tokens: int
    model: str | None
    cost_usd: float | None
    created_at: str


@router.get("")
async def list_sessions(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """List all sessions, most recent first."""
    db = await get_db()
    sessions = await db.get_sessions(limit=limit, offset=offset)
    return {"sessions": sessions, "count": len(sessions)}


def _slim_event(event: dict) -> dict:
    """
    Strip large data from event for initial load. Keep structure for display.

    ⚠️  IMPORTANT: When adding new fields to events in db/client.py, you MUST
    also add them here if they should be visible in the frontend!

    This function explicitly whitelists fields per event_type. Any field not
    listed here will be stripped from the slim response, causing the frontend
    to not receive it.

    Common mistake: Adding a field to the database/API but forgetting to add
    it here, resulting in the field being null in the frontend.

    See: docs/guides/slim-event-fields.md
    """
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
            "thinkingContent": data.get("thinkingContent"),  # Extended thinking
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
    """Truncate text if too long. Recursively handles nested dicts and lists."""
    if isinstance(text, str):
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"... [{len(text) - max_len} more chars]"
    elif isinstance(text, dict):
        return {k: _slim_text(v, max_len) for k, v in text.items()}
    elif isinstance(text, list):
        return [_slim_text(item, max_len) for item in text]
    else:
        return text


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

    elif format == "jsonl":
        # Return raw JSONL file from ~/.claude/projects/
        if not session.get("file_path"):
            raise HTTPException(status_code=404, detail="JSONL file not found")

        file_path = Path(session["file_path"])
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="JSONL file not found")

        return Response(
            content=file_path.read_text(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f'attachment; filename="{session_id}.jsonl"'
            },
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'json', 'md', or 'jsonl'")


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


# =============================================================================
# Context Window Tracking Endpoints
# =============================================================================


@router.post("/{session_id}/context")
async def store_context_snapshot(
    session_id: str,
    context: ContextUpdateRequest,
) -> dict[str, Any]:
    """
    Store a context window snapshot for a session.

    Called by Claude Code hooks to report current context window usage.
    Broadcasts the update via WebSocket to subscribed clients.

    Args:
        session_id: Session to store context for
        context: Context window data including token counts and percentages

    Returns:
        Stored context record with ID and timestamp
    """
    db = await get_db()

    # Generate timestamp for this snapshot
    timestamp = datetime.now(timezone.utc).isoformat()

    # Compute remaining percentage if not provided
    remaining = context.remaining_percentage
    if remaining is None:
        remaining = 100.0 - context.used_percentage

    # Store in database
    context_id = await db.save_session_context(
        session_id=session_id,
        timestamp=timestamp,
        used_percentage=context.used_percentage,
        remaining_percentage=remaining,
        context_window_size=context.context_window_size,
        total_input_tokens=context.total_input_tokens,
        total_output_tokens=context.total_output_tokens,
        cache_read_tokens=context.cache_read_tokens,
        cache_create_tokens=context.cache_create_tokens,
        model=context.model,
        cost_usd=context.cost_usd,
    )

    # Prepare response data
    context_data = {
        "id": context_id,
        "session_id": session_id,
        "timestamp": timestamp,
        "used_percentage": context.used_percentage,
        "remaining_percentage": remaining,
        "context_window_size": context.context_window_size,
        "total_input_tokens": context.total_input_tokens,
        "total_output_tokens": context.total_output_tokens,
        "cache_read_tokens": context.cache_read_tokens,
        "cache_create_tokens": context.cache_create_tokens,
        "model": context.model,
        "cost_usd": context.cost_usd,
    }

    # Broadcast update via WebSocket to subscribed clients
    await manager.broadcast_to_session(
        session_id,
        {
            "event": "context_updated",
            "session_id": session_id,
            "data": context_data,
        }
    )

    return {"status": "ok", "context": context_data}


@router.get("/{session_id}/context")
async def get_context_snapshots(
    session_id: str,
    limit: int = 100,
    latest_only: bool = False,
) -> dict[str, Any]:
    """
    Get context window snapshots for a session.

    Args:
        session_id: Session to get context for
        limit: Maximum number of snapshots to return (default 100)
        latest_only: If True, return only the most recent snapshot

    Returns:
        List of context snapshots or single latest snapshot
    """
    db = await get_db()

    if latest_only:
        context = await db.get_latest_session_context(session_id)
        if not context:
            return {"context": None, "count": 0}
        return {"context": context, "count": 1}

    snapshots = await db.get_session_context(session_id, limit=limit)
    return {"snapshots": snapshots, "count": len(snapshots)}
