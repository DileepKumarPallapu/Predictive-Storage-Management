#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

echo "=========================================================="
echo "AEGISSTOR — Storage Resilience Intelligence Platform"
echo "=========================================================="

# Start backend
echo "[1/2] Launching Backend on http://localhost:8000..."
(cd "$DIR/backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# Start frontend
echo "[2/2] Launching Frontend on http://localhost:5173..."
(cd "$DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
