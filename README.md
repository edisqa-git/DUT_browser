# DUT Browser

## Quick Start

```bash
bash scripts/bootstrap.sh
npm run dev
```

DUT Browser is now structured as a single-entry desktop application for QA and test workflows. The product entrypoint is the desktop shell, which owns backend startup, opens the UI, and checks for updates on startup.

## Status

- Primary architecture: Tauri desktop shell + React frontend + FastAPI backend
- Version source of truth: `VERSION`
- Release metadata: `release.json`
- Cross-platform update scripts: `update.sh`, `update.ps1`

## Deprecated

The legacy two-terminal workflow is deprecated. Starting `python3 -m app.main` in one terminal and `npm run dev` in another is no longer the supported product path because it creates startup races, confuses non-developer users, and blocks packaging.

## Prerequisites For Source Builds

- Node.js 20+
- Python 3.11+
- Rust toolchain for Tauri packaging

## One-Time Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
npm install --prefix dut-dashboard/frontend
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm install --prefix dut-dashboard/frontend
```

## Single Command Startup

Development:

```bash
npm run dev
```

Packaged app build:

```bash
npm run package
```

After packaging, QA and non-developer users launch the generated desktop executable only. They do not manually run Node or Python processes.

## Update Flow

macOS/Linux:

```bash
./update.sh
```

Windows:

```powershell
.\update.ps1
```

The updater aborts on a dirty worktree, pulls the latest branch with tags, rebuilds Python dependencies in a temporary virtualenv, reinstalls Node dependencies, and promotes the new environment only after successful completion.

## Repository Layout

```text
.
├── VERSION
├── CHANGELOG.md
├── release.json
├── package.json
├── update.sh
├── update.ps1
├── desktop/
│   ├── resources/
│   └── src-tauri/
├── scripts/
├── dut-dashboard/
│   ├── backend/
│   ├── frontend/
│   └── tools/
└── .github/workflows/
```

## Operational Notes

- Desktop launcher starts the backend on `127.0.0.1:8765`.
- Frontend uses Vite proxying in dev and direct localhost API access in packaged mode.
- Startup version checks query GitHub releases first, then tags, and show a clear user-visible message when a newer version exists.
