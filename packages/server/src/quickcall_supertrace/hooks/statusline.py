#!/usr/bin/env python3
"""
Statusline command for Claude Code.

This receives the REAL context and cost data from Claude Code
and sends it to SuperTrace. Much more accurate than recalculating
from transcripts.

Usage in ~/.claude/settings.json:
{
  "statusline": {
    "command": "/path/to/quickcall-supertrace-statusline"
  }
}
"""

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# Server configuration
DEFAULT_SERVER_URL = "http://localhost:7845"
TIMEOUT_SECONDS = 2


def get_server_url() -> str:
    """Get server URL from env or use default."""
    import os
    return os.environ.get("QUICKCALL_SUPERTRACE_URL", DEFAULT_SERVER_URL)


def send_context_update(session_id: str, data: dict) -> bool:
    """Send context update to SuperTrace server."""
    url = f"{get_server_url()}/api/sessions/{session_id}/context"

    try:
        payload = json.dumps(data).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status == 200
    except (URLError, Exception):
        return False


def format_statusline(data: dict) -> str:
    """Format the statusline output for Claude Code CLI display."""
    model = data.get("model", {}).get("display_name", "")
    ctx = data.get("context_window", {})
    cost = data.get("cost", {})
    workspace = data.get("workspace", {})

    used_pct = ctx.get("used_percentage", 0)
    total_cost = cost.get("total_cost_usd", 0)
    cwd = workspace.get("current_dir", "")

    # Directory basename
    dir_base = Path(cwd).name if cwd else ""

    # Progress bar (8 segments)
    used_int = int(used_pct)
    filled = min(8, (used_int + 12) // 13)
    bar = "█" * filled + "░" * (8 - filled)

    # Color codes
    if used_int < 50:
        bar_color = "\033[32m"  # Green
    elif used_int < 75:
        bar_color = "\033[33m"  # Yellow
    else:
        bar_color = "\033[31m"  # Red

    reset = "\033[0m"
    dim = "\033[90m"
    blue = "\033[34m"
    magenta = "\033[35m"
    yellow = "\033[33m"

    # Build status line
    parts = []
    if dir_base:
        parts.append(f"{blue}{dir_base}{reset}")
    if model:
        parts.append(f"{magenta}{model}{reset}")
    parts.append(f"{bar_color}[{bar}]{reset} {dim}{used_int}%{reset}")
    if total_cost > 0:
        parts.append(f"{yellow}${total_cost:.2f}{reset}")

    return f" {dim}•{reset} ".join(parts)


def main():
    """Main entry point for statusline command."""
    # Read JSON from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    # Extract session ID from transcript path
    transcript_path = input_data.get("transcript_path", "")
    if transcript_path:
        # Session ID is the filename without extension
        session_id = Path(transcript_path).stem
    else:
        session_id = input_data.get("session_id", "")

    # Extract the real data from Claude Code
    ctx = input_data.get("context_window", {})
    cost = input_data.get("cost", {})
    model_info = input_data.get("model", {})

    # Send to SuperTrace if we have a session ID
    if session_id:
        context_data = {
            "used_percentage": ctx.get("used_percentage", 0),
            "remaining_percentage": ctx.get("remaining_percentage", 100),
            "context_window_size": ctx.get("context_window_size", 200000),
            "total_input_tokens": ctx.get("total_input_tokens", 0),
            "total_output_tokens": ctx.get("total_output_tokens", 0),
            "cache_read_tokens": ctx.get("current_usage", {}).get("cache_read_input_tokens", 0),
            "cache_create_tokens": ctx.get("current_usage", {}).get("cache_creation_input_tokens", 0),
            "model": model_info.get("id") or model_info.get("display_name"),
        }
        send_context_update(session_id, context_data)

    # Output the formatted statusline for CLI display
    print(format_statusline(input_data))


if __name__ == "__main__":
    main()
