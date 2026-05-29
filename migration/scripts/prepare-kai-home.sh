#!/usr/bin/env bash
# Prepare KAI_HOME from a tenant pack (sibling kai-tenant-* repo or explicit path).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KAI_HOME="${1:-$HOME/.kai}"
TENANT_SRC="${2:-$(dirname "$ROOT")/kai-tenant-kommu}"
if [ ! -d "$TENANT_SRC" ]; then
  echo "Tenant source not found: $TENANT_SRC" >&2
  echo "Usage: $0 [KAI_HOME] [tenant_pack_dir]" >&2
  exit 1
fi
mkdir -p "$KAI_HOME"/{knowledge/learn_queue,compiled,data/sop,tools/plugins,skills}
rsync -a --exclude='.git' "$TENANT_SRC/" "$KAI_HOME/"
[ -d "$ROOT/data" ] && cp -R "$ROOT/data/." "$KAI_HOME/data/" || true
[ -f "$ROOT/.env" ] && cp -f "$ROOT/.env" "$KAI_HOME/.env" || true
echo "Prepared KAI_HOME at $KAI_HOME from $TENANT_SRC"
