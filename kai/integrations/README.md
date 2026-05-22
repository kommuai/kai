# Legacy integrations path (deprecated)

Tenant-specific integrations belong in the workspace, not in the Python package:

```
agent_workspace/03_tools/plugins/<plugin_id>/main.py
```

Kommu visitor pass: `agent_workspace/03_tools/plugins/smartserva_visitor_pass/main.py`

Configure in `agent_workspace/03_tools/tools.yaml` (`plugin:` + `profile_overrides`). Run `python3 -m kai.cli port-check` after changes.
