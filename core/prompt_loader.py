"""Load identity and safety markdown from agent_workspace/01_core/."""
from __future__ import annotations

import logging
from pathlib import Path

from config import AGENT_WORKSPACE

log = logging.getLogger("kai.prompt_loader")


def _read_if_exists(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def load_core_prompt_sections() -> tuple[str, str]:
    """Return (identity_block, safety_block) from markdown files."""
    core = Path(AGENT_WORKSPACE) / "01_core"
    identity = _read_if_exists(core / "identity.md")
    safety = _read_if_exists(core / "safety_guidelines.md")
    if not identity:
        log.warning("Missing identity.md under %s", core)
    if not safety:
        log.warning("Missing safety_guidelines.md under %s", core)
    return identity, safety


def build_rag_system_prompt(*, dropoff_token: str, testdrive_token: str) -> str:
    """Assemble system prompt for RAG dual path (KaiService.run_rag_dual)."""
    identity, safety = load_core_prompt_sections()
    parts = []
    if identity:
        parts.append(identity)
    if safety:
        parts.append(safety)
    # Tokens are runtime-specific (templates / handover)
    parts.append(
        f"- If user asks about drop offs, add: For dropoffs, type {dropoff_token}.\n"
        f"- If user asks about test drives, add: To schedule a test drive, type {testdrive_token}."
    )
    return "\n\n".join(parts).strip()
