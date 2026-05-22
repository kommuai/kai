from openai import OpenAI

from kai.settings import get_settings

_s = get_settings()
_client = OpenAI(api_key=_s.deepseek_api_key, base_url=_s.deepseek_base_url)


def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 500) -> str:
    if not (_s.deepseek_api_key or "").strip():
        print("[LLM] SKIP — no DEEPSEEK_API_KEY")
        return ""
    resp = _client.chat.completions.create(
        model=_s.deepseek_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()
