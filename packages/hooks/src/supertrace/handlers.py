"""
Event handlers for different Claude Code hook types.

Receives parsed HookInput, transforms it into TracingEvent,
and sends to the server. Each handler corresponds to a hook event type.

Related: models.py (data structures), client.py (sends events), cli.py (dispatches here)
"""

import json
from pathlib import Path

from .client import send_event
from .models import HookInput, TracingEvent


def read_transcript(path: str | None) -> list[dict] | None:
    """Read and parse the JSONL transcript file."""
    if not path:
        return None

    transcript_path = Path(path)
    if not transcript_path.exists():
        return None

    messages = []
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
    except (json.JSONDecodeError, IOError):
        return None

    return messages


def handle_session_start(hook_input: HookInput) -> None:
    """Handle SessionStart hook - new session began."""
    event = TracingEvent(
        event_type="session_start",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={},
    )
    send_event(event)


def handle_session_end(hook_input: HookInput) -> None:
    """Handle SessionEnd hook - session ended."""
    event = TracingEvent(
        event_type="session_end",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={},
    )
    send_event(event)


def handle_prompt(hook_input: HookInput) -> None:
    """Handle UserPromptSubmit hook - user sent a message."""
    # prompt is passed directly in the hook input (field name is 'prompt')
    event = TracingEvent(
        event_type="user_prompt",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "prompt": hook_input.prompt,
        },
    )
    send_event(event)


def handle_stop(hook_input: HookInput) -> None:
    """Handle Stop hook - Claude finished responding."""
    # Read the full transcript to get the latest messages
    transcript = read_transcript(hook_input.transcript_path)

    event = TracingEvent(
        event_type="assistant_stop",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "transcript": transcript,
        },
    )
    send_event(event)


def handle_tool_use(hook_input: HookInput) -> None:
    """Handle PostToolUse hook - tool finished executing."""
    event = TracingEvent(
        event_type="tool_use",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "tool_name": hook_input.tool_name,
            "tool_input": hook_input.tool_input,
        },
    )
    send_event(event)
