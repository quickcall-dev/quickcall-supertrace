"""
Event handlers for different Claude Code hook types.

Receives parsed HookInput, transforms it into TracingEvent,
and sends to the server. Each handler corresponds to a hook event type.

Related: models.py (data structures), client.py (sends events), cli.py (dispatches here)
"""

import json
import sys
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


def extract_image_paste_ids_from_transcript(transcript: list[dict] | None) -> list[int] | None:
    """
    Extract imagePasteIds from the LAST user message in the transcript.

    WHY THIS IS NEEDED:
    Claude Code does NOT send imagePasteIds in the UserPromptSubmit hook input.
    It only stores imagePasteIds in the transcript JSONL file. Without this
    fallback, we would never capture image counts for the images_per_hour metric.

    The transcript entry looks like:
    {"type": "user", "message": {...}, "imagePasteIds": [1, 2, 3], ...}

    We read the last user entry and extract imagePasteIds from there.
    """
    if not transcript:
        return None

    # Find the last user message (iterate backwards)
    for entry in reversed(transcript):
        if entry.get("type") == "user":
            image_paste_ids = entry.get("imagePasteIds")
            if image_paste_ids:
                return image_paste_ids

    return None


def extract_thinking_metadata_from_transcript(transcript: list[dict] | None) -> dict[str, Any] | None:
    """
    Extract thinkingMetadata from the LAST user message in the transcript.

    WHY THIS IS NEEDED:
    Claude Code does NOT send thinkingMetadata in the UserPromptSubmit hook input.
    It only stores thinkingMetadata in the transcript JSONL file. Without this
    fallback, we would never capture thinking mode usage for the thinking_usage metric.

    The transcript entry looks like:
    {"type": "user", "message": {...}, "thinkingMetadata": {"level": "high", ...}, ...}

    We read the last user entry and extract thinkingMetadata from there.
    """
    if not transcript:
        return None

    # Find the last user message (iterate backwards)
    for entry in reversed(transcript):
        if entry.get("type") == "user":
            thinking_meta = entry.get("thinkingMetadata")
            if thinking_meta:
                return thinking_meta

    return None


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
    """
    Handle UserPromptSubmit hook - user sent a message.

    IMPORTANT: Claude Code's hook input does NOT include all fields stored in the transcript.
    Specifically, imagePasteIds and thinkingMetadata are stored in the transcript JSONL
    but NOT passed to hooks. We must read the transcript as a fallback to capture this data.

    Without this fallback:
    - images_per_hour metric would always be 0
    - thinking_usage metric would always be 0/0
    """
    # prompt is passed directly in the hook input (field name is 'prompt')

    # Read transcript for fallback data extraction
    # This is necessary because Claude Code doesn't pass all fields to hooks
    transcript = read_transcript(hook_input.transcript_path)

    # Extract images from hook input (future feature) or transcript
    images = extract_images_from_hook(hook_input)
    images_source = "hook" if images else None
    if not images:
        images = extract_images_from_transcript(transcript)
        if images:
            images_source = "transcript"

    # Get imagePasteIds - Claude Code does NOT send this in hook input
    # Must fall back to transcript to get image counts for metrics
    image_paste_ids = hook_input.imagePasteIds
    image_paste_ids_source = "hook" if image_paste_ids else None
    if not image_paste_ids:
        image_paste_ids = extract_image_paste_ids_from_transcript(transcript)
        if image_paste_ids:
            image_paste_ids_source = "transcript"

    # Get thinkingMetadata - Claude Code does NOT send this in hook input
    # Must fall back to transcript to track thinking mode usage
    thinking_metadata = hook_input.thinkingMetadata
    thinking_source = "hook" if thinking_metadata else None
    if not thinking_metadata:
        thinking_metadata = extract_thinking_metadata_from_transcript(transcript)
        if thinking_metadata:
            thinking_source = "transcript"

    # Debug logging to file
    log_path = Path.home() / ".supertrace" / "hooks.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"[handle_prompt] session={hook_input.session_id}\n")
        f.write(f"  images: {len(images) if images else 0} (source: {images_source})\n")
        f.write(f"  imagePasteIds: {image_paste_ids} (source: {image_paste_ids_source})\n")
        f.write(f"  thinkingMetadata: {thinking_metadata is not None} (source: {thinking_source})\n")

    event = TracingEvent(
        event_type="user_prompt",
        session_id=hook_input.session_id,
        project_path=hook_input.cwd,
        transcript_path=hook_input.transcript_path,
        data={
            "prompt": hook_input.prompt,
            "images": images if images else None,
            "imagePasteIds": image_paste_ids,
            "thinkingMetadata": thinking_metadata,
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
