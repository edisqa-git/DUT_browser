from copy import deepcopy
import json
import re
from collections.abc import Callable


class SysMonParser:
    """Milestone 3 parser: console lines + snapshots + CPU + wifi clients."""

    SNAPSHOT_RE = re.compile(r"^= Test Time:\s*(\d+),\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*$")
    CPU_RE = re.compile(
        r"^CPU(\d+):\s*([\d.]+)% usr\s+([\d.]+)% sys\s+([\d.]+)% nic\s+([\d.]+)% idle\s+([\d.]+)% io\s+([\d.]+)% irq\s+([\d.]+)% sirq\s*$"
    )
    CLIENT_MARKER_RE = re.compile(r"^--- CLIENTS Radio=(2G|5G|6G) ---\s*$")

    def __init__(self, on_event: Callable[[dict], None]) -> None:
        self.on_event = on_event
        self._current_snapshot: dict | None = None
        self._pending_clients_radio: str | None = None

    def feed(self, line: str) -> None:
        text = line.rstrip("\r\n")

        snap_match = self.SNAPSHOT_RE.match(text)
        if snap_match:
            self._emit_current_snapshot()
            self._current_snapshot = {
                "test_count": int(snap_match.group(1)),
                "device_ts": snap_match.group(2),
                "cpu": {},
                "wifi_clients": {},
            }
            self._pending_clients_radio = None
            return

        marker_match = self.CLIENT_MARKER_RE.match(text)
        if marker_match:
            self._pending_clients_radio = marker_match.group(1)
            return

        if self._pending_clients_radio is not None and text.startswith("{"):
            self._consume_clients_json(text)
            return

        if self._current_snapshot is None:
            self.on_event({"type": "console_line", "text": text})
            return

        cpu_match = self.CPU_RE.match(text)
        if not cpu_match:
            self.on_event({"type": "console_line", "text": text})
            return

        core_id = cpu_match.group(1)
        self._current_snapshot["cpu"][core_id] = {
            "usr": float(cpu_match.group(2)),
            "sys": float(cpu_match.group(3)),
            "nic": float(cpu_match.group(4)),
            "idle": float(cpu_match.group(5)),
            "io": float(cpu_match.group(6)),
            "irq": float(cpu_match.group(7)),
            "sirq": float(cpu_match.group(8)),
        }
        self._emit_snapshot_update()

    def flush(self) -> None:
        self._emit_current_snapshot()

    def _consume_clients_json(self, text: str) -> None:
        radio = self._pending_clients_radio
        self._pending_clients_radio = None
        if radio is None:
            return

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return

        if not isinstance(parsed, dict):
            return

        data = parsed.get("data")
        if not isinstance(data, dict):
            return

        clients_raw = data.get("client_list")
        clients = clients_raw if isinstance(clients_raw, list) else []
        total_size_raw = data.get("total_size")

        try:
            total_size = int(total_size_raw)
        except (TypeError, ValueError):
            total_size = len(clients)

        event = {
            "type": "wifi_clients_update",
            "radio": radio,
            "total_size": total_size,
            "clients": clients,
        }
        self.on_event(event)

        if self._current_snapshot is not None:
            self._current_snapshot["wifi_clients"][radio] = {
                "total_size": total_size,
                "clients": clients,
            }

    def _emit_current_snapshot(self) -> None:
        if self._current_snapshot is None:
            return
        self._emit_snapshot_update()
        self._current_snapshot = None

    def _emit_snapshot_update(self) -> None:
        if self._current_snapshot is None:
            return
        self.on_event({"type": "snapshot_update", "snapshot": deepcopy(self._current_snapshot)})
