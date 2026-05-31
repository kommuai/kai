#!/bin/sh
set -e

if [ -z "${SHADOU_HOME:-}" ]; then
  echo "SHADOU_HOME is not set. Mount a workspace volume and set SHADOU_HOME=/shadou-home" >&2
  exit 1
fi

if [ ! -d "$SHADOU_HOME" ]; then
  echo "SHADOU_HOME directory missing: $SHADOU_HOME" >&2
  exit 1
fi

if [ -f "${SHADOU_ENV_FILE:-$SHADOU_HOME/.env}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${SHADOU_ENV_FILE:-$SHADOU_HOME/.env}"
  set +a
fi

COMPILED="$SHADOU_HOME/compiled/kb_chunks.jsonl"
if [ ! -f "$COMPILED" ]; then
  echo "Compiling FAQ knowledge base into $COMPILED ..."
  python3 -m shadou.cli compile
fi

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}" --timeout-graceful-shutdown 30
