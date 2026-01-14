"""
WebSocket module for real-time updates.

Manages connected clients and broadcasts new events.

Related: broadcast.py (implementation), routes/events.py (triggers broadcasts)
"""

from .broadcast import ConnectionManager, manager

__all__ = ["ConnectionManager", "manager"]
