from __future__ import annotations

import os
import re
import subprocess

import requests

from config import BUKAPILOT_BRANCH, BUKAPILOT_LOCAL_PATH, BUKAPILOT_REPO
from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult


class BukapilotBacklogSearchSkill:
    skill_id = "bukapilot_backlog_search"
    version = "0.1.0"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        txt = (request.text or "").lower()
        keys = {"backlog", "diagnostic", "error", "bug", "issue", "bukapilot", "possible solution"}
        score = 0.0
        for k in keys:
            if k in txt:
                score += 0.15
        if "ka2" in txt or "ka1" in txt:
            score += 0.1
        return min(0.99, score)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) >= 4][:6]

    def search_hits(self, issue_text: str, branch: str | None = None, max_hits: int = 3) -> list[dict]:
        branch = (branch or BUKAPILOT_BRANCH).strip() or "release_ka2"
        tokens = self._tokens(issue_text)
        if not tokens:
            return []

        # Prefer local search for deterministic branch context.
        if BUKAPILOT_LOCAL_PATH and os.path.isdir(BUKAPILOT_LOCAL_PATH):
            try:
                pattern = "|".join(re.escape(t) for t in tokens)
                proc = subprocess.run(
                    ["rg", "-n", "-i", "--max-count", "1", "-e", pattern, "."],
                    cwd=BUKAPILOT_LOCAL_PATH,
                    capture_output=True,
                    text=True,
                    timeout=8,
                    check=False,
                )
                if proc.returncode in (0, 1):
                    out = []
                    for line in (proc.stdout or "").splitlines():
                        if len(out) >= max_hits:
                            break
                        parts = line.split(":", 2)
                        if len(parts) < 3:
                            continue
                        path, line_no, snippet = parts[0], parts[1], parts[2]
                        out.append(
                            {
                                "path": path,
                                "line": line_no,
                                "snippet": snippet.strip()[:180],
                                "url": f"https://github.com/{BUKAPILOT_REPO}/blob/{branch}/{path}#L{line_no}",
                                "source": "local-rg",
                            }
                        )
                    if out:
                        return out
            except Exception:
                pass

        query = "+".join(tokens + [f"repo:{BUKAPILOT_REPO}"])
        headers = {}
        if os.getenv("KAI_GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.getenv('KAI_GITHUB_TOKEN')}"
        try:
            resp = requests.get(
                f"https://api.github.com/search/code?q={query}",
                headers=headers,
                timeout=12,
            )
            if not resp.ok:
                return []
            items = (resp.json() or {}).get("items", [])[:max_hits]
            out = []
            for item in items:
                path = item.get("path", "")
                if not path:
                    continue
                out.append(
                    {
                        "path": path,
                        "line": "",
                        "snippet": "",
                        "url": f"https://github.com/{BUKAPILOT_REPO}/blob/{branch}/{path}",
                        "source": "github-code-search",
                    }
                )
            return out
        except Exception:
            return []

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        branch = (request.metadata or {}).get("branch") or BUKAPILOT_BRANCH
        hits = self.search_hits(request.text, branch=branch, max_hits=3)
        if not hits:
            return self.degrade("no_matching_bukapilot_hits")
        evidence = "; ".join(f"{h.get('path')} ({h.get('url')})" for h in hits if h.get("path") and h.get("url"))
        answer = f"Cross-check on {branch}: {evidence}"
        return CapabilityResult(
            ok=True,
            answer=answer,
            capability_used=self.skill_id,
            confidence=0.72,
            sources=hits,
            metadata={"branch": branch, "repo": BUKAPILOT_REPO},
        )

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)
