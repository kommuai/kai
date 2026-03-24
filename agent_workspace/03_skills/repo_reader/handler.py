import base64
import os
from pathlib import Path
import re

import requests

from core.skills.contracts import SkillBudget, SkillContextBundle
from core.types import CapabilityRequest, CapabilityResult


class RepoReaderSkill:
    skill_id = "repo_reader"
    version = "0.2.0"
    api_base = "https://api.github.com"
    allowed_org = "kommuai"

    def can_handle(self, request: CapabilityRequest, context_meta: dict) -> float:
        txt = request.text.lower()
        # Make repo lookup the default first-pass skill for general company knowledge.
        if any(k in txt for k in ["repo", "code", "function", "file", "commit", "github", "kommuai"]):
            return 0.99
        return 0.92

    def _headers(self) -> dict:
        token = os.getenv("KAI_GITHUB_TOKEN", "").strip()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "kai-repo-reader",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _search_public_repos(self, org: str, limit: int = 8) -> list[dict]:
        url = f"{self.api_base}/orgs/{org}/repos"
        r = requests.get(url, params={"per_page": limit, "type": "public", "sort": "updated"}, headers=self._headers(), timeout=8)
        r.raise_for_status()
        return r.json()

    def _readme_text(self, org: str, repo: str) -> str:
        url = f"{self.api_base}/repos/{org}/{repo}/readme"
        r = requests.get(url, headers=self._headers(), timeout=8)
        if not r.ok:
            return ""
        payload = r.json()
        content = payload.get("content", "")
        if not content:
            return ""
        try:
            raw = base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            return ""
        return re.sub(r"\s+", " ", raw).strip()

    def _best_repo_match(self, query: str, repos: list[dict]) -> tuple[dict | None, float]:
        q_terms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
        if not q_terms:
            return (repos[0], 0.3) if repos else (None, 0.0)
        best = None
        best_score = 0.0
        for repo in repos:
            name = (repo.get("name") or "").lower()
            desc = (repo.get("description") or "").lower()
            readme = self._readme_text(repo.get("owner", {}).get("login", ""), repo.get("name", ""))
            haystack = f"{name} {desc} {readme.lower()[:4000]}"
            score = 0.0
            for t in q_terms:
                if t in name:
                    score += 2.0
                elif t in desc:
                    score += 1.0
                elif t in haystack:
                    score += 0.5
            if score > best_score:
                best = repo
                best_score = score
        if not best and repos:
            return repos[0], 0.3
        return best, min(0.95, 0.3 + (best_score / max(1, len(q_terms))) * 0.2)

    def execute(self, request: CapabilityRequest, context_bundle: SkillContextBundle, budget: SkillBudget) -> CapabilityResult:
        # Hard-lock public repo lookup to kommuai org only.
        org = self.allowed_org
        try:
            repos = self._search_public_repos(org)
            if not repos:
                return self.degrade("no_public_repos_found")
            best, conf = self._best_repo_match(request.text, repos)
            if not best:
                return self.degrade("repo_match_not_found")
            owner = best.get("owner", {}).get("login", org)
            repo_name = best.get("name", "")
            repo_url = best.get("html_url", "")
            default_branch = best.get("default_branch", "")
            desc = best.get("description") or "No description."
            answer = (
                f"Best public repo match from {org}: {repo_name}. "
                f"{desc} Repository: {repo_url}"
            )
            return CapabilityResult(
                ok=True,
                answer=answer,
                capability_used=self.skill_id,
                confidence=conf,
                sources=[
                    {
                        "source_type": "repo",
                        "repo": f"{owner}/{repo_name}",
                        "path": "README.md",
                        "commit_or_version": default_branch,
                        "retrieval_score": conf,
                        "snippet": desc,
                    }
                ],
            )
        except Exception as exc:  # noqa: BLE001
            # Backward-compatible local repo fallback if configured.
            allow = os.getenv("KAI_ALLOWED_REPO_ROOT", "").strip()
            if allow:
                root = Path(allow)
                if root.exists():
                    candidates = sorted([p for p in root.rglob("*.py")][:20])
                    if candidates:
                        top = candidates[0]
                        return CapabilityResult(
                            ok=True,
                            answer=f"Repo context fallback (local) file: {top}",
                            capability_used=self.skill_id,
                            confidence=0.4,
                            sources=[
                                {
                                    "source_type": "repo_local",
                                    "path": str(top),
                                    "repo": root.name,
                                    "retrieval_score": 0.4,
                                    "snippet": "local filesystem fallback",
                                }
                            ],
                            fallback_reason=f"github_lookup_failed:{exc}",
                        )
            return self.degrade(f"github_lookup_failed:{exc}")

    def degrade(self, reason: str) -> CapabilityResult:
        return CapabilityResult(ok=False, fallback_reason=reason, capability_used=self.skill_id)
