# agent_workspace (dev fallback only)

Production tenants use **`KAI_HOME`** pointing at `kai-tenant-<slug>/` under your tenants root.

This directory is a **minimal local fallback** when `KAI_HOME` is unset (tests, legacy Docker mounts). It is not the ReAct agent's runtime brain — only files under the active tenant workspace are.

| Path | Role |
|------|------|
| `02_knowledge/faq/master_faq.md` | Legacy default FAQ when `MASTER_FAQ_PATH` points here |
| `compiled/kb_chunks.jsonl` | Optional precompiled chunks (regenerated on startup) |

Session SQLite lives in `data/sessions.db` (or tenant `data/sessions.db`), not here.

Set `KAI_HOME=/path/to/kai-tenant-<slug>` for Studio and WhatsApp.
