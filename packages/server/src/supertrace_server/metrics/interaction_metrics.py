"""
Efficiency metrics.

Measures how efficiently work was done.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents


@metric(
    name="prompt_count",
    category=MetricCategory.INTERACTION,
    label="Prompts",
    icon="ri-chat-3-line",
    order=0,
)
def calc_prompt_count(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Number of user prompts sent."""
    if pre:
        return len(pre.user_prompts)
    return len([e for e in events if e.get("event_type") == "user_prompt"])


@metric(
    name="edits_per_prompt",
    category=MetricCategory.INTERACTION,
    label="Edits/Prompt",
    description="Average file edits per prompt (higher = more efficient)",
    icon="ri-speed-line",
    order=1,
)
def calc_edits_per_prompt(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Ratio of edits to prompts - higher means more efficient."""
    if pre:
        prompts = len(pre.user_prompts)
        edits = sum(pre.tool_counts.get(t, 0) for t in ["Edit", "Write", "MultiEdit"])
    else:
        prompts = len([e for e in events if e.get("event_type") == "user_prompt"])
        edits = len([
            e for e in events
            if e.get("event_type") == "tool_use"
            and (e.get("data") or {}).get("tool_name") in ["Edit", "Write", "MultiEdit"]
        ])

    if prompts == 0:
        return 0.0
    return round(edits / prompts, 1)


@metric(
    name="completion_rate",
    category=MetricCategory.INTERACTION,
    label="Completion Rate",
    description="Percentage of prompts that got complete responses",
    icon="ri-checkbox-circle-line",
    order=2,
)
def calc_completion_rate(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Percentage of prompts that resulted in assistant_stop."""
    if pre:
        prompts = len(pre.user_prompts)
        stops = len(pre.assistant_stops)
    else:
        prompts = len([e for e in events if e.get("event_type") == "user_prompt"])
        stops = len([e for e in events if e.get("event_type") == "assistant_stop"])

    if prompts == 0:
        return 0
    return min(100, round((stops / prompts) * 100))
