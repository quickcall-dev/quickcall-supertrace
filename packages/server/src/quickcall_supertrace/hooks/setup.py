"""
Auto-registration of Claude Code hooks.

When QuickCall SuperTrace starts, this module configures Claude Code
to send hook events to the supertrace-hook CLI.

This eliminates manual setup - users just run quickcall-supertrace
and hooks are automatically configured.
"""

import json
import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Claude Code settings path
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# Marker to identify our hooks
SUPERTRACE_HOOK_MARKER = "quickcall-supertrace-hook"


def get_hook_command_path() -> str:
    """
    Find the full path to quickcall-supertrace-hook command.

    This is needed because Claude Code runs hooks in a shell that
    may not have the same PATH as the user's terminal.
    """
    # The hook CLI is installed alongside the main package
    # Find it relative to the current Python executable
    python_bin_dir = Path(sys.executable).parent
    hook_path = python_bin_dir / "quickcall-supertrace-hook"

    if hook_path.exists():
        return str(hook_path)

    # Fallback: try to find via shutil.which
    import shutil as sh
    found = sh.which("quickcall-supertrace-hook")
    if found:
        return found

    # Last resort: assume it's in PATH (may fail but worth trying)
    logger.warning("Could not find quickcall-supertrace-hook path, using bare command")
    return "quickcall-supertrace-hook"


def get_supertrace_hooks() -> dict:
    """Get hook configuration with the correct command path."""
    hook_cmd = get_hook_command_path()
    return {
        "Stop": [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": f"{hook_cmd} stop",
                        "timeout": 5
                    }
                ]
            }
        ]
    }


def get_claude_settings() -> dict:
    """Read Claude Code settings, return empty dict if not found."""
    if not CLAUDE_SETTINGS_PATH.exists():
        return {}

    try:
        with open(CLAUDE_SETTINGS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to read Claude settings: {e}")
        return {}


def save_claude_settings(settings: dict) -> bool:
    """Save Claude Code settings with backup."""
    try:
        # Ensure directory exists
        CLAUDE_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing settings
        if CLAUDE_SETTINGS_PATH.exists():
            backup_path = CLAUDE_SETTINGS_PATH.with_suffix(".json.bak")
            shutil.copy2(CLAUDE_SETTINGS_PATH, backup_path)

        # Write new settings
        with open(CLAUDE_SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=2)

        return True
    except IOError as e:
        logger.error(f"Failed to save Claude settings: {e}")
        return False


def is_supertrace_hook(hook_config: dict) -> bool:
    """Check if a hook configuration is from SuperTrace."""
    hooks = hook_config.get("hooks", [])
    for hook in hooks:
        command = hook.get("command", "")
        if SUPERTRACE_HOOK_MARKER in command:
            return True
    return False


def register_hooks() -> bool:
    """
    Register SuperTrace hooks in Claude Code settings.

    Returns True if hooks were registered or already present.
    """
    settings = get_claude_settings()

    # Get or create hooks section
    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks = settings["hooks"]
    modified = False

    # Get hook configs with correct command path
    supertrace_hooks = get_supertrace_hooks()

    # Register each hook type
    for event_type, hook_configs in supertrace_hooks.items():
        if event_type not in hooks:
            hooks[event_type] = []

        # Check if our hooks are already registered
        existing_hooks = hooks[event_type]
        has_supertrace = any(is_supertrace_hook(h) for h in existing_hooks)

        if not has_supertrace:
            # Add our hooks
            hooks[event_type].extend(hook_configs)
            modified = True
            logger.info(f"Registered {event_type} hook for QuickCall SuperTrace")

    if modified:
        if save_claude_settings(settings):
            logger.info("Claude Code hooks configured successfully")
            logger.info("Restart Claude Code to activate hooks")
            return True
        else:
            logger.error("Failed to save Claude Code settings")
            return False
    else:
        logger.debug("QuickCall SuperTrace hooks already registered")
        return True


def unregister_hooks() -> bool:
    """
    Remove SuperTrace hooks from Claude Code settings.

    Returns True if hooks were removed.
    """
    settings = get_claude_settings()

    if "hooks" not in settings:
        return True

    hooks = settings["hooks"]
    modified = False

    for event_type in list(hooks.keys()):
        original_count = len(hooks[event_type])
        hooks[event_type] = [h for h in hooks[event_type] if not is_supertrace_hook(h)]

        if len(hooks[event_type]) < original_count:
            modified = True
            logger.info(f"Removed {event_type} hook for QuickCall SuperTrace")

        # Remove empty event types
        if not hooks[event_type]:
            del hooks[event_type]

    if modified:
        return save_claude_settings(settings)

    return True


def check_hooks_status() -> dict:
    """
    Check current status of SuperTrace hooks.

    Returns dict with status info.
    """
    settings = get_claude_settings()
    hooks = settings.get("hooks", {})
    supertrace_hooks = get_supertrace_hooks()

    registered = {}
    for event_type in supertrace_hooks.keys():
        event_hooks = hooks.get(event_type, [])
        registered[event_type] = any(is_supertrace_hook(h) for h in event_hooks)

    return {
        "settings_path": str(CLAUDE_SETTINGS_PATH),
        "settings_exists": CLAUDE_SETTINGS_PATH.exists(),
        "hooks_registered": registered,
        "all_registered": all(registered.values()),
        "hook_command": get_hook_command_path(),
    }
