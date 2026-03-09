# AP6_monitor

Local DUT monitoring dashboard for AP6 telemetry using FastAPI + React.

## Features

- Serial console control and realtime line streaming
- SysMon snapshot parsing for CPU and Wi-Fi clients
- Realtime dashboard updates over WebSocket
- Offline log analysis using `analyzer3.py`
- CSV artifact download (`cpu_usage.csv`, `memory.csv`)

## Repository Structure

```text
.
├── dut-dashboard/
│   ├── backend/
│   ├── frontend/
│   ├── tools/
│   ├── scripts/
│   └── logs/
├── spec.md
└── task.md
```

## Quick Start

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd dut-dashboard/backend
python3 -m app.main
```

### Frontend

```bash
cd dut-dashboard/frontend
npm install
npm run dev
```

Dashboard URL (local): `http://127.0.0.1:5173`
Dashboard URL (same LAN): `http://<your-server-ip>:5173`

## API Summary

- `POST /api/serial/open`
- `POST /api/serial/close`
- `POST /api/serial/send`
- `POST /api/analyzer/run`
- `GET /api/download/{file}`
- `WS /ws` event types:
  - `console_line`
  - `wifi_clients_update`
  - `snapshot_update`

## Typical Flow

1. Start backend and frontend.
2. Open serial mode or replay mode:
```bash
curl -X POST http://127.0.0.1:8000/api/serial/open \
  -H 'Content-Type: application/json' \
  -d '{"mode":"serial","port":"/dev/ttyUSB0","baudrate":115200}'
```
3. Watch console and charts update in realtime.
4. Run offline analyzer:
```bash
curl -X POST http://127.0.0.1:8000/api/analyzer/run \
  -H 'Content-Type: application/json' \
  -d '{"log_path":"logs/session.log"}'
```
5. Download outputs:
```bash
curl -L -o cpu_usage.csv http://127.0.0.1:8000/api/download/cpu_usage.csv
curl -L -o memory.csv http://127.0.0.1:8000/api/download/memory.csv
```

## Documentation

For detailed event contracts and milestone behavior, see:

- `dut-dashboard/README.md`
