# Kommu tenant pack for Kai

Install into your Kai home directory (`~/.kai/`):

```bash
export KAI_HOME=~/.kai
python3 -m kai.cli workspace init          # empty home (skip if already initialized)
python3 -m kai.cli pack install /path/to/kai-tenant-kommu
python3 -m kai.cli doctor
```

## Required environment (`~/.kai/.env`)

| Variable | Purpose |
|----------|---------|
| `DEEPSEEK_API_KEY` | LLM provider |
| `ADMIN_TOKEN` | Admin API routes |

## Kommu integrations (optional)

| Variable | Purpose |
|----------|---------|
| `WARRANTY_CSV_URL` / `EXTRA_WARRANTY_CSV_URL` | Sheet warranty lookup |
| `KAI_GITHUB_REPO` | GitHub repo search (default bukapilot via workspace overrides) |
| `SMARTSERVA_USERNAME` / `SMARTSERVA_PASSWORD` | Visitor pass plugin |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | Sheet tools |

## Layout

```
workspace.yaml
system_prompt.md
knowledge/master_faq.md
tools/plugins/smartserva_visitor_pass/main.py
```

After install, compiled KB lives in `~/.kai/compiled/kb_chunks.jsonl`.
