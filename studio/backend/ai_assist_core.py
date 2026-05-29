"""Shared AI Assist logic: scoped patches for tenant workspace files."""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
import yaml
from fastapi import HTTPException

log = logging.getLogger("kai.ai_assist")

CONFIG_FILES: dict[str, str] = {
    "workspace": "workspace.yaml",
    "system_prompt": "system_prompt.md",
    "faq": "knowledge/master_faq.md",
}

PLUGIN_TEMPLATE = '''\
#!/usr/bin/env python3
"""<one-line description — deterministic CLI plugin for Kai agent tools."""
from __future__ import annotations

import argparse
import json
import sys


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="<plugin_id>")
    p.add_argument("--query", required=True, help="Primary input for this tool")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    query = (args.query or "").strip()
    if not query:
        print(json.dumps({"ok": False, "error": "missing_query"}))
        return 1
    print(json.dumps({"ok": True, "result": {"query": query}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
'''

SYSTEM_PROMPT = """
You are KAI CONFIG ASSISTANT — a friendly, guided assistant helping non-technical users configure their AI support agent inside Kai Studio.

## Your only purpose
Help the user configure these resources in their tenant workspace:
1. **workspace.yaml** — channels, office hours, handover keywords, agent settings, and **skills/plugins list**.
2. **system_prompt.md** — the personality, scope, and escalation rules for the AI support agent.
3. **knowledge/master_faq.md** — the official FAQ / knowledge base.
4. **Plugin scripts** — Python files at `tools/plugins/<plugin_name>/main.py` that implement custom actions.

You are NOT a general assistant. Politely refuse anything outside these resources.

## What you CAN do
- Read the current file contents (provided in the conversation).
- Guide the user with friendly, plain-language questions.
- Propose edits to config files AND create/edit plugin scripts.
- Enable or disable skills by editing the `profile_overrides` block in workspace.yaml.
- Add a new plugin skill: write the Python script AND register it in workspace.yaml.
- Remove a skill by removing it from the tools list (or setting `enabled: false`).
- Explain every change before applying.

## What you MUST NOT do
- Modify files outside workspace.yaml, system_prompt.md, master_faq.md, and tools/plugins/*.
- Reveal API keys, secrets, or environment variables.
- Invent information — ask the user if uncertain.
- Run arbitrary code or shell commands.

## Plugin contract (mandatory for every tools/plugins/*/main.py)
- Use **argparse** CLI flags (kebab-case on the command line). The runtime passes `--arg-name value` from tool JSON args.
- Print **one JSON object** on stdout: always include `"ok": true` or `"ok": false` and on failure a clear `"error": "..."` string.
- Never use stdin JSON (`json.load(sys.stdin)`). Never swallow errors — return `ok: false` with the exact error message.
- Register new tools in `workspace.yaml` `tools_profile.profile_overrides` with `plugin`, `description`, and `params.schema` (JSON Schema for args).
- Map agent arg names to CLI flags via `params.arg_aliases` when they differ (e.g. `visit_date` → `date`).

## How to propose changes
Reply with ONE JSON block inside a fenced code block tagged `kai-patch`:

```kai-patch
{
  "patches": [
    {
      "type": "config_file",
      "file": "workspace",
      "content": "<FULL updated file content>"
    },
    {
      "type": "plugin_file",
      "plugin_name": "my_plugin_name",
      "content": "<FULL Python script content>"
    }
  ],
  "summary": "One sentence: what changed and why."
}
```

### Patch types
- `config_file`: edits one of workspace, system_prompt, faq. `content` = full new file.
- `plugin_file`: creates or overwrites `tools/plugins/<plugin_name>/main.py`. `plugin_name` must be snake_case.

ALWAYS provide the FULL file content — never partial snippets or diffs.
ALWAYS preserve YAML / Markdown / Python formatting exactly.

## Tone and flow
- Be warm, clear, and encouraging.
- Ask ONE question at a time when chatting.
- Keep responses short unless showing the patch block.
""".strip()


BOOTSTRAP_SYSTEM_PROMPT = """
You are KAI TENANT BOOTSTRAP — you populate a NEW tenant workspace from uploaded business documents and a short questionnaire.

## Output format (required)
Reply with ONLY one fenced block tagged `kai-patch` (no other prose):

```kai-patch
{
  "patches": [
    { "type": "config_file", "file": "workspace", "content": "..." },
    { "type": "config_file", "file": "system_prompt", "content": "..." },
    { "type": "config_file", "file": "faq", "content": "..." }
  ],
  "summary": "One sentence describing what you configured."
}
```

## Rules (same guardrails as AI Assist)
- You may ONLY change: workspace.yaml, system_prompt.md, knowledge/master_faq.md, and tools/plugins/*/main.py.
- Provide FULL file contents for every patch.
- Use facts from the questionnaire and uploaded documents only — do not invent pricing, policies, or features.
- master_faq.md must use the project's FAQ markdown format with `## intent_id` sections when possible.
- workspace.yaml must remain valid YAML; keep tools_profile minimal (search_faq, search_session_memory, escalate_to_human) unless documents clearly require more.
- Merge questionnaire personality, scope, escalation, and fallback into system_prompt.md.
- If documents lack FAQ detail, create a small starter FAQ from questionnaire product summary only.

## Skills
- Prefer enabling built-in skills in tools_profile; only add plugin_file patches when documents describe a clear custom action.
""".strip()


def make_deepseek_client() -> tuple[str, str, str]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from kai.settings import get_settings

    s = get_settings()
    api_key = (s.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    base_url = (s.deepseek_base_url or "https://api.deepseek.com/v1").rstrip("/")
    model = (s.deepseek_model or "deepseek-chat").strip()
    return api_key, base_url, model


def safe_plugin_name(name: str) -> bool:
    return bool(re.fullmatch(r"[a-zA-Z0-9_]+", name))


def current_config_files(home: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, rel in CONFIG_FILES.items():
        p = home / rel
        out[key] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return out


def current_plugins(home: Path) -> list[dict[str, str]]:
    plugins_dir = home / "tools" / "plugins"
    if not plugins_dir.is_dir():
        return []
    plugins = []
    for child in sorted(plugins_dir.iterdir()):
        if not child.is_dir():
            continue
        script = child / "main.py"
        if script.is_file():
            plugins.append({
                "name": child.name,
                "path": str(script.relative_to(home)),
                "content": script.read_text(encoding="utf-8", errors="replace")[:4000],
            })
    return plugins


def current_skills_summary(home: Path) -> str:
    try:
        from kai_capabilities import get_capabilities

        caps = get_capabilities(home)
        skills = caps.get("skills") or []
        if not skills:
            return "No skills configured yet."
        lines = []
        for s in skills:
            status = "enabled" if s.get("enabled") else "disabled"
            src = "plugin" if s.get("plugin") else ("builtin" if s.get("builtin") else "document")
            lines.append(f"- `{s['id']}` [{src}] {status} — {s.get('description', '')[:80]}")
        return "\n".join(lines)
    except Exception:
        return "(Could not load skills list)"


def build_context(home: Path) -> str:
    files = current_config_files(home)
    plugins = current_plugins(home)
    parts: list[str] = []
    for key, content in files.items():
        rel = CONFIG_FILES[key]
        parts.append(f"### Current {key} ({rel}):\n```\n{content[:8000]}\n```")
    parts.append(f"### Current skills overview:\n{current_skills_summary(home)}")
    if plugins:
        for p in plugins:
            parts.append(f"### Plugin script `{p['path']}`:\n```python\n{p['content']}\n```")
    else:
        parts.append(f"### Plugin template:\n```python\n{PLUGIN_TEMPLATE}\n```")
    return "\n\n".join(parts)


def extract_patch(text: str) -> dict[str, Any] | None:
    m = re.search(r"```kai-patch\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def apply_patch_item(home: Path, patch: dict[str, Any]) -> dict[str, str] | None:
    ptype = (patch.get("type") or "config_file").strip()

    if ptype == "config_file" or ("file" in patch and "type" not in patch):
        file_key = (patch.get("file") or "").strip()
        new_content = patch.get("content", "")
        rel = CONFIG_FILES.get(file_key)
        if not rel:
            return None
        p = home / rel
        old_content = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if file_key == "workspace":
            try:
                yaml.safe_load(new_content)
            except yaml.YAMLError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid YAML in patch: {exc}") from exc
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_content, encoding="utf-8")
        if file_key == "workspace":
            from channel_config import reapply_saved_channel

            reapply_saved_channel(home)
        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        return {"type": "config_file", "file": file_key, "path": rel, "diff": diff}

    if ptype == "plugin_file":
        plugin_name = (patch.get("plugin_name") or "").strip()
        new_content = patch.get("content", "")
        if not plugin_name or not safe_plugin_name(plugin_name):
            raise HTTPException(status_code=422, detail=f"Invalid plugin_name: {plugin_name}")
        script_path = home / "tools" / "plugins" / plugin_name / "main.py"
        old_content = script_path.read_text(encoding="utf-8", errors="replace") if script_path.is_file() else ""
        script_path.parent.mkdir(parents=True, exist_ok=True)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from kai.tools_plugins.contract import validate_plugin_source

        contract_errors = validate_plugin_source(new_content, plugin_id=plugin_name)
        if contract_errors:
            raise HTTPException(
                status_code=422,
                detail="Plugin contract validation failed: " + "; ".join(contract_errors),
            )
        script_path.write_text(new_content, encoding="utf-8")
        rel = str(script_path.relative_to(home))
        diff = "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
                lineterm="",
            )
        )
        return {"type": "plugin_file", "file": f"plugin:{plugin_name}", "path": rel, "diff": diff}

    return None


def apply_patches(home: Path, patches: list[dict[str, Any]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for patch in patches:
        result = apply_patch_item(home, patch)
        if result:
            results.append(result)
    return results


def preview_patches(home: Path, patches: list[dict[str, Any]]) -> list[dict[str, str]]:
    current_configs = current_config_files(home)
    previews: list[dict[str, str]] = []
    for patch in patches:
        ptype = (patch.get("type") or "config_file").strip()
        if ptype == "config_file" or ("file" in patch and "type" not in patch):
            file_key = (patch.get("file") or "").strip()
            new_content = patch.get("content", "")
            rel = CONFIG_FILES.get(file_key)
            if not rel:
                continue
            old = current_configs.get(file_key, "")
            diff = "".join(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                )
            )
            previews.append({"type": "config_file", "file": file_key, "path": rel, "diff": diff})
        elif ptype == "plugin_file":
            plugin_name = (patch.get("plugin_name") or "").strip()
            new_content = patch.get("content", "")
            if not plugin_name or not safe_plugin_name(plugin_name):
                continue
            script_path = home / "tools" / "plugins" / plugin_name / "main.py"
            old = script_path.read_text(encoding="utf-8", errors="replace") if script_path.is_file() else ""
            rel = f"tools/plugins/{plugin_name}/main.py"
            diff = "".join(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{rel}",
                    tofile=f"b/{rel}",
                    lineterm="",
                )
            )
            previews.append({"type": "plugin_file", "file": f"plugin:{plugin_name}", "path": rel, "diff": diff})
    return previews


def chat_completion(system: str, user: str, *, max_tokens: int = 4000, temperature: float = 0.25) -> str:
    api_key, base_url, model = make_deepseek_client()
    if not api_key:
        raise HTTPException(status_code=503, detail="AI unavailable: DEEPSEEK_API_KEY not configured.")
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    if not resp.ok:
        raise HTTPException(status_code=502, detail=f"LLM error {resp.status_code}")
    data = resp.json()
    return (data.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
