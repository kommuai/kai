from core.context.contracts import ContextProvider


class StaticContextProvider(ContextProvider):
    def __init__(self, provider_id: str, chunks: list[dict]):
        self.provider_id = provider_id
        self.chunks = chunks

    def refresh(self) -> None:
        return None

    def retrieve(self, query: str, filters: dict, top_k: int = 4) -> list[dict]:
        _ = query, filters
        return self.chunks[:top_k]

    def health(self) -> dict:
        return {"provider_id": self.provider_id, "ok": True, "items": len(self.chunks)}

