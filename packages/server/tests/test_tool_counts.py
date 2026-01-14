"""
Test tool counting for prompts.

Analyzes JSONL files to verify tool counts match what the dashboard shows.
Can be run against any JSONL file or the default test session.

Usage:
    # Run with default file
    python -m pytest tests/test_tool_counts.py -v -s

    # Run analysis on specific file
    python tests/test_tool_counts.py /path/to/session.jsonl

    # Run analysis on specific prompts
    python tests/test_tool_counts.py --prompts 9,20
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from conftest import (
    SAMPLE_USER_MESSAGE,
    SAMPLE_ASSISTANT_MESSAGE,
    SAMPLE_TOOL_RESULT,
    make_assistant_message,
)


# =============================================================================
# Unit Tests
# =============================================================================

class TestToolParsing:
    """Test tool extraction from messages."""

    def test_tool_count_extraction(self):
        """Test that tool_use blocks are correctly counted."""
        from quickcall_supertrace.ingest.parser import parse_message

        msg = parse_message(SAMPLE_ASSISTANT_MESSAGE, line_num=1)

        assert msg.tool_use_count == 1
        assert msg.tool_names == ["Read"]

    def test_multiple_tools(self):
        """Test counting multiple tools in one message."""
        from quickcall_supertrace.ingest.parser import parse_message

        multi_tool_msg = make_assistant_message(
            uuid="asst-multi",
            tools=["Read", "Bash", "Write", "Glob"],
        )

        msg = parse_message(multi_tool_msg, line_num=1)

        assert msg.tool_use_count == 4
        assert set(msg.tool_names) == {"Read", "Bash", "Write", "Glob"}

    def test_no_tools(self):
        """Test message with no tools."""
        from quickcall_supertrace.ingest.parser import parse_message

        no_tool_msg = make_assistant_message(uuid="asst-no-tool", tools=None)

        msg = parse_message(no_tool_msg, line_num=1)

        assert msg.tool_use_count == 0
        assert msg.tool_names == []


class TestToolAggregation:
    """Test tool aggregation across messages."""

    def test_tool_distribution(self, temp_jsonl_with_data):
        """Test that tool distribution is correctly aggregated."""
        from quickcall_supertrace.ingest.parser import parse_jsonl_file

        messages = [
            SAMPLE_USER_MESSAGE,
            make_assistant_message(uuid="a1", tools=["Read", "Read", "Bash"]),
            SAMPLE_TOOL_RESULT,
            make_assistant_message(uuid="a2", tools=["Write", "Read"]),
        ]

        temp_file = temp_jsonl_with_data(messages)
        parsed = list(parse_jsonl_file(temp_file))

        # Count tools
        tool_counts = defaultdict(int)
        for m in parsed:
            for t in m.tool_names:
                tool_counts[t] += 1

        assert tool_counts["Read"] == 3
        assert tool_counts["Bash"] == 1
        assert tool_counts["Write"] == 1


# =============================================================================
# Analysis Functions
# =============================================================================

def analyze_prompts(file_path: Path, target_prompts: list[int] = None):
    """
    Analyze tool usage per prompt in a JSONL file.

    Args:
        file_path: Path to JSONL file
        target_prompts: Specific prompt numbers to analyze in detail

    Returns:
        List of prompt dicts with tool info
    """
    print(f"\n{'='*60}")
    print(f"ANALYZING: {file_path.name}")
    print(f"{'='*60}\n")

    # Read all messages
    messages = []
    with open(file_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                data["_line"] = line_num
                messages.append(data)
            except json.JSONDecodeError:
                continue

    print(f"Total messages in file: {len(messages)}")

    # Group by conversation turn
    prompts = []
    current_prompt = None
    prompt_num = 0

    for msg in messages:
        msg_type = msg.get("type")

        if msg_type == "user":
            content = msg.get("message", {}).get("content")
            is_tool_result = isinstance(content, list) and any(
                isinstance(c, dict) and c.get("type") == "tool_result"
                for c in content
            )

            if not is_tool_result:
                if current_prompt:
                    prompts.append(current_prompt)
                prompt_num += 1
                current_prompt = {
                    "num": prompt_num,
                    "user_msg": msg,
                    "assistant_msgs": [],
                    "tool_uses": [],
                    "tool_counts": defaultdict(int),
                }

        elif msg_type == "assistant" and current_prompt:
            current_prompt["assistant_msgs"].append(msg)

            content = msg.get("message", {}).get("content", [])
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_name = item.get("name", "unknown")
                    current_prompt["tool_uses"].append({
                        "name": tool_name,
                        "id": item.get("id"),
                        "input": item.get("input", {}),
                    })
                    current_prompt["tool_counts"][tool_name] += 1

    if current_prompt:
        prompts.append(current_prompt)

    print(f"Total user prompts: {len(prompts)}")

    # Print summary
    print(f"\n{'='*60}")
    print("PROMPT SUMMARY")
    print(f"{'='*60}")
    print(f"{'#':<4} {'Tools':<8} {'Tool Breakdown':<50}")
    print("-" * 70)

    for p in prompts:
        tool_total = len(p["tool_uses"])
        breakdown = ", ".join(f"{k}:{v}" for k, v in sorted(p["tool_counts"].items()))
        print(f"{p['num']:<4} {tool_total:<8} {breakdown[:50]}")

    # Detailed analysis for target prompts
    if target_prompts:
        for target_num in target_prompts:
            print(f"\n{'='*60}")
            print(f"DETAILED ANALYSIS: PROMPT {target_num}")
            print(f"{'='*60}")

            if target_num > len(prompts):
                print(f"  ERROR: Only {len(prompts)} prompts in file!")
                continue

            p = prompts[target_num - 1]

            user_content = p["user_msg"].get("message", {}).get("content", "")
            if isinstance(user_content, str):
                prompt_preview = user_content[:100].replace("\n", " ")
            else:
                prompt_preview = "[list content]"

            print(f"\nUser prompt: {prompt_preview}...")
            print(f"Total tools used: {len(p['tool_uses'])}")
            print(f"\nTool breakdown:")
            for tool, count in sorted(p["tool_counts"].items()):
                print(f"  {tool}: {count}")

            print(f"\nTool list:")
            for i, tool in enumerate(p["tool_uses"][:20], 1):
                tool_input = tool["input"]
                if "command" in tool_input:
                    preview = tool_input["command"][:50]
                elif "file_path" in tool_input:
                    preview = tool_input["file_path"]
                elif "pattern" in tool_input:
                    preview = f"pattern: {tool_input['pattern'][:30]}"
                else:
                    preview = str(tool_input)[:50]
                print(f"  {i:2}. {tool['name']:<12} {preview}")

    return prompts


def check_metrics_calculation(file_path: Path):
    """Check how metrics would count tools from this file."""
    print(f"\n{'='*60}")
    print("CHECKING METRICS CALCULATION")
    print(f"{'='*60}\n")

    from quickcall_supertrace.ingest.parser import parse_jsonl_file

    messages = list(parse_jsonl_file(file_path))

    print(f"Parser returned {len(messages)} messages")

    by_type = defaultdict(int)
    for m in messages:
        by_type[m.msg_type] += 1

    print(f"\nBy type: {dict(by_type)}")

    total_tools = sum(m.tool_use_count for m in messages)
    print(f"Total tool_use_count from parser: {total_tools}")

    all_tools = []
    for m in messages:
        if m.tool_names:
            all_tools.extend(m.tool_names)

    tool_counts = defaultdict(int)
    for t in all_tools:
        tool_counts[t] += 1

    print(f"\nTool distribution:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        print(f"  {tool}: {count}")


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze tool usage in JSONL files")
    parser.add_argument("file", nargs="?", help="Path to JSONL file")
    parser.add_argument("--prompts", "-p", help="Comma-separated prompt numbers to analyze")

    args = parser.parse_args()

    # Find file
    if args.file:
        file_path = Path(args.file)
    else:
        # Try to find most recent session
        base = Path.home() / ".claude" / "projects"
        jsonl_files = sorted(base.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        if jsonl_files:
            file_path = jsonl_files[0]
            print(f"Using most recent file: {file_path}")
        else:
            print("No JSONL files found. Specify a path.")
            sys.exit(1)

    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    target_prompts = None
    if args.prompts:
        target_prompts = [int(x.strip()) for x in args.prompts.split(",")]

    analyze_prompts(file_path, target_prompts)
    check_metrics_calculation(file_path)


if __name__ == "__main__":
    main()
