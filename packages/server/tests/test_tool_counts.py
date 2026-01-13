"""
Test tool counting for specific prompts.

Analyzes a JSONL file to verify tool counts match what the dashboard shows.
"""

import json
from pathlib import Path
from collections import defaultdict

# The file to test
TEST_FILE = Path("/Users/sagar/.claude/projects/-Users-sagar-work-all-things-quickcall-quickcall-supertrace/f0fa7faf-f147-4745-bd3d-2e33a785167c.jsonl")


def analyze_prompts():
    """Analyze tool usage per prompt in the JSONL file."""

    print(f"\n{'='*60}")
    print(f"ANALYZING: {TEST_FILE.name}")
    print(f"{'='*60}\n")

    # Read all messages
    messages = []
    with open(TEST_FILE, "r") as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())
                data["_line"] = line_num
                messages.append(data)
            except json.JSONDecodeError:
                continue

    print(f"Total messages in file: {len(messages)}")

    # Group by conversation turn
    # A "prompt" is a user message followed by assistant response(s)
    prompts = []
    current_prompt = None
    prompt_num = 0

    for msg in messages:
        msg_type = msg.get("type")

        if msg_type == "user":
            # Check if this is a tool result (not a new prompt)
            content = msg.get("message", {}).get("content")
            is_tool_result = isinstance(content, list) and any(
                isinstance(c, dict) and c.get("type") == "tool_result"
                for c in content
            )

            if not is_tool_result:
                # This is a new user prompt
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
            else:
                # Tool result - still part of current prompt
                pass

        elif msg_type == "assistant" and current_prompt:
            current_prompt["assistant_msgs"].append(msg)

            # Extract tool uses from content
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

    # Don't forget the last prompt
    if current_prompt:
        prompts.append(current_prompt)

    print(f"Total user prompts: {len(prompts)}")

    # Print summary for all prompts
    print(f"\n{'='*60}")
    print("PROMPT SUMMARY")
    print(f"{'='*60}")
    print(f"{'#':<4} {'Tools':<8} {'Tool Breakdown':<50}")
    print("-" * 70)

    for p in prompts:
        tool_total = len(p["tool_uses"])
        breakdown = ", ".join(f"{k}:{v}" for k, v in sorted(p["tool_counts"].items()))
        print(f"{p['num']:<4} {tool_total:<8} {breakdown[:50]}")

    # Detailed analysis for prompts 9 and 20
    for target_num in [9, 20]:
        print(f"\n{'='*60}")
        print(f"DETAILED ANALYSIS: PROMPT {target_num}")
        print(f"{'='*60}")

        if target_num > len(prompts):
            print(f"  ERROR: Only {len(prompts)} prompts in file!")
            continue

        p = prompts[target_num - 1]  # 0-indexed

        # Get user prompt text
        user_content = p["user_msg"].get("message", {}).get("content", "")
        if isinstance(user_content, str):
            prompt_preview = user_content[:100].replace("\n", " ")
        else:
            prompt_preview = "[tool result]"

        print(f"\nUser prompt preview: {prompt_preview}...")
        print(f"\nTotal tools used: {len(p['tool_uses'])}")
        print(f"\nTool breakdown:")
        for tool, count in sorted(p["tool_counts"].items()):
            print(f"  {tool}: {count}")

        print(f"\nDetailed tool list:")
        for i, tool in enumerate(p["tool_uses"], 1):
            tool_input = tool["input"]
            # Get a preview of the input
            if "command" in tool_input:
                preview = tool_input["command"][:60]
            elif "file_path" in tool_input:
                preview = tool_input["file_path"]
            elif "pattern" in tool_input:
                preview = f"pattern: {tool_input['pattern'][:40]}"
            elif "content" in tool_input:
                preview = f"content: {len(tool_input['content'])} chars"
            else:
                preview = str(tool_input)[:60]

            print(f"  {i:2}. {tool['name']:<12} {preview}")

    return prompts


def check_metrics_calculation():
    """Check how metrics would count these tools."""
    print(f"\n{'='*60}")
    print("CHECKING METRICS CALCULATION")
    print(f"{'='*60}\n")

    from supertrace_server.ingest.parser import parse_jsonl_file

    # Parse file
    messages = list(parse_jsonl_file(TEST_FILE))

    print(f"Parser returned {len(messages)} messages")

    # Count by type
    by_type = defaultdict(int)
    for m in messages:
        by_type[m.msg_type] += 1

    print(f"\nBy type: {dict(by_type)}")

    # Check tool counts
    total_tools = sum(m.tool_use_count for m in messages)
    print(f"Total tool_use_count from parser: {total_tools}")

    # List all tool names
    all_tools = []
    for m in messages:
        if m.tool_names:
            all_tools.extend(m.tool_names)

    tool_counts = defaultdict(int)
    for t in all_tools:
        tool_counts[t] += 1

    print(f"\nTool distribution from parser:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        print(f"  {tool}: {count}")


if __name__ == "__main__":
    prompts = analyze_prompts()
    check_metrics_calculation()
