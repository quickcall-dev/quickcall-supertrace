"""
Efficiency metrics.

Measures how efficiently work was done.
"""

from .registry import metric, MetricCategory


def _get_prompts(events: list[dict]) -> list[dict]:
    """Get all user_prompt events."""
    return [e for e in events if e.get("event_type") == "user_prompt"]


def _get_tool_events(events: list[dict], tool_names: list[str]) -> list[dict]:
    """Get tool_use events for specific tools."""
    return [
        e for e in events
        if e.get("event_type") == "tool_use"
        and (e.get("data") or {}).get("tool_name") in tool_names
    ]


@metric(
    name="prompt_count",
    category=MetricCategory.INTERACTION,
    label="Prompts",
    icon="ri-chat-3-line",
    order=0,
)
def calc_prompt_count(events: list[dict]) -> int:
    """Number of user prompts sent."""
    return len(_get_prompts(events))


@metric(
    name="edits_per_prompt",
    category=MetricCategory.INTERACTION,
    label="Edits/Prompt",
    description="Average file edits per prompt (higher = more efficient)",
    icon="ri-speed-line",
    order=1,
)
def calc_edits_per_prompt(events: list[dict]) -> float:
    """Ratio of edits to prompts - higher means more efficient."""
    prompts = len(_get_prompts(events))
    edits = len(_get_tool_events(events, ["Edit", "Write", "MultiEdit"]))
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
def calc_completion_rate(events: list[dict]) -> int:
    """Percentage of prompts that resulted in assistant_stop."""
    prompts = len(_get_prompts(events))
    stops = len([e for e in events if e.get("event_type") == "assistant_stop"])

    if prompts == 0:
        return 0
    return min(100, round((stops / prompts) * 100))
