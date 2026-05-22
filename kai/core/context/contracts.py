from typing import Any, Protocol


class ContextProvider(Protocol):
    provider_id: str

    def refresh(self) -> None:
        ...

    def retrieve(self, query: str, filters: dict[str, Any], top_k: int = 4) -> list[dict[str, Any]]:
        ...

    def health(self) -> dict[str, Any]:
        ...

