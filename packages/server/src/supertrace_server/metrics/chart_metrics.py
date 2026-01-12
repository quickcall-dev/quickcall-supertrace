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

# Tool colors matching frontend
TOOL_COLORS = {
    "Read": "#60a5fa",
    "Glob": "#60a5fa",
    "Grep": "#60a5fa",
    "Write": "#34d399",
    "Edit": "#fbbf24",
    "Bash": "#f97316",
    "Task": "#a78bfa",
    "TodoWrite": "#34d399",
    "WebFetch": "#38bdf8",
    "WebSearch": "#38bdf8",
    "AskUserQuestion": "#f472b6",
}

DEFAULT_TOOL_COLOR = "#94a3b8"


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
    total_output = 0
    total_tools = 0
    total_commits = 0
    max_tokens = 0
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
            prompt_index += 1
            start_time = parse_timestamp(event.get("timestamp"))
            turn = {
                "promptIndex": prompt_index,
                "promptEventId": event.get("id"),
                "responseEventId": event.get("id"),
                "inputTokens": 0,
                "outputTokens": 0,
                "tools": [],
                "totalTools": 0,
                "hasCommit": False,
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
                        # Total context = input + cache_read + cache_create
                        input_tok = token_usage.get("input_tokens", 0)
                        cache_read = token_usage.get("cache_read_input_tokens", 0)
                        cache_create = token_usage.get("cache_creation_input_tokens", 0)
                        turn["inputTokens"] = input_tok + cache_read + cache_create
                        # Sum output tokens from all assistant_stops in this turn
                        total_output_tokens += token_usage.get("output_tokens", 0)

                j += 1

            turn["outputTokens"] = total_output_tokens

            # Calculate duration
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
                turn["durationSeconds"] = round(duration, 1)
                max_duration = max(max_duration, duration)

            # Convert tool counts to sorted list
            turn["tools"] = sorted(
                [
                    {
                        "name": name,
                        "count": count,
                        "color": TOOL_COLORS.get(name, DEFAULT_TOOL_COLOR),
                    }
                    for name, count in tool_counts.items()
                ],
                key=lambda x: x["count"],
                reverse=True,
            )

            # Update totals and maxes
            total_input += turn["inputTokens"]
            total_output += turn["outputTokens"]
            total_tools += turn["totalTools"]
            max_tokens = max(max_tokens, turn["inputTokens"], turn["outputTokens"])
            max_tools = max(max_tools, turn["totalTools"])

            turns.append(turn)

        i += 1

    # Build tool legend (sorted by count, top 6)
    tool_legend = sorted(
        [
            {
                "name": name,
                "count": count,
                "color": TOOL_COLORS.get(name, DEFAULT_TOOL_COLOR),
            }
            for name, count in global_tool_counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:6]

    return {
        "turns": turns,
        "maxTokens": max_tokens,
        "maxTools": max_tools,
        "maxDuration": round(max_duration, 1) if max_duration else 0,
        "totals": {
            "inputTokens": total_input,
            "outputTokens": total_output,
            "tools": total_tools,
            "commits": total_commits,
        },
        "toolLegend": tool_legend,
    }
