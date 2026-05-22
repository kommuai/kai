#!/usr/bin/env python3
"""Deprecated: workspace skill handlers are no longer used in production chat.

Add capabilities via support_runtime/agent_tools.py and master_faq.md instead.
"""
import argparse
from pathlib import Path

TEMPLATE_HANDLER = '''from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult


class {class_name}:
    skill_id = "{skill_id}"
    version = "0.1.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        return 0.0

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        return CapabilityResult(ok=False, capability_used=self.skill_id, fallback_reason="not_implemented")

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, capability_used=self.skill_id, fallback_reason=reason)
'''

TEMPLATE_SKILL_MD = """---
id: {skill_id}
version: "0.1.0"
enabled: true
handler_class: {class_name}
timeout_ms: 8000
retry_count: 1
permissions:
  - public_info.read
---

# {skill_id}

"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="skill id, e.g. stock_lookup")
    args = ap.parse_args()
    skill_id = args.id.strip()
    class_name = "".join([p.capitalize() for p in skill_id.split("_")]) + "Skill"

    base = Path(__file__).resolve().parents[1]
    ws = base / "agent_workspace" / "03_skills" / skill_id

    ws.mkdir(parents=True, exist_ok=True)
    skill_md = ws / "skill.md"
    handler_py = ws / "handler.py"

    if not skill_md.exists():
        skill_md.write_text(
            TEMPLATE_SKILL_MD.format(skill_id=skill_id, class_name=class_name),
            encoding="utf-8",
        )
    if not handler_py.exists():
        handler_py.write_text(
            TEMPLATE_HANDLER.format(skill_id=skill_id, class_name=class_name),
            encoding="utf-8",
        )
    print(f"Created agent_workspace/03_skills/{skill_id}/skill.md and handler.py")


if __name__ == "__main__":
    main()
