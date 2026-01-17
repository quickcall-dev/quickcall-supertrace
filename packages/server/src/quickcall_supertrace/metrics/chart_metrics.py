"""
Chart data metrics.

Pre-computes data for frontend charts:
- prompt_turns: tokens and tools per prompt turn for unified chart
"""

import re
from datetime import datetime
from .registry import MetricCategory, MetricFormat, metric


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to datetime (always returns naive UTC)."""
    if not ts:
        return None
    try:
        # Normalize to naive UTC datetime for consistent comparison
        ts = ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        # Convert to naive UTC by removing tzinfo
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None

# Patterns to detect git commits
GIT_COMMIT_PATTERNS = [
    re.compile(r"\bgit\s+commit\b", re.IGNORECASE),
    re.compile(r"\bgit\s+.*\s+commit\b", re.IGNORECASE),  # git -c ... commit
]

# Tool colors - distinctive palette for each tool type
# Using colors that are visually distinct from each other and from token lines
TOOL_COLORS = {
    # File reading tools - shades of blue/cyan
    "Read": "#3b82f6",       # Blue
    "Glob": "#06b6d4",       # Cyan
    "Grep": "#6366f1",       # Indigo

    # File writing tools - warm colors
    "Write": "#10b981",      # Emerald
    "Edit": "#f59e0b",       # Amber
    "TodoWrite": "#84cc16",  # Lime

    # System tools - orange/red spectrum
    "Bash": "#f97316",       # Orange
    "KillShell": "#ef4444",  # Red
    "TaskOutput": "#fb923c", # Light orange

    # Agent tools - purple spectrum
    "Task": "#a855f7",       # Purple
    "EnterPlanMode": "#8b5cf6",  # Violet
    "ExitPlanMode": "#7c3aed",   # Dark violet

    # Web tools - teal/sky
    "WebFetch": "#14b8a6",   # Teal
    "WebSearch": "#0ea5e9",  # Sky blue

    # Interaction tools - pink/rose
    "AskUserQuestion": "#ec4899",  # Pink
    "Skill": "#f43f5e",      # Rose

    # MCP tools
    "mcp__ide__getDiagnostics": "#64748b",  # Slate
}

DEFAULT_TOOL_COLOR = "#94a3b8"  # Slate gray for unknown tools
MCP_PLUGIN_COLOR = "#14b8a6"   # Teal 500 (brand color) - for mcp__plugin_* tools


def get_tool_color(name: str) -> str:
    """Get color for a tool, with special handling for MCP plugin tools."""
    if name in TOOL_COLORS:
        return TOOL_COLORS[name]
    if name.startswith("mcp__plugin"):
        return MCP_PLUGIN_COLOR
    return DEFAULT_TOOL_COLOR


@metric(
    name="prompt_turns",
    category=MetricCategory.CHARTS,
    label="Prompt Turns",
    format=MetricFormat.RAW,
    order=1,
)
def calc_prompt_turns(events: list[dict]) -> dict:
    """
    Compute per-prompt turn data for unified chart.

    Returns:
        {
            "turns": [
                {
                    "promptIndex": 1,
                    "promptEventId": 123,
                    "responseEventId": 456,
                    "inputTokens": 5000,
                    "outputTokens": 1200,
                    "tools": [
                        {"name": "Read", "count": 3, "color": "#60a5fa"},
                        {"name": "Edit", "count": 2, "color": "#fbbf24"}
                    ],
                    "totalTools": 5
                },
                ...
            ],
            "maxTokens": 15000,
            "maxTools": 12,
            "totals": {
                "inputTokens": 50000,
                "outputTokens": 12000,
                "tools": 45
            },
            "toolLegend": [
                {"name": "Read", "count": 20, "color": "#60a5fa"},
                ...
            ]
        }
    """
    turns = []
    prompt_index = 0

    total_input = 0
    total_input_no_cache = 0
    total_cache_read = 0
    total_cache_create = 0
    total_output = 0
    total_tools = 0
    total_commits = 0
    total_thinking = 0
    max_tokens = 0
    max_tokens_no_cache = 0
    max_tools = 0
    max_duration = 0

    # Global tool counts for legend
    global_tool_counts: dict[str, int] = {}

    def is_git_commit(command: str) -> bool:
        """Check if a bash command is a git commit."""
        return any(p.search(command) for p in GIT_COMMIT_PATTERNS)

    i = 0
    while i < len(events):
        event = events[i]

        if event.get("event_type") == "user_prompt":
            # Use the actual promptIndex from event data (set by get_messages_as_events)
            # This preserves correct numbering even when time-filtered
            event_data = event.get("data", {})
            actual_prompt_index = event_data.get("promptIndex")
            if actual_prompt_index is None:
                # Fallback for legacy events without promptIndex
                prompt_index += 1
                actual_prompt_index = prompt_index

            start_time = parse_timestamp(event.get("timestamp"))
            turn = {
                "promptIndex": actual_prompt_index,
                "promptEventId": event.get("id"),
                "responseEventId": event.get("id"),
                "inputTokens": 0,        # Total context (input + cache_read + cache_create)
                "inputTokensNoCache": 0, # Just input_tokens (new tokens, not from cache)
                "cacheReadTokens": 0,    # Tokens read from cache
                "cacheCreateTokens": 0,  # Tokens written to cache
                "outputTokens": 0,
                "tools": [],
                "totalTools": 0,
                "hasCommit": False,
                "hasThinking": False,
                "startTime": event.get("timestamp"),
                "endTime": None,
                "durationSeconds": None,
            }

            # Collect ALL tools and assistant_stops until next user_prompt
            # Tools may come before OR after assistant_stop events
            tool_counts: dict[str, int] = {}
            end_time = None
            total_output_tokens = 0

            j = i + 1
            while j < len(events):
                e = events[j]

                # Stop at next user prompt
                if e.get("event_type") == "user_prompt":
                    break

                if e.get("event_type") == "tool_use":
                    tool_name = e.get("data", {}).get("tool_name", "unknown")
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                    turn["totalTools"] += 1
                    # Update global counts
                    global_tool_counts[tool_name] = global_tool_counts.get(tool_name, 0) + 1

                    # Check for git commit in Bash commands
                    if tool_name == "Bash" and not turn["hasCommit"]:
                        tool_input = e.get("data", {}).get("tool_input", {})
                        command = tool_input.get("command", "")
                        if is_git_commit(command):
                            turn["hasCommit"] = True
                            total_commits += 1

                elif e.get("event_type") == "assistant_stop":
                    # Track the last assistant_stop for end time and tokens
                    turn["responseEventId"] = e.get("id")
                    turn["endTime"] = e.get("timestamp")
                    end_time = parse_timestamp(e.get("timestamp"))
                    token_usage = e.get("data", {}).get("token_usage", {})
                    if token_usage:
                        # Extract all token values
                        input_tok = token_usage.get("input_tokens", 0)
                        cache_read = token_usage.get("cache_read_input_tokens", 0)
                        cache_create = token_usage.get("cache_creation_input_tokens", 0)

                        # Total context = input + cache_read + cache_create
                        turn["inputTokens"] = input_tok + cache_read + cache_create
                        # Individual components for toggle
                        turn["inputTokensNoCache"] = input_tok
                        turn["cacheReadTokens"] = cache_read
                        turn["cacheCreateTokens"] = cache_create

                        # Sum output tokens from all assistant_stops in this turn
                        total_output_tokens += token_usage.get("output_tokens", 0)

                    # Check for thinking content
                    if not turn["hasThinking"] and e.get("data", {}).get("thinkingContent"):
                        turn["hasThinking"] = True
                        total_thinking += 1

                j += 1

            turn["outputTokens"] = total_output_tokens

            # Calculate duration
            # Cap at 30 minutes - longer durations indicate user went AFK/took a break
            # and shouldn't count as actual turn duration
            MAX_TURN_DURATION = 30 * 60  # 30 minutes in seconds
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                if duration <= MAX_TURN_DURATION:
                    turn["durationSeconds"] = round(duration, 1)
                    max_duration = max(max_duration, duration)
                # else: leave as None - user was likely AFK

            # Convert tool counts to sorted list
            turn["tools"] = sorted(
                [
                    {
                        "name": name,
                        "count": count,
                        "color": get_tool_color(name),
                    }
                    for name, count in tool_counts.items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )

            # Update totals and maxes
            total_input += turn["inputTokens"]
            total_input_no_cache += turn["inputTokensNoCache"]
            total_cache_read += turn["cacheReadTokens"]
            total_cache_create += turn["cacheCreateTokens"]
            total_output += turn["outputTokens"]
            total_tools += turn["totalTools"]
            max_tokens = max(max_tokens, turn["inputTokens"], turn["outputTokens"])
            max_tokens_no_cache = max(max_tokens_no_cache, turn["inputTokensNoCache"], turn["outputTokens"])
            max_tools = max(max_tools, turn["totalTools"])

            turns.append(turn)

        i += 1

    # Build tool legend (sorted by count, top 6)
    tool_legend = sorted(
        [
            {
                "name": name,
                "count": count,
                "color": get_tool_color(name),
            }
            for name, count in global_tool_counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:6]

    return {
        "turns": turns,
        "maxTokens": max_tokens,
        "maxTokensNoCache": max_tokens_no_cache,
        "maxTools": max_tools,
        "maxDuration": round(max_duration, 1) if max_duration else 0,
        "totals": {
            "inputTokens": total_input,
            "inputTokensNoCache": total_input_no_cache,
            "cacheReadTokens": total_cache_read,
            "cacheCreateTokens": total_cache_create,
            "outputTokens": total_output,
            "tools": total_tools,
            "commits": total_commits,
            "thinking": total_thinking,
        },
        "toolLegend": tool_legend,
    }
