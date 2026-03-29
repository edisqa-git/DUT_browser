import asyncio
from argparse import ArgumentParser
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.app_api import router as app_router
from app.api.analyzer_api import router as analyzer_router
from app.api.serial_api import router as serial_router
from app.config import ANALYZER_OUTPUT_DIR, SNAPSHOT_FILE
from app.parser.sysmon_parser import SysMonParser
from app.serial.serial_worker import SerialWorker
from app.services.analyzer_service import AnalyzerService
from app.services.snapshot_store import SnapshotStore
from app.services.version_service import VersionService
from app.versioning import read_version
from app.websocket.ws_manager import WebSocketManager

app = FastAPI(title="DUT Local Monitoring Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://tauri.localhost",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(app_router)
app.include_router(serial_router)
app.include_router(analyzer_router)


@app.on_event("startup")
async def on_startup() -> None:
    ws_manager = WebSocketManager()
    ws_manager.bind_loop(asyncio.get_running_loop())

    def on_event(event: dict) -> None:
        ws_manager.emit_from_thread(event)

    app.state.ws_manager = ws_manager
    app.state.snapshot_store = SnapshotStore(SNAPSHOT_FILE)
    app.state.parser = SysMonParser(on_event=on_event)
    app.state.serial_worker = SerialWorker(app.state.parser)
    app.state.analyzer_service = AnalyzerService()
    app.state.version_service = VersionService()


@app.get("/health")
def health() -> dict:
    return {"ok": True, "phase": "desktop-shell", "version": read_version()}


@app.get("/api/download/{file_name}")
def download_file(file_name: str) -> FileResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    file_path = ANALYZER_OUTPUT_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=file_path, filename=safe_name, media_type="application/octet-stream")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    manager: WebSocketManager = app.state.ws_manager
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn

    parser = ArgumentParser(description="DUT Browser backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
