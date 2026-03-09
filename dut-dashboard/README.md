# DUT Local Monitoring Dashboard (Milestone 4)

Milestone 4 implements:
- realtime `console_line` streaming
- snapshot boundary + CPU parsing into `snapshot_update`
- clients marker + JSON parsing into `wifi_clients_update`
- analyzer integration via `POST /api/analyzer/run`
- artifact download via `GET /api/download/{file}`

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
