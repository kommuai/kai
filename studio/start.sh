#!/usr/bin/env bash
# Start both backend and frontend dev servers
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "==> Starting Shadou Admin UI"
echo "    Backend  →  http://localhost:8080"
echo "    Frontend →  http://localhost:5173"
echo ""

# Backend (PYTHONPATH = monorepo root for shadou package)
(
  cd "$ROOT/backend"
  export PYTHONPATH="${ROOT}/..${PYTHONPATH:+:$PYTHONPATH}"
  uvicorn main:app --host 0.0.0.0 --port 8080 --reload &
  echo "Backend PID: $!"
)

# Frontend
(
  cd "$ROOT/frontend"
  npm run dev &
  echo "Frontend PID: $!"
)

wait
