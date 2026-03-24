# Legacy Tool Paths

Before the capability architecture, external calls were hardcoded in the chat path.

## Existing External Paths

- LLM call path:
  - `services/kai_service.py -> run_rag_dual() -> deepseek_client.chat_completion()`
- SOP fetch + RAG rebuild:
  - `services/kai_service.py -> refresh_sop_and_warranty() -> sop_doc_loader + rag.rebuild_index_combined`
- Warranty fetch/lookup:
  - `google_sheets.py -> fetch_warranty_all(), warranty_lookup_by_dongle()`
- Translation:
  - `GoogleTranslator.translate()` inside `run_rag_dual()`
- Media retrieval:
  - `media_handler.py -> get_media_url(), download_media(), insert_media_record()`

## Migration Strategy

- Wrap each path as a skill capability.
- Execute through policy adapter (`ToolAdapter`).
- If no skill succeeds, `main_conversation` in `KaiService` provides the same tail behavior as before (no duplicate `pre_router` on fallback).

