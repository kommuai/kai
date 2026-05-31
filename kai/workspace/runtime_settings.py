from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from kai.settings import Settings, get_settings
from kai.workspace.manifest import load_workspace_data, load_workspace_manifest


_DEFAULT_ABSTAIN_THRESHOLD = 0.4
_DEFAULT_ABSTAIN_COPY_EN = (
    "I don't have enough information to answer that reliably. Type LA for a live agent."
)
_DEFAULT_ABSTAIN_COPY_BM = (
    "Saya tidak mempunyai maklumat yang cukup untuk menjawab itu. Taip LA untuk ejen."
)


@dataclass(frozen=True)
class RuntimeSettings:
    """Effective non-secret config: env Settings with workspace.yaml overrides."""

    timezone: str
    office_weekdays: tuple[int, ...]
    office_start_hour: int
    office_end_hour: int
    session_idle_hours: int
    session_max_history_messages: int
    agent_max_steps: int
    footer_history_threshold: int
    whatsapp_max_reply_chars: int
    compile_extra_artifacts: bool
    eval_abstain_threshold: float = _DEFAULT_ABSTAIN_THRESHOLD
    eval_abstain_copy_en: str = _DEFAULT_ABSTAIN_COPY_EN
    eval_abstain_copy_bm: str = _DEFAULT_ABSTAIN_COPY_BM

    @classmethod
    def from_sources(cls, settings: Settings, workspace_yaml: dict[str, Any]) -> RuntimeSettings:
        session = workspace_yaml.get("session") if isinstance(workspace_yaml.get("session"), dict) else {}
        agent = workspace_yaml.get("agent") if isinstance(workspace_yaml.get("agent"), dict) else {}
        compile_block = workspace_yaml.get("compile") if isinstance(workspace_yaml.get("compile"), dict) else {}
        channels = workspace_yaml.get("channels") if isinstance(workspace_yaml.get("channels"), dict) else {}
        whatsapp = channels.get("whatsapp") if isinstance(channels.get("whatsapp"), dict) else {}
        copy_block = workspace_yaml.get("copy") if isinstance(workspace_yaml.get("copy"), dict) else {}
        eval_block = workspace_yaml.get("eval") if isinstance(workspace_yaml.get("eval"), dict) else {}

        manifest = load_workspace_manifest()
        tz = str(session.get("timezone") or manifest.timezone or settings.tz_region)

        raw_threshold = eval_block.get("abstain_threshold")
        try:
            abstain_threshold = float(raw_threshold) if raw_threshold is not None else _DEFAULT_ABSTAIN_THRESHOLD
        except (TypeError, ValueError):
            abstain_threshold = _DEFAULT_ABSTAIN_THRESHOLD

        return cls(
            timezone=tz,
            office_weekdays=(0, 1, 2, 3, 4),
            office_start_hour=settings.office_start,
            office_end_hour=settings.office_end,
            session_idle_hours=int(session.get("idle_hours") or settings.session_idle_hours),
            session_max_history_messages=int(
                session.get("max_history_messages") or settings.session_max_history_messages
            ),
            agent_max_steps=int(agent.get("max_steps") or settings.kai_route_agent_max_steps),
            footer_history_threshold=int(agent.get("footer_history_threshold") or 10),
            whatsapp_max_reply_chars=int(whatsapp.get("max_reply_chars") or 4096),
            compile_extra_artifacts=bool(
                compile_block.get("extra_artifacts")
                if "extra_artifacts" in compile_block
                else settings.kai_compile_extra_artifacts
            ),
            eval_abstain_threshold=abstain_threshold,
            eval_abstain_copy_en=str(copy_block.get("abstain_en") or _DEFAULT_ABSTAIN_COPY_EN),
            eval_abstain_copy_bm=str(copy_block.get("abstain_bm") or _DEFAULT_ABSTAIN_COPY_BM),
        )


@lru_cache(maxsize=1)
def load_workspace_settings_yaml() -> dict[str, Any]:
    return load_workspace_data()


def reload_workspace_settings_yaml() -> dict[str, Any]:
    load_workspace_settings_yaml.cache_clear()
    get_runtime_settings.cache_clear()
    load_grounded_tools.cache_clear()
    load_workspace_data.cache_clear()
    return load_workspace_settings_yaml()


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings.from_sources(get_settings(), load_workspace_settings_yaml())


@lru_cache(maxsize=1)
def load_grounded_tools() -> frozenset[str]:
    """Tenant tool ids that count as grounded evidence (no unverified footnote)."""
    data = load_workspace_settings_yaml()
    agent = data.get("agent") if isinstance(data.get("agent"), dict) else {}
    raw = agent.get("grounded_tools")
    if not isinstance(raw, list):
        return frozenset({"search_faq"})
    ids = {str(x).strip() for x in raw if str(x).strip()}
    return frozenset(ids) if ids else frozenset({"search_faq"})


def reload_grounded_tools() -> frozenset[str]:
    load_grounded_tools.cache_clear()
    return load_grounded_tools()
