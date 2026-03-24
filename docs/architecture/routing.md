# Routing Modes

Kai supports route modes controlled by `KAI_ROUTE_MODE`:

- `hybrid` (default): after `pre_router`, `RouterEngine` tries workspace skills; if none succeed, `main_conversation` runs (warranty / RAG tail).
- `agent_first`: same skill ordering as `hybrid` today; reserved for future stricter agent preference.
- `stable_only`: legacy env value; mapped to `hybrid`.

`stable_only` is no longer a separate runtime mode (removed from `RouteMode` enum).

## Endpoints

- `POST /agent/message` — same handler as v2 message path; includes `trace_id`, `route_mode`, `capability_used`, `latency_ms` (and `fallback_reason` when applicable).
- `POST /v2/agent/message` — identical behavior; optional shadow logging compares against full `handle_agent_message` when `KAI_SHADOW_MODE` is enabled.
- `POST /v2/agent/query` — machine-facing A2A (auth required).
