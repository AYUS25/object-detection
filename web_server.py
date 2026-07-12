"""
web_server.py
=============
FastAPI web server for the Smart Vision Assistant.

Endpoints:
  GET  /api/status         → Live system metrics JSON
  GET  /scene/report       → Full session intelligence report (active + inactive)
  GET  /objects            → Active objects (conf ≥ 80%, age ≥ 2s)
  GET  /session            → Full session memory (active + inactive)
  WS   /ws/live            → WebSocket push (1-second interval)
  GET  /video/stream       → MJPEG camera stream
  GET  /health             → Server health check

Start with:
  uvicorn web_server:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from smart_vision_headless import SmartVisionHeadless
from search_engine import SearchEngine
from timeline_engine import TimelineEngine
from knowledge_graph import KnowledgeGraph
from query_interpreter import QueryInterpreter

log = logging.getLogger("web_server")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

# ──────────────────────────────────────────────────────────────────────────────
# Global vision instance
# ──────────────────────────────────────────────────────────────────────────────

_vision: SmartVisionHeadless = None  # type: ignore

# ──────────────────────────────────────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _vision
    log.info("Starting SmartVisionHeadless…")
    _vision = SmartVisionHeadless()
    _vision.start()
    log.info("Vision system started. Server ready.")
    yield
    log.info("Shutting down vision system…")
    _vision.stop()
    log.info("Shutdown complete.")


# ──────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart Vision Assistant API",
    description="Visual Scene Intelligence Engine — Session Memory Web Interface",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve snapshots folder
snapshots_dir = Path("data/entity_snapshots")
snapshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory="data/entity_snapshots"), name="snapshots")

# Instantiate stateless engines
search_engine = SearchEngine()
timeline_engine = TimelineEngine()
knowledge_graph = KnowledgeGraph()
query_interpreter = QueryInterpreter()

# ──────────────────────────────────────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status() -> JSONResponse:
    """Live system metrics + session object counts."""
    state = _vision.get_state()
    registry = _vision.get_entity_registry()
    return JSONResponse({
        "fps":              state.get("fps", 0.0),
        "cpu":              state.get("cpu", 0.0),
        "ram_mb":           state.get("ram_mb", 0.0),
        "active_objects":   state.get("active_objects", 0),
        "inactive_objects": registry.session_object_count - state.get("active_objects", 0),
        "session_objects":  registry.session_object_count,
        "session_time":     state.get("session_time", 0.0),
        "status":           state.get("status", {}),
    })


@app.get("/scene/report")
async def get_scene_report() -> JSONResponse:
    """
    Full session intelligence report.
    Contains BOTH active (currently visible) and inactive (previously seen) objects.
    Confidence gate: >= 80%. Age gate for active: >= 2s.
    Returns structured JSON — never text blobs.
    """
    state = _vision.get_state()
    report = state.get("report", {})
    if not report:
        report = {
            "summary": "Initialising…",
            "active_objects": 0,
            "session_objects": 0,
            "objects": [],
            "inactive_objects": [],
            "events": [],
            "relationships": [],
        }
    return JSONResponse(report)


@app.get("/objects")
async def get_objects() -> JSONResponse:
    """
    Currently active objects: conf >= 80%, age >= 2s.
    For the live camera overlay section.
    """
    registry = _vision.get_entity_registry()
    active = registry.get_active(min_confidence=0.80, min_age_seconds=2.0)
    return JSONResponse({
        "count":   len(active),
        "objects": [e.to_dict() for e in active],
        "filters": {"min_confidence": 0.80, "min_age_seconds": 2.0},
    })


@app.get("/session")
async def get_session() -> JSONResponse:
    """
    Full session memory: all objects ever seen with conf >= 80%.
    Includes both active and inactive objects.
    This never shrinks — it is the complete session history.
    """
    registry = _vision.get_entity_registry()
    session = registry.get_session(min_confidence=0.80, min_age_seconds=2.0)
    return JSONResponse(session)


@app.get("/search")
async def search_memory(query: str = Query(None), brand: str = None, category: str = None, text: str = None, event: str = None) -> JSONResponse:
    """Search visual memory using natural language query or explicit filters."""
    filters = {}
    if query:
        filters = query_interpreter.parse(query)
    
    # Explicit filters override natural language parsed filters
    if brand: filters["brand"] = brand
    if category: filters["category"] = category
    if text: filters["text"] = text
    if event: filters["event"] = event
    
    session_id = _vision._session_id
    results = search_engine.search(session_id, filters)
    return JSONResponse({"results": results})


@app.get("/timeline")
async def get_timeline() -> JSONResponse:
    """Fetch chronological event timeline for the session."""
    session_id = _vision._session_id
    timeline = timeline_engine.get_session_timeline(session_id)
    return JSONResponse({"timeline": timeline})


@app.get("/graph")
async def get_graph() -> JSONResponse:
    """Fetch session knowledge graph (nodes & edges)."""
    session_id = _vision._session_id
    graph = knowledge_graph.get_graph(session_id)
    return JSONResponse(graph)


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket — Live Push
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket):
    """
    WebSocket — pushes full session state every second.

    Payload includes:
      objects          — active objects (conf >= 80%, age >= 2s)
      inactive_objects — previously seen objects (full session history)
      events           — all session events (active + inactive)
      relationships    — all session relationships with counts
      status           — component health + FPS/CPU/RAM
      report           — summary + category counts + session stats
    """
    await ws.accept()
    log.info("WebSocket client connected: %s", ws.client)
    try:
        while True:
            state = _vision.get_state()
            report = state.get("report", {})

            payload = {
                "objects":          state.get("objects", []),
                "inactive_objects": state.get("inactive_objects", []),
                "events":           state.get("events", []),
                "relationships":    state.get("relationships", []),
                "status":           state.get("status", {}),
                "report": {
                    "summary":            report.get("summary", ""),
                    "active_objects":     report.get("active_objects", 0),
                    "session_objects":    report.get("session_objects", 0),
                    "inactive_count":     len(state.get("inactive_objects", [])),
                    "fps":                report.get("fps", 0.0),
                    "cpu":                report.get("cpu", 0.0),
                    "ram_mb":             report.get("ram_mb", 0.0),
                    "session_time":       report.get("session_time", 0.0),
                    "session_time_str":   report.get("session_time_str", "0s"),
                    "scene_stability":    report.get("scene_stability", 0.0),
                    "active_by_category": report.get("active_by_category", {}),
                    "session_by_category":report.get("session_by_category", {}),
                    "total_registered":   report.get("total_registered", 0),
                },
            }

            await ws.send_json(payload)
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected: %s", ws.client)
    except Exception as exc:
        log.warning("WebSocket error: %s", exc)


# ──────────────────────────────────────────────────────────────────────────────
# MJPEG Camera Stream
# ──────────────────────────────────────────────────────────────────────────────

async def _mjpeg_generator() -> AsyncGenerator[bytes, None]:
    boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
    tail = b"\r\n"
    while True:
        jpeg = _vision.get_latest_frame()
        if jpeg:
            yield boundary + jpeg + tail
        await asyncio.sleep(1 / 30)


@app.get("/video/stream")
async def video_stream():
    """MJPEG stream — React CameraView uses <img src='/video/stream' />."""
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace;boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> JSONResponse:
    registry = _vision.get_entity_registry() if _vision else None
    return JSONResponse({
        "status":          "ok",
        "vision_running":  _vision.is_running if _vision else False,
        "session_objects": registry.session_object_count if registry else 0,
    })
