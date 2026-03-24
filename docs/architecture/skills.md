# Runtime Capabilities (Haystack Revision)

The support runtime is router-first and Haystack-oriented, and no longer depends on workspace skill `can_handle` competition for primary chat flow.

## Core capability nodes

- `canonical_answer` for high-confidence known intents
- `grounded_composer` for retrieve + rerank + grounded answering
- `tool_policy` for conditional tool-required turns
- `confidence_gate` / validator for escalation and low-confidence handling
- `guardrails` for unsafe-content escalation

## Legacy skills

Legacy workspace skills under `agent_workspace/03_skills/` are still present for compatibility and tests, but they are not the primary runtime routing mechanism for `/agent/message` and `/v2/agent/query`.

## Compiled knowledge artifacts

`support_runtime.compiler` compiles support content into:

- `agent_workspace/compiled/intents.json`
- `agent_workspace/compiled/workflows.json`
- `agent_workspace/compiled/kb_chunks.jsonl`
- `agent_workspace/compiled/tool_policies.json`
