"""
Timing metrics.

Session duration info.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory, MetricFormat

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents


@metric(
    name="session_duration",
    category=MetricCategory.TIMING,
    label="Duration",
    format=MetricFormat.DURATION,
    icon="ri-time-line",
    order=0,
)
def calc_session_duration(events: list[dict], pre: PreprocessedEvents = None) -> int | None:
    """Session duration in seconds from first to last event."""
    if pre and pre.first_timestamp and pre.last_timestamp:
        duration = (pre.last_timestamp - pre.first_timestamp).total_seconds()
        return int(duration)

    # Fallback
    from datetime import datetime

    def parse_ts(ts):
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    timestamps = [parse_ts(e.get("timestamp")) for e in events]
    valid = [t for t in timestamps if t]

    if len(valid) < 2:
        return None

    duration = (max(valid) - min(valid)).total_seconds()
    return int(duration)
