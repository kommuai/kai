# Generic workspace template

Copy via:

```bash
python3 tools/kai init --workspace /path/to/agent_workspace
```

## Edit first

1. `00_manifest.yaml` — `tenant.id`, `display_name`, `timezone`
2. `02_knowledge/faq/master_faq.md` — your FAQ
3. `01_core/system_prompt.md` — tone and JSON response rules
4. `03_tools/tools.yaml` — start with `active_profile: minimal`
5. `05_copy/chat_copy.yaml` — greetings and handover text
6. `04_channels/handover.yaml` — office hours and LA keywords

Then:

```bash
python3 -m kai.cli compile
python3 tools/kai doctor
```

See [docs/PORTING.md](../../../docs/PORTING.md) in the engine repo.
