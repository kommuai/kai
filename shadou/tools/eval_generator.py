"""Synthetic eval pack generator for Shadou.

Reads ``compiled/corpus_map.json`` and ``compiled/kb_chunks.jsonl``
and produces a tenant-agnostic JSONL eval pack compatible with
``shadou.tools.eval_run``.

Usage:
    python -m shadou.tools.eval_generator [--out PATH] [--compiled-dir PATH]

Output JSONL schema (one item per line):
    {
        "question": "...",
        "expected_intent": "intent_id",
        "expected_decision": "direct_answer" | "abstain",
        "tags": ["lookup"] | ["multi_intent"] | ["unanswerable"],
        "source": "generated"
    }

Difficulty labels:
    lookup       — single alias of one intent (easiest, answers in one search)
    multi_intent — question that touches two related intents
    unanswerable — phrased so the corpus cannot answer; expected_decision=abstain
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _default_compiled_dir() -> Path:
    try:
        from shadou.settings import get_settings
        from shadou.workspace.manifest import load_workspace_manifest
        return get_settings().shadou_home / load_workspace_manifest().paths.knowledge_compiled_dir
    except Exception:  # noqa: BLE001
        return Path("compiled")


def _load_corpus_map(compiled_dir: Path) -> dict[str, Any]:
    p = compiled_dir / "corpus_map.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _load_chunks(compiled_dir: Path) -> list[dict[str, Any]]:
    p = compiled_dir / "kb_chunks.jsonl"
    if not p.is_file():
        return []
    items = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items


def _negate(phrase: str) -> str:
    """Best-effort negation for unanswerable variants."""
    phrase = phrase.strip()
    prefixes = ("how to ", "how do i ", "what is ", "where is ", "when is ", "can i ", "do you ")
    lp = phrase.lower()
    for pre in prefixes:
        if lp.startswith(pre):
            return f"why can't I {phrase[len(pre):]}"
    return f"unrelated topic: {phrase[:40]}"


def _slug_to_question(intent_id: str) -> str:
    """Turn an intent_id like 'product_warranty' into a readable question."""
    words = re.sub(r"[_-]+", " ", intent_id).strip()
    return f"What can you tell me about {words}?"


def generate_eval_pack(
    corpus_map: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate a deterministic eval pack from compiled knowledge."""
    intents: list[dict[str, Any]] = corpus_map.get("intents") or []
    if not intents:
        return []

    # Build a lookup: intent_id → first alias / title
    chunk_index: dict[str, str] = {}
    for c in chunks:
        sid = str(c.get("source_id") or "")
        if sid.startswith("faq:"):
            iid = sid[len("faq:"):]
            if iid not in chunk_index:
                chunk_index[iid] = str(c.get("text") or "")[:80]

    items: list[dict[str, Any]] = []

    for intent in intents:
        iid = str(intent.get("intent_id") or "").strip()
        if not iid:
            continue
        aliases: list[str] = [str(a) for a in (intent.get("aliases") or []) if str(a).strip()]
        title = str(intent.get("title") or "").strip() or _slug_to_question(iid)

        # --- lookup: use first alias as question ---
        question = aliases[0] if aliases else title
        items.append({
            "question": question,
            "expected_intent": iid,
            "expected_decision": "direct_answer",
            "tags": ["lookup"],
            "source": "generated",
        })

        # --- unanswerable: negated / off-topic variant of the alias ---
        unanswerable_q = _negate(question)
        items.append({
            "question": unanswerable_q,
            "expected_intent": "",
            "expected_decision": "abstain",
            "tags": ["unanswerable"],
            "source": "generated",
        })

    # --- multi_intent: pair consecutive intents ---
    for i in range(0, len(intents) - 1, 2):
        a = intents[i]
        b = intents[i + 1]
        a_aliases = [str(x) for x in (a.get("aliases") or []) if str(x).strip()]
        b_aliases = [str(x) for x in (b.get("aliases") or []) if str(x).strip()]
        q_a = a_aliases[0] if a_aliases else _slug_to_question(str(a.get("intent_id") or ""))
        q_b = b_aliases[0] if b_aliases else _slug_to_question(str(b.get("intent_id") or ""))
        items.append({
            "question": f"{q_a} and also {q_b}",
            "expected_intent": str(a.get("intent_id") or ""),
            "expected_decision": "direct_answer",
            "tags": ["multi_intent"],
            "source": "generated",
        })

    return items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Shadou synthetic eval generator")
    parser.add_argument("--out", default="eval_generated.jsonl", help="Output JSONL path")
    parser.add_argument("--compiled-dir", default=None, help="Path to compiled/ directory")
    args = parser.parse_args(argv)

    compiled_dir = Path(args.compiled_dir) if args.compiled_dir else _default_compiled_dir()

    corpus_map = _load_corpus_map(compiled_dir)
    if not corpus_map:
        print(f"No corpus_map.json found in {compiled_dir}", file=sys.stderr)
        return 1

    chunks = _load_chunks(compiled_dir)
    items = generate_eval_pack(corpus_map, chunks)

    out_path = Path(args.out)
    out_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items),
        encoding="utf-8",
    )
    print(f"Generated {len(items)} eval items → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
