# Routing Runtime (Haystack + Chatwoot Parity)

Kai runs a deterministic support pipeline under `support_runtime/` with strict Chatwoot parity pre-routing:

1. `pre_router` handover/frozen checks
2. canonical intent router (rules + intent match)
3. confidence gate
4. path selection:
   - direct canonical answer
   - retrieve + rerank + grounded compose
   - tool policy branch
   - human escalation
5. answer validator + guardrails checks

## Decision Outcomes

Each turn produces one of:

- `direct_answer`
- `clarifying_question`
- `tool_use`
- `escalate_human`

## Integrations

- Haystack pipeline orchestration (with graceful fallback when optional deps are unavailable)
- Qdrant hybrid retrieval (env-gated)
- Provider-backed reranking (env-gated backend selection)
- Tracing spans and safety gates (env-gated)

## Endpoints

- `POST /agent/message` and `POST /v2/agent/message`:
  - still return trace fields (`trace_id`, `capability_used`, `latency_ms`)
  - now include runtime decision metadata (`decision`, `confidence`, `source_ids`, `tool_needed`, `escalate_needed`) when available
- `POST /v2/agent/query`:
  - uses the same support runtime execution path (service auth required)
