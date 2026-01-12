#!/usr/bin/env python3
"""
Re-import session from Claude Code JSONL transcript.

Structure:
- user entry with message.content (string) → user_prompt
- user entry with message.content (array of tool_result) → match with tool_use
- assistant entry → assistant_stop + extract tool_use blocks
"""

import json
import sys
from pathlib import Path

import httpx

SERVER_URL = "http://localhost:3456"
client = httpx.Client(timeout=30.0)


def send_event(event: dict) -> bool:
    try:
        resp = client.post(f"{SERVER_URL}/api/events", json=event)
        return resp.status_code == 200
    except Exception as e:
        print(f"  Error sending event: {e}")
        return False


def process_transcript(transcript_path: str) -> None:
    session_id = Path(transcript_path).stem
    print(f"Session: {session_id}")

    entries = []
    with open(transcript_path) as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    total = len(entries)
    print(f"Total entries: {total}")

    # Find project path
    project_path = next((e.get("cwd") for e in entries if e.get("cwd")), None)

    # Find first timestamp
    first_ts = next((e.get("timestamp") for e in entries if e.get("timestamp")), None)

    # Counters
    event_count = 0
    user_prompts = 0
    assistant_stops = 0
    tool_uses = 0

    # Session start
    send_event({
        "event_type": "session_start",
        "session_id": session_id,
        "timestamp": first_ts,
        "project_path": project_path,
        "data": {},
    })
    event_count += 1

    # Track pending tool_use blocks: id -> {name, input}
    pending_tools = {}

    for i, entry in enumerate(entries):
        entry_type = entry.get("type")
        ts = entry.get("timestamp")

        if not ts or entry_type not in ("user", "assistant"):
            continue

        if entry_type == "user":
            message = entry.get("message", {})
            content = message.get("content")

            # Case 1: content is string → user prompt
            if isinstance(content, str) and content.strip():
                send_event({
                    "event_type": "user_prompt",
                    "session_id": session_id,
                    "timestamp": ts,
                    "project_path": project_path,
                    "data": {
                        "prompt": content,
                        "imagePasteIds": entry.get("imagePasteIds"),
                        "thinkingMetadata": entry.get("thinkingMetadata"),
                    },
                })
                event_count += 1
                user_prompts += 1

            # Case 2: content is array → tool results
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id")
                        result_content = block.get("content")
                        is_error = block.get("is_error", False)

                        if tool_use_id and tool_use_id in pending_tools:
                            tool_info = pending_tools.pop(tool_use_id)

                            # Format tool_result properly
                            tool_result = result_content
                            if is_error:
                                tool_result = {"content": result_content, "is_error": True}

                            send_event({
                                "event_type": "tool_use",
                                "session_id": session_id,
                                "timestamp": ts,
                                "project_path": project_path,
                                "data": {
                                    "tool_name": tool_info["name"],
                                    "tool_input": tool_info["input"],
                                    "tool_result": tool_result,
                                },
                            })
                            event_count += 1
                            tool_uses += 1

        elif entry_type == "assistant":
            message = entry.get("message", {})
            usage = message.get("usage", {})
            content = message.get("content", [])

            # Extract tool_use blocks
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_id = block.get("id")
                        if tool_id:
                            pending_tools[tool_id] = {
                                "name": block.get("name"),
                                "input": block.get("input"),
                            }

            # Extract text content from assistant message
            assistant_text = ""
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                assistant_text = "\n".join(text_parts)

            # Create assistant_stop with token usage and content
            if usage:
                send_event({
                    "event_type": "assistant_stop",
                    "session_id": session_id,
                    "timestamp": ts,
                    "project_path": project_path,
                    "data": {
                        "message": assistant_text if assistant_text else None,
                        "token_usage": {
                            "input_tokens": usage.get("input_tokens", 0),
                            "output_tokens": usage.get("output_tokens", 0),
                            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                        },
                    },
                })
                event_count += 1
                assistant_stops += 1

        # Progress
        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{total} entries processed...")

    print(f"\nDone!")
    print(f"  Events: {event_count}")
    print(f"  User prompts: {user_prompts}")
    print(f"  Assistant stops: {assistant_stops}")
    print(f"  Tool uses: {tool_uses}")
    print(f"  Pending (unmatched): {len(pending_tools)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python reimport_fast.py <transcript.jsonl>")
        sys.exit(1)

    path = sys.argv[1]
    if not Path(path).exists():
        print(f"File not found: {path}")
        sys.exit(1)

    try:
        httpx.get(f"{SERVER_URL}/health", timeout=2.0)
    except Exception:
        print(f"Server not running at {SERVER_URL}")
        sys.exit(1)

    process_transcript(path)
    client.close()


if __name__ == "__main__":
    main()
