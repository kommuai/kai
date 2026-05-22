#!/usr/bin/env python3
"""Deprecated: production tools live in support_runtime/agent_tools.py.

Scaffolds agent_workspace/03_skills/<id>/skill.md only (handler stubs removed).
"""
import argparse
from pathlib import Path

TEMPLATE_SKILL_MD = """---
id: {skill_id}
version: "0.1.0"
enabled: false
permissions:
  - public_info.read
---

# {skill_id}

Document the skill here. Implement runtime behavior in `kai/support_runtime/agent_tools.py`.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="skill id, e.g. stock_lookup")
    args = ap.parse_args()
    skill_id = args.id.strip()

    base = Path(__file__).resolve().parents[1]
    ws = base / "agent_workspace" / "03_skills" / skill_id
    ws.mkdir(parents=True, exist_ok=True)
    skill_md = ws / "skill.md"
    if not skill_md.exists():
        skill_md.write_text(TEMPLATE_SKILL_MD.format(skill_id=skill_id), encoding="utf-8")
    print(f"Created agent_workspace/03_skills/{skill_id}/skill.md")


if __name__ == "__main__":
    main()
