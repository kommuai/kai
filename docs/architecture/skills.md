# Runtime capabilities

Production chat (`POST /agent/message`) does **not** load workspace skill handlers. Flow:

1. `KaiService.pre_router` — handover / frozen / resume
2. `SupportRuntimeService.execute` — FAQ-first (first message) → `ReActAgentLoop` + `AgentToolRegistry`
3. `prepare_outbound_message` — WhatsApp length cap

## Capability nodes

- `canonical_answer` — high-confidence FAQ hit on first message
- `react_agent_loop` — multi-turn reasoning with tools
- `guardrails` — unsafe-content escalation
- Retrieval/rerank — used inside agent tools and Haystack paths when enabled

## `agent_workspace/03_skills/`

Manifest and docs only (`skill_manifest.md`). Skill `handler.py` stubs were removed; add new behavior via `support_runtime/agent_tools.py` and FAQ entries in `master_faq.md`.

## Compiled knowledge

`support_runtime.compiler` writes:

- `agent_workspace/compiled/intents.json`
- `agent_workspace/compiled/workflows.json`
- `agent_workspace/compiled/kb_chunks.jsonl`
- `agent_workspace/compiled/tool_policies.json`

Refresh with `POST /admin/refresh-sop`.
