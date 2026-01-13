"""
Test a specific JSONL file for token accuracy.
"""

import json
from pathlib import Path

import pandas as pd

# The file to test
TEST_FILE = Path("/Users/sagar/work/all-things-quickcall/quickcall-supertrace/temp/fce48a76-01e1-44e7-9620-c7a46ef6cdfd.jsonl")


def test_specific_jsonl_file():
    """Parse the specific JSONL file and verify token extraction."""
    from supertrace_server.ingest.parser import parse_jsonl_file
    from supertrace_server.metrics.preprocess import preprocess_events

    assert TEST_FILE.exists(), f"File not found: {TEST_FILE}"

    print(f"\n=== Parsing: {TEST_FILE.name} ===")
    print(f"File size: {TEST_FILE.stat().st_size:,} bytes")

    # Step 1: Parse all messages
    messages = list(parse_jsonl_file(TEST_FILE))
    print(f"Total messages parsed: {len(messages)}")

    # Create DataFrame for analysis
    data = []
    for m in messages:
        data.append({
            "uuid": m.uuid[:12] + "..." if len(m.uuid) > 12 else m.uuid,
            "type": m.msg_type,
            "input_tokens": m.input_tokens,
            "output_tokens": m.output_tokens,
            "cache_read": m.cache_read_tokens,
            "cache_create": m.cache_create_tokens,
            "tool_count": m.tool_use_count,
            "tools": ",".join(m.tool_names) if m.tool_names else "",
            "model": (m.model or "")[:20],
        })

    df = pd.DataFrame(data)

    # Show message type breakdown
    print("\n=== Message Type Breakdown ===")
    print(df["type"].value_counts().to_string())

    # Show assistant messages with tokens
    print("\n=== Assistant Messages (with tokens) ===")
    asst_df = df[df["type"] == "assistant"].copy()
    if len(asst_df) > 0:
        # Only show rows with tokens
        asst_with_tokens = asst_df[asst_df["output_tokens"] > 0]
        print(f"Assistant messages with output tokens: {len(asst_with_tokens)}")
        print(asst_with_tokens.to_string())
    else:
        print("No assistant messages found!")

    # Calculate totals from parsed data
    print("\n=== Token Totals from Parser ===")
    total_input = df["input_tokens"].sum()
    total_output = df["output_tokens"].sum()
    total_cache_read = df["cache_read"].sum()
    total_cache_create = df["cache_create"].sum()

    print(f"  Input tokens:        {total_input:,}")
    print(f"  Output tokens:       {total_output:,}")
    print(f"  Cache read tokens:   {total_cache_read:,}")
    print(f"  Cache create tokens: {total_cache_create:,}")

    # Step 2: Convert to events and run through metrics preprocessing
    print("\n=== Converting to Events Format ===")
    events = []
    for m in messages:
        if m.msg_type == "user":
            raw = json.loads(m.raw_data) if m.raw_data else {}
            events.append({
                "event_type": "user_prompt",
                "timestamp": m.timestamp,
                "data": {
                    "prompt": m.prompt_text,
                    "imagePasteIds": raw.get("imagePasteIds", []),
                    "thinkingMetadata": raw.get("thinkingMetadata", {}),
                },
            })
        elif m.msg_type == "assistant":
            events.append({
                "event_type": "assistant_stop",
                "timestamp": m.timestamp,
                "data": {
                    "model": m.model,
                    "token_usage": {
                        "input_tokens": m.input_tokens,
                        "output_tokens": m.output_tokens,
                        "cache_read_input_tokens": m.cache_read_tokens,
                        "cache_creation_input_tokens": m.cache_create_tokens,
                    },
                },
            })
            # Add tool_use events
            raw = json.loads(m.raw_data) if m.raw_data else {}
            content = raw.get("message", {}).get("content", [])
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    events.append({
                        "event_type": "tool_use",
                        "timestamp": m.timestamp,
                        "data": {
                            "tool_name": item.get("name", "unknown"),
                            "tool_input": item.get("input", {}),
                        },
                    })

    print(f"Events generated: {len(events)}")
    print(f"  - user_prompt:    {sum(1 for e in events if e['event_type'] == 'user_prompt')}")
    print(f"  - assistant_stop: {sum(1 for e in events if e['event_type'] == 'assistant_stop')}")
    print(f"  - tool_use:       {sum(1 for e in events if e['event_type'] == 'tool_use')}")

    # Step 3: Run through metrics preprocessing
    print("\n=== Metrics Preprocessing ===")
    pre = preprocess_events(events)

    print(f"  Total input tokens (context):  {pre.total_input_tokens:,}")
    print(f"  Total output tokens:           {pre.total_output_tokens:,}")
    print(f"  Total cache read tokens:       {pre.total_cache_read_tokens:,}")
    print(f"  Total cache creation tokens:   {pre.total_cache_creation_tokens:,}")
    print(f"  Images sent:                   {pre.images_sent}")
    print(f"  Thinking enabled prompts:      {pre.thinking_enabled_prompts}")
    print(f"  Tool uses:                     {len(pre.tool_uses)}")
    print(f"  Commits:                       {pre.commit_count}")

    # Verify consistency
    print("\n=== Verification ===")
    # Metrics sees total_context = input + cache_read + cache_create
    expected_context = total_input + total_cache_read + total_cache_create
    print(f"  Expected context (input + cache): {expected_context:,}")
    print(f"  Metrics total_input_tokens:       {pre.total_input_tokens:,}")

    assert pre.total_input_tokens == expected_context, \
        f"Mismatch! Expected {expected_context}, got {pre.total_input_tokens}"
    assert pre.total_output_tokens == total_output, \
        f"Output mismatch! Expected {total_output}, got {pre.total_output_tokens}"

    print("\n✅ All token counts verified correctly!")


def analyze_raw_jsonl():
    """Directly read the JSONL to see raw token data."""
    print(f"\n=== Raw JSONL Analysis: {TEST_FILE.name} ===\n")

    assistant_messages = []
    line_num = 0

    with open(TEST_FILE, "r") as f:
        for line in f:
            line_num += 1
            try:
                data = json.loads(line.strip())
                if data.get("type") == "assistant":
                    msg = data.get("message", {})
                    usage = msg.get("usage", {})
                    assistant_messages.append({
                        "line": line_num,
                        "model": (msg.get("model") or "")[:25],
                        "input": usage.get("input_tokens", 0),
                        "output": usage.get("output_tokens", 0),
                        "cache_read": usage.get("cache_read_input_tokens", 0),
                        "cache_create": usage.get("cache_creation_input_tokens", 0),
                    })
            except json.JSONDecodeError:
                continue

    print(f"Total lines: {line_num}")
    print(f"Assistant messages: {len(assistant_messages)}")

    if assistant_messages:
        df = pd.DataFrame(assistant_messages)
        print("\n=== Raw Token Data from JSONL ===")
        print(df.to_string())

        print("\n=== Totals ===")
        print(f"  input_tokens:                  {df['input'].sum():,}")
        print(f"  output_tokens:                 {df['output'].sum():,}")
        print(f"  cache_read_input_tokens:       {df['cache_read'].sum():,}")
        print(f"  cache_creation_input_tokens:   {df['cache_create'].sum():,}")


if __name__ == "__main__":
    analyze_raw_jsonl()
    print("\n" + "=" * 60 + "\n")
    test_specific_jsonl_file()
