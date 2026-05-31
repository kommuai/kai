"""Resolve SHADOU_HOME and standard paths under the tenant workspace."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def default_shadou_home() -> Path:
    return Path.home() / ".shadou"


def resolve_shadou_home(*, base_dir: Path | None = None) -> Path:
    """Workspace root: SHADOU_HOME, else deprecated AGENT_WORKSPACE, else ~/.shadou."""
    base = base_dir or BASE_DIR
    explicit = os.getenv("SHADOU_HOME", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else base / path
    legacy = os.getenv("AGENT_WORKSPACE", "").strip()
    if legacy:
        path = Path(legacy).expanduser()
        return path if path.is_absolute() else base / path
    return default_shadou_home()


def resolve_env_file(home: Path) -> Path:
    explicit = os.getenv("SHADOU_ENV_FILE", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else BASE_DIR / path
    return home / ".env"


def resolve_session_db_path(home: Path) -> str:
    explicit = os.getenv("SESSION_DB_PATH", "").strip() or os.getenv("DB_PATH", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_absolute():
            return str(path)
        return str(BASE_DIR / path)
    return str(home / "data" / "sessions.db")


def resolve_sop_sync_state_path(home: Path) -> Path:
    explicit = os.getenv("SHADOU_SOP_SYNC_STATE_PATH", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else BASE_DIR / path
    return home / "data" / "sop" / "sop_sync_state.json"


class ShadouPaths:
    """Canonical layout under SHADOU_HOME."""

    def __init__(self, home: Path) -> None:
        self.home = home

    @property
    def workspace_yaml(self) -> Path:
        return self.home / "workspace.yaml"

    @property
    def system_prompt(self) -> Path:
        return self.home / "system_prompt.md"

    @property
    def knowledge_dir(self) -> Path:
        return self.home / "knowledge"

    @property
    def master_faq(self) -> Path:
        return self.knowledge_dir / "master_faq.md"

    @property
    def learnt_faq(self) -> Path:
        return self.knowledge_dir / "learnt_faq.md"

    @property
    def learn_queue(self) -> Path:
        return self.knowledge_dir / "learn_queue"

    @property
    def skills_dir(self) -> Path:
        return self.home / "skills"

    @property
    def plugins_dir(self) -> Path:
        return self.home / "tools" / "plugins"

    @property
    def compiled_dir(self) -> Path:
        return self.home / "compiled"

    @property
    def data_dir(self) -> Path:
        return self.home / "data"

    @property
    def sessions_db(self) -> Path:
        return Path(resolve_session_db_path(self.home))

    @property
    def sop_sync_state(self) -> Path:
        return resolve_sop_sync_state_path(self.home)

    def ensure_runtime_dirs(self) -> None:
        for d in (
            self.knowledge_dir,
            self.learn_queue,
            self.skills_dir,
            self.home / "tools" / "plugins",
            self.compiled_dir,
            self.data_dir,
            self.data_dir / "sop",
        ):
            d.mkdir(parents=True, exist_ok=True)


def using_deprecated_agent_workspace() -> bool:
    return bool(os.getenv("AGENT_WORKSPACE", "").strip()) and not os.getenv("SHADOU_HOME", "").strip()
