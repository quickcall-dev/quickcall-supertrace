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
FULL_ANALYSIS_PROMPT = """Extract 2-3 user intents from these coding session prompts.

Rules:
- Each intent must be 3-6 words maximum
- Use action verbs (Build, Fix, Add, Debug, Refactor)
- No filler words

Prompts:
{prompts}"""

# Prompt for incremental analysis (subsequent refreshes)
INCREMENTAL_PROMPT = """Previous intents: {existing_intents}

New prompts since last analysis:
{new_prompts}

Did intents change? Keep each intent to 3-6 words max."""

# JSON schemas for --json-schema flag (forces reliable JSON output)
FULL_ANALYSIS_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "intents": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-3 high-level user intents"
        }
    },
    "required": ["intents"]
})

INCREMENTAL_SCHEMA = json.dumps({
    "type": "object",
    "properties": {
        "intents": {"type": "array", "items": {"type": "string"}},
        "changed": {"type": "boolean"},
        "change_reason": {"type": ["string", "null"]}
    },
    "required": ["intents", "changed", "change_reason"]
})


def _extract_json_from_response(output: str) -> Any:
    """
    Extract JSON from Claude's response, handling markdown code blocks.

    Claude sometimes wraps JSON in ```json blocks. We detect and strip these.

    Raises:
        HTTPException: If output is empty or not valid JSON
    """
    original_output = output  # Keep for logging
    output = output.strip()

    if not output:
        logger.error("Claude CLI returned empty output")
        raise HTTPException(
            status_code=500,
            detail="Claude CLI returned empty response",
        )

    # Log raw output for debugging (truncated)
    logger.debug(f"Raw Claude output (first 500 chars): {output[:500]}")

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

    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parse failed, attempting extraction: {output[:200]}")

        # Fallback: Try to find JSON array or object in the response
        # Sometimes Claude prefixes with prose text
        import re

        # Try to find a JSON array
        array_match = re.search(r'\[[\s\S]*?\]', output)
        if array_match:
            try:
                result = json.loads(array_match.group())
                logger.info(f"Successfully extracted JSON array from response")
                return result
            except json.JSONDecodeError:
                pass

        # Try to find a JSON object
        obj_match = re.search(r'\{[\s\S]*\}', output)
        if obj_match:
            try:
                result = json.loads(obj_match.group())
                logger.info(f"Successfully extracted JSON object from response")
                return result
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse Claude response as JSON: {output[:200]}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse intent response: {e}",
        )


def _run_claude_cli(prompt: str, json_schema: str | None = None, timeout: int = 120) -> dict[str, Any]:
    """
    Run Claude CLI with the given prompt and optional JSON schema.

    Uses --output-format json for structured output.
    When json_schema is provided, uses --json-schema for enforced structure.

    Args:
        prompt: The prompt to send to Claude
        json_schema: Optional JSON schema string for structured output
        timeout: Command timeout in seconds (default 120s)

    Returns:
        Parsed JSON response. When json_schema is used, returns the structured_output field.

    Raises:
        HTTPException: On CLI errors, timeouts, or if CLI not found
    """
    try:
        logger.info("Running Claude CLI for intent extraction...")
        logger.info(f"Prompt length: {len(prompt)} chars")
        logger.debug(f"Full prompt:\n{prompt}")

        # Build command with JSON output format
        # --no-session-persistence prevents creating session files that pollute the session list
        cmd = ["claude", "-p", prompt, "--output-format", "json", "--no-session-persistence"]

        # Add JSON schema if provided for structured output
        if json_schema:
            cmd.extend(["--json-schema", json_schema])
            logger.debug(f"Using JSON schema: {json_schema[:100]}...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            logger.error(f"Claude CLI failed (code {result.returncode}): {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Claude CLI error: {result.stderr or 'Unknown error'}",
            )

        output = result.stdout.strip()
        if not output:
            logger.warning(f"Claude CLI returned empty stdout. stderr: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail="Claude CLI returned empty response",
            )

        logger.info(f"Claude CLI returned {len(output)} chars")
        logger.debug(f"Full Claude output: {output}")

        # Parse the JSON response from Claude CLI
        try:
            response = json.loads(output)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude CLI JSON response: {output[:200]}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse Claude CLI response: {e}",
            )

        # When using --json-schema, the structured output is in 'structured_output' field
        if json_schema and "structured_output" in response:
            return response["structured_output"]

        # Fallback: return the 'result' field or the whole response
        if "result" in response:
            # Parse the result field if it's a string containing JSON
            result_content = response["result"]
            logger.info(f"Result field type: {type(result_content).__name__}, length: {len(str(result_content))}")
            logger.debug(f"Result content (first 300 chars): {str(result_content)[:300]}")

            if isinstance(result_content, str):
                try:
                    parsed = json.loads(result_content)
                    logger.info(f"Successfully parsed result as JSON: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}")
                    return parsed
                except json.JSONDecodeError as e:
                    # Not JSON, might need extraction
                    logger.warning(f"Result is not valid JSON ({e}), attempting extraction...")
                    return _extract_json_from_response(result_content)
            return result_content

        return response

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

        # Format new prompts for incremental analysis (truncate each to save tokens)
        new_prompts_text = "\n---\n".join([
            m["prompt_text"][:300] for m in new_messages
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

        # Run incremental analysis with --json-schema for reliable JSON
        prompt = INCREMENTAL_PROMPT.format(
            existing_intents=json.dumps(cached["intents"]),
            new_prompts=new_prompts_text,
        )

        result = _run_claude_cli(prompt, json_schema=INCREMENTAL_SCHEMA)

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
        # Truncate each prompt to 300 chars to keep context reasonable
        prompts_text = "\n---\n".join([
            m["prompt_text"][:300] for m in all_messages
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
        result = _run_claude_cli(prompt, json_schema=FULL_ANALYSIS_SCHEMA)
        intents = result.get("intents", [])

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
