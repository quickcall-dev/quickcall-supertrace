"""
Token calculation utilities.

Provides consistent token counting across the codebase.
The Claude API reports tokens in multiple fields that must be combined.

Related: metrics/preprocess.py (uses for aggregation), db/client.py (uses for events)
"""


def calculate_total_input_tokens(token_usage: dict) -> int:
    """
    Calculate total input tokens from token usage dict.

    The Claude API reports input tokens across multiple fields:
    - input_tokens: New tokens sent (can be 0 when all from cache)
    - cache_read_input_tokens: Tokens read from cache
    - cache_creation_input_tokens: Tokens added to cache

    Total context = input_tokens + cache_read + cache_creation

    Args:
        token_usage: Dict with token usage fields from API response

    Returns:
        Total input token count
    """
    input_tok = token_usage.get("input_tokens", 0) or 0
    cache_read = token_usage.get("cache_read_input_tokens", 0) or 0
    cache_create = token_usage.get("cache_creation_input_tokens", 0) or 0
    return input_tok + cache_read + cache_create
