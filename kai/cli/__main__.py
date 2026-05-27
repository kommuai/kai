#!/usr/bin/env python3
"""Usage: python -m kai.cli <workspace|pack|doctor|compile|port-check|paths>"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kai.cli.pack import export_pack, install_pack, scaffold_workspace
from kai.settings import get_settings, reload_settings
from kai.settings.loader import BASE_DIR
from kai.settings.paths import resolve_kai_home, using_deprecated_agent_workspace
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
    if using_deprecated_agent_workspace():
        print("[WARN] AGENT_WORKSPACE is deprecated; use KAI_HOME instead.")
    issues = validate_workspace(compile_kb=not args.skip_compile, ping_llm=args.ping_llm)
    _print_issues(issues)
    return 0 if workspace_is_healthy(issues) else 1


def cmd_validate(args: argparse.Namespace) -> int:
    return cmd_doctor(args)


def cmd_port_check(_args: argparse.Namespace) -> int:
    from kai.engine.features import get_workspace_features
    from kai.workspace.manifest import load_workspace_manifest

    manifest = load_workspace_manifest()
    feat = get_workspace_features()
    settings = get_settings()
    print(f"tenant_id={manifest.tenant_id} display_name={manifest.display_name}")
    print(f"KAI_HOME={settings.kai_home}")
    print(f"enabled_builtins={','.join(feat.enabled_builtins) or '(defaults)'}")
    if feat.plugin_ids:
        print(f"plugins={','.join(feat.plugin_ids)}")
    if feat.optional_pip_hint:
        print(f"integration_hints: {feat.optional_pip_hint}")
    return 0


def cmd_paths(_args: argparse.Namespace) -> int:
    from kai.workspace.manifest import load_workspace_manifest, workspace_yaml_path

    manifest = load_workspace_manifest()
    home = get_settings().kai_home
    print(f"KAI_HOME={home}")
    print(f"  workspace_yaml: {workspace_yaml_path()}")
    for label, rel in (
        ("system_prompt", manifest.paths.system_prompt),
        ("knowledge", manifest.paths.knowledge_primary),
        ("compiled_dir", manifest.paths.knowledge_compiled_dir),
        ("tools_plugins", manifest.paths.tools_plugins_dir),
    ):
        print(f"  {label}: {manifest.resolve(rel)}")
    print(f"  session_db: {get_settings().session_db_path}")
    return 0


def cmd_init_plugin(args: argparse.Namespace) -> int:
    import shutil

    plugin_id = (args.plugin_id or "").strip()
    if not plugin_id or not plugin_id.replace("_", "").isalnum():
        print("plugin_id must be alphanumeric/underscore")
        return 1
    home = get_settings().kai_home
    from kai.workspace.manifest import load_workspace_manifest

    plugins_dir = load_workspace_manifest().paths.tools_plugins_dir
    dest_dir = home / plugins_dir / plugin_id
    if dest_dir.exists() and not args.force:
        print(f"Plugin directory already exists: {dest_dir}")
        return 1
    template = _template_root() / "tools" / "plugins" / "example_plugin" / "main.py"
    if not template.is_file():
        print(f"Template missing: {template}")
        return 1
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "main.py"
    shutil.copy2(template, dest)
    print(f"Created plugin at {dest}")
    print(f"Register in workspace.yaml tools_profile with plugin: {plugin_id}")
    return 0


def cmd_compile(_args: argparse.Namespace) -> int:
    counts = compile_canonical_knowledge()
    print(f"Compiled intents={counts.get('intents', 0)} chunks={counts.get('chunks', 0)}")
    return 0


def cmd_workspace_init(args: argparse.Namespace) -> int:
    home = Path(args.home or resolve_kai_home()).expanduser().resolve()
    try:
        copied, target = scaffold_workspace(home, force=args.force)
    except FileExistsError as exc:
        print(str(exc))
        print("Use --force to add missing template files without overwriting.")
        return 1
    except FileNotFoundError as exc:
        print(str(exc))
        return 1
    reload_settings()
    print(f"Initialized KAI_HOME at {target} ({copied} files from template).")
    print("Next:")
    print("  kai pack install <tenant-pack>   # optional tenant content")
    print("  kai doctor")
    return 0


def cmd_pack_install(args: argparse.Namespace) -> int:
    copied, messages = install_pack(args.source, force=args.force)
    for line in messages:
        print(line)
    if copied == 0 and messages and "not found" in messages[0].lower():
        return 1
    reload_settings()
    from kai.workspace.reload import reload_workspace_caches

    reload_workspace_caches()
    return 0


def cmd_pack_export(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser() if args.home else get_settings().kai_home
    out = export_pack(
        args.output or f"kai-pack-{home.name}.tar.gz",
        home=home,
        exclude_runtime=not args.include_runtime,
    )
    print(f"Exported {home} -> {out}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Deprecated alias for workspace init."""
    args.home = args.workspace
    return cmd_workspace_init(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kai", description="Kai agent harness CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ws = sub.add_parser("workspace", help="Manage KAI_HOME workspace")
    ws_sub = p_ws.add_subparsers(dest="workspace_cmd", required=True)
    p_ws_init = ws_sub.add_parser("init", help="Scaffold ~/.kai from generic template")
    p_ws_init.add_argument("--home", default="", help="KAI_HOME path (default ~/.kai or KAI_HOME env)")
    p_ws_init.add_argument("--force", action="store_true", help="Add missing files without overwriting existing")
    p_ws_init.set_defaults(func=cmd_workspace_init)

    p_pack = sub.add_parser("pack", help="Install or export tenant packs")
    pack_sub = p_pack.add_subparsers(dest="pack_cmd", required=True)
    p_pack_in = pack_sub.add_parser("install", help="Install tenant pack into KAI_HOME")
    p_pack_in.add_argument("source", help="Local directory, .tar.gz path, or https URL")
    p_pack_in.add_argument("--force", action="store_true", help="Overwrite existing files")
    p_pack_in.set_defaults(func=cmd_pack_install)
    p_pack_ex = pack_sub.add_parser("export", help="Export KAI_HOME as tar.gz")
    p_pack_ex.add_argument("--output", default="")
    p_pack_ex.add_argument("--home", default="")
    p_pack_ex.add_argument(
        "--include-runtime",
        action="store_true",
        help="Include compiled/ and data/ in export",
    )
    p_pack_ex.set_defaults(func=cmd_pack_export)

    p_init = sub.add_parser("init", help="[deprecated] Use: kai workspace init")
    p_init.add_argument("--workspace", default=str(resolve_kai_home()), help="Target KAI_HOME")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    for name in ("doctor", "validate"):
        p = sub.add_parser(name, help="Validate KAI_HOME layout, FAQ, tools")
        p.add_argument("--skip-compile", action="store_true")
        p.add_argument("--ping-llm", action="store_true")
        p.set_defaults(func=cmd_doctor)

    p_compile = sub.add_parser("compile", help="Compile master FAQ to kb_chunks.jsonl")
    p_compile.set_defaults(func=cmd_compile)

    p_port = sub.add_parser("port-check", help="Show deps and env hints for this workspace")
    p_port.set_defaults(func=cmd_port_check)

    p_paths = sub.add_parser("paths", help="Print resolved KAI_HOME paths")
    p_paths.set_defaults(func=cmd_paths)

    p_plugin = sub.add_parser("init-plugin", help="Scaffold a plugin under tools/plugins/")
    p_plugin.add_argument("plugin_id")
    p_plugin.add_argument("--force", action="store_true")
    p_plugin.set_defaults(func=cmd_init_plugin)

    p_export = sub.add_parser("export-pack", help="[deprecated] Use: kai pack export")
    p_export.add_argument("--workspace", default="")
    p_export.add_argument("--output", default="")
    p_export.add_argument("--include-runtime", action="store_true")
    p_export.set_defaults(
        func=lambda ns: cmd_pack_export(
            argparse.Namespace(
                output=ns.output,
                home=ns.workspace or str(get_settings().kai_home),
                include_runtime=ns.include_runtime,
            )
        )
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
