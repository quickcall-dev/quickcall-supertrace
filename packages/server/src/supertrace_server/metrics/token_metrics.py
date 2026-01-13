"""
Cost metrics.

Computes actual cost from token usage.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory, MetricFormat

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents

# Cost per 1M tokens (Claude Sonnet 4 pricing)
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00
CACHE_READ_COST_PER_M = 0.30
CACHE_WRITE_COST_PER_M = 3.75


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
def calc_estimated_cost(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """
    Estimated USD cost based on Claude pricing.

    TOKEN STRUCTURE FROM ANTHROPIC API:
    - input_tokens: Can be 0 when all context is cached
    - cache_read_input_tokens: Tokens read from cache (cheaper)
    - cache_creation_input_tokens: Tokens used to create cache (1.25x input cost)
    - Total context = input_tokens + cache_read + cache_create
    - Billable input = total context - cache tokens (the non-cached portion)
    """
    if pre:
        # pre.total_input_tokens already includes cache tokens (total context)
        total_context = pre.total_input_tokens
        output_tokens = pre.total_output_tokens
        cache_read = pre.total_cache_read_tokens
        cache_create = pre.total_cache_creation_tokens
    else:
        # Fallback for legacy calls
        usages = [
            e.get("data", {}).get("token_usage", {})
            for e in events
            if e.get("event_type") == "assistant_stop"
        ]
        # Total context = input + cache_read + cache_create
        raw_input = sum(u.get("input_tokens", 0) for u in usages)
        cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)
        cache_create = sum(u.get("cache_creation_input_tokens", 0) for u in usages)
        total_context = raw_input + cache_read + cache_create
        output_tokens = sum(u.get("output_tokens", 0) for u in usages)

    # Billable input = non-cached tokens (total context minus cached portions)
    billable_input = max(0, total_context - cache_read - cache_create)

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
def calc_input_cost(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Cost for input tokens only (context sent to model)."""
    if pre:
        # pre.total_input_tokens already includes cache tokens (total context)
        total_context = pre.total_input_tokens
        cache_read = pre.total_cache_read_tokens
        cache_create = pre.total_cache_creation_tokens
    else:
        usages = [
            e.get("data", {}).get("token_usage", {})
            for e in events
            if e.get("event_type") == "assistant_stop"
        ]
        raw_input = sum(u.get("input_tokens", 0) for u in usages)
        cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)
        cache_create = sum(u.get("cache_creation_input_tokens", 0) for u in usages)
        total_context = raw_input + cache_read + cache_create

    billable_input = max(0, total_context - cache_read - cache_create)

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
def calc_output_cost(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Cost for output tokens only."""
    if pre:
        output_tokens = pre.total_output_tokens
    else:
        usages = [
            e.get("data", {}).get("token_usage", {})
            for e in events
            if e.get("event_type") == "assistant_stop"
        ]
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
def calc_cache_savings(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Estimated savings from using prompt cache vs full price."""
    if pre:
        cache_read = pre.total_cache_read_tokens
    else:
        usages = [
            e.get("data", {}).get("token_usage", {})
            for e in events
            if e.get("event_type") == "assistant_stop"
        ]
        cache_read = sum(u.get("cache_read_input_tokens", 0) for u in usages)

    full_price = (cache_read / 1_000_000) * INPUT_COST_PER_M
    cache_price = (cache_read / 1_000_000) * CACHE_READ_COST_PER_M
    return round(full_price - cache_price, 2)
