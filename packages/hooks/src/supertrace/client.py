"""
HTTP client for sending events to the tracing server.

Handles POST requests to the server with retry logic and
graceful failure (hooks should not block Claude Code).

Related: models.py (TracingEvent), handlers.py (calls send_event)
"""

import os

import httpx

from .models import TracingEvent

DEFAULT_SERVER_URL = "http://localhost:3456"
TIMEOUT_SECONDS = 2.0


def get_server_url() -> str:
    """Get server URL from env or use default."""
    return os.environ.get("SUPERTRACE_URL", DEFAULT_SERVER_URL)


def send_event(event: TracingEvent) -> bool:
    """
    Send event to tracing server.

    Returns True if successful, False otherwise.
    Fails silently to avoid blocking Claude Code.
    """
    url = f"{get_server_url()}/api/events"

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                json=event.model_dump(mode="json"),
            )
            return response.status_code == 200
    except (httpx.RequestError, httpx.TimeoutException):
        # Fail silently - don't block Claude Code
        return False
