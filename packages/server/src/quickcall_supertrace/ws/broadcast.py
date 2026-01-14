"""
WebSocket connection manager and broadcasting.

Maintains list of connected clients with session subscriptions.
Only broadcasts events to clients subscribed to that session.

Related: routes/events.py (calls broadcast), main.py (WebSocket endpoint)
"""

import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections with session subscriptions."""

    def __init__(self):
        # Map of websocket -> set of subscribed session_ids
        self.subscriptions: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection."""
        await websocket.accept()
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected client."""
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    def subscribe(self, websocket: WebSocket, session_id: str) -> None:
        """Subscribe client to a session's updates."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(session_id)

    def unsubscribe(self, websocket: WebSocket, session_id: str) -> None:
        """Unsubscribe client from a session's updates."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(session_id)

    async def broadcast_to_session(self, session_id: str, data: dict[str, Any]) -> None:
        """Send data only to clients subscribed to this session."""
        message = json.dumps(data)
        disconnected = []

        for websocket, subscribed_sessions in self.subscriptions.items():
            if session_id in subscribed_sessions:
                try:
                    await websocket.send_text(message)
                except Exception:
                    disconnected.append(websocket)

        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_all(self, data: dict[str, Any]) -> None:
        """Send data to all connected clients (for global updates like new session)."""
        message = json.dumps(data)
        disconnected = []

        for websocket in self.subscriptions.keys():
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.append(websocket)

        for conn in disconnected:
            self.disconnect(conn)


# Singleton instance
manager = ConnectionManager()
