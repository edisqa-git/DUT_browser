# DUT Browser

Real-time QA monitoring desktop tool for DUT (Device Under Test) devices.
Streams serial console output, parses sysmon data live, detects crashes, and plots CPU / memory history.

**Stack:** Tauri desktop shell · React + TypeScript + Vite frontend · FastAPI + Python backend

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Tauri Desktop Shell                │
│  (manages backend process lifecycle + native window) │
└────────────────────┬────────────────────────────────┘
                     │ spawns
         ┌───────────▼───────────┐
         │   FastAPI Backend     │  127.0.0.1:8765
         │                       │
         │  SysMonParser         │  parses serial stream
         │  ├─ CPU_RE            │  → snapshot_update / snapshot_delta
         │  ├─ MEM_RE            │  → memory_update
         │  ├─ CLIENT_MARKER_RE  │  → wifi_clients_update
         │  └─ SNAPSHOT_RE       │  → test boundary detection
         │                       │
         │  TOOL_REGISTRY        │  @tool decorator dispatch
         │  ├─ serial_tools      │  open / close / send / replay
         │  └─ analyzer_tools    │  run analyzer / download zip
         │                       │
         │  WebSocketManager     │  broadcast to all connected UIs
         └───────────┬───────────┘
                     │ WebSocket  ws://127.0.0.1:8765/ws
         ┌───────────▼───────────┐
         │   React Frontend      │
         │                       │
         │  Dashboard            │
         │  ├─ CpuChart          │  live CPU core % (Recharts)
         │  ├─ MemoryChart       │  live used / free MB (Recharts)
         │  ├─ ClientsPanel      │  Wi-Fi clients per radio (2G/5G/6G)
         │  ├─ ConsolePanel      │  serial terminal + vim popup editor
         │  └─ CriticalCrash     │  kernel panic / Q6 crash / watchdog alerts
         └───────────────────────┘
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Node.js | 20+ |
| Python | 3.11+ |
| Rust + Cargo | latest stable (for Tauri packaging only) |

---

## One-Time Setup

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm install --prefix dut-dashboard/frontend
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm install --prefix dut-dashboard/frontend
```

---

## Run

### Development (hot-reload)

```bash
npm run dev
```

Opens the Tauri window. Backend starts automatically on `127.0.0.1:8765`. Frontend proxies API calls via Vite.

### Packaged Desktop App

```bash
npm run package
```

Produces a native installer under `desktop/src-tauri/target/release/bundle/`. QA users launch the installer — no terminal needed.

---

## Features

### Serial Console

- Connect to a DUT via serial port — dropdown auto-detects pyserial ports; manual override input with autocomplete (sourced from `/dev/cu.*` glob scan)
- Dropdown auto-refreshes every 3 seconds while in Serial mode (silent, no flicker)
- Replay mode: feed a saved `.log` file at configurable speed for offline testing
- Full-featured terminal with vim popup editor for long/multi-line commands
- `Ctrl+C` global shortcut sends interrupt to DUT
- ANSI escape sequences stripped before display
- Auto-reconnect on unexpected disconnect: up to 5 retries (2 s apart) with amber status banner

### Snapshot Replay

- Replay a previously saved `snapshots.jsonl` from the Snapshot Replay panel
- Configurable playback speed (ms per frame)
- Progress bar shows current frame / total; Start / Stop controls
- Each frame re-broadcasts `snapshot_update` (and `memory_update` when memory data is present) — all live charts update in sync

### Live Charts

| Chart | Data Source | Max History |
|-------|-------------|-------------|
| CPU Usage | `CPU0…N` lines parsed from sysmon | 60 snapshots |
| Memory Usage | `Mem: XK used, YK free` from `top` output | 60 data points |

> To populate the Memory chart: click **Run top** in the CPU Monitor Commands panel. The chart fills in automatically while `top` is running on the DUT.

### Wi-Fi Clients Panel

Parses `--- CLIENTS Radio=2G/5G/6G ---` markers and the JSON payload that follows.
Shows connected client list per radio band with MAC, IP, RSSI, SNR.

### Critical Crash Detection

Scans every incoming console line for:
- `kernel panic`
- `Q6 crash`
- `watchdog` (reset / bite / timeout)
- Custom keywords (lock in via the input field)

New detections show a badge count. Click **Mark as seen** to acknowledge.

### Log Download + Analysis

Click **Download DUT Log** to trigger:

1. **Short log (< 100 lines, no TOP)** → returns the raw `.log` directly.
2. **Full log** → backend runs `tools/analyzer3.py`, packages all artifacts into a `.zip`:
   - `*cpu_usage.csv` / `*cpu_usage_plot.png`
   - `*memory.csv` / `*memavailable_plot.png`
   - `*slab_plot.png` / `*sunreclaim_plot.png`
   - `*cpu_spike_report.txt`

### Auto Update Check

On startup the app queries GitHub releases (falls back to tags). Shows a banner when a newer version is available with a link to the releases page.

---

## WebSocket Event Reference

All events flow over `ws://127.0.0.1:8765/ws` as JSON.

| Event type | Direction | Payload fields |
|------------|-----------|----------------|
| `console_line_batch` | server → client | `lines: string[]` |
| `snapshot_update` | server → client | `test_count`, `device_ts`, `cpu: {id: CpuCore}`, `wifi_clients` |
| `snapshot_delta` | server → client | partial update; client merges into last snapshot |
| `wifi_clients_update` | server → client | `radio: "2G"\|"5G"\|"6G"`, `total_size`, `clients` |
| `memory_update` | server → client | `used_kb`, `free_kb`, `total_kb` |
| `serial_disconnected` | server → client | serial read loop exited unexpectedly (triggers auto-reconnect) |
| `replay_progress` | server → client | `frame: number`, `total: number` |
| `replay_done` | server → client | `total: number` |
| `replay_stopped` | server → client | — (stop was requested) |
| `{"tool": "...", "params": {}}` | client → server | TOOL_REGISTRY dispatch; response: `{"type":"tool_result", ...}` |

**CpuCore fields:** `usr`, `sys`, `nic`, `idle`, `io`, `irq`, `sirq` (all `number`, percent)

---

## Repository Layout

```
DUT_browser/
├── VERSION                        # single source of truth for version (e.g. 1.0.0)
├── release.json                   # GitHub repo / releases page metadata
├── requirements.txt               # Python deps (shared)
├── package.json                   # root npm scripts (dev / package)
├── update.sh / update.ps1        # one-command updater for macOS/Windows
│
├── desktop/
│   ├── src-tauri/                 # Tauri Rust shell (window, backend spawner)
│   └── resources/runtime/        # bundled Python runtime for packaged app
│
├── scripts/
│   ├── bootstrap.sh               # first-run setup helper
│   └── build_backend.py           # freezes Python backend for packaging
│
└── dut-dashboard/
    ├── backend/
    │   └── app/
    │       ├── main.py            # FastAPI app + lifespan
    │       ├── config.py          # ports, paths
    │       ├── versioning.py      # reads VERSION + release.json
    │       ├── api/               # HTTP route handlers (serial, analyzer, health)
    │       ├── parser/
    │       │   ├── sysmon_parser.py  # CPU / memory / snapshot / clients parser
    │       │   └── models.py         # SnapshotModel (Pydantic)
    │       ├── serial/            # serial read loop + replay
    │       ├── services/
    │       │   ├── analyzer_service.py   # runs analyzer3.py, zips artifacts
    │       │   ├── snapshot_store.py     # JSONL snapshot persistence
    │       │   └── version_service.py    # GitHub update check + caching
    │       ├── tools/
    │       │   ├── registry.py      # @tool decorator + dispatch()
    │       │   ├── serial_tools.py  # open/close/send/replay tools
    │       │   └── analyzer_tools.py
    │       └── websocket/
    │           └── ws_manager.py    # broadcast + thread-safe emit
    │
    ├── frontend/
    │   └── src/
    │       ├── api/
    │       │   ├── rest.ts          # typed HTTP client
    │       │   └── websocket.ts     # WS connect + snapshot delta merge
    │       ├── components/
    │       │   ├── CpuChart.tsx     # Recharts CPU line chart
    │       │   ├── MemoryChart.tsx  # Recharts memory line chart
    │       │   ├── ClientsPanel.tsx # Wi-Fi clients table
    │       │   └── ConsolePanel.tsx # terminal + vim popup editor
    │       └── pages/
    │           └── Dashboard.tsx    # main page — wires all state + WS handler
    │
    └── tools/
        ├── analyzer3.py             # offline log analysis (CPU + memory plots)
        └── log_event_detector.py    # batch anomaly scanner
```

---

## Sanity Checks

```bash
# Backend tests
cd /path/to/DUT_browser
.venv/bin/python -m pytest dut-dashboard/backend/tests/ -v

# Frontend type check
cd dut-dashboard/frontend
npx tsc --noEmit
```

---

## Update (existing installation)

**macOS / Linux**

```bash
./update.sh
```

**Windows**

```powershell
.\update.ps1
```

The updater: aborts on dirty worktree → pulls latest branch + tags → rebuilds Python deps in a temp venv → reinstalls Node deps → promotes new environment atomically.
