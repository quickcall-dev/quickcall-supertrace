"""
CLI entry point for supertrace hooks.

Reads JSON from stdin (passed by Claude Code hooks), parses it,
and dispatches to the appropriate handler based on the command.

Related: handlers.py (event handlers), models.py (HookInput parsing)
"""

import json
import sys

from .handlers import (
    handle_prompt,
    handle_session_end,
    handle_session_start,
    handle_stop,
    handle_tool_use,
)
from .models import HookInput

COMMANDS = {
    "session-start": handle_session_start,
    "session-end": handle_session_end,
    "prompt": handle_prompt,
    "stop": handle_stop,
    "tool": handle_tool_use,
}


def read_stdin() -> dict | None:
    """Read and parse JSON from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError:
        return None


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: supertrace <command>", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    # Read hook input from stdin
    stdin_data = read_stdin()
    if stdin_data is None:
        # No input is okay - some hooks might not pass data
        sys.exit(0)

    try:
        hook_input = HookInput(**stdin_data)
    except Exception as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        sys.exit(1)

    # Dispatch to handler
    handler = COMMANDS[command]
    handler(hook_input)


if __name__ == "__main__":
    main()
