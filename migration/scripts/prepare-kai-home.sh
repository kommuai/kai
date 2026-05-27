#!/usr/bin/env bash
# Port Kommu legacy agent_workspace + data into KAI_HOME layout (for full refactor tenant mode).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KAI_HOME="${1:-$HOME/.kai}"
SRC_WS="$ROOT/agent_workspace"
mkdir -p "$KAI_HOME"/{knowledge/learn_queue,compiled,data/sop,tools/plugins,skills}
cp -f "$SRC_WS/02_knowledge/faq/master_faq.md" "$KAI_HOME/knowledge/master_faq.md"
[ -f "$SRC_WS/02_knowledge/faq/agent_learnt_faq.md" ] && \
  cp -f "$SRC_WS/02_knowledge/faq/agent_learnt_faq.md" "$KAI_HOME/knowledge/learnt_faq.md" || true
[ -d "$SRC_WS/02_knowledge/faq/learn_queue" ] && \
  cp -R "$SRC_WS/02_knowledge/faq/learn_queue/." "$KAI_HOME/knowledge/learn_queue/" || true
[ -d "$ROOT/data" ] && cp -R "$ROOT/data/." "$KAI_HOME/data/" || true
[ -f "$ROOT/.env" ] && cp -f "$ROOT/.env" "$KAI_HOME/.env" || true
if [ ! -f "$KAI_HOME/workspace.yaml" ]; then
  cp -f "$(dirname "$ROOT")/kai-main-refactor/templates/workspace/generic/workspace.yaml" "$KAI_HOME/workspace.yaml" 2>/dev/null || true
fi
echo "Prepared KAI_HOME at $KAI_HOME"
