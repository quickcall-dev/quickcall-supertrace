"""
Tool usage breakdown.

Shows which tools were used and how often.
"""

from collections import Counter

from .registry import metric, MetricCategory, MetricFormat


def _get_tool_events(events: list[dict]) -> list[dict]:
    """Get all tool_use events."""
    return [e for e in events if e.get("event_type") == "tool_use"]


@metric(
    name="tool_distribution",
    category=MetricCategory.TOOLS,
    label="Tools Used",
    format=MetricFormat.DISTRIBUTION,
    icon="ri-pie-chart-line",
    order=10,
)
def calc_tool_distribution(events: list[dict]) -> dict[str, int]:
    """Count of each tool type used, sorted by frequency."""
    tool_events = _get_tool_events(events)
    counter = Counter(
        (e.get("data") or {}).get("tool_name", "unknown") for e in tool_events
    )
    return dict(counter.most_common())
