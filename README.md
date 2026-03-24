# Kai Kommu ChatBot  

An AI-powered assistant for **Kommu**.  
Designed to handle customer and internal support queries with **speed, accuracy, and bilingual support (English & Malay)**.

---

##  Features

- **Router-first Haystack runtime:** Canonical FAQ/workflow data compiled from `agent_workspace/02_knowledge/faq/master_faq.md` into `agent_workspace/compiled/*`  
- **Agent workspace:** Markdown-first core prompts, FAQ, and v2 skill metadata under `agent_workspace/` (see `agent_workspace/README.md` and `00_manifest.md`)  
- **Google Sheets Integration:** Warranty & stock lookups  
- **Multi-language:** English ↔ Bahasa Melayu auto-switching  
- **WhatsApp Integration (via Twilio)**  
- **Daily Auto-Refresh** of compiled runtime knowledge + warranty cache  
- **Debug, Health & Benchmark Tools** to test coverage and performance  

---

##  Setup

### 1) Clone & prepare environment

```bash
# Clone
git clone https://github.com/kommuai/kai.git
cd kai

# (Recommended) Python 3.10–3.12
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### 2) Configure environment

Create a `.env` file:

```bash
# Minimal required (examples)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
SOP_DOC_URL=https://docs.google.com/document/d/xxxxxxxxxxxxxxxxxxxx
WARRANTY_CSV_URL=https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv
EXTRA_WARRANTY_CSV_URL=https://docs.google.com/spreadsheets/d/e/.../pub?gid=0&single=true&output=csv
```

Or hardcode in `config.py`.

### 3) Run locally

```bash
# App (FastAPI + uvicorn)
uvicorn app:app --host 0.0.0.0 --port 8000
# Health check
curl http://127.0.0.1:8000/docs
```

### 4) Run with Docker

```bash
docker compose up -d
# health
curl http://127.0.0.1:6090/
```

Docker mounts `./agent_workspace` at `/app/agent_workspace`. Session SQLite stays on `./data` → `/data/sessions.db` (see `00_manifest.md` frontmatter `session_store`).

**Env (optional):**

- `AGENT_WORKSPACE` — path to workspace root (default: `agent_workspace` next to `app.py`)
- `MASTER_FAQ_PATH` — override FAQ markdown path
- `CONTEXT_REGISTRY_YAML` — override path to `agent_workspace/04_context/context_registry.yaml`

Exposed endpoints (in Docker):

- `http://127.0.0.1:6090/agent/message`
- `http://127.0.0.1:6090/v2/agent/message`
- `http://127.0.0.1:6090/v2/agent/query`
- `http://127.0.0.1:6090/v2/agent/search`
- `http://127.0.0.1:6090/admin/refresh-sop`
- `http://127.0.0.1:6090/admin/reset_memory`

Route mode (trace label + future strategy toggle):

- `KAI_ROUTE_MODE=hybrid` (default) — try skills after session/handover gate, then `main_conversation` if no skill succeeds
- `KAI_ROUTE_MODE=agent_first` — same router ordering today; reserved for stricter agent preference later
- `KAI_ROUTE_MODE=stable_only` — treated as `hybrid` (legacy env value)

Both `POST /agent/message` and `POST /v2/agent/message` use the same active handler (trace fields always included). Legacy shadow execution has been removed.

Model backend (default DeepSeek, model-agnostic adapter):

- `KAI_LLM_PROVIDER=deepseek` (default)
- `KAI_LLM_MODEL=<provider_model_name>`
- `KAI_LLM_BASE_URL=<openai_compatible_base_url>`
- `KAI_LLM_API_KEY=<provider_api_key>`

Canonical runtime artifacts are compiled at startup into `agent_workspace/compiled/` (`intents.json`, `workflows.json`, `kb_chunks.jsonl`, `tool_policies.json`).

Haystack/Qdrant/rerank/observability toggles:

- `KAI_QDRANT_ENABLED=1`
- `KAI_QDRANT_URL=http://127.0.0.1:6333`
- `KAI_QDRANT_COLLECTION=kai_support`
- `KAI_RERANKER_BACKEND=provider`
- `KAI_GUARDRAILS_ENABLED=1`
- `KAI_TRACING_ENABLED=1`
- `KAI_CHATWOOT_ENFORCE_LIVE_HANDOVER=1` (on escalation, force Chatwoot conversation switch to live-agent mode; fail-closed on switch failure)
- `KAI_SOP_WRITEBACK_ENABLED=1` (on FAQ publish, write updated `master_faq.md` back to Google Docs)
- `GOOGLE_DOCS_SOP_DOC_ID=<google_doc_id>` (target SOP/FAQ Google Doc for writeback)

Machine-agent auth for `/v2/agent/*`:

- `KAI_SERVICE_KEYS=internal-key:public_info.read|repo.read|media.read`
- `KAI_GITHUB_TOKEN=<optional_github_token_for_higher_rate_limits>`
- Repo-reader scope is hard-locked to public repos under `https://github.com/kommuai`.

Admin endpoint auth for `/admin/*`:

- `ADMIN_TOKEN=<strong-admin-token>`
- Send `x-admin-token: <ADMIN_TOKEN>` header with admin requests.

---

##  Debug & Health Checks

### A) One-shot full system check (CLI)

```bash
python debug_check.py
```

### E) Runtime evaluation harness (offline)

```bash
python tools/eval_support_runtime.py
```

### F) FAQ approval CLI

```bash
# API mode (default)
python tools/faq_approval_cli.py --base-url http://127.0.0.1:8000 poll
python tools/faq_approval_cli.py list --status pending_review
python tools/faq_approval_cli.py approve 12
python tools/faq_approval_cli.py publish 12

# Local mode (no API server, direct SQLite/functions)
python tools/faq_approval_cli.py --mode local list --status pending_review
python tools/faq_approval_cli.py --mode local approve 12
python tools/faq_approval_cli.py --mode local publish 12
```

Expected output:

```
[SOP-DOC] Loaded FAQ content and refreshed compiled knowledge artifacts.
[WARRANTY] Loaded total rows: 476; 308 unique dongle ids; 98 phone/serial keys.
[HEALTH] All templates OK.
[LANG] Detector ready (EN/BM).
[OK] System is ready.
```

### B) Runtime checks (HTTP)

```bash
# Trigger SOP + warranty refresh manually
curl -X POST http://127.0.0.1:6090/admin/refresh-sop \
  -H "x-admin-token: <ADMIN_TOKEN>"

# Reset one conversation memory
curl -X POST "http://127.0.0.1:6090/admin/reset_memory?user_id=+6000000000" \
  -H "x-admin-token: <ADMIN_TOKEN>"
```

### C) Test message route manually

```bash
curl -X POST http://127.0.0.1:6090/agent/message \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+6000000000","content":"Hi, what cars are supported?"}'
```

### D) Test machine-agent query (A2A)

```bash
curl -X POST http://127.0.0.1:6090/v2/agent/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: internal-key" \
  -d '{"user_id":"agent-client","query":"What is KommuAssist?","lang":"EN"}'
```

---

##  Daily Auto-Refresh

Script path: `/home/deployment-user/bin/kai-refresh.sh`

Cron (every day 9:00 AM):

```bash
0 9 * * * /home/deployment-user/bin/kai-refresh.sh >> /home/deployment-user/kai-refresh.log 2>&1
```

Run manually:

```bash
/home/deployment-user/bin/kai-refresh.sh
tail -n 200 /home/deployment-user/kai-refresh.log
```

---

##  How the Chatbot Works (High-Level)

The diagram below illustrates the **end-to-end workflow**. A chat message hits `POST /agent/message` or `POST /v2/agent/message` (same logic). **Pre-router** preserves Chatwoot handover/frozen behavior first. Then runtime follows deterministic router-first flow with retrieval/rerank/tool/escalation decisions.

```mermaid
flowchart TD
    A[User sends message] --> C[FastAPI /agent/message or /v2/agent/message]
    C --> D[PreRouter handover frozen resume]
    D -->|Immediate| E[Response + trace]
    D -->|Continue| F[IntentRouter confidence gate]
    F -->|Known high confidence| E
    F -->|Needs retrieval| G[Haystack retrieve plus rerank plus grounded answer]
    G --> E


   
```

---

##  Repo Layout

```bash
├── app.py                    # FastAPI app
├── config.py                 # Config + constants
├── data/sop/                 # SOP docs
├── support_runtime/          # Active runtime (router/retrieval/graph/tools)
├── tools/                    # Audits & benchmarks
├── logs/                     # Runtime & benchmark logs
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Current Architecture Files

Use these as the primary runtime map:

- Runtime/API:
  - `app.py`
  - `api/v2/agent_message.py`
  - `api/v2/agent_query.py`
  - `support_runtime/`
- Chatwoot parity/session layer:
  - `services/kai_service.py`
  - `session_state.py`
- Knowledge + eval:
  - `agent_workspace/02_knowledge/faq/master_faq.md`
  - `agent_workspace/compiled/`
  - `tools/eval_support_runtime.py`
  - `tests/test_pre_router.py`
  - `tests/test_chatwoot_parity_contract.py`
  - `tests/test_support_runtime.py`

Legacy items that were moved are documented in:

- `docs/architecture/current_architecture_map.md`
- `archive_legacy/`
- `ARCHIVE_LEGACY.md`

---



##  Troubleshooting

- `curl 127.0.0.1:8000` fails → ensure `uvicorn app:app` is running.  
- In Docker, use **6090** not 8000.  
- SOP outdated → run `python debug_check.py`.  
- Always “live agent” → call `/admin/reset_memory?user_id=<phone_number>`.  
- Wrong language → check pinned language.  
