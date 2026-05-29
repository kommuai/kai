from __future__ import annotations

from openai import OpenAI

from kai.settings import get_settings

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        s = get_settings()
        _client = OpenAI(api_key=s.deepseek_api_key, base_url=s.deepseek_base_url)
    return _client


def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 500) -> str:
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        print("[LLM] SKIP — no DEEPSEEK_API_KEY")
        return ""
    resp = _get_client().chat.completions.create(
        model=s.deepseek_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        from kai.lib.llm_usage_record import record_openai_usage

        record_openai_usage(
            model=s.deepseek_model,
            usage=getattr(resp, "usage", None),
            source="engine_tool",
        )
    except Exception:
        pass
    return (resp.choices[0].message.content or "").strip()
