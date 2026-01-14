"""
Metric registry with decorator-based configuration.

Metrics are pure functions that compute values from events.
Register with @metric decorator. Access all via MetricRegistry.

Usage:
    @metric(
        name="total_tokens",
        category=MetricCategory.TOKENS,
        label="Total Tokens",
        mini_bar=True
    )
    def calc_total_tokens(events: list[dict]) -> int:
        return sum(...)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar


class MetricCategory(str, Enum):
    """Categories for grouping metrics in the UI."""
    TOKENS = "tokens"
    TOOLS = "tools"
    TIMING = "timing"
    INTERACTION = "interaction"
    CHARTS = "charts"


class MetricFormat(str, Enum):
    """Display format for metric values."""
    NUMBER = "number"
    PERCENTAGE = "percentage"
    DURATION = "duration"
    CURRENCY = "currency"
    DISTRIBUTION = "distribution"
    RAW = "raw"  # For complex data like chart data


@dataclass
class MetricConfig:
    """Configuration for a registered metric."""
    name: str
    category: MetricCategory
    label: str
    description: str = ""
    format: MetricFormat = MetricFormat.NUMBER
    icon: str = ""
    order: int = 0
    mini_bar: bool = False
    mini_bar_order: int = 99


T = TypeVar("T")
MetricFunc = Callable[[list[dict]], T]


class MetricRegistry:
    """Singleton registry for all metrics."""

    _metrics: dict[str, tuple[MetricConfig, MetricFunc]] = {}

    @classmethod
    def register(cls, config: MetricConfig, func: MetricFunc) -> None:
        """Register a metric function."""
        cls._metrics[config.name] = (config, func)

    @classmethod
    def compute_all(cls, events: list[dict], preprocessed: Any = None) -> dict[str, Any]:
        """Compute all metrics for given events.

        Args:
            events: Raw event list
            preprocessed: Optional PreprocessedEvents for optimized metrics
        """
        result = {}
        for name, (config, func) in cls._metrics.items():
            try:
                # Try to call with preprocessed data first (optimized metrics)
                # Fall back to events-only for legacy metrics
                import inspect
                sig = inspect.signature(func)
                if len(sig.parameters) >= 2 and preprocessed is not None:
                    value = func(events, preprocessed)
                else:
                    value = func(events)

                result[name] = {
                    "value": value,
                    "config": {
                        "name": config.name,
                        "category": config.category.value,
                        "label": config.label,
                        "description": config.description,
                        "format": config.format.value,
                        "icon": config.icon,
                        "order": config.order,
                        "mini_bar": config.mini_bar,
                        "mini_bar_order": config.mini_bar_order,
                    },
                }
            except Exception as e:
                result[name] = {"value": None, "error": str(e), "config": {
                    "name": config.name,
                    "category": config.category.value,
                    "label": config.label,
                    "format": config.format.value,
                }}
        return result

    @classmethod
    def get_by_category(cls) -> dict[str, list[str]]:
        """Get metric names grouped by category."""
        categories: dict[str, list[str]] = {}
        for name, (config, _) in cls._metrics.items():
            cat = config.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
        return categories


def metric(
    name: str,
    category: MetricCategory,
    label: str,
    description: str = "",
    format: MetricFormat = MetricFormat.NUMBER,
    icon: str = "",
    order: int = 0,
    mini_bar: bool = False,
    mini_bar_order: int = 99,
) -> Callable[[MetricFunc], MetricFunc]:
    """
    Decorator to register a metric function.

    Args:
        name: Unique identifier for the metric
        category: Category for grouping (tokens, tools, timing, interaction)
        label: Human-readable label for UI
        description: Optional longer description
        format: How to display the value (number, currency, duration, etc.)
        icon: Remix icon class name (e.g., "ri-coins-line")
        order: Display order within category (lower = first)
        mini_bar: Whether to show in collapsed mini-bar view
        mini_bar_order: Display order in mini-bar (lower = first)
    """

    def decorator(func: MetricFunc) -> MetricFunc:
        config = MetricConfig(
            name=name,
            category=category,
            label=label,
            description=description,
            format=format,
            icon=icon,
            order=order,
            mini_bar=mini_bar,
            mini_bar_order=mini_bar_order,
        )
        MetricRegistry.register(config, func)
        return func

    return decorator
