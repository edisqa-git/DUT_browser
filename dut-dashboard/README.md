# DUT Local Monitoring Dashboard

DEPRECATED: this file documents the legacy split frontend/backend workflow and remains only as subsystem reference material. Product onboarding now starts at the repository root `README.md`.

Milestone 4 implements:
- realtime `console_line` streaming
- snapshot boundary + CPU parsing into `snapshot_update`
- clients marker + JSON parsing into `wifi_clients_update`
- analyzer integration via `POST /api/analyzer/run`
- artifact download via `GET /api/download/{file}`
- frontend `Critical Crash` panel with live keyword detection (`kernel panic` / `Q6 crash` / `watchdog`)

## Run Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cd backend
python3 -m app.main
```

## Run Frontend

```bash
cd dut-dashboard/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` (local) or `http://<your-server-ip>:5173` (LAN).

## Frontend Console Controls

- `CPU Monitor Commands` provides:
- `Memory Info`: sends `top`
- `Stop`: sends Ctrl+C to stop the running foreground command
- `Download DUT Log` calls `GET /api/serial/logs/{file_name}` and chooses one of two backend paths:
- direct log download (short log without `TOP`)
- full analyzer bundle (`.zip`) with CPU and memory artifacts
- `Critical Crash` panel shows live matched critical crash lines from console stream:
- keeps recent entries in view
- shows `New <count>` badge for unseen entries
- includes `Mark as seen` to clear unseen count

## Download DUT Log + CPU/Memory Plots Mechanism

Endpoint:

```bash
GET /api/serial/logs/{file_name}
```

Decision logic:

1. If the log file is shorter than 100 lines and contains no `TOP` command:
- backend returns the original `.log` directly (`text/plain`)
- analyzer is skipped
- frontend notification (bottom-right): `The log file is ready.` (blue)

2. Otherwise:
- backend creates a session directory in `logs/`:
  `dut-session-YYYYMMDD-HHMMSS`
- copies the requested log into that directory
- runs `tools/analyzer3.py` with `cwd` set to the session directory
- keeps all generated artifacts in that same directory (`.csv`, `.png`, `.txt`, etc.)
- zips the full session directory to:
  `dut-session-YYYYMMDD-HHMMSS.zip`
- returns the zip file to frontend (`application/zip`)
- frontend notification (bottom-right):
  `DUT CPU and Memory usage plots are created.` (green)

Typical analyzer outputs in the session directory:
- `*cpu_usage.csv`
- `*memory.csv`
- `*cpu_usage_plot.png`
- `*memavailable_plot.png`
- `*slab_plot.png`
- `*sunreclaim_plot.png`
- `*cpu_spike_report.txt`

Error handling highlights:
- invalid filename -> `400`
- log file missing -> `404`
- log too short for analysis path -> `422`
- analyzer/zip/runtime failures -> `500` with readable error detail

## Serial / Replay

Serial mode:

```bash
curl -X POST http://127.0.0.1:8000/api/serial/open \
  -H 'Content-Type: application/json' \
  -d '{"mode":"serial","port":"/dev/ttyUSB0","baudrate":115200}'
```

Replay mode:

```bash
curl -X POST http://127.0.0.1:8000/api/serial/open \
  -H 'Content-Type: application/json' \
  -d '{"mode":"replay","replay_path":"logs/sample.log","replay_interval_ms":100}'
```

## Analyzer Example Flow

1. Prepare a log file at `dut-dashboard/logs/session.log`.
2. Run analyzer:

```bash
curl -X POST http://127.0.0.1:8000/api/analyzer/run \
  -H 'Content-Type: application/json' \
  -d '{"log_path":"logs/session.log"}'
```

Example response includes produced files, including `cpu_usage.csv` and `memory.csv`.

3. Download CSV outputs:

```bash
curl -L -o cpu_usage.csv http://127.0.0.1:8000/api/download/cpu_usage.csv
curl -L -o memory.csv http://127.0.0.1:8000/api/download/memory.csv
```

Generated artifacts are stored in `logs/analyzer_output/`.

## Log Event Detector Tool

Standalone detector script:

```bash
python3 tools/log_event_detector.py --root . --output log_events.json
```

Produces:
- `log_events.json`: merged abnormal event detection result for scanned logs
- `tools/example_output.json`: example output snapshot

Rule and usage details:
- `tools/README_log_event_detector.md`

## Event Contracts

`console_line`:

```json
{ "type": "console_line", "text": "..." }
```

`wifi_clients_update`:

```json
{
  "type": "wifi_clients_update",
  "radio": "5G",
  "total_size": 1,
  "clients": [{"mac":"AA:...","ip":"192.168.1.9","rssi":-42,"snr":30}]
}
```

`snapshot_update`:

```json
{
  "type": "snapshot_update",
  "snapshot": {
    "test_count": 1,
    "device_ts": "2026-02-26 09:46:01",
    "cpu": {"0": {"usr": 1.9, "sys": 2.9, "nic": 0.0, "idle": 80.6, "io": 0.0, "irq": 1.9, "sirq": 12.6}},
    "wifi_clients": {"5G": {"total_size": 1, "clients": [{"mac":"AA:..."}]}}
  }
}
```

## Sanity Checks

```bash
python3 -m compileall backend/app
cd frontend && npm run sanity
```
