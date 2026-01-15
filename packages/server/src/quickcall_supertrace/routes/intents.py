"""
Session intents extraction API.

Provides endpoint to extract high-level user intents from session prompts
using Claude CLI (claude -p). This runs on-demand when the endpoint is called.

## Architecture Decisions

1. **On-demand extraction**: Intents are extracted only when the API is called,
   not during polling. This avoids unnecessary API costs and keeps polling fast.

2. **Claude CLI over API**: Uses `claude -p` subprocess instead of direct API calls.
   This leverages existing CLI authentication and doesn't require separate API keys.
   Trade-off: Requires Claude CLI installed on server.

3. **Caching in SQLite**: Results cached in `session_intents` table to avoid
   repeated extractions. Cache is invalidated via `refresh=true` parameter.
   No automatic invalidation when new messages arrive (would need explicit refresh).

4. **Markdown code block handling**: Claude sometimes wraps JSON in ```json blocks.
   We detect and strip these to parse the actual JSON array.

5. **Error handling**: Returns HTTP errors for missing sessions (404), CLI failures (500),
   timeouts (504). Errors are logged but not cached.

## API Contract

- GET /api/sessions/{session_id}/intents
- GET /api/sessions/{session_id}/intents?refresh=true (bypass cache)
- Returns: {session_id, intents: [...], prompt_count, cached, created_at?}

Related: db/client.py (get_user_messages, intent caching methods)
"""

import json
import logging
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["intents"])


@router.get("/{session_id}/intents")
async def get_session_intents(
    session_id: str,
    refresh: bool = False,
) -> dict[str, Any]:
    """
    Extract high-level user intents from a session's prompts.

    Results are cached in the database. Use refresh=true to force
    re-computation.

    This calls `claude -p` on-demand to analyze the user prompts
    and extract 2-3 high-level goals/intents.

    Args:
        session_id: The session to analyze
        refresh: If true, ignore cache and recompute intents

    Returns:
        Dictionary with session_id, intents array, prompt_count, and cached flag
    """
    db = await get_db()

    # 1. Check cache first (unless refresh requested)
    if not refresh:
        cached = await db.get_session_intents(session_id)
        if cached:
            return {
                "session_id": cached["session_id"],
                "intents": cached["intents"],
                "prompt_count": cached["prompt_count"],
                "cached": True,
                "created_at": cached["created_at"],
            }

    # 2. Get all user messages for session
    messages = await db.get_user_messages(session_id)

    if not messages:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or no user messages: {session_id}",
        )

    # 3. Format prompts for Claude
    prompts_text = "\n---\n".join([
        m["prompt_text"] for m in messages
        if m["prompt_text"]
    ])

    if not prompts_text.strip():
        return {
            "session_id": session_id,
            "intents": [],
            "prompt_count": len(messages),
            "cached": False,
            "error": "No prompt text found in user messages",
        }

    # 4. Call claude -p to extract intents (using default model)
    try:
        result = subprocess.run(
            [
                "claude", "-p",
                f"""Analyze these user prompts from a coding session and extract 2-3 high-level user intents/goals. Be concise.

Prompts:
{prompts_text}

Output JSON array of intents like: ["intent1", "intent2", "intent3"]""",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Claude CLI error: {result.stderr}",
            )

        # 5. Parse JSON output
        output = result.stdout.strip()

        # Handle potential markdown code blocks in response
        if output.startswith("```"):
            # Extract JSON from code block
            lines = output.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            output = "\n".join(json_lines)

        intents = json.loads(output)

        # 6. Cache the result
        await db.save_session_intents(session_id, intents, len(messages))

        return {
            "session_id": session_id,
            "intents": intents,
            "prompt_count": len(messages),
            "cached": False,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Claude CLI timed out for session {session_id}")
        raise HTTPException(
            status_code=504,
            detail="Claude CLI timed out",
        )
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse intents: {e}",
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        raise HTTPException(
            status_code=500,
            detail="Claude CLI not installed or not in PATH",
        )
