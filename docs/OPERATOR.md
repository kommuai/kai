# Kai operator guide

One-page map of **where to edit** the WhatsApp bot without hunting Python modules.

Production security (gateway-only chat, admin token, debug gating): [`SECURITY.md`](SECURITY.md).

## Edit map

| What you change | File or command |
|-----------------|-----------------|
| Bot personality, tool rules, JSON response format | [`agent_workspace/01_core/system_prompt.md`](../agent_workspace/01_core/system_prompt.md) |
| FAQ answers (pricing, install, warranty, office, …) | [`agent_workspace/02_knowledge/faq/master_faq.md`](../agent_workspace/02_knowledge/faq/master_faq.md) |
| SOP install region (Google Doc sync) | Same file, between `<!-- sop-sync:start -->` and `<!-- sop-sync:end -->` |
| Handover / resume / footer text | [`agent_workspace/05_copy/chat_copy.yaml`](../agent_workspace/05_copy/chat_copy.yaml) |
| Office hours, LA/resume keywords, media policy | [`agent_workspace/04_channels/handover.yaml`](../agent_workspace/04_channels/handover.yaml) |
| Non-secret defaults (session length, agent steps) | [`agent_workspace/settings.yaml`](../agent_workspace/settings.yaml) |
| Secrets and overrides | `.env` (never commit) |
| Path registry | [`agent_workspace/00_manifest.yaml`](../agent_workspace/00_manifest.yaml) (or legacy `00_manifest.md`) |
| Enabled agent tools | [`agent_workspace/03_tools/tools.yaml`](../agent_workspace/03_tools/tools.yaml) |

After FAQ or prompt edits, refresh runtime knowledge:

```bash
curl -X POST http://127.0.0.1:6090/admin/refresh-sop -H "x-admin-token: $ADMIN_TOKEN"
# or
cd /home/ting/workspace/kai && python3 tools/merge_learn_queue.py --apply <id> --compile
```

## FAQ learn queue (post handoff)

When users type **resume** after a live-agent segment, proposals land in:

`agent_workspace/02_knowledge/faq/learn_queue/<proposal_id>/`

```bash
python3 tools/merge_learn_queue.py --list
python3 tools/merge_learn_queue.py --show <proposal_id>
python3 tools/merge_learn_queue.py --apply <proposal_id> --compile
```

## SOP sync

```bash
cd /home/ting/workspace/kai && ./tools/force_sop_sync.py
```

## Workspace health check

```bash
python3 tools/kai doctor
python3 tools/kai compile
```

New tenant from template:

```bash
python3 tools/kai init --workspace ./agent_workspace
```

See [`docs/SETUP.md`](SETUP.md) and [`docs/architecture/workspace_v2.md`](architecture/workspace_v2.md).

## Test the API locally

```bash
python3 tools/kai_api_cli.py message "What cars are supported?"
python3 tools/kai_api_cli.py chat --phone test-user
```

Set `KAI_API_BASE_URL` if not on `http://127.0.0.1:6090`.

## Code layout (developers)

| Package | Role |
|---------|------|
| `kai/content/` | Load prompts, FAQ cache, chat copy from `agent_workspace/` |
| `kai/settings/` | All env configuration |
| `kai/services/` | `pre_router`, footers, `turn_ingest` |
| `kai/support_runtime/` | ReAct loop, tools, compiler |
| `kai/workspace/` | Manifest, tools YAML, validation, runtime settings |
| `config.py` | Backward-compatible re-exports |

## Verification

```bash
cd /home/ting/workspace/kai
pytest tests/test_chat_copy_parity.py tests/test_prompt_assembly_snapshot.py \
  tests/test_api_contracts.py tests/test_architecture_import_boundaries.py -q
pytest tests/ --ignore=tests/test_support_runtime.py -q
```
