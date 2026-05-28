"""AI Assist — scoped DeepSeek chat that can read and patch tenant config files + plugin scripts."""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Generator

import requests
import yaml
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from deps import get_current_user
from models import User
from routers.tenants_router import _assert_tenant_member

log = logging.getLogger("kai.ai_assist")

router = APIRouter(prefix="/tenants", tags=["ai-assist"])

# ── config files directly editable ───────────────────────────────────────────
_CONFIG_FILES: dict[str, str] = {
    "workspace":     "workspace.yaml",
    "system_prompt": "system_prompt.md",
    "faq":           "knowledge/master_faq.md",
}

# ── plugin contract template (shown to the AI) ────────────────────────────────
_PLUGIN_TEMPLATE = '''\
"""<one-line description of what this plugin does>"""
import json
import sys


def main():
    req = json.load(sys.stdin)
    args = req.get("args") or {}
    # TODO: implement plugin logic here
    print(json.dumps({"ok": True, "result": {}}))


if __name__ == "__main__":
    main()
'''

# ── system prompt for the assistant ──────────────────────────────────────────
_SYSTEM_PROMPT = """
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
- `plugin_file`: creates or overwrites `tools/plugins/<plugin_name>/main.py`. `plugin_name` must be snake_case letters, numbers, underscores only.

ALWAYS provide the FULL file content — never partial snippets or diffs.
ALWAYS preserve YAML / Markdown / Python formatting exactly.

### workspace.yaml: skills/profile_overrides structure
```yaml
tools_profile:
  active_profile: default
  profiles:
    default:
      - my_skill_id
  profile_overrides:
    my_skill_id:
      id: my_skill_id
      enabled: true          # set false to disable
      description: "What this skill does"
      plugin: tools/plugins/my_plugin/main.py   # path for plugin skills
```
To add a new plugin skill:
1. Add its id to `profiles.default` list.
2. Add an entry under `profile_overrides` with `plugin` pointing to the script.
3. Include a `plugin_file` patch with the Python implementation.

To disable: set `enabled: false` in its `profile_overrides` entry.
To remove: delete the id from `profiles.default` AND its `profile_overrides` entry.

### Plugin Python contract
Every plugin reads JSON from stdin and writes JSON to stdout:
```python
import json, sys
req = json.load(sys.stdin)
args = req.get("args") or {}
# do work…
print(json.dumps({"ok": True, "result": {…}}))
```

## Tone and flow
- Be warm, clear, and encouraging.
- Ask ONE question at a time.
- Confirm what you understood before writing any patch.
- Keep responses short — 3–5 sentences unless showing the patch block.
- If the user seems confused, explain in simpler terms.
""".strip()


def _make_deepseek_client() -> tuple[str, str, str]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from kai.settings import get_settings
    s = get_settings()
    api_key = (s.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY") or "").strip()
    base_url = (s.deepseek_base_url or "https://api.deepseek.com/v1").rstrip("/")
    model = (s.deepseek_model or "deepseek-chat").strip()
    return api_key, base_url, model


def _safe_plugin_name(name: str) -> bool:
    """Ensure plugin_name is a safe path component (no traversal)."""
    return bool(re.fullmatch(r"[a-zA-Z0-9_]+", name))


def _current_config_files(home: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, rel in _CONFIG_FILES.items():
        p = home / rel
        out[key] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
    return out


def _current_plugins(home: Path) -> list[dict[str, str]]:
    """Return list of {name, path, content} for existing plugin scripts."""
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


def _current_skills_summary(home: Path) -> str:
    """Build a plain-text summary of current skills from workspace.yaml."""
    try:
        from kai_capabilities import get_capabilities
        caps = get_capabilities(home)
        skills = caps.get("skills") or []
        if not skills:
            return "No skills configured yet."
        lines = []
        for s in skills:
            status = "✅ enabled" if s.get("enabled") else "🚫 disabled"
            src = "plugin" if s.get("plugin") else ("builtin" if s.get("builtin") else "document")
            lines.append(f"- `{s['id']}` [{src}] {status} — {s.get('description','')[:80]}")
        return "\n".join(lines)
    except Exception:
        return "(Could not load skills list)"


def _build_context(home: Path) -> str:
    files = _current_config_files(home)
    plugins = _current_plugins(home)

    parts: list[str] = []

    # Config files
    for key, content in files.items():
        rel = _CONFIG_FILES[key]
        parts.append(f"### Current {key} ({rel}):\n```\n{content[:8000]}\n```")

    # Skills summary
    skills_sum = _current_skills_summary(home)
    parts.append(f"### Current skills overview:\n{skills_sum}")

    # Plugin scripts
    if plugins:
        for p in plugins:
            parts.append(f"### Plugin script `{p['path']}`:\n```python\n{p['content']}\n```")
    else:
        parts.append(f"### Plugin template (for reference when creating new plugins):\n```python\n{_PLUGIN_TEMPLATE}\n```")

    return "\n\n".join(parts)


def _compute_diff(old: str, new: str, filename: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    ))


def _extract_patch(text: str) -> dict[str, Any] | None:
    m = re.search(r"```kai-patch\s*(\{.*?\})\s*```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def _apply_patch_item(home: Path, patch: dict[str, Any]) -> dict[str, str] | None:
    """Apply one patch item; returns result dict or None if skipped."""
    ptype = (patch.get("type") or "config_file").strip()

    if ptype == "config_file" or "file" in patch and "type" not in patch:
        # Backward-compat: old format had no "type" field.
        file_key = (patch.get("file") or "").strip()
        new_content = patch.get("content", "")
        rel = _CONFIG_FILES.get(file_key)
        if not rel:
            return None
        p = home / rel
        old_content = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        if file_key == "workspace":
            try:
                yaml.safe_load(new_content)
            except yaml.YAMLError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid YAML in proposed workspace patch: {exc}") from exc
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(new_content, encoding="utf-8")
        diff = _compute_diff(old_content, new_content, rel)
        return {"type": "config_file", "file": file_key, "path": rel, "diff": diff, "new_content": new_content}

    if ptype == "plugin_file":
        plugin_name = (patch.get("plugin_name") or "").strip()
        new_content = patch.get("content", "")
        if not plugin_name or not _safe_plugin_name(plugin_name):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid plugin_name '{plugin_name}'. Use snake_case letters and underscores only.",
            )
        script_path = home / "tools" / "plugins" / plugin_name / "main.py"
        old_content = script_path.read_text(encoding="utf-8", errors="replace") if script_path.is_file() else ""
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(new_content, encoding="utf-8")
        rel = str(script_path.relative_to(home))
        diff = _compute_diff(old_content, new_content, rel)
        return {"type": "plugin_file", "file": f"plugin:{plugin_name}", "path": rel, "diff": diff, "new_content": new_content}

    return None


def _apply_patches(home: Path, patches: list[dict[str, Any]]) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for patch in patches:
        result = _apply_patch_item(home, patch)
        if result:
            results.append(result)
    return results


def _preview_patches(home: Path, patches: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build diff previews WITHOUT writing anything."""
    current_configs = _current_config_files(home)
    previews: list[dict[str, str]] = []

    for patch in patches:
        ptype = (patch.get("type") or "config_file").strip()

        if ptype == "config_file" or "file" in patch and "type" not in patch:
            file_key = (patch.get("file") or "").strip()
            new_content = patch.get("content", "")
            rel = _CONFIG_FILES.get(file_key)
            if not rel:
                continue
            old = current_configs.get(file_key, "")
            diff = _compute_diff(old, new_content, rel)
            previews.append({"type": "config_file", "file": file_key, "path": rel, "diff": diff})

        elif ptype == "plugin_file":
            plugin_name = (patch.get("plugin_name") or "").strip()
            new_content = patch.get("content", "")
            if not plugin_name or not _safe_plugin_name(plugin_name):
                continue
            script_path = home / "tools" / "plugins" / plugin_name / "main.py"
            old = script_path.read_text(encoding="utf-8", errors="replace") if script_path.is_file() else ""
            rel = f"tools/plugins/{plugin_name}/main.py"
            diff = _compute_diff(old, new_content, rel)
            previews.append({"type": "plugin_file", "file": f"plugin:{plugin_name}", "path": rel, "diff": diff})

    return previews


# ── endpoint ─────────────────────────────────────────────────────────────────

@router.post("/{tenant_id}/ai-assist/chat")
def ai_assist_chat(
    tenant_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    body: {
      messages: [{role: "user"|"assistant", content: str}],
      apply_patches: bool
    }
    Streams SSE:
      data: {"type": "delta", "content": "..."}
      data: {"type": "done", "patches": [...], "summary": "..."}
    """
    t = _assert_tenant_member(tenant_id, user, db)
    home = Path(t.workspace_home).resolve()

    messages: list[dict] = body.get("messages") or []
    apply: bool = bool(body.get("apply_patches", False))

    # ── apply mode ────────────────────────────────────────────────────────────
    if apply:
        last_assistant = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "assistant"),
            None,
        )
        if last_assistant:
            patch_block = _extract_patch(last_assistant)
            if patch_block and patch_block.get("patches"):
                applied = _apply_patches(home, patch_block["patches"])
                return {"ok": True, "applied": applied, "summary": patch_block.get("summary", "")}
        return {"ok": False, "error": "No patch found in last assistant message"}

    # ── chat mode ─────────────────────────────────────────────────────────────
    api_key, base_url, model = _make_deepseek_client()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="AI Assist unavailable: DEEPSEEK_API_KEY not configured.",
        )

    ctx = _build_context(home)
    sys_msg = _SYSTEM_PROMPT + f"\n\n---\n\n{ctx}"
    full_messages = [{"role": "system", "content": sys_msg}, *messages]

    def _stream() -> Generator[str, None, None]:
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": full_messages,
                    "temperature": 0.3,
                    "max_tokens": 3000,
                    "stream": True,
                },
                stream=True,
                timeout=90,
            )
            if not resp.ok:
                yield f"data: {json.dumps({'type': 'error', 'content': f'LLM error {resp.status_code}'})}\n\n"
                return

            full_text = ""
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                        delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if delta:
                            full_text += delta
                            yield f"data: {json.dumps({'type': 'delta', 'content': delta})}\n\n"
                    except Exception:
                        continue

            patch_block = _extract_patch(full_text)
            patches_preview: list[dict[str, str]] = []
            if patch_block and patch_block.get("patches"):
                patches_preview = _preview_patches(home, patch_block["patches"])

            yield f"data: {json.dumps({'type': 'done', 'patches': patches_preview, 'summary': patch_block.get('summary', '') if patch_block else ''})}\n\n"
        except Exception as exc:
            log.exception("AI assist stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(exc)})}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
