#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Repo root on sys.path for config
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main():
    import yaml

    from shadou.workspace.manifest import load_workspace_data, workspace_yaml_path

    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="context id, e.g. public_repo")
    args = ap.parse_args()
    context_id = args.id.strip()
    path = workspace_yaml_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file():
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        doc = {"version": "2", "contexts": []}
    if not isinstance(doc, dict):
        doc = {"version": "2", "contexts": []}
    items = doc.get("contexts")
    if not isinstance(items, list):
        items = []
        doc["contexts"] = items

    if any(isinstance(x, dict) and x.get("id") == context_id for x in items):
        print(f"Context {context_id!r} already in {path}")
        return

    items.append(
        {
            "id": context_id,
            "enabled": True,
            "kind": "generic",
            "config": {"notes": "fill provider config"},
        }
    )
    path.write_text(
        yaml.safe_dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    print(f"Appended context to {path}")


if __name__ == "__main__":
    main()
