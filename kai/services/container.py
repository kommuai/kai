from __future__ import annotations

from typing import Any, Callable

from kai.services.kai_service import KaiService
from kai.support_runtime.service import SupportRuntimeService

_kai_service: KaiService | None = None
_support_runtime_service: SupportRuntimeService | None = None


class _LazyServiceProxy:
    """Defer heavy runtime construction until first use; supports unittest.mock.patch."""

    def __init__(self, factory: Callable[[], Any]) -> None:
        object.__setattr__(self, "_factory", factory)
        object.__setattr__(self, "_overrides", {})

    def _inst(self) -> Any:
        return object.__getattribute__(self, "_factory")()

    def __getattr__(self, name: str) -> Any:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            return overrides[name]
        return getattr(self._inst(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        object.__getattribute__(self, "_overrides")[name] = value

    def __delattr__(self, name: str) -> None:
        overrides = object.__getattribute__(self, "_overrides")
        if name in overrides:
            del overrides[name]
            return
        delattr(self._inst(), name)


def get_kai_service() -> KaiService:
    global _kai_service
    if _kai_service is None:
        _kai_service = KaiService()
    return _kai_service


def get_support_runtime_service() -> SupportRuntimeService:
    global _support_runtime_service
    if _support_runtime_service is None:
        _support_runtime_service = SupportRuntimeService()
    return _support_runtime_service


kai_service: KaiService = _LazyServiceProxy(get_kai_service)  # type: ignore[assignment]
support_runtime_service: SupportRuntimeService = _LazyServiceProxy(get_support_runtime_service)  # type: ignore[assignment]
