#!/usr/bin/env python3
"""Usage: python -m kai.cli <init|doctor|validate|compile|port-check|paths>"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from kai.settings import get_settings
from kai.settings.loader import BASE_DIR
from kai.support_runtime.compiler import compile_canonical_knowledge
from kai.workspace.validate import ValidationIssue, validate_workspace, workspace_is_healthy


def _repo_root() -> Path:
    return BASE_DIR


def _template_root() -> Path:
    return _repo_root() / "templates" / "workspace" / "generic"


def _print_issues(issues: list[ValidationIssue]) -> None:
    for issue in issues:
        prefix = {"ok": "OK", "warn": "WARN", "error": "ERR"}.get(issue.level, "?")
        print(f"[{prefix}] {issue.code}: {issue.message}")


def cmd_doctor(args: argparse.Namespace) -> int:
    issues = validate_workspace(compile_kb=not args.skip_compile, ping_llm=args.ping_llm)
    _print_issues(issues)
    return 0 if workspace_is_healthy(issues) else 1


def cmd_validate(args: argparse.Namespace) -> int:
    return cmd_doctor(args)


def cmd_port_check(_args: argparse.Namespace) -> int:
    """Print what this workspace needs to run (deps + env hints)."""
    from kai.engine.features import get_workspace_features
    from kai.workspace.manifest import load_workspace_manifest

    manifest = load_workspace_manifest()
    feat = get_workspace_features()
    print(f"tenant_id={manifest.tenant_id} display_name={manifest.display_name}")
    print(f"workspace={get_settings().agent_workspace}")
    print(f"enabled_builtins={','.join(feat.enabled_builtins) or '(defaults)'}")
    if feat.plugin_ids:
        print(f"plugins={','.join(feat.plugin_ids)}")
    if feat.optional_pip_hint:
        print(f"optional_install: {feat.optional_pip_hint}")
        print("  pip install -r requirements-optional.txt")
    else:
        print("optional_install: none (core requirements.txt only)")
    print("startup_hints:")
    print("  KAI_STARTUP_COMPILE=auto     # skip compile when kb_chunks.jsonl exists")
    print("  KAI_SCHEDULER_ENABLED=0      # disable daily refresh background task")
    print("  KAI_STRICT_STARTUP=1         # fail boot on validation errors")
    return 0


def cmd_paths(_args: argparse.Namespace) -> int:
    from kai.workspace.manifest import load_workspace_manifest

    manifest = load_workspace_manifest()
    ws = get_settings().agent_workspace
    print(f"workspace={ws}")
    for label, rel in (
        ("manifest_yaml", "00_manifest.yaml"),
        ("system_prompt", manifest.paths.system_prompt),
        ("knowledge", manifest.paths.knowledge_primary),
        ("compiled_dir", manifest.paths.knowledge_compiled_dir),
        ("tools", manifest.paths.tools),
        ("channels", manifest.paths.channels_handover),
        ("chat_copy", manifest.paths.chat_copy),
        ("settings", manifest.paths.settings),
    ):
        p = ws / rel if label == "manifest_yaml" else manifest.resolve(rel)
        print(f"  {label}: {p}")
    return 0


def cmd_init_plugin(args: argparse.Namespace) -> int:
    plugin_id = (args.plugin_id or "").strip()
    if not plugin_id or not plugin_id.replace("_", "").isalnum():
        print("plugin_id must be alphanumeric/underscore")
        return 1
    ws = get_settings().agent_workspace
    dest_dir = ws / "03_tools" / "plugins" / plugin_id
    if dest_dir.exists() and not args.force:
        print(f"Plugin directory already exists: {dest_dir}")
        return 1
    template = _template_root() / "03_tools" / "plugins" / "example_plugin" / "main.py"
    if not template.is_file():
        print(f"Template missing: {template}")
        return 1
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "main.py"
    shutil.copy2(template, dest)
    print(f"Created plugin at {dest}")
    print("Register in 03_tools/tools.yaml with plugin: {0}".format(plugin_id))
    return 0


def cmd_export_pack(args: argparse.Namespace) -> int:
    import tarfile

    ws = Path(args.workspace or get_settings().agent_workspace).resolve()
    if not ws.is_dir():
        print(f"Workspace not found: {ws}")
        return 1
    out = Path(args.output or f"kai-workspace-{ws.name}.tar.gz").resolve()
    with tarfile.open(out, "w:gz") as tar:
        tar.add(ws, arcname=ws.name)
    print(f"Exported {ws} -> {out}")
    return 0


def cmd_compile(_args: argparse.Namespace) -> int:
    counts = compile_canonical_knowledge()
    print(f"Compiled intents={counts.get('intents', 0)} chunks={counts.get('chunks', 0)}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    if not args.force and ws.exists() and any(ws.iterdir()):
        print(f"Workspace already exists and is not empty: {ws}")
        print("Use --force to merge template files (existing files are not overwritten).")
        return 1

    template = _template_root()
    if not template.is_dir():
        print(f"Template missing: {template}")
        return 1

    ws.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in template.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(template)
        dest = ws / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not args.force:
            continue
        if dest.exists() and args.force:
            continue
        shutil.copy2(src, dest)
        copied += 1

    env_example = _repo_root() / ".env.example"
    env_dest = _repo_root() / ".env"
    if env_example.is_file() and not env_dest.exists():
        shutil.copy2(env_example, env_dest)
        print(f"Created {_rel(env_dest)} from .env.example — add your API keys.")

    print(f"Initialized workspace at {ws} ({copied} files from template).")
    print("Next:")
    print(f"  1. Set AGENT_WORKSPACE={ws} in .env (or use default agent_workspace/)")
    print("  2. Edit FAQ: 02_knowledge/faq/master_faq.md")
    print("  3. Run: python -m kai.cli doctor")
    return 0


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_repo_root()))
    except ValueError:
        return str(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kai", description="Kai workspace CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Scaffold a new agent_workspace from template")
    p_init.add_argument(
        "--workspace",
        default=str(get_settings().agent_workspace),
        help="Target workspace directory",
    )
    p_init.add_argument("--force", action="store_true", help="Copy missing template files into existing workspace")
    p_init.set_defaults(func=cmd_init)

    for name in ("doctor", "validate"):
        p = sub.add_parser(name, help="Validate workspace manifest, paths, FAQ compile, tools")
        p.add_argument("--skip-compile", action="store_true", help="Do not compile FAQ")
        p.add_argument("--ping-llm", action="store_true", help="Ping LLM provider (uses API key)")
        p.set_defaults(func=cmd_doctor)

    p_compile = sub.add_parser("compile", help="Compile master_faq.md to kb_chunks.jsonl")
    p_compile.set_defaults(func=cmd_compile)

    p_port = sub.add_parser("port-check", help="Show deps and env hints for this workspace")
    p_port.set_defaults(func=cmd_port_check)

    p_paths = sub.add_parser("paths", help="Print resolved workspace file paths")
    p_paths.set_defaults(func=cmd_paths)

    p_plugin = sub.add_parser("init-plugin", help="Scaffold a plugin under 03_tools/plugins/")
    p_plugin.add_argument("plugin_id", help="Plugin directory name")
    p_plugin.add_argument("--force", action="store_true")
    p_plugin.set_defaults(func=cmd_init_plugin)

    p_export = sub.add_parser("export-pack", help="Tar.gz the workspace directory")
    p_export.add_argument("--workspace", default=str(get_settings().agent_workspace))
    p_export.add_argument("--output", default="")
    p_export.set_defaults(func=cmd_export_pack)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
