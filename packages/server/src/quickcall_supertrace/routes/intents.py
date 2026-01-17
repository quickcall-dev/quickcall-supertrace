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

4. **Incremental Analysis**: When refresh is triggered, only new prompts since
   last analysis are sent to Claude. This saves tokens significantly.

5. **Intent Change Detection**: Compares new intents with previous, flags changes
   and includes change_reason from Claude.

6. **Markdown code block handling**: Claude sometimes wraps JSON in ```json blocks.
   We detect and strip these to parse the actual JSON.

7. **Error handling**: Returns HTTP errors for missing sessions (404), CLI failures (500),
   timeouts (504). Errors are logged but not cached.

## API Contract

- GET /api/sessions/{session_id}/intents
- GET /api/sessions/{session_id}/intents?refresh=true (force recompute)
- GET /api/sessions/{session_id}/intents?refresh_threshold=5 (auto-refresh if 5+ new prompts)

Response:
{
    session_id, intents: [...], prompt_count, cached,
    last_analyzed_prompt_index, intent_changed, change_reason?, previous_intents?
}

Related: db/client.py (get_user_messages, intent caching methods)
"""

import json
import logging
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import get_db
from ..ws import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["intents"])

# Prompt for full analysis (first time or forced refresh)
FULL_ANALYSIS_PROMPT = """Analyze these user prompts from a coding session and extract 2-3 high-level user intents/goals. Be concise.

Prompts:
{prompts}

Output JSON array of intents like: ["intent1", "intent2", "intent3"]"""

# Prompt for incremental analysis (subsequent refreshes)
INCREMENTAL_PROMPT = """You are analyzing user prompts from a coding session.

Previous intents extracted from earlier prompts:
{existing_intents}

New prompts since last analysis:
{new_prompts}

Analyze if the user's intents have changed based on the new prompts.

Return JSON:
{{
  "intents": ["intent1", "intent2", "intent3"],
  "changed": true/false,
  "change_reason": "Brief explanation if changed, null otherwise"
}}"""


def _extract_json_from_response(output: str) -> Any:
    """
    Extract JSON from Claude's response, handling markdown code blocks.

    Claude sometimes wraps JSON in ```json blocks. We detect and strip these.
    """
    output = output.strip()

    # Handle markdown code blocks
    if output.startswith("```"):
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

    return json.loads(output)


def _run_claude_cli(prompt: str, timeout: int = 60) -> str:
    """
    Run Claude CLI with the given prompt.

    Raises:
        HTTPException: On CLI errors, timeouts, or if CLI not found
    """
    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Claude CLI error: {result.stderr}",
            )

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out")
        raise HTTPException(
            status_code=504,
            detail="Claude CLI timed out",
        )
    except FileNotFoundError:
        logger.error("Claude CLI not found")
        raise HTTPException(
            status_code=500,
            detail="Claude CLI not installed or not in PATH",
        )


@router.get("/{session_id}/intents")
async def get_session_intents(
    session_id: str,
    refresh: bool = False,
    refresh_threshold: int = 5,
) -> dict[str, Any]:
    """
    Extract high-level user intents from a session's prompts.

    Results are cached in the database. Use refresh=true to force
    re-computation, or set refresh_threshold to auto-refresh when
    N+ new prompts exist since last analysis.

    This calls `claude -p` on-demand to analyze the user prompts
    and extract 2-3 high-level goals/intents. Incremental analysis
    only sends new prompts to save tokens.

    Args:
        session_id: The session to analyze
        refresh: If true, ignore cache and recompute intents
        refresh_threshold: Auto-refresh if this many new prompts since last analysis

    Returns:
        Dictionary with session_id, intents array, prompt_count, cached flag,
        and incremental analysis fields (last_analyzed_prompt_index, intent_changed, etc.)
    """
    db = await get_db()

    # 1. Get all user messages for session (needed for prompt count check)
    all_messages = await db.get_user_messages(session_id)

    if not all_messages:
        raise HTTPException(
            status_code=404,
            detail=f"Session not found or no user messages: {session_id}",
        )

    current_prompt_count = len(all_messages)

    # 2. Check cache first (unless refresh requested)
    cached = await db.get_session_intents(session_id)

    if cached and not refresh:
        # Check staleness - auto-refresh if enough new prompts
        last_analyzed = cached.get("last_analyzed_prompt_index") or cached.get("prompt_count") or 0
        new_prompts_since = current_prompt_count - last_analyzed

        if new_prompts_since < refresh_threshold:
            # Return cached result (not stale enough)
            return {
                "session_id": cached["session_id"],
                "intents": cached["intents"],
                "prompt_count": current_prompt_count,
                "last_analyzed_prompt_index": last_analyzed,
                "cached": True,
                "intent_changed": cached.get("intent_changed", False),
                "change_reason": cached.get("change_reason"),
                "previous_intents": cached.get("previous_intents"),
                "created_at": cached.get("created_at"),
            }

        # Auto-refresh triggered (enough new prompts)
        logger.info(
            f"Auto-refresh triggered for session {session_id}: "
            f"{new_prompts_since} new prompts >= threshold {refresh_threshold}"
        )

    # 3. Determine if we can do incremental analysis
    # Only do incremental if NOT explicitly refreshing (auto-refresh case)
    # When refresh=True is explicitly set, always do full analysis
    can_do_incremental = (
        not refresh  # Don't do incremental if explicit refresh requested
        and cached is not None
        and cached.get("intents")
        and (cached.get("last_analyzed_prompt_index") or cached.get("prompt_count"))
    )

    if can_do_incremental:
        # Incremental analysis - only fetch new prompts
        last_index = cached.get("last_analyzed_prompt_index") or cached.get("prompt_count") or 0
        new_messages = await db.get_user_messages_from_index(session_id, last_index)

        if not new_messages:
            # No new messages, return cached
            return {
                "session_id": session_id,
                "intents": cached["intents"],
                "prompt_count": current_prompt_count,
                "last_analyzed_prompt_index": last_index,
                "cached": True,
                "intent_changed": False,
                "change_reason": None,
                "previous_intents": None,
            }

        # Format new prompts for incremental analysis
        new_prompts_text = "\n---\n".join([
            m["prompt_text"] for m in new_messages
            if m.get("prompt_text")
        ])

        if not new_prompts_text.strip():
            return {
                "session_id": session_id,
                "intents": cached["intents"],
                "prompt_count": current_prompt_count,
                "last_analyzed_prompt_index": last_index,
                "cached": True,
                "intent_changed": False,
            }

        # Run incremental analysis
        prompt = INCREMENTAL_PROMPT.format(
            existing_intents=json.dumps(cached["intents"]),
            new_prompts=new_prompts_text,
        )

        output = _run_claude_cli(prompt)
        result = _extract_json_from_response(output)

        intents = result.get("intents", cached["intents"])
        intent_changed = result.get("changed", False)
        change_reason = result.get("change_reason") if intent_changed else None

        # Get the max prompt index from new messages
        max_prompt_index = max(
            (m.get("prompt_index") or 0 for m in new_messages),
            default=current_prompt_count
        )

        # Save updated intents
        await db.save_session_intents(
            session_id=session_id,
            intents=intents,
            prompt_count=current_prompt_count,
            last_analyzed_prompt_index=max_prompt_index,
            intent_changed=intent_changed,
            change_reason=change_reason,
            previous_intents=cached["intents"] if intent_changed else None,
        )

        # Broadcast to subscribed clients if intent changed
        if intent_changed:
            await manager.broadcast_to_session(session_id, {
                "type": "intent_changed",
                "session_id": session_id,
                "intents": intents,
                "changed": True,
                "change_reason": change_reason,
                "previous_intents": cached["intents"],
            })

        return {
            "session_id": session_id,
            "intents": intents,
            "prompt_count": current_prompt_count,
            "last_analyzed_prompt_index": max_prompt_index,
            "cached": False,
            "intent_changed": intent_changed,
            "change_reason": change_reason,
            "previous_intents": cached["intents"] if intent_changed else None,
        }

    else:
        # Full analysis - first time or forced refresh with no prior data
        prompts_text = "\n---\n".join([
            m["prompt_text"] for m in all_messages
            if m.get("prompt_text")
        ])

        if not prompts_text.strip():
            return {
                "session_id": session_id,
                "intents": [],
                "prompt_count": current_prompt_count,
                "last_analyzed_prompt_index": 0,
                "cached": False,
                "intent_changed": False,
                "error": "No prompt text found in user messages",
            }

        prompt = FULL_ANALYSIS_PROMPT.format(prompts=prompts_text)
        output = _run_claude_cli(prompt)
        intents = _extract_json_from_response(output)

        # Get the max prompt index
        max_prompt_index = max(
            (m.get("prompt_index") or 0 for m in all_messages),
            default=current_prompt_count
        )

        # Determine if this is a change from cached intents
        intent_changed = False
        change_reason = None
        previous_intents = None

        if cached and cached.get("intents"):
            # Compare with previous intents
            if set(intents) != set(cached["intents"]):
                intent_changed = True
                previous_intents = cached["intents"]
                change_reason = "Intents re-analyzed from all prompts"

        # Save the result
        await db.save_session_intents(
            session_id=session_id,
            intents=intents,
            prompt_count=current_prompt_count,
            last_analyzed_prompt_index=max_prompt_index,
            intent_changed=intent_changed,
            change_reason=change_reason,
            previous_intents=previous_intents,
        )

        # Broadcast to subscribed clients if intent changed
        if intent_changed:
            await manager.broadcast_to_session(session_id, {
                "type": "intent_changed",
                "session_id": session_id,
                "intents": intents,
                "changed": True,
                "change_reason": change_reason,
                "previous_intents": previous_intents,
            })

        return {
            "session_id": session_id,
            "intents": intents,
            "prompt_count": current_prompt_count,
            "last_analyzed_prompt_index": max_prompt_index,
            "cached": False,
            "intent_changed": intent_changed,
            "change_reason": change_reason,
            "previous_intents": previous_intents,
        }
