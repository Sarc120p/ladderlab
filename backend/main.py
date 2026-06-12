"""
LadderLab – FastAPI backend.
Exposes the PLC engine via REST API and WebSocket for real‑time monitoring.
"""

import asyncio
import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from engine.scan_cycle import ScanCycle
from backend.routes import router
from backend.database import init_db, engine
from backend.event_persistence import EventPersistence


# =============================================================================
# WebSocket connection manager
# =============================================================================
class ConnectionManager:
    """Manages active WebSocket connections and broadcasts."""

    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, data: dict):
        """Send a JSON payload to all connected clients."""
        if not self._connections:
            return

        payload = json.dumps(data)
        for ws in self._connections[:]:
            try:
                await ws.send_text(payload)
            except Exception:
                self._connections.remove(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# =============================================================================
# Global state
# =============================================================================
scan_engine: Optional[ScanCycle] = None
ws_manager = ConnectionManager()
event_persistence: Optional[EventPersistence] = None

# Allow routes to access the scan engine
import backend.routes as routes_module
routes_module.scan_engine = scan_engine


# =============================================================================
# Background broadcast callback
# =============================================================================
def create_broadcast_callback():
    """
    Returns a synchronous callback suitable for ScanCycle.on_update.
    The callback schedules an async broadcast on the running event loop.
    """
    loop = asyncio.get_running_loop()

    def _broadcast(tags: dict):
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(tags), loop)

    return _broadcast


# =============================================================================
# Event persistence callback (called from scan cycle thread)
# =============================================================================
def create_event_callback(persistence: EventPersistence):
    """
    Returns a synchronous callback suitable for ScanCycle.on_event.
    The callback enqueues the event for asynchronous persistence.
    """
    def _on_event(event_type: str, message: str, severity: Optional[str] = None):
        persistence.enqueue(event_type, message, severity)

    return _on_event


# =============================================================================
# Application lifecycle
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global scan_engine, event_persistence

    # --- Startup ---
    await init_db()             # create database tables

    event_persistence = EventPersistence()
    await event_persistence.start()

    scan_engine = ScanCycle(scan_time=0.1)
    routes_module.scan_engine = scan_engine
    scan_engine.on_update = create_broadcast_callback()
    scan_engine.on_event = create_event_callback(event_persistence)
    scan_engine.start()

    yield

    # --- Shutdown ---
    if scan_engine:
        scan_engine.stop()
    if event_persistence:
        await event_persistence.stop()
    await engine.dispose()


# =============================================================================
# FastAPI application
# =============================================================================
app = FastAPI(
    title="LadderLab API",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
base_dir = Path(__file__).resolve().parent.parent

frontend_dir = base_dir / "frontend"
programs_dir = base_dir / "programs"

frontend_dir.mkdir(parents=True, exist_ok=True)
programs_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
app.mount("/programs", StaticFiles(directory=str(programs_dir)), name="programs")

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)

# ---------------------------------------------------------------------------
# Serve frontend
# ---------------------------------------------------------------------------
@app.get("/")
async def serve_dashboard():
    """Serve the main HMI dashboard."""
    return FileResponse(str(frontend_dir / "index.html"))


# =============================================================================
# Run (development only)
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)