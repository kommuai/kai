#!/bin/sh
set -e

if [ -z "${KAI_HOME:-}" ]; then
  echo "KAI_HOME is not set. Mount a workspace volume and set KAI_HOME=/kai-home" >&2
  exit 1
fi

if [ ! -d "$KAI_HOME" ]; then
  echo "KAI_HOME directory missing: $KAI_HOME" >&2
  exit 1
fi

if [ -f "${KAI_ENV_FILE:-$KAI_HOME/.env}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${KAI_ENV_FILE:-$KAI_HOME/.env}"
  set +a
fi

COMPILED="$KAI_HOME/compiled/kb_chunks.jsonl"
if [ ! -f "$COMPILED" ]; then
  echo "Compiling FAQ knowledge base into $COMPILED ..."
  python3 -m kai.cli compile
fi

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}" --timeout-graceful-shutdown 30
