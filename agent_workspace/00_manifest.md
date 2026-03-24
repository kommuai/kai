---
version: "1.0"
agent_name: Kai
agent_workspace_root: agent_workspace
rag_source: 02_knowledge/faq/master_faq.md
context_registry: 04_context/context_registry.yaml
session_store:
  backend: sqlite
  env_path_var: SESSION_DB_PATH
  env_fallback_var: DB_PATH
  default_relative: data/sessions.db
  docker_container_path: /data/sessions.db
  compose_volume_note: "Host ./data is mounted to /data; SESSION_DB_PATH=/data/sessions.db in docker-compose."
sop_sync:
  markers:
    start: "<!-- sop-sync:start -->"
    end: "<!-- sop-sync:end -->"
  optional_env_url: SOP_DOC_URL
---

# Kai agent workspace

Human-editable **content** for the Kommu chatbot: core tone and safety rules, FAQ knowledge, and skill metadata. Runtime code lives in the parent `kai-main` package.

- **01_core** — Identity and safety text loaded into the LLM system prompt (plus any legacy template fallbacks).
- **02_knowledge** — `master_faq.md` is the canonical FAQ for RAG indexing. The SOP Google Doc sync overwrites only the region between `<!-- sop-sync:start -->` and `<!-- sop-sync:end -->`.
- **03_skills** — One folder per skill: `skill.md` (YAML frontmatter + description) and `handler.py` (re-exports the Python skill class).
- **04_context** — Machine-oriented context registry YAML (not SQLite session rows).

Session and conversation history remain in **SQLite**; see `session_store` above.
