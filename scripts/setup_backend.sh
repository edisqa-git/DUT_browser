#!/bin/bash
set -e

cd dut-dashboard/backend

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn

echo "[OK] Backend environment ready"
