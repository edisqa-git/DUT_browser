#!/bin/bash
set -e

echo "=== Setup frontend ==="
npm install
npm install --prefix dut-dashboard/frontend

echo "=== Setup backend ==="
bash scripts/setup_backend.sh

echo "=== Done ==="
