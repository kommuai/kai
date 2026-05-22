from openai import OpenAI
import os

_api_key = os.getenv("DEEPSEEK_API_KEY", "")
_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

_client = OpenAI(api_key=_api_key, base_url=_base)

def chat_completion(system_prompt: str, user_prompt: str) -> str:
    if not _api_key:
        print("[LLM] SKIP — no DEEPSEEK_API_KEY")
        return ""
    resp = _client.chat.completions.create(
        model=_model,
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_prompt}
        ],
        temperature=0.3,
        max_tokens=450,
    )
    return (resp.choices[0].message.content or "").strip()
