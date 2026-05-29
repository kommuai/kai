---
version: "1.0"
agent_name: Kai
agent_workspace_root: agent_workspace
rag_source: 02_knowledge/faq/master_faq.md
session_store:
  backend: sqlite
  env_path_var: SESSION_DB_PATH
  env_fallback_var: DB_PATH
  default_relative: data/sessions.db
  docker_container_path: /data/sessions.db
sop_sync:
  markers:
    start: "<!-- sop-sync:start -->"
    end: "<!-- sop-sync:end -->"
  optional_env_url: SOP_DOC_URL
---

# Kai agent workspace (dev fallback)

Prefer **`KAI_HOME`** at a tenant directory (`kai-tenant-<slug>/`) with `workspace.yaml`, `system_prompt.md`, and `knowledge/master_faq.md`.

- **02_knowledge/faq/** — Legacy default `master_faq.md` when env points here.
- **compiled/** — Optional `kb_chunks.jsonl` (rebuilt on engine startup).

Session history is in SQLite (`data/sessions.db`), not in this tree.
