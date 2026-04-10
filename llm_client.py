"""
llm_client.py
"""
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_ENDPOINT = os.getenv("API_ENDPOINT", "")
API_KEY = os.getenv("API_KEY", "")
MODEL = os.getenv("MODEL", "")



def call_llm(
    messages: list[dict],
    system_prompt: str = "",
    temperature: float = 0.3,
    max_tokens: int = 4096,
    json_mode: bool = False,
) -> str:
    """
    Call the LLM endpoint. Returns the assistant message text.
    Falls back to OpenAI-compatible /v1/chat/completions endpoint.
    """
    endpoint = API_ENDPOINT.rstrip("/") + "/v1/chat/completions"

    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    payload = {
        "model": MODEL,
        "messages": full_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        # Return a structured error message so callers can handle gracefully
        return json.dumps({"error": str(e), "fallback": True})


def call_llm_json(messages: list[dict], system_prompt: str = "") -> dict:
    """Convenience wrapper that always returns parsed JSON."""
    raw = call_llm(messages, system_prompt=system_prompt, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown fences
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass
        return {"error": "Failed to parse JSON", "raw": raw}
