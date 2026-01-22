"""
FastAPI application entry point.

Sets up routes, WebSocket endpoint, CORS, background poller, and runs the server.
Use `quickcall-supertrace` CLI or `uvicorn quickcall_supertrace.main:app`.

Related: routes/ (API endpoints), ws/ (WebSocket), db/ (storage), ingest/ (session import)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .db import get_db
from .hooks.setup import register_hooks

# Static files directory (bundled frontend)
STATIC_DIR = Path(__file__).parent / "static"
from .ingest.poller import polling_loop
from .routes import (
    ingest_router,
    intents_router,
    media_router,
    metrics_router,
    sessions_router,
    version_router,
)
from .ws import manager

logger = logging.getLogger(__name__)

# Background task reference
_poller_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    global _poller_task

    # Startup
    logger.info("Starting QuickCall SuperTrace server...")
    await get_db()

    # Auto-register Claude Code hooks (unless disabled)
    auto_hooks = os.environ.get("QUICKCALL_SUPERTRACE_AUTO_HOOKS", "true").lower() == "true"
    if auto_hooks:
        register_hooks()

    # Start background poller if enabled
    enable_poller = os.environ.get("QUICKCALL_SUPERTRACE_ENABLE_POLLER", "true").lower() == "true"
    if enable_poller:
        poll_interval = int(os.environ.get("QUICKCALL_SUPERTRACE_POLL_INTERVAL", "2"))
        logger.info(f"Starting session poller (interval: {poll_interval}s)")
        _poller_task = asyncio.create_task(polling_loop(interval=poll_interval))

    yield

    # Shutdown
    if _poller_task:
        logger.info("Stopping session poller...")
        _poller_task.cancel()
        try:
            await _poller_task
        except asyncio.CancelledError:
            pass

    logger.info("QuickCall SuperTrace server stopped")


app = FastAPI(
    title="QuickCall SuperTrace",
    description="Tracing server for AI coding assistant sessions",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend - configurable via environment variable
# Set QUICKCALL_SUPERTRACE_CORS_ORIGINS to comma-separated list of allowed origins
# Example: QUICKCALL_SUPERTRACE_CORS_ORIGINS="http://localhost:2255,https://myapp.com"
_cors_origins_env = os.environ.get("QUICKCALL_SUPERTRACE_CORS_ORIGINS", "*")
_cors_origins = (
    ["*"] if _cors_origins_env == "*"
    else [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ingest_router)
app.include_router(intents_router)
app.include_router(sessions_router)
app.include_router(media_router)
app.include_router(metrics_router)
app.include_router(version_router)

# Mount static files for bundled frontend (if available)
if STATIC_DIR.exists():
    # Serve static assets (js, css, etc.)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA - return index.html for client-side routing."""
        # Don't catch API or WebSocket routes
        if path.startswith("api/") or path == "ws":
            return {"status": "not_found"}
        # Serve static file if it exists
        static_file = STATIC_DIR / path
        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)
        # Otherwise serve index.html for SPA routing
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        """Health check endpoint (no frontend bundled)."""
        return {"status": "ok", "service": "quickcall-supertrace", "frontend": "not bundled"}


@app.get("/api/health")
async def health():
    """Health check for monitoring."""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Clients send JSON messages to subscribe/unsubscribe from sessions:
    - {"type": "subscribe", "session_id": "..."}
    - {"type": "unsubscribe", "session_id": "..."}
    """
    import json

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                session_id = msg.get("session_id")

                if msg_type == "subscribe" and session_id:
                    manager.subscribe(websocket, session_id)
                elif msg_type == "unsubscribe" and session_id:
                    manager.unsubscribe(websocket, session_id)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from WebSocket client: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def run():
    """CLI entry point."""
    port = int(os.environ.get("QUICKCALL_SUPERTRACE_PORT", "7845"))
    host = os.environ.get("QUICKCALL_SUPERTRACE_HOST", "127.0.0.1")

    uvicorn.run(
        "quickcall_supertrace.main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    run()
