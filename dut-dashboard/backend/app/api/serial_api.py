from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from serial.tools import list_ports

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
        request.app.state.serial_worker.open(
            port=body.port,
            baudrate=body.baudrate,
            mode=body.mode,
            replay_path=body.replay_path,
            replay_interval_ms=body.replay_interval_ms,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "mode": body.mode}


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
