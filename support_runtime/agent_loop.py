from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from support_runtime.agent_tools import AgentToolRegistry
from support_runtime.guardrails import safety_gate
from support_runtime.models import RuntimeResult

log = logging.getLogger("kai.agent_loop")

MAX_AGENT_STEPS = 8
MAX_RESPONSE_TOKENS = 1200


def _extract_json(raw: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", raw or "", flags=re.S)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _looks_like_chitchat(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    short = len(t.split()) <= 6
    markers = (
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "ok",
        "okay",
        "good morning",
        "good afternoon",
        "good evening",
    )
    return short and any(m in t for m in markers)


@dataclass
class AgentLoopDependencies:
    provider: Any
    tools: AgentToolRegistry
    system_prompt: str


class ReActAgentLoop:
    def __init__(self, deps: AgentLoopDependencies) -> None:
        self.deps = deps

    def run(
        self,
        *,
        text: str,
        lang: str = "EN",
        user_id: str = "",
        conversation_history: list[dict] | None = None,
    ) -> dict[str, Any]:
        ok, reason = safety_gate(text)
        if not ok:
            return {
                "result": RuntimeResult(
                    decision="escalate_human",
                    answer="I cannot help with that safely. I will connect you to a live agent.",
                    confidence=0.99,
                    escalate_needed=True,
                    capability_used="safety_gate",
                    fallback_reason=reason,
                )
            }

        messages: list[dict[str, str]] = [{"role": "system", "content": self.deps.system_prompt}]

        if conversation_history:
            for turn in conversation_history[-10:]:
                role = turn.get("role", "user")
                content = turn.get("text", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        lang_hint = " (User writes in Malay)" if lang == "BM" else ""
        messages.append({"role": "user", "content": f"{text}{lang_hint}"})

        source_ids: list[str] = []
        tool_trace: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        answer = ""
        decision = "clarifying_question"
        confidence = 0.5
        fallback_reason = ""
        user_chitchat = _looks_like_chitchat(text)

        for step in range(MAX_AGENT_STEPS):
            raw = self.deps.provider.chat_messages(
                messages, temperature=0.15, max_tokens=MAX_RESPONSE_TOKENS
            )
            log.debug("Agent step %d raw: %s", step + 1, raw[:300])
            parsed = _extract_json(raw)

            if not parsed:
                fallback_reason = "invalid_agent_json"
                messages.append({"role": "assistant", "content": raw})
                messages.append({
                    "role": "user",
                    "content": "Please respond with ONLY a JSON object as instructed.",
                })
                continue

            action = str(parsed.get("action", "")).strip().lower()

            if action == "tool":
                tool_name = str(parsed.get("tool", "")).strip()
                args = parsed.get("args") or {}
                if not isinstance(args, dict):
                    args = {}

                result = self.deps.tools.call(tool_name, args)
                observations.append({"tool": tool_name, "args": args, "result": result})
                tool_trace.append({"step": step + 1, "tool": tool_name, "ok": bool(result.get("ok"))})
                if result.get("ok"):
                    source_ids.append(f"tool:{tool_name}")

                result_summary = json.dumps(result, ensure_ascii=False, default=str)
                max_tool_chars = 80_000 if tool_name == "read_bukapilot_file" else 2000
                if len(result_summary) > max_tool_chars:
                    result_summary = result_summary[:max_tool_chars] + "..."

                messages.append({"role": "assistant", "content": json.dumps(parsed)})
                messages.append({
                    "role": "user",
                    "content": f"Tool result for {tool_name}:\n{result_summary}\n\nContinue reasoning. Call another tool or give your final answer.",
                })
                continue

            if action == "final":
                answer = str(parsed.get("answer", "")).strip()
                decision = str(parsed.get("decision", "direct_answer")).strip()
                if decision not in ("direct_answer", "clarifying_question", "escalate_human"):
                    decision = "direct_answer"
                confidence = float(parsed.get("confidence", 0.85) or 0.85)
                for sid in parsed.get("source_ids") or []:
                    if isinstance(sid, str) and sid:
                        source_ids.append(sid)
                fallback_reason = str(parsed.get("fallback_reason", "")).strip()
                break

            answer_text = parsed.get("answer", "")
            if answer_text:
                answer = str(answer_text).strip()
                decision = str(parsed.get("decision", "direct_answer")).strip()
                confidence = float(parsed.get("confidence", 0.75) or 0.75)
                break

        if not answer:
            if any(obs.get("result", {}).get("escalate") for obs in observations):
                decision = "escalate_human"
                answer = "Let me connect you to a live agent who can help further."
                confidence = 0.9
            elif observations:
                messages.append({
                    "role": "user",
                    "content": "Based on all the tool results above, give a concise final answer to the user. Output JSON: {\"action\":\"final\",\"answer\":\"...\",\"decision\":\"direct_answer\",\"confidence\":0.8}",
                })
                raw = self.deps.provider.chat_messages(
                    messages, temperature=0.15, max_tokens=MAX_RESPONSE_TOKENS
                )
                parsed = _extract_json(raw)
                if parsed and parsed.get("answer"):
                    answer = str(parsed["answer"]).strip()
                    decision = str(parsed.get("decision", "direct_answer"))
                    confidence = float(parsed.get("confidence", 0.75) or 0.75)
                else:
                    answer = "I found some information but need one more detail to avoid guessing. Could you clarify your model/year or the exact error shown?"
                    decision = "clarifying_question"
                    confidence = 0.55
            else:
                decision = "clarifying_question"
                answer = "Could you share a bit more detail so I can help you better?"
                fallback_reason = fallback_reason or "no_signal"

        has_tool_evidence = any(bool(obs.get("result", {}).get("ok")) for obs in observations)
        has_source_ids = bool(source_ids)
        if decision == "direct_answer" and not user_chitchat and not (has_tool_evidence or has_source_ids):
            if confidence >= 0.65:
                decision = "clarifying_question"
                confidence = 0.55
                fallback_reason = fallback_reason or "ungrounded_answer_blocked"
                answer = "I want to make sure I give you accurate info. Could you share one more detail so I can confirm the facts?"
            else:
                confidence = min(confidence, 0.55)

        return {
            "result": RuntimeResult(
                decision=decision,  # type: ignore[arg-type]
                answer=answer,
                confidence=max(0.0, min(1.0, confidence)),
                source_ids=sorted(set(source_ids)),
                tool_needed=bool(observations),
                escalate_needed=(decision == "escalate_human"),
                capability_used="react_agent_loop",
                fallback_reason=fallback_reason,
                metadata={
                    "agentic_route": {"steps": tool_trace},
                    "evidence": {"observations": observations},
                },
            )
        }
