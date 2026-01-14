"""
Metrics package.

Exposes compute_metrics() for calculating all session metrics
and the metric decorator for adding new metrics.

Usage:
    from quickcall_supertrace.metrics import compute_metrics

    events = [...]  # list of event dicts
    metrics = compute_metrics(events)

Adding new metrics:
    @metric(
        name="my_metric",
        category=MetricCategory.TOKENS,
        label="My Metric",
    )
    def calc_my_metric(events: list[dict]) -> int:
        return ...
"""

from typing import Any

from .registry import MetricCategory, MetricFormat, MetricRegistry, metric
from .preprocess import preprocess_events

# Import all metric modules to register them
from . import chart_metrics as _charts  # noqa: F401
from . import interaction_metrics as _interaction  # noqa: F401
from . import timing_metrics as _timing  # noqa: F401
from . import token_metrics as _tokens  # noqa: F401
from . import tool_metrics as _tools  # noqa: F401
from . import work_metrics as _work  # noqa: F401

__all__ = [
    "compute_metrics",
    "metric",
    "MetricCategory",
    "MetricFormat",
]


def compute_metrics(events: list[dict]) -> dict[str, Any]:
    """
    Compute all registered metrics for a list of events.

    Uses single-pass preprocessing for efficiency - all event filtering
    is done once upfront, then metrics use the pre-filtered data.

    Returns dict with two keys:
    - by_category: Metrics grouped by category (tokens, tools, timing, interaction)
    - mini_bar: List of metrics flagged for mini-bar display

    Example response:
    {
        "by_category": {
            "tokens": {
                "total_tokens": {"value": 12500, "config": {...}},
                ...
            },
            "tools": {...}
        },
        "mini_bar": [
            {"name": "total_tokens", "value": 12500, "config": {...}},
            ...
        ]
    }
    """
    # Single-pass preprocessing - extract all commonly needed data
    preprocessed = preprocess_events(events)

    # Compute metrics using preprocessed data
    raw = MetricRegistry.compute_all(events, preprocessed)

    # Group by category
    grouped: dict[str, dict] = {}
    mini_bar: list[dict] = []

    for name, data in raw.items():
        config = data.get("config", {})
        category = config.get("category", "other")

        if category not in grouped:
            grouped[category] = {}
        grouped[category][name] = data

        if config.get("mini_bar"):
            mini_bar.append({"name": name, **data})

    # Sort within categories by order
    for cat in grouped.values():
        sorted_items = sorted(
            cat.items(), key=lambda x: x[1].get("config", {}).get("order", 99)
        )
        cat.clear()
        cat.update(sorted_items)

    # Sort mini_bar by mini_bar_order
    mini_bar.sort(key=lambda x: x.get("config", {}).get("mini_bar_order", 99))

    return {
        "by_category": grouped,
        "mini_bar": mini_bar,
    }
