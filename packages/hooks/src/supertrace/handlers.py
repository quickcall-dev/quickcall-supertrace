"""
Event handlers for different Claude Code hook types.

Receives parsed HookInput, transforms it into TracingEvent,
and sends to the server. Each handler corresponds to a hook event type.

Related: models.py (data structures), client.py (sends events), cli.py (dispatches here)
"""

import json
from pathlib import Path
from typing import Any

from .client import send_event
from .models import HookInput, TracingEvent


def extract_images_from_transcript(
    transcript: list[dict] | None,
) -> list[dict[str, Any]]:
    """
    Extract images from the transcript.

    Claude Code stores images in the transcript as content blocks with type "image".
    The format is:
    {
        "type": "human",
        "message": {
            "content": [
                {"type": "text", "text": "..."},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
            ]
        }
    }
    """
    images = []
    if not transcript:
        return images

    for entry in transcript:
        if entry.get("type") != "human":
            continue

        message = entry.get("message", {})
        content = message.get("content")

        # Content can be a string or an array of blocks
        if not isinstance(content, list):
            continue

        for idx, block in enumerate(content):
            if not isinstance(block, dict):
                continue

            if block.get("type") == "image":
                source = block.get("source", {})
                if source.get("type") == "base64":
                    images.append(
                        {
                            "index": len(images),
                            "media_type": source.get("media_type", "image/png"),
                            "base64": source.get("data", ""),
                            "source": "transcript",
                        }
                    )

    return images


def extract_images_from_hook(hook_input: HookInput) -> list[dict[str, Any]]:
    """
    Extract images from the hook input.

    This supports the proposed images field in UserPromptSubmit hook.
    See: https://github.com/anthropics/claude-code/issues/16592
    """
    images = []
    if not hook_input.images:
        return images

    for idx, img in enumerate(hook_input.images):
        images.append(
            {
                "index": img.get("index", idx),
                "media_type": img.get("media_type", "image/png"),
                "base64": img.get("base64", ""),
                "source": "hook",
            }
        )

    return images


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


def extract_token_usage(transcript: list[dict] | None) -> dict[str, Any] | None:
    """
    Extract token usage from the LAST assistant message in the transcript.

    Each stop event should only report the usage for that specific response,
    not cumulative usage from all messages.
    """
    if not transcript:
        return None

    # Find the last assistant message (iterate backwards)
    for entry in reversed(transcript):
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            usage = message.get("usage", {})
            if usage:
                return {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                }

    return None


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

    # Extract images from hook input (future feature) or transcript
    images = extract_images_from_hook(hook_input)

    # If no images from hook, try to extract from transcript
    # This is a fallback for when images are in the transcript but not in hook
    if not images:
        transcript = read_transcript(hook_input.transcript_path)
        images = extract_images_from_transcript(transcript)

    event = TracingEvent(
        event_type="user_prompt",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "prompt": hook_input.prompt,
            "images": images if images else None,
            "imagePasteIds": hook_input.imagePasteIds,
            "thinkingMetadata": hook_input.thinkingMetadata,
        },
    )
    send_event(event)


def handle_stop(hook_input: HookInput) -> None:
    """Handle Stop hook - Claude finished responding."""
    # Read the full transcript to get the latest messages
    transcript = read_transcript(hook_input.transcript_path)

    # Extract token usage from transcript
    token_usage = extract_token_usage(transcript)

    event = TracingEvent(
        event_type="assistant_stop",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "transcript": transcript,
            "token_usage": token_usage,
        },
    )
    send_event(event)


def handle_tool_use(hook_input: HookInput) -> None:
    """Handle PostToolUse hook - tool finished executing."""
    # Tool result may come as tool_result or tool_response depending on Claude Code version
    result = hook_input.tool_result or hook_input.tool_response

    event = TracingEvent(
        event_type="tool_use",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "tool_name": hook_input.tool_name,
            "tool_input": hook_input.tool_input,
            "tool_result": result,
        },
    )
    send_event(event)


def handle_precompact(hook_input: HookInput) -> None:
    """Handle PreCompact hook - context compaction is about to happen (/compact command)."""
    # Read current transcript before compaction
    transcript = read_transcript(hook_input.transcript_path)
    token_usage = extract_token_usage(transcript)

    event = TracingEvent(
        event_type="compact",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "command": "/compact",
            "transcript_before": transcript,
            "token_usage_before": token_usage,
        },
    )
    send_event(event)


def handle_notification(hook_input: HookInput) -> None:
    """Handle Notification hook - Claude sent a notification to user."""
    event = TracingEvent(
        event_type="notification",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "notification": hook_input.reason or "Notification",
        },
    )
    send_event(event)
