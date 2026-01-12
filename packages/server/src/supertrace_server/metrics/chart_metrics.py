"""
Chart data metrics.

Pre-computes data for frontend charts:
- prompt_turns: tokens and tools per prompt turn for unified chart
"""

from .registry import MetricCategory, MetricFormat, metric

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
    max_tokens = 0
    max_tools = 0

    # Global tool counts for legend
    global_tool_counts: dict[str, int] = {}

    i = 0
    while i < len(events):
        event = events[i]

        if event.get("event_type") == "user_prompt":
            prompt_index += 1
            turn = {
                "promptIndex": prompt_index,
                "promptEventId": event.get("id"),
                "responseEventId": event.get("id"),
                "inputTokens": 0,
                "outputTokens": 0,
                "tools": [],
                "totalTools": 0,
            }

            # Collect tools and find assistant_stop
            tool_counts: dict[str, int] = {}

            j = i + 1
            while j < len(events):
                e = events[j]

                if e.get("event_type") == "tool_use":
                    tool_name = e.get("data", {}).get("tool_name", "unknown")
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                    turn["totalTools"] += 1
                    # Update global counts
                    global_tool_counts[tool_name] = global_tool_counts.get(tool_name, 0) + 1

                if e.get("event_type") == "assistant_stop":
                    turn["responseEventId"] = e.get("id")
                    token_usage = e.get("data", {}).get("token_usage", {})
                    if token_usage:
                        turn["inputTokens"] = token_usage.get("input_tokens", 0)
                        turn["outputTokens"] = token_usage.get("output_tokens", 0)
                    break

                if e.get("event_type") == "user_prompt":
                    break

                j += 1

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
        "totals": {
            "inputTokens": total_input,
            "outputTokens": total_output,
            "tools": total_tools,
        },
        "toolLegend": tool_legend,
    }
