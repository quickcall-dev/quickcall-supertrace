"""
Single-pass event preprocessing for efficient metrics computation.

Extracts commonly needed data from events in one iteration,
avoiding repeated filtering in individual metric functions.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime."""
    if not ts:
        return None
    try:
        ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
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

        elif event_type == "assistant_stop":
            result.assistant_stops.append(event)
            # Extract token usage
            if token_usage := data.get("token_usage"):
                result.token_usages.append(token_usage)
                # Aggregate tokens
                result.total_input_tokens += token_usage.get("input_tokens", 0)
                result.total_output_tokens += token_usage.get("output_tokens", 0)
                result.total_cache_read_tokens += token_usage.get(
                    "cache_read_input_tokens", 0
                )
                result.total_cache_creation_tokens += token_usage.get(
                    "cache_creation_input_tokens", 0
                )

        elif event_type == "tool_use":
            result.tool_uses.append(event)
            tool_name = data.get("tool_name", "unknown")
            result.tool_counts[tool_name] += 1

        elif event_type == "session_start":
            result.session_starts.append(event)

        elif event_type == "session_end":
            result.session_ends.append(event)

    return result
