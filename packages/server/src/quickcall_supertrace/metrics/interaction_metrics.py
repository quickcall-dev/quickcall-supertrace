"""
Efficiency metrics.

Measures how efficiently work was done.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents


@metric(
    name="prompt_count",
    category=MetricCategory.INTERACTION,
    label="Prompts",
    icon="ri-chat-3-line",
    order=0,
)
def calc_prompt_count(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Number of user prompts sent."""
    if pre:
        return len(pre.user_prompts)
    return len([e for e in events if e.get("event_type") == "user_prompt"])


@metric(
    name="edits_per_prompt",
    category=MetricCategory.INTERACTION,
    label="Edits/Prompt",
    description="Average file edits per prompt (higher = more efficient)",
    icon="ri-speed-line",
    order=1,
)
def calc_edits_per_prompt(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Ratio of edits to prompts - higher means more efficient."""
    if pre:
        prompts = len(pre.user_prompts)
        edits = sum(pre.tool_counts.get(t, 0) for t in ["Edit", "Write", "MultiEdit"])
    else:
        prompts = len([e for e in events if e.get("event_type") == "user_prompt"])
        edits = len([
            e for e in events
            if e.get("event_type") == "tool_use"
            and (e.get("data") or {}).get("tool_name") in ["Edit", "Write", "MultiEdit"]
        ])

    if prompts == 0:
        return 0.0
    return round(edits / prompts, 1)


@metric(
    name="commit_count",
    category=MetricCategory.INTERACTION,
    label="Commits",
    description="Git commits made this session",
    icon="ri-git-commit-line",
    order=2,
)
def calc_commit_count(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Count of successful git commits."""
    if pre:
        return pre.commit_count
    # Fallback: scan for git commit in Bash tools
    count = 0
    for e in events:
        if e.get("event_type") == "tool_use":
            data = e.get("data") or {}
            if data.get("tool_name") == "Bash":
                command = (data.get("tool_input") or {}).get("command", "")
                result = data.get("tool_result", "")
                if "git commit" in command and isinstance(result, str):
                    if "[" in result and "]" in result:
                        count += 1
    return count


@metric(
    name="turns_per_commit",
    category=MetricCategory.INTERACTION,
    label="Turns/Commit",
    description="Prompts per commit (lower = faster delivery)",
    icon="ri-speed-line",
    order=3,
)
def calc_turns_per_commit(events: list[dict], pre: PreprocessedEvents = None) -> float:
    """Prompts per commit - lower means faster delivery."""
    if pre:
        prompts = len(pre.user_prompts)
        commits = pre.commit_count
    else:
        prompts = len([e for e in events if e.get("event_type") == "user_prompt"])
        commits = calc_commit_count(events)

    if commits == 0:
        return 0.0
    return round(prompts / commits, 1)


@metric(
    name="tool_success_rate",
    category=MetricCategory.INTERACTION,
    label="Tool Success",
    description="Percentage of tools that completed successfully",
    icon="ri-checkbox-circle-line",
    order=4,
)
def calc_tool_success_rate(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Percentage of tool calls that succeeded."""
    if pre:
        total = pre.tool_successes + pre.tool_failures
        successes = pre.tool_successes
    else:
        total = 0
        successes = 0
        for e in events:
            if e.get("event_type") == "tool_use":
                total += 1
                result = (e.get("data") or {}).get("tool_result")
                if isinstance(result, dict):
                    if not result.get("is_error") and not result.get("interrupted"):
                        successes += 1
                else:
                    successes += 1  # String result = success

    if total == 0:
        return 100
    return round((successes / total) * 100)


@metric(
    name="lines_per_hour",
    category=MetricCategory.INTERACTION,
    label="Lines/Hour",
    description="Net lines changed per hour",
    icon="ri-speed-line",
    order=5,
)
def calc_lines_per_hour(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """
    Productivity - lines of output per hour.

    WHY RAW COUNT BEFORE 1 HOUR:
    Extrapolating rates from short sessions is misleading. If someone writes
    50 lines in 10 minutes, showing "300 lines/hour" is not useful - they
    might be done for the day. We show raw counts until a full hour passes,
    then switch to per-hour rate for longer sessions.
    """
    # Import here to avoid circular dependency
    from .timing_metrics import calc_session_duration
    from .work_metrics import calc_net_lines

    duration_seconds = calc_session_duration(events, pre)
    net_lines = abs(calc_net_lines(events, pre))  # Use absolute value

    # Only extrapolate per-hour after a full hour has passed
    # Before that, show raw count - extrapolation from short sessions is misleading
    if duration_seconds is None or duration_seconds < 3600:
        return net_lines  # Less than an hour, just return raw lines

    hours = duration_seconds / 3600
    return round(net_lines / hours)


@metric(
    name="images_sent",
    category=MetricCategory.INTERACTION,
    label="Images",
    description="Total images shared in this session",
    icon="ri-image-line",
    order=6,
)
def calc_images_sent(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """
    Total images shared - indicates visual communication.

    HOW IMAGES ARE COUNTED:
    Claude Code stores imagePasteIds as an array like [1, 2, 3] where each number
    is a paste ID. We count len(imagePasteIds) to get the number of images per prompt.
    The actual values in the array are IDs, not counts - we count the array LENGTH.
    """
    if pre:
        return pre.images_sent

    images = 0
    for e in events:
        if e.get("event_type") == "user_prompt":
            data = e.get("data") or {}
            # imagePasteIds is an array of paste IDs like [1, 2, 3]
            # len() gives us the count of images, NOT the sum of IDs
            image_paste_ids = data.get("imagePasteIds") or []
            images += len(image_paste_ids)

    return images


@metric(
    name="thinking_usage",
    category=MetricCategory.INTERACTION,
    label="Thinking",
    description="Prompts with extended thinking enabled",
    icon="ri-brain-line",
    order=7,
)
def calc_thinking_usage(events: list[dict], pre: PreprocessedEvents = None) -> str:
    """Fraction of prompts with thinking mode on."""
    if pre:
        thinking_on = pre.thinking_enabled_prompts
        total = len(pre.user_prompts)
    else:
        thinking_on = 0
        total = 0
        for e in events:
            if e.get("event_type") == "user_prompt":
                total += 1
                data = e.get("data") or {}
                thinking_meta = data.get("thinkingMetadata") or {}
                thinking_disabled = thinking_meta.get("disabled", True)
                thinking_level = thinking_meta.get("level", "none")
                if not thinking_disabled or thinking_level != "none":
                    thinking_on += 1

    return f"{thinking_on}/{total}"
