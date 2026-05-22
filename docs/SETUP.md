# Kai setup guide (non-technical)

Follow these steps to run a support chatbot for your business **without editing Python**.

## 1. Install

```bash
cd /path/to/kai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# If your tools.yaml enables Sheets, GitHub backlog, or OCR plugins:
# pip install -r requirements-optional.txt
```

See [PORTING.md](PORTING.md) for a full tenant checklist and [SECURITY.md](SECURITY.md) for production exposure.

## 2. Create your workspace

```bash
cp .env.example .env
# Edit .env: add KAI_LLM_API_KEY and ADMIN_TOKEN

python3 tools/kai init --workspace agent_workspace
```

## 3. Edit your bot content

| File | What to change |
|------|----------------|
| `agent_workspace/01_core/system_prompt.md` | Tone, rules, JSON response format |
| `agent_workspace/02_knowledge/faq/master_faq.md` | Your FAQ answers |
| `agent_workspace/05_copy/chat_copy.yaml` | Greetings, handover, footers |
| `agent_workspace/04_channels/handover.yaml` | Office hours, LA keywords, media policy |
| `agent_workspace/03_tools/tools.yaml` | Which tools the bot may use |
| `agent_workspace/00_manifest.yaml` | Bot name, timezone, FAQ inject mode |

**Lightweight mode (recommended for large FAQ):** in `00_manifest.yaml` set:

```yaml
knowledge:
  inject_mode: retrieval_first
```

## 4. Health check

```bash
python3 tools/kai doctor
python3 -m kai.cli paths
python3 tools/kai compile
```

Fix any line marked `ERR` before going live.

## 5. Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Check:

- http://127.0.0.1:8000/health — process up
- http://127.0.0.1:8000/ready — workspace + knowledge ready

Test a message:

```bash
python3 tools/kai_api_cli.py message "What are your opening hours?"
```

## After FAQ edits

```bash
python3 tools/kai compile
# or POST /admin/refresh-sop with x-admin-token header
```

## Tool profiles (recommended)

```yaml
active_profile: minimal
tools: []

profiles:
  minimal:
    - search_faq
    - search_session_memory
    - escalate_to_human

profile_overrides:
  search_official_site:
    params:
      official_url: https://example.com/support/
```

Kommu in this repo uses `active_profile: kommu` with `profile_overrides` (URLs, GitHub repo, SmartServa plugin). Legacy tool names still work via engine aliases.

## Production checklist

- [ ] Strong `ADMIN_TOKEN` in `.env`
- [ ] `python3 tools/kai doctor` shows no ERR
- [ ] `KAI_STRICT_STARTUP=1` in `.env` (optional: refuse boot if workspace invalid)
- [ ] Docker: mount `./agent_workspace` and `./data` as volumes

See also [`OPERATOR.md`](OPERATOR.md) and [`architecture/workspace_v2.md`](architecture/workspace_v2.md).
