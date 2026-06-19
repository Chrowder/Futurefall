import json
import os
from typing import Optional
from urllib import error, request


def generate_text(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int = 700,
) -> str:
    if not api_key:
        raise ValueError("OpenAI-compatible API key is missing.")
    if not base_url:
        raise ValueError("OpenAI-compatible base URL is missing.")
    if not model:
        raise ValueError("OpenAI-compatible model is missing.")

    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))

    try:
        from openai import OpenAI
    except ImportError:
        return generate_text_with_urllib(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
    )

    choice = response.choices[0] if response.choices else None
    message = getattr(choice, "message", None)
    content: Optional[str] = getattr(message, "content", None)
    return (content or "").strip()


def generate_text_with_urllib(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int,
    timeout: float,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=timeout) as response:
            raw_response = response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(
            f"OpenAI-compatible provider returned HTTP {exc.code}. Check provider, model, and API settings."
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(
            "OpenAI-compatible provider connection failed. Check base URL and network access."
        ) from exc

    parsed = json.loads(raw_response)
    choices = parsed.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    return (message.get("content") or "").strip()
