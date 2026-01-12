#!/usr/bin/env python3
"""
Re-import a session from JSONL transcript with updated event format.

Usage:
    python reimport.py <transcript_path> [--clear-db]

This script:
1. Reads the Claude Code JSONL transcript
2. Converts entries to SuperTrace events using the latest format
3. Posts them to the SuperTrace server
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

SERVER_URL = "http://localhost:3456"


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp."""
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def extract_session_id(transcript_path: str) -> str:
    """Extract session ID from transcript path."""
    return Path(transcript_path).stem


def send_event(event: dict) -> bool:
    """Send event to server."""
    try:
        resp = httpx.post(f"{SERVER_URL}/api/events", json=event, timeout=5.0)
        return resp.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False


def process_transcript(transcript_path: str) -> None:
    """Process JSONL transcript and send events."""
    session_id = extract_session_id(transcript_path)
    print(f"Session ID: {session_id}")
    print(f"Transcript: {transcript_path}")

    # Read all entries
    entries = []
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    print(f"Found {len(entries)} entries")

    # Track state
    sent_session_start = False
    project_path = None
    event_count = 0

    for i, entry in enumerate(entries):
        entry_type = entry.get("type")
        timestamp = entry.get("timestamp", datetime.utcnow().isoformat())

        # Extract project path from first entry
        if not project_path:
            project_path = entry.get("cwd")

        # Send session_start on first entry
        if not sent_session_start:
            event = {
                "event_type": "session_start",
                "session_id": session_id,
                "timestamp": timestamp,
                "project_path": project_path,
                "transcript_path": transcript_path,
                "data": {},
            }
            if send_event(event):
                event_count += 1
                print(f"  [{event_count}] session_start")
            sent_session_start = True

        # Process based on entry type
        if entry_type == "user":
            # User prompt
            message = entry.get("message", {})
            content = message.get("content", "")

            # Handle content as string or array
            prompt = ""
            if isinstance(content, str):
                prompt = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        prompt = block.get("text", "")
                        break

            event = {
                "event_type": "user_prompt",
                "session_id": session_id,
                "timestamp": timestamp,
                "project_path": project_path,
                "data": {
                    "prompt": prompt,
                    "imagePasteIds": entry.get("imagePasteIds"),
                    "thinkingMetadata": entry.get("thinkingMetadata"),
                },
            }
            if send_event(event):
                event_count += 1
                thinking = entry.get("thinkingMetadata", {})
                images = entry.get("imagePasteIds", [])
                extras = []
                if images:
                    extras.append(f"{len(images)} imgs")
                if thinking and not thinking.get("disabled", True):
                    extras.append("thinking")
                extra_str = f" ({', '.join(extras)})" if extras else ""
                print(f"  [{event_count}] user_prompt{extra_str}")

        elif entry_type == "assistant":
            # Assistant response - extract token usage
            message = entry.get("message", {})
            usage = message.get("usage", {})

            # Build transcript up to this point for context
            transcript_so_far = entries[:i+1]

            event = {
                "event_type": "assistant_stop",
                "session_id": session_id,
                "timestamp": timestamp,
                "project_path": project_path,
                "data": {
                    "transcript": transcript_so_far,
                    "token_usage": {
                        "input_tokens": usage.get("input_tokens", 0),
                        "output_tokens": usage.get("output_tokens", 0),
                        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                        "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                        "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                    } if usage else None,
                },
            }
            if send_event(event):
                event_count += 1
                tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                print(f"  [{event_count}] assistant_stop ({tokens} tokens)")

        elif entry_type == "tool_use":
            # Tool use
            event = {
                "event_type": "tool_use",
                "session_id": session_id,
                "timestamp": timestamp,
                "project_path": project_path,
                "data": {
                    "tool_name": entry.get("tool_name") or entry.get("name"),
                    "tool_input": entry.get("tool_input") or entry.get("input"),
                    "tool_result": entry.get("tool_result") or entry.get("result"),
                },
            }
            if send_event(event):
                event_count += 1
                tool_name = entry.get("tool_name") or entry.get("name", "unknown")
                print(f"  [{event_count}] tool_use: {tool_name}")

    print(f"\nDone! Sent {event_count} events")


def clear_session(session_id: str) -> bool:
    """Clear a session from the database."""
    try:
        resp = httpx.delete(f"{SERVER_URL}/api/sessions/{session_id}", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python reimport.py <transcript_path> [--clear-db]")
        print("\nExample:")
        print("  python reimport.py ~/.claude/projects/.../session.jsonl")
        sys.exit(1)

    transcript_path = sys.argv[1]

    if not Path(transcript_path).exists():
        print(f"Error: File not found: {transcript_path}")
        sys.exit(1)

    # Check if server is running
    try:
        httpx.get(f"{SERVER_URL}/health", timeout=2.0)
    except Exception:
        print(f"Error: Server not running at {SERVER_URL}")
        print("Start the server first: cd packages/server && uv run uvicorn ...")
        sys.exit(1)

    process_transcript(transcript_path)


if __name__ == "__main__":
    main()
