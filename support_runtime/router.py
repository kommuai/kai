from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Callable

from config import AGENT_WORKSPACE
from support_runtime.models import IntentRecord, RouteType


INTENTS_PATH = Path(AGENT_WORKSPACE) / "compiled" / "intents.json"


def _terms(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t}


class IntentRouter:
    def __init__(self, classifier: Callable[[str, list[str]], tuple[str, float]] | None = None) -> None:
        self.intents: list[IntentRecord] = []
        self.classifier = classifier

    def _llm_route_hint(self, text: str) -> tuple[RouteType, float] | None:
        if not self.classifier:
            return None
        labels: list[RouteType] = [
            "vehicle_support_check_intent",
            "known_faq_intent",
            "troubleshooting_intent",
            "account_order_status_intent",
            "unsafe_human_escalation",
            "unsupported_ambiguous",
        ]
        try:
            label, conf = self.classifier(
                (
                    "Classify support intent. Vehicle_support is for questions about whether a car/model/trim is "
                    "supported, compatible, has ACC/LKA requirements, CAN/FlexRay checks, or installation feasibility.\n"
                    f"Message: {text}"
                ),
                labels,
            )
        except Exception:
            return None
        if label in labels and conf >= 0.68:
            return label, conf
        return None

    def load(self) -> None:
        self.intents = []
        if not INTENTS_PATH.exists():
            return
        payload = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
        for row in payload:
            self.intents.append(
                IntentRecord(
                    intent_id=row.get("intent_id", ""),
                    route_type=row.get("route_type", "known_faq_intent"),
                    aliases=row.get("aliases", []),
                    canonical_answer=row.get("canonical_answer", ""),
                    policy_flags=row.get("policy_flags", []),
                    metadata=row.get("metadata", {}),
                )
            )

    def route(self, text: str) -> tuple[RouteType, float, IntentRecord | None]:
        rt, conf, intent, _ = self.route_with_meta(text)
        return rt, conf, intent

    def route_with_meta(self, text: str) -> tuple[RouteType, float, IntentRecord | None, dict]:
        t = (text or "").lower().strip()
        meta = {
            "is_diagnostic": any(k in t for k in ("error", "issue", "diagnostic", "not working", "cannot", "can't")),
            "product_class": "unknown_product",
            "exact_match_required": False,
        }
        if any(k in t for k in ("ka2", "kommuassist 2", "kommu assist 2")):
            meta["product_class"] = "KA2"
        elif any(k in t for k in ("ka1", "ka1s", "1s", "kommuassist 1")):
            meta["product_class"] = "KA1/1s"

        if meta["is_diagnostic"]:
            meta["exact_match_required"] = True

        has_warranty_phrase = any(k in t for k in ("warranty", "waranti", "dongle", "check warranty"))
        bare_dongle_like = bool(re.fullmatch(r"[a-z0-9\-_]{6,24}", t))
        if has_warranty_phrase or bare_dongle_like:
            return "warranty_lookup_intent", 0.9 if bare_dongle_like else 0.84, None, meta

        if any(k in t for k in ("refund", "cancel order", "angry", "complaint", "human agent", "live agent")):
            return "unsafe_human_escalation", 0.92, None, meta

        if any(k in t for k in ("order", "shipment", "tracking", "payment status", "paid")):
            return "account_order_status_intent", 0.85, None, meta

        if any(
            k in t
            for k in (
                "supported car",
                "is my car supported",
                "is this car supported",
                "vehicle support",
                "car support",
                "can bus",
                "flexray",
                "acc",
                "lka",
            )
        ):
            return "vehicle_support_check_intent", 0.88, None, meta
        if "supported" in t and any(
            b in t
            for b in (
                "car",
                "vehicle",
                "perodua",
                "proton",
                "honda",
                "toyota",
                "byd",
                "lexus",
                "bmw",
                "audi",
                "mercedes",
                "mazda",
            )
        ):
            return "vehicle_support_check_intent", 0.82, None, meta

        # LLM-assisted intent routing for ambiguous/weak keyword cases.
        hinted = self._llm_route_hint(t)
        if hinted:
            rt, conf = hinted
            return rt, conf, None, meta

        q = _terms(t)
        best: IntentRecord | None = None
        best_score = 0.0
        for intent in self.intents:
            alias_terms = _terms(" ".join(intent.aliases))
            overlap = len(q.intersection(alias_terms))
            if overlap <= 0:
                continue
            score = overlap / max(1, len(q))
            if score > best_score:
                best = intent
                best_score = score
        if best and best_score >= 0.6:
            return best.route_type, min(0.99, best_score), best, meta
        if best and best_score >= 0.3:
            return best.route_type, best_score, best, meta
        return "unsupported_ambiguous", 0.2, None, meta
