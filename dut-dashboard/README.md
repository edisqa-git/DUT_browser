# dut-dashboard — Subsystem Developer Reference

This document covers the `dut-dashboard/` subsystem in detail:
backend API routes, parser patterns, tool registry, WebSocket contracts, and frontend components.

For product-level setup and architecture overview, see the [root README](../README.md).

---

## Run Standalone (without Tauri)

Useful for backend / frontend development without the full desktop shell.

**Terminal 1 — Backend**

```bash
cd dut-dashboard/backend
python3 -m app.main
```

Backend listens on `http://127.0.0.1:8765`.

**Terminal 2 — Frontend**

```bash
cd dut-dashboard/frontend
npm install
npm run dev
```

Frontend dev server at `http://127.0.0.1:5173`. Open in a browser.

> **Note:** The Tauri shell owns backend process lifecycle in production. Running both terminals is for dev iteration only and is not the supported product path.

---

## Backend

### HTTP API Routes

All routes are prefixed by the FastAPI app mounted at `/`.

#### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns `{"status":"ok","version":"x.y.z"}` |
| `GET` | `/api/meta` | Returns product name, current version, releases page URL |
| `GET` | `/api/version/check` | Checks GitHub releases/tags for a newer version (10-min cache) |
| `GET` | `/api/version/check?force=true` | Bypasses cache |

#### Serial

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/serial/open` | Open serial port or start replay |
| `POST` | `/api/serial/close` | Stop serial session |
| `POST` | `/api/serial/send` | Send raw text to DUT |
| `GET` | `/api/serial/ports` | List available serial ports + glob scan |
| `GET` | `/api/serial/logs/{file_name}` | Download log (raw `.log` or analyzer `.zip`) |

**`GET /api/serial/ports` response:**

```json
{
  "ports": [{ "device": "/dev/cu.usbserial-0001", "description": "...", "hwid": "..." }],
  "glob_devices": ["/dev/cu.Bluetooth-Incoming-Port", "/dev/cu.usbserial-0001"]
}
```

`ports` — pyserial-detected devices (with description/hwid). `glob_devices` — all `/dev/cu.*` paths found via glob (macOS); may include devices pyserial doesn't enumerate.

#### Snapshots

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/snapshots/list` | List saved `.jsonl` snapshot files |
| `POST` | `/api/snapshots/replay/start` | Start replay; body: `{"file": "snapshots.jsonl", "speed_ms": 500}` |
| `POST` | `/api/snapshots/replay/stop` | Stop an in-progress replay |
| `GET` | `/api/snapshots/{file_name}/download` | Download a snapshot JSONL file |

**`POST /api/serial/open` body:**

```json
{
  "mode": "serial",
  "port": "/dev/ttyUSB0",
  "baudrate": 115200
}
```

```json
{
  "mode": "replay",
  "replay_path": "logs/sample.log",
  "replay_interval_ms": 100
}
```

#### Analyzer

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyzer/run` | Run `tools/analyzer3.py` on a log file |
| `GET` | `/api/download/{file}` | Download a named artifact from `logs/analyzer_output/` |

**Log Download Decision Logic (`GET /api/serial/logs/{file_name}`):**

```
log < 100 lines AND no "TOP" marker
    └─► return raw .log  (Content-Type: text/plain)

otherwise
    └─► create  logs/dut-session-YYYYMMDD-HHMMSS/
        copy log into session dir
        run tools/analyzer3.py (cwd = session dir)
        zip session dir → dut-session-YYYYMMDD-HHMMSS.zip
        return .zip  (Content-Type: application/zip)
```

Typical analyzer artifacts in the zip:
- `*cpu_usage.csv` / `*cpu_usage_plot.png`
- `*memory.csv` / `*memavailable_plot.png`
- `*slab_plot.png` / `*sunreclaim_plot.png`
- `*cpu_spike_report.txt`

**HTTP error codes:**

| Code | Cause |
|------|-------|
| 400 | Invalid filename |
| 404 | Log file not found |
| 422 | Log too short for analysis path |
| 500 | Analyzer / zip / runtime failure |

---

### SysMonParser — Line Patterns

`dut-dashboard/backend/app/parser/sysmon_parser.py`

The parser runs on every line arriving from the serial stream (or replay). Matched lines are consumed as structured data; unmatched lines go to the console batch queue.

| Pattern | Regex (simplified) | Emits |
|---------|--------------------|-------|
| `SNAPSHOT_RE` | `= Test Time: N, YYYY-MM-DD HH:MM:SS =` | `snapshot_update` (boundary) |
| `CPU_RE` | `CPU0: X% usr Y% sys … Z% sirq` | updates `current_snapshot["cpu"]` |
| `MEM_RE` | `Mem: XK used, YK free …` | `memory_update` event + `current_snapshot["memory"]` |
| `CLIENT_MARKER_RE` | `--- CLIENTS Radio=2G/5G/6G ---` | sets pending radio |
| JSON line after marker | `{"data": {"client_list": […]}}` | `wifi_clients_update` |
| everything else | — | `console_line_batch` (batched ≤ 20 lines or 200 ms) |

**Console batch tuning constants:**

```python
CONSOLE_BATCH_SIZE = 20          # flush immediately at this count
CONSOLE_BATCH_MAX_LATENCY_SEC = 0.2   # max wait before timer flush
```

---

### TOOL_REGISTRY

`dut-dashboard/backend/app/tools/`

Tools are registered with `@tool` and dispatched via WebSocket JSON messages.

**Client → Server message format:**

```json
{ "tool": "open_serial", "params": { "mode": "serial", "port": "/dev/ttyUSB0", "baudrate": 115200 }, "request_id": "abc123" }
```

**Server → Client response:**

```json
{ "type": "tool_result", "request_id": "abc123", "ok": true, "result": { … } }
```

**Registered tools:**

| Tool name | Module | Description |
|-----------|--------|-------------|
| `open_serial` | `serial_tools` | Open port or start replay |
| `close_serial` | `serial_tools` | Stop session |
| `send_serial` | `serial_tools` | Send text to DUT |
| `list_serial_ports` | `serial_tools` | List available serial ports + glob scan |
| `get_efficiency_report` | `serial_tools` | Serial read efficiency stats |
| `run_analyzer` | `analyzer_tools` | Trigger offline analysis |
| `download_artifact` | `analyzer_tools` | Fetch an artifact file |

---

### WebSocketManager

`dut-dashboard/backend/app/websocket/ws_manager.py`

- `connect(ws)` — accepts and registers a client
- `disconnect(ws)` — removes client; dead clients pruned on next broadcast
- `broadcast(event)` — async; sends JSON to all connected clients
- `emit_from_thread(event)` — thread-safe bridge; uses `asyncio.run_coroutine_threadsafe` so the Task is retained by the event loop

---

### SnapshotStore

`dut-dashboard/backend/app/services/snapshot_store.py`

Appends each completed snapshot as a JSONL record:

```
{"test_count": 1, "device_ts": "2026-05-17 09:00:00", "cpu": {…}, "memory": {…}, "wifi_clients": {…}}
{"test_count": 2, …}
```

Default path: `logs/snapshots.jsonl`

---

## WebSocket Event Reference

All events are JSON objects over `ws://127.0.0.1:8765/ws`.

### Server → Client

#### `console_line_batch`

```json
{ "type": "console_line_batch", "lines": ["line1", "line2"] }
```

#### `snapshot_update`

```json
{
  "type": "snapshot_update",
  "snapshot": {
    "test_count": 42,
    "device_ts": "2026-05-17 09:46:01",
    "cpu": {
      "0": { "usr": 1.9, "sys": 2.9, "nic": 0.0, "idle": 80.6, "io": 0.0, "irq": 1.9, "sirq": 12.6 }
    },
    "wifi_clients": {
      "5G": { "total_size": 1, "clients": [{ "mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.9", "rssi": -42, "snr": 30 }] }
    }
  }
}
```

#### `snapshot_delta`

Partial update — frontend merges into the last full snapshot before re-rendering.

```json
{
  "type": "snapshot_delta",
  "delta": {
    "cpu": { "0": { "usr": 3.1, "sys": 1.5, "idle": 82.0, "nic": 0.0, "io": 0.0, "irq": 0.0, "sirq": 13.4 } }
  }
}
```

Optional delta fields: `test_count`, `device_ts`, `cpu`, `cpu_removed`, `wifi_clients`, `wifi_clients_removed`

#### `wifi_clients_update`

```json
{
  "type": "wifi_clients_update",
  "radio": "5G",
  "total_size": 2,
  "clients": [
    { "mac": "AA:BB:CC:DD:EE:FF", "ip": "192.168.1.9", "rssi": -42, "snr": 30 }
  ]
}
```

#### `memory_update`

Emitted each time a `Mem: XK used, YK free …` line is parsed (from `top` output).

```json
{ "type": "memory_update", "used_kb": 74616, "free_kb": 12504, "total_kb": 87120 }
```

#### `serial_disconnected`

```json
{ "type": "serial_disconnected" }
```

Emitted when the serial read loop exits unexpectedly (stop_event not set). Frontend retries up to 5 times (2 s apart) and shows an amber banner.

#### `replay_progress`

```json
{ "type": "replay_progress", "frame": 12, "total": 120 }
```

#### `replay_done`

```json
{ "type": "replay_done", "total": 120 }
```

#### `replay_stopped`

```json
{ "type": "replay_stopped" }
```

#### `tool_result`

```json
{ "type": "tool_result", "request_id": "abc123", "ok": true, "result": { … } }
```

---

## Frontend Components

### `Dashboard.tsx`

Main page. Owns all state and the WebSocket handler.

| State | Type | Fed by |
|-------|------|--------|
| `lines` | `string[]` (max 1000) | `console_line_batch` |
| `cpuHistory` | `CpuPoint[]` (max 60) | `snapshot_update` |
| `cpuCoreKeys` | `string[]` | derived from snapshot cpu keys |
| `memHistory` | `MemPoint[]` (max 60) | `memory_update` |
| `clientsByRadio` | `Record<2G\|5G\|6G, WifiClient[]>` | `wifi_clients_update` |

### `CpuChart.tsx`

Recharts `LineChart`. One line per CPU core. Y-axis: 0–100%.
Props: `data: CpuPoint[]`, `coreKeys: string[]`

### `MemoryChart.tsx`

Recharts `LineChart`. Two lines: **Used** (red) and **Free** (green). Values in MB.
Shows a placeholder when `data` is empty: *"run `top` on the DUT to populate"*.
Props: `data: MemPoint[]`

`MemPoint`: `{ ts: string; used_mb: number; free_mb: number; total_mb: number }`

### `ClientsPanel.tsx`

Wi-Fi client table grouped by radio band (2G / 5G / 6G).

### `ConsolePanel.tsx`

Serial terminal. Features:
- Scrollback buffer (last 1000 lines, memoized join; ANSI escape sequences stripped)
- Stick-to-bottom auto-scroll; releases on manual scroll up
- Inline command input + **Edit in Popup** (CodeMirror + vim mode)
- Global `Ctrl+C` / `Cmd+C` sends `` to DUT (skips if text is selected)
- `canSend` prop disables Send / Edit-in-Popup when serial is not open

### `SnapshotReplayPanel.tsx`

Snapshot file browser and playback controller.
- Lists saved `.jsonl` files with name, frame count, size, and timestamp
- Per-file download button
- Speed input (ms per frame) + Start / Stop buttons
- Progress bar driven by `replay_progress` events

---

## Tests

```bash
# from repo root
.venv/bin/python -m pytest dut-dashboard/backend/tests/ -v
```

```bash
# TypeScript type check
cd dut-dashboard/frontend
npx tsc --noEmit
```

Current test coverage: 42 tests across 3 files:

| File | Tests | Scope |
|------|-------|-------|
| `test_serial_download_workflow.py` | 6 | log download + analyzer path |
| `test_sysmon_parser.py` | 29 | SNAPSHOT_RE / CPU_RE / MEM_RE patterns + `feed()` integration |
| `test_snapshot_api.py` | 7 | snapshot `safe_name` validation + `list_snapshots` logic |

---

## Standalone Tools

### `tools/analyzer3.py`

Offline log analysis. Expects to be run with `cwd` set to the session directory containing the log file.
Produces CPU and memory CSVs and plots.

### `tools/log_event_detector.py`

Batch anomaly scanner across multiple log files.

```bash
python3 tools/log_event_detector.py --root . --output log_events.json
```

Output: `log_events.json` with merged event detections. See `tools/README_log_event_detector.md` for rule details.
