"""
Tool usage breakdown.

Shows which tools were used and how often.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from collections import Counter
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory, MetricFormat

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents


@metric(
    name="tool_distribution",
    category=MetricCategory.TOOLS,
    label="Tools Used",
    format=MetricFormat.DISTRIBUTION,
    icon="ri-pie-chart-line",
    order=10,
)
def calc_tool_distribution(events: list[dict], pre: PreprocessedEvents = None) -> dict[str, int]:
    """Count of each tool type used, sorted by frequency."""
    if pre:
        return dict(pre.tool_counts.most_common())

    # Fallback
    counter = Counter(
        (e.get("data") or {}).get("tool_name", "unknown")
        for e in events
        if e.get("event_type") == "tool_use"
    )
    return dict(counter.most_common())
