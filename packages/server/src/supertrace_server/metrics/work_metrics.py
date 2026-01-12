"""
Work output metrics.

Measures actual work done: files changed, lines written, edits made.
Uses preprocessed data for efficiency.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .registry import metric, MetricCategory, MetricFormat

if TYPE_CHECKING:
    from .preprocess import PreprocessedEvents


def _get_tool_events_from_pre(pre: PreprocessedEvents, tool_names: list[str]) -> list[dict]:
    """Get tool_use events for specific tools from preprocessed data."""
    return [
        e for e in pre.tool_uses
        if (e.get("data") or {}).get("tool_name") in tool_names
    ]


def _get_tool_events(events: list[dict], tool_names: list[str]) -> list[dict]:
    """Get tool_use events for specific tools (fallback)."""
    return [
        e for e in events
        if e.get("event_type") == "tool_use"
        and (e.get("data") or {}).get("tool_name") in tool_names
    ]


@metric(
    name="files_changed",
    category=MetricCategory.TOOLS,
    label="Files",
    description="Unique files modified",
    icon="ri-file-edit-line",
    order=0,
    mini_bar=True,
    mini_bar_order=1,
)
def calc_files_changed(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Count unique files that were edited or written."""
    if pre:
        file_tools = _get_tool_events_from_pre(pre, ["Edit", "Write", "MultiEdit"])
    else:
        file_tools = _get_tool_events(events, ["Edit", "Write", "MultiEdit"])

    files = set()
    for e in file_tools:
        data = e.get("data") or {}
        tool_input = data.get("tool_input") or {}
        file_path = tool_input.get("file_path")
        if file_path:
            files.add(file_path)

    return len(files)


@metric(
    name="lines_added",
    category=MetricCategory.TOOLS,
    label="Lines +",
    description="Lines of code added",
    icon="ri-add-line",
    order=1,
)
def calc_lines_added(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Estimate lines added from Write and Edit tools."""
    if pre:
        write_events = _get_tool_events_from_pre(pre, ["Write"])
        edit_events = _get_tool_events_from_pre(pre, ["Edit"])
    else:
        write_events = _get_tool_events(events, ["Write"])
        edit_events = _get_tool_events(events, ["Edit"])

    lines = 0

    # Write tool - count lines in content
    for e in write_events:
        data = e.get("data") or {}
        tool_input = data.get("tool_input") or {}
        content = tool_input.get("content", "")
        if content:
            lines += content.count("\n") + 1

    # Edit tool - count lines in new_string minus old_string
    for e in edit_events:
        data = e.get("data") or {}
        tool_input = data.get("tool_input") or {}
        new_str = tool_input.get("new_string", "")
        old_str = tool_input.get("old_string", "")
        new_lines = new_str.count("\n") + 1 if new_str else 0
        old_lines = old_str.count("\n") + 1 if old_str else 0
        if new_lines > old_lines:
            lines += new_lines - old_lines

    return lines


@metric(
    name="lines_removed",
    category=MetricCategory.TOOLS,
    label="Lines -",
    description="Lines of code removed",
    icon="ri-subtract-line",
    order=2,
)
def calc_lines_removed(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Estimate lines removed from Edit tools."""
    if pre:
        edit_events = _get_tool_events_from_pre(pre, ["Edit"])
    else:
        edit_events = _get_tool_events(events, ["Edit"])

    lines = 0
    for e in edit_events:
        data = e.get("data") or {}
        tool_input = data.get("tool_input") or {}
        new_str = tool_input.get("new_string", "")
        old_str = tool_input.get("old_string", "")
        new_lines = new_str.count("\n") + 1 if new_str else 0
        old_lines = old_str.count("\n") + 1 if old_str else 0
        if old_lines > new_lines:
            lines += old_lines - new_lines

    return lines


@metric(
    name="net_lines",
    category=MetricCategory.TOOLS,
    label="Net Lines",
    description="Net lines changed (added - removed)",
    icon="ri-code-line",
    order=3,
    mini_bar=True,
    mini_bar_order=2,
)
def calc_net_lines(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Net lines changed (positive = added, negative = removed)."""
    return calc_lines_added(events, pre) - calc_lines_removed(events, pre)


@metric(
    name="edit_count",
    category=MetricCategory.TOOLS,
    label="Edits",
    description="Number of file edits made",
    icon="ri-edit-2-line",
    order=4,
)
def calc_edit_count(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Count of Edit and Write operations."""
    if pre:
        return sum(pre.tool_counts.get(t, 0) for t in ["Edit", "Write", "MultiEdit"])
    return len(_get_tool_events(events, ["Edit", "Write", "MultiEdit"]))


@metric(
    name="files_read",
    category=MetricCategory.TOOLS,
    label="Files Read",
    description="Files read for context",
    icon="ri-file-search-line",
    order=5,
)
def calc_files_read(events: list[dict], pre: PreprocessedEvents = None) -> int:
    """Count unique files read."""
    if pre:
        read_events = _get_tool_events_from_pre(pre, ["Read", "Glob", "Grep"])
    else:
        read_events = _get_tool_events(events, ["Read", "Glob", "Grep"])

    files = set()
    for e in read_events:
        data = e.get("data") or {}
        tool_input = data.get("tool_input") or {}
        file_path = tool_input.get("file_path") or tool_input.get("path")
        if file_path:
            files.add(file_path)

    return len(files)
