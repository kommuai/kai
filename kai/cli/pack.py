"""Tenant pack install/export into KAI_HOME."""

from __future__ import annotations

import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable
from urllib.request import urlretrieve

import yaml

from kai.settings import get_settings
from kai.settings.loader import BASE_DIR
from kai.settings.paths import KaiPaths

# Always overwrite when installing a pack (tenant content replaces scaffold)
_ALWAYS_OVERWRITE = {
    "workspace.yaml",
    "system_prompt.md",
    "pack.yaml",
}


def _should_overwrite(rel: Path, *, force: bool) -> bool:
    if force:
        return True
    if rel.name in _ALWAYS_OVERWRITE:
        return True
    if rel.parts and rel.parts[0] in {"knowledge", "tools", "skills"}:
        return True
    return False


_SKIP_DIRS = {"compiled", "data", "__pycache__", ".git"}
_SKIP_FILES = {".env"}


def _pack_root(src: Path) -> Path:
    """If src contains workspace.yaml, use src; else first child dir that does."""
    if (src / "workspace.yaml").is_file():
        return src
    for child in sorted(src.iterdir()):
        if child.is_dir() and (child / "workspace.yaml").is_file():
            return child
    return src


def _iter_pack_files(root: Path) -> Iterable[tuple[Path, Path]]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in _SKIP_DIRS:
            continue
        if path.name in _SKIP_FILES:
            continue
        yield path, rel


def install_pack(src: str | Path, *, force: bool = False) -> tuple[int, list[str]]:
    """Copy tenant pack files into KAI_HOME. Returns (copied_count, messages)."""
    home = get_settings().kai_home
    paths = KaiPaths(home)
    paths.ensure_runtime_dirs()

    raw = Path(str(src)).expanduser()
    tmp_dir: tempfile.TemporaryDirectory[str] | None = None
    try:
        if str(src).startswith(("http://", "https://")):
            tmp_dir = tempfile.TemporaryDirectory(prefix="kai-pack-")
            archive = Path(tmp_dir.name) / "pack.tgz"
            urlretrieve(str(src), archive)
            extract_to = Path(tmp_dir.name) / "extract"
            extract_to.mkdir()
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(extract_to)
            raw = extract_to
        elif raw.suffix in {".gz", ".tgz"} or str(raw).endswith(".tar.gz"):
            tmp_dir = tempfile.TemporaryDirectory(prefix="kai-pack-")
            extract_to = Path(tmp_dir.name) / "extract"
            extract_to.mkdir()
            with tarfile.open(raw, "r:gz") as tar:
                tar.extractall(extract_to)
            raw = extract_to

        if not raw.is_dir():
            return 0, [f"Pack source not found: {src}"]

        root = _pack_root(raw)
        if not (root / "workspace.yaml").is_file() and not (root / "pack.yaml").is_file():
            return 0, [f"No workspace.yaml or pack.yaml under {root}"]

        copied = 0
        messages: list[str] = []
        for src_file, rel in _iter_pack_files(root):
            dest = home / rel
            if dest.exists() and not _should_overwrite(rel, force=force):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest)
            copied += 1

        pack_meta = root / "pack.yaml"
        if pack_meta.is_file():
            meta = yaml.safe_load(pack_meta.read_text(encoding="utf-8")) or {}
            if isinstance(meta, dict) and meta.get("id"):
                messages.append(f"Installed pack id={meta.get('id')} version={meta.get('version', '?')}")

        messages.append(f"Copied {copied} files into {home}")
        return copied, messages
    finally:
        if tmp_dir is not None:
            tmp_dir.cleanup()


def export_pack(
    output: str | Path,
    *,
    home: Path | None = None,
    exclude_runtime: bool = True,
) -> Path:
    """Tar.gz KAI_HOME (or subset) for portability."""
    src = home or get_settings().kai_home
    out = Path(output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    def _filter(ti: tarfile.TarInfo) -> tarfile.TarInfo | None:
        name = ti.name
        if exclude_runtime:
            if name.startswith("compiled/") or name.startswith("data/"):
                return None
        return ti

    with tarfile.open(out, "w:gz") as tar:
        for path in src.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(src)
            if exclude_runtime and rel.parts and rel.parts[0] in _SKIP_DIRS:
                continue
            if path.name in _SKIP_FILES:
                continue
            tar.add(path, arcname=str(rel), filter=_filter)
    return out


def _template_root() -> Path:
    return BASE_DIR / "templates" / "workspace" / "generic"


def scaffold_workspace(home: Path | None = None, *, force: bool = False) -> tuple[int, Path]:
    """Initialize KAI_HOME from engine generic template."""
    target = home or get_settings().kai_home
    template = _template_root()
    if not template.is_dir():
        raise FileNotFoundError(f"Template missing: {template}")

    if target.exists() and any(target.iterdir()) and not force:
        raise FileExistsError(f"KAI_HOME is not empty: {target}")

    KaiPaths(target).ensure_runtime_dirs()
    copied = 0
    for src in template.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(template)
        dest = target / rel
        if dest.exists() and not force:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    env_example = get_settings().base_dir / ".env.example"
    env_dest = target / ".env"
    if env_example.is_file() and not env_dest.exists():
        shutil.copy2(env_example, env_dest)

    skills_readme = target / "skills" / "README.md"
    if not skills_readme.exists():
        skills_readme.parent.mkdir(parents=True, exist_ok=True)
        skills_readme.write_text(
            "# Skills\n\nOptional procedural skill docs for this tenant.\n",
            encoding="utf-8",
        )

    return copied, target
