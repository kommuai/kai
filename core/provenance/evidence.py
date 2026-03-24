from typing import Any


def normalize_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": source.get("source_type", "unknown"),
        "repo": source.get("repo", ""),
        "path": source.get("path", ""),
        "commit_or_version": source.get("commit_or_version", ""),
        "retrieval_score": float(source.get("retrieval_score", 0.0)),
        "snippet": source.get("snippet", ""),
    }

