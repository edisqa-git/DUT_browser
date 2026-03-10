from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from serial.tools import list_ports

from app.config import LOG_DIR

router = APIRouter(prefix="/api/serial", tags=["serial"])


class SerialOpenRequest(BaseModel):
    port: str = ""
    baudrate: int = 115200
    mode: Literal["serial", "replay"] = "serial"
    replay_path: str | None = None
    replay_interval_ms: int = 100


class SerialSendRequest(BaseModel):
    text: str


@router.get("/ports")
def list_serial_ports() -> dict:
    ports = []
    for info in list_ports.comports():
        ports.append(
            {
                "device": info.device,
                "description": info.description or "",
                "hwid": info.hwid or "",
            }
        )
    return {"ports": ports}


@router.post("/open")
def open_serial(body: SerialOpenRequest, request: Request) -> dict:
    try:
        serial_worker = request.app.state.serial_worker
        serial_worker.open(
            port=body.port,
            baudrate=body.baudrate,
            mode=body.mode,
            replay_path=body.replay_path,
            replay_interval_ms=body.replay_interval_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "mode": body.mode, "log_path": serial_worker.current_log_path}


@router.post("/close")
def close_serial(request: Request) -> dict:
    request.app.state.serial_worker.close()
    return {"ok": True}


@router.post("/send")
def send_serial(body: SerialSendRequest, request: Request) -> dict:
    try:
        request.app.state.serial_worker.send(body.text)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/logs/{file_name}")
def download_log(file_name: str) -> FileResponse:
    safe_name = file_name.split("/")[-1]
    if safe_name != file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    file_path = LOG_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(path=file_path, filename=safe_name, media_type="text/plain")
