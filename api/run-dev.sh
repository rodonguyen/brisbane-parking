#!/usr/bin/env bash
# Start API (8080) then Vite (5173). Run from repo root after ingest.
set -euo pipefail
cd "$(dirname "$0")"
python -m py.server &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
cd ../web
npm run dev -- --host 127.0.0.1 --port 5173
