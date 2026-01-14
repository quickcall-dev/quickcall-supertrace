"""
Single-pass event preprocessing for efficient metrics computation.

Extracts commonly needed data from events in one iteration,
avoiding repeated filtering in individual metric functions.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.tokens import calculate_total_input_tokens

# Patterns to detect git commits
GIT_COMMIT_PATTERNS = [
    re.compile(r"\bgit\s+commit\b", re.IGNORECASE),
    re.compile(r"\bgit\s+.*\s+commit\b", re.IGNORECASE),  # git -c ... commit
]


def is_git_commit(command: str) -> bool:
    """Check if a bash command is a git commit."""
    return any(p.search(command) for p in GIT_COMMIT_PATTERNS)


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime (always returns naive UTC)."""
    if not ts:
        return None
    try:
        # Normalize to naive UTC datetime for consistent comparison
        ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        # Convert to naive UTC by removing tzinfo
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


@dataclass
class PreprocessedEvents:
    """Pre-extracted event data for efficient metric computation."""

    # Raw events for metrics that need full iteration
    events: list[dict] = field(default_factory=list)

    # Filtered event lists (single-pass extraction)
    user_prompts: list[dict] = field(default_factory=list)
    assistant_stops: list[dict] = field(default_factory=list)
    tool_uses: list[dict] = field(default_factory=list)
    session_starts: list[dict] = field(default_factory=list)
    session_ends: list[dict] = field(default_factory=list)

    # Token usage extracted from assistant_stop events
    token_usages: list[dict] = field(default_factory=list)

    # Tool counts
    tool_counts: Counter = field(default_factory=Counter)

    # Timestamps
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None

    # Aggregated token counts (computed during preprocessing)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0

    # Interrupt tracking
    user_interrupts: int = 0  # "[Request interrupted by user]" messages
    tool_interrupts: int = 0  # Tools with interrupted=true

    # Hero metrics tracking
    commit_count: int = 0  # Successful git commits
    tool_successes: int = 0  # Tools that completed without error
    tool_failures: int = 0  # Tools with is_error=true or interrupted
    images_sent: int = 0  # Images pasted/sent by user
    thinking_enabled_prompts: int = 0  # Prompts with thinking mode on


def preprocess_events(events: list[dict]) -> PreprocessedEvents:
    """
    Single-pass preprocessing of events.

    Extracts all commonly needed data in one iteration through the event list.
    This is much more efficient than having each metric iterate separately.
    """
    result = PreprocessedEvents(events=events)

    for event in events:
        event_type = event.get("event_type")
        data = event.get("data") or {}

        # Parse timestamp for first/last tracking
        ts = parse_timestamp(event.get("timestamp"))
        if ts:
            if result.first_timestamp is None or ts < result.first_timestamp:
                result.first_timestamp = ts
            if result.last_timestamp is None or ts > result.last_timestamp:
                result.last_timestamp = ts

        # Categorize by event type
        if event_type == "user_prompt":
            result.user_prompts.append(event)
            # Check for user interrupt - "[Request interrupted by user]"
            prompt = data.get("prompt") or ""
            if "[Request interrupted by user]" in prompt:
                result.user_interrupts += 1
            # Count images from imagePasteIds
            # imagePasteIds is an array of paste IDs like [1, 2, 3] - we count LENGTH not sum
            # Each ID represents one image pasted by the user in that prompt
            image_paste_ids = data.get("imagePasteIds") or []
            result.images_sent += len(image_paste_ids)
            # Check thinking mode - enabled if not disabled or level is not "none"
            thinking_meta = data.get("thinkingMetadata") or {}
            thinking_disabled = thinking_meta.get("disabled", True)
            thinking_level = thinking_meta.get("level", "none")
            if not thinking_disabled or thinking_level != "none":
                result.thinking_enabled_prompts += 1

        elif event_type == "assistant_stop":
            result.assistant_stops.append(event)
            # Extract token usage
            if token_usage := data.get("token_usage"):
                result.token_usages.append(token_usage)
                # Aggregate tokens using shared utility
                result.total_input_tokens += calculate_total_input_tokens(token_usage)
                result.total_output_tokens += token_usage.get("output_tokens", 0) or 0
                result.total_cache_read_tokens += token_usage.get("cache_read_input_tokens", 0) or 0
                result.total_cache_creation_tokens += token_usage.get("cache_creation_input_tokens", 0) or 0

        elif event_type == "tool_use":
            result.tool_uses.append(event)
            tool_name = data.get("tool_name", "unknown")
            result.tool_counts[tool_name] += 1

            tool_result = data.get("tool_result")
            tool_input = data.get("tool_input") or {}

            # Track tool success/failure
            is_error = False
            is_interrupted = False

            if isinstance(tool_result, dict):
                is_error = tool_result.get("is_error", False)
                is_interrupted = tool_result.get("interrupted", False)

            if is_error or is_interrupted:
                result.tool_failures += 1
                if is_interrupted:
                    result.tool_interrupts += 1
            else:
                result.tool_successes += 1

            # Detect git commits - Bash tool with "git commit" command
            if tool_name == "Bash" and not is_error and not is_interrupted:
                command = tool_input.get("command", "")
                if is_git_commit(command):
                    result.commit_count += 1

        elif event_type == "session_start":
            result.session_starts.append(event)

        elif event_type == "session_end":
            result.session_ends.append(event)

    return result
