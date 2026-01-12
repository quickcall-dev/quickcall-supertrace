"""
FastAPI application entry point.

Sets up routes, WebSocket endpoint, CORS, and runs the server.
Use `supertrace-server` CLI or `uvicorn supertrace_server.main:app`.

Related: routes/ (API endpoints), ws/ (WebSocket), db/ (storage)
"""

import os

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .db import get_db
from .routes import events_router, media_router, metrics_router, sessions_router
from .ws import manager

app = FastAPI(
    title="SuperTrace",
    description="Tracing server for AI coding assistant sessions",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(events_router)
app.include_router(sessions_router)
app.include_router(media_router)
app.include_router(metrics_router)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await get_db()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "supertrace"}


@app.get("/api/health")
async def health():
    """Health check for monitoring."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Clients connect here to receive new events as they arrive.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Could handle client commands here if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def run():
    """CLI entry point."""
    port = int(os.environ.get("SUPERTRACE_PORT", "3456"))
    host = os.environ.get("SUPERTRACE_HOST", "127.0.0.1")

    uvicorn.run(
        "supertrace_server.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    run()
