"""
Cost metrics.

Computes actual cost from token usage.
"""

from .registry import metric, MetricCategory, MetricFormat

# Cost per 1M tokens (Claude Sonnet 4 pricing)
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00
CACHE_READ_COST_PER_M = 0.30
CACHE_WRITE_COST_PER_M = 3.75


def _extract_token_usage(events: list[dict]) -> list[dict]:
    """Extract token_usage from assistant_stop events."""
    usages = []
    for e in events:
        if e.get("event_type") == "assistant_stop":
            data = e.get("data") or {}
            if usage := data.get("token_usage"):
                usages.append(usage)
    return usages


@metric(
    name="estimated_cost",
    category=MetricCategory.TOKENS,
    label="Cost",
    format=MetricFormat.CURRENCY,
    icon="ri-money-dollar-circle-line",
    order=0,
    mini_bar=True,
    mini_bar_order=0,
)
def calc_estimated_cost(events: list[dict]) -> float:
    """Estimated USD cost based on Claude pricing."""
    usages = _extract_token_usage(events)

    input_tokens = sum(u.get("input_tokens", 0) for u in usages)
    output_tokens = sum(u.get("output_tokens", 0) for u in usages)
    cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)
    cache_create = sum(u.get("cache_creation_input_tokens", 0) for u in usages)

    # Adjust input tokens for cache (cached tokens are billed differently)
    billable_input = max(0, input_tokens - cache_read - cache_create)

    cost = (
        (billable_input / 1_000_000) * INPUT_COST_PER_M
        + (output_tokens / 1_000_000) * OUTPUT_COST_PER_M
        + (cache_read / 1_000_000) * CACHE_READ_COST_PER_M
        + (cache_create / 1_000_000) * CACHE_WRITE_COST_PER_M
    )

    return round(cost, 2)


@metric(
    name="input_cost",
    category=MetricCategory.TOKENS,
    label="Input Cost",
    description="Cost for input/context tokens",
    format=MetricFormat.CURRENCY,
    icon="ri-arrow-down-circle-line",
    order=1,
)
def calc_input_cost(events: list[dict]) -> float:
    """Cost for input tokens only."""
    usages = _extract_token_usage(events)
    input_tokens = sum(u.get("input_tokens", 0) for u in usages)
    cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)
    cache_create = sum(u.get("cache_creation_input_tokens", 0) for u in usages)

    billable_input = max(0, input_tokens - cache_read - cache_create)

    cost = (
        (billable_input / 1_000_000) * INPUT_COST_PER_M
        + (cache_read / 1_000_000) * CACHE_READ_COST_PER_M
        + (cache_create / 1_000_000) * CACHE_WRITE_COST_PER_M
    )
    return round(cost, 2)


@metric(
    name="output_cost",
    category=MetricCategory.TOKENS,
    label="Output Cost",
    description="Cost for generated tokens",
    format=MetricFormat.CURRENCY,
    icon="ri-arrow-up-circle-line",
    order=2,
)
def calc_output_cost(events: list[dict]) -> float:
    """Cost for output tokens only."""
    usages = _extract_token_usage(events)
    output_tokens = sum(u.get("output_tokens", 0) for u in usages)
    return round((output_tokens / 1_000_000) * OUTPUT_COST_PER_M, 2)


@metric(
    name="cache_savings",
    category=MetricCategory.TOKENS,
    label="Cache Savings",
    description="Money saved from prompt caching",
    format=MetricFormat.CURRENCY,
    icon="ri-discount-percent-line",
    order=3,
)
def calc_cache_savings(events: list[dict]) -> float:
    """Estimated savings from using prompt cache vs full price."""
    usages = _extract_token_usage(events)
    cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)

    # Savings = what it would have cost at full price minus cache price
    full_price = (cache_read / 1_000_000) * INPUT_COST_PER_M
    cache_price = (cache_read / 1_000_000) * CACHE_READ_COST_PER_M
    return round(full_price - cache_price, 2)
