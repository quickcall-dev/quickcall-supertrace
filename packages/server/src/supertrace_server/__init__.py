"""
SuperTrace server package.

FastAPI server that receives hook events, stores them in SQLite,
and provides REST API + WebSocket for the frontend.

Related: main.py (entry), db/ (storage), routes/ (API), ws/ (realtime)
"""

__version__ = "0.1.0"
