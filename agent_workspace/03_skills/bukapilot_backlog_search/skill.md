---
id: bukapilot_backlog_search
version: "0.1.0"
enabled: true
handler_class: BukapilotBacklogSearchSkill
timeout_ms: 12000
retry_count: 0
permissions:
  - repo.read
  - backlog.triage
---

# bukapilot_backlog_search

Search Bukapilot for backlog-related diagnostic evidence.

Defaults:
- repo: `bukapilot/bukapilot`
- branch: `release_ka2` (unless explicitly overridden)
