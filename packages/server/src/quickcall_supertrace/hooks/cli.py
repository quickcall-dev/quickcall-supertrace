"""
CLI entry point for QuickCall SuperTrace hooks.

Reads JSON from stdin (passed by Claude Code hooks), parses it,
and dispatches to the appropriate handler based on the command.

Usage:
    quickcall-supertrace-hook <command>

Commands:
    stop          - Handle Stop event (Claude finished responding)
    tool          - Handle PostToolUse event (tool finished)
    session-start - Handle SessionStart event
    session-end   - Handle SessionEnd event
    prompt        - Handle UserPromptSubmit event
    notification  - Handle Notification event
    precompact    - Handle PreCompact event

Example Claude Code hooks.json configuration:
{
    "hooks": {
        "Stop": [{
            "matcher": "*",
            "hooks": [{
                "type": "command",
                "command": "quickcall-supertrace-hook stop",
                "timeout": 5
            }]
        }],
        "PostToolUse": [{
            "matcher": "*",
            "hooks": [{
                "type": "command",
                "command": "quickcall-supertrace-hook tool",
                "timeout": 5
            }]
        }]
    }
}
"""

import json
import sys

from .handlers import (
    handle_notification,
    handle_precompact,
    handle_prompt,
    handle_session_end,
    handle_session_start,
    handle_stop,
    handle_tool,
    debug,
)
from .models import HookInput

# Command to handler mapping
COMMANDS = {
    "stop": handle_stop,
    "tool": handle_tool,
    "session-start": handle_session_start,
    "session-end": handle_session_end,
    "prompt": handle_prompt,
    "notification": handle_notification,
    "precompact": handle_precompact,
}


def read_stdin() -> dict | None:
    """Read and parse JSON from stdin."""
    try:
        data = sys.stdin.read()
        if not data.strip():
            return None
        return json.loads(data)
    except json.JSONDecodeError as e:
        debug(f"Invalid JSON input: {e}")
        return None


def main() -> None:
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: quickcall-supertrace-hook <command>", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    if command not in COMMANDS:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Commands: {', '.join(COMMANDS.keys())}", file=sys.stderr)
        sys.exit(1)

    # Read hook input from stdin
    stdin_data = read_stdin()
    if stdin_data is None:
        # No input is okay - some hooks might not pass data
        debug("No stdin data received")
        sys.exit(0)

    try:
        hook_input = HookInput(**stdin_data)
    except Exception as e:
        debug(f"Failed to parse hook input: {e}")
        # Don't fail hard - hooks should not block Claude Code
        sys.exit(0)

    # Dispatch to handler
    try:
        handler = COMMANDS[command]
        handler(hook_input)
    except Exception as e:
        debug(f"Handler error: {e}")
        # Don't fail hard - hooks should not block Claude Code
        sys.exit(0)


if __name__ == "__main__":
    main()
