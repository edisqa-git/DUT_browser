from __future__ import annotations

import threading
import time
from pathlib import Path

import serial

from app.parser.sysmon_parser import SysMonParser


class SerialWorker:
    def __init__(self, parser: SysMonParser) -> None:
        self.parser = parser
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._mode: str | None = None

    def open(
        self,
        port: str,
        baudrate: int,
        mode: str = "serial",
        replay_path: str | None = None,
        replay_interval_ms: int = 100,
    ) -> None:
        self.close()

        with self._lock:
            self._stop_event.clear()
            if mode == "replay":
                if not replay_path:
                    raise RuntimeError("replay_path is required when mode is replay")
                replay_file = Path(replay_path)
                if not replay_file.exists() or not replay_file.is_file():
                    raise RuntimeError(f"Replay file not found: {replay_path}")
                self._mode = "replay"
                self._thread = threading.Thread(
                    target=self._replay_loop,
                    args=(replay_file, replay_interval_ms),
                    daemon=True,
                )
                self._thread.start()
                return

            self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=1)
            self._mode = "serial"
            self._thread = threading.Thread(target=self.read_loop, daemon=True)
            self._thread.start()

    def close(self) -> None:
        old_thread: threading.Thread | None = None
        with self._lock:
            self._stop_event.set()
            if self._serial is not None:
                try:
                    if self._serial.is_open:
                        self._serial.close()
                finally:
                    self._serial = None
            self._mode = None
            old_thread = self._thread
            self._thread = None

        if old_thread is not None and old_thread.is_alive() and old_thread is not threading.current_thread():
            old_thread.join(timeout=1.5)

        self.parser.flush()

    def send(self, text: str) -> None:
        with self._lock:
            if self._mode != "serial" or self._serial is None or not self._serial.is_open:
                raise RuntimeError("Serial port is not open")
            self._serial.write(text.encode("utf-8", errors="ignore"))
            self._serial.flush()

    def read_loop(self) -> None:
        while not self._stop_event.is_set():
            ser = self._serial
            if ser is None or not ser.is_open:
                break
            try:
                line = ser.readline()
            except Exception:
                break
            if not line:
                continue
            self.parser.feed(line.decode("utf-8", errors="ignore"))

    def _replay_loop(self, replay_file: Path, replay_interval_ms: int) -> None:
        delay_sec = max(1, replay_interval_ms) / 1000.0
        try:
            with replay_file.open("r", encoding="utf-8", errors="ignore") as fp:
                for line in fp:
                    if self._stop_event.is_set():
                        break
                    self.parser.feed(line)
                    time.sleep(delay_sec)
        finally:
            self.parser.flush()
            with self._lock:
                self._mode = None
                self._thread = None
