"""
Timing metrics.

Session duration info.
"""

from datetime import datetime

from .registry import metric, MetricCategory, MetricFormat


def _parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime."""
    if not ts:
        return None
    try:
        ts_clean = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts_clean)
    except (ValueError, AttributeError):
        return None


@metric(
    name="session_duration",
    category=MetricCategory.TIMING,
    label="Duration",
    format=MetricFormat.DURATION,
    icon="ri-time-line",
    order=0,
)
def calc_session_duration(events: list[dict]) -> int | None:
    """Session duration in seconds from first to last event."""
    timestamps = [_parse_timestamp(e.get("timestamp")) for e in events]
    valid = [t for t in timestamps if t]

    if len(valid) < 2:
        return None

    duration = (max(valid) - min(valid)).total_seconds()
    return int(duration)
