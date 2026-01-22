"""
Event handlers for Claude Code hooks.

Each handler processes a specific hook event type and sends
relevant data to the QuickCall SuperTrace server.

Related: models.py (data structures), cli.py (dispatches here)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

from .models import HookInput, ContextData

# Server configuration
DEFAULT_SERVER_URL = "http://localhost:7845"
TIMEOUT_SECONDS = 5

# Context window sizes by model
MODEL_CONTEXT_SIZES = {
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-opus-4": 200000,
    "claude-sonnet-4": 200000,
}
DEFAULT_CONTEXT_SIZE = 200000


def get_server_url() -> str:
    """Get server URL from env or use default."""
    return os.environ.get("QUICKCALL_SUPERTRACE_URL", DEFAULT_SERVER_URL)


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return os.environ.get("QUICKCALL_SUPERTRACE_DEBUG", "").lower() in ("true", "1", "yes")


def debug(msg: str) -> None:
    """Print debug message if debug mode is enabled."""
    if is_debug():
        print(f"[QuickCall SuperTrace] {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    """Log error message."""
    print(f"[QuickCall SuperTrace Error] {msg}", file=sys.stderr)


def send_context_update(session_id: str, context_data: ContextData) -> bool:
    """
    Send context update to QuickCall SuperTrace server.

    Returns True if successful, False otherwise.
    Fails silently to avoid blocking Claude Code.
    """
    url = f"{get_server_url()}/api/sessions/{session_id}/context"

    try:
        data = json.dumps(context_data.model_dump()).encode("utf-8")
        request = Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            debug(f"Context update sent: {response.status}")
            return response.status == 200
    except URLError as e:
        debug(f"Failed to send context update: {e}")
        return False
    except Exception as e:
        debug(f"Unexpected error sending context: {e}")
        return False


def get_context_size_for_model(model: str | None) -> int:
    """Get context window size for a model."""
    if not model:
        return DEFAULT_CONTEXT_SIZE

    # Normalize model name
    model_lower = model.lower()
    for key, size in MODEL_CONTEXT_SIZES.items():
        if key in model_lower:
            return size

    return DEFAULT_CONTEXT_SIZE


def read_transcript(path: str | None) -> list[dict] | None:
    """Read and parse the JSONL transcript file."""
    if not path:
        return None

    transcript_path = Path(path)
    if not transcript_path.exists():
        return None

    messages = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    except (json.JSONDecodeError, IOError) as e:
        debug(f"Error reading transcript: {e}")
        return None

    return messages


def extract_usage_from_transcript(transcript: list[dict] | None) -> dict[str, Any] | None:
    """
    Extract token usage from the LAST assistant message in the transcript.

    Returns dict with input_tokens, output_tokens, cache tokens, and model.
    """
    if not transcript:
        return None

    # Find the last assistant message (iterate backwards)
    for entry in reversed(transcript):
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            usage = message.get("usage", {})
            model = message.get("model")

            if usage:
                return {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    "model": model,
                }

    return None


def handle_stop(hook_input: HookInput) -> None:
    """
    Handle Stop hook - Claude finished responding.

    This is the main hook for context tracking since it fires
    after each complete response with full usage data.

    Context window % is calculated from input_tokens only (not output).
    The input_tokens field represents the total context sent to the model.
    """
    debug(f"Handle stop for session: {hook_input.session_id}")

    # Read transcript to get usage data
    transcript = read_transcript(hook_input.transcript_path)
    usage = extract_usage_from_transcript(transcript)

    if not usage:
        debug("No usage data found in transcript")
        return

    # Get model and context size
    model = usage.get("model") or hook_input.model
    context_size = get_context_size_for_model(model)

    # Extract token counts from the LAST message
    # From Anthropic API:
    # - input_tokens: FRESH (non-cached) input tokens
    # - cache_read_input_tokens: tokens read from cache
    # - cache_creation_input_tokens: tokens written to cache
    # - output_tokens: tokens generated by model (NOT part of context window)
    #
    # Total context = input_tokens + cache_read + cache_create
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)

    # Context window = total INPUT tokens (fresh + cached)
    # Output tokens do NOT count toward context window
    total_context = input_tokens + cache_read + cache_create
    used_pct = min(100.0, (total_context / context_size) * 100)
    remaining_pct = max(0.0, 100.0 - used_pct)

    debug(f"Usage: {total_context}/{context_size} tokens ({used_pct:.1f}%)")

    # Build context data
    context_data = ContextData(
        used_percentage=round(used_pct, 2),
        remaining_percentage=round(remaining_pct, 2),
        context_window_size=context_size,
        total_input_tokens=total_context,  # Total context (fresh + cached)
        total_output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_create_tokens=cache_create,
        model=model,
    )

    # Send to server
    send_context_update(hook_input.session_id, context_data)


def handle_tool(hook_input: HookInput) -> None:
    """
    Handle PostToolUse hook - tool finished executing.

    We also capture context here for more granular tracking.
    """
    debug(f"Handle tool for session: {hook_input.session_id}, tool: {hook_input.tool_name}")

    # Same logic as stop - extract usage and send
    transcript = read_transcript(hook_input.transcript_path)
    usage = extract_usage_from_transcript(transcript)

    if not usage:
        debug("No usage data found")
        return

    model = usage.get("model") or hook_input.model
    context_size = get_context_size_for_model(model)

    # Context window = total input (fresh + cached), NOT output
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)

    total_context = input_tokens + cache_read + cache_create
    used_pct = min(100.0, (total_context / context_size) * 100)
    remaining_pct = max(0.0, 100.0 - used_pct)

    context_data = ContextData(
        used_percentage=round(used_pct, 2),
        remaining_percentage=round(remaining_pct, 2),
        context_window_size=context_size,
        total_input_tokens=total_context,
        total_output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_create_tokens=cache_create,
        model=model,
    )

    send_context_update(hook_input.session_id, context_data)


def handle_session_start(hook_input: HookInput) -> None:
    """Handle SessionStart hook - new session began."""
    debug(f"Session started: {hook_input.session_id}")
    # Could notify server of new session if needed


def handle_session_end(hook_input: HookInput) -> None:
    """Handle SessionEnd hook - session ended."""
    debug(f"Session ended: {hook_input.session_id}")
    # Could notify server of session end if needed


def handle_prompt(hook_input: HookInput) -> None:
    """Handle UserPromptSubmit hook - user sent a message."""
    debug(f"User prompt for session: {hook_input.session_id}")
    # Could track prompts if needed


def handle_notification(hook_input: HookInput) -> None:
    """Handle Notification hook - Claude sent a notification."""
    debug(f"Notification for session: {hook_input.session_id}: {hook_input.reason}")


def handle_precompact(hook_input: HookInput) -> None:
    """Handle PreCompact hook - context compaction about to happen."""
    debug(f"PreCompact for session: {hook_input.session_id}")
    # Context is about to be compressed - could log current state
