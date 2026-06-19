import os
from typing import Optional

from ai_core.env_config import load_local_env
from ai_core.llm_clients.openai_compatible_client import generate_text as generate_openai_compatible_text

load_local_env()

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
) -> str:
    return generate_openai_compatible_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        api_key=os.getenv("OPENAI_API_KEY", ""),
        base_url=os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL,
        model=model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
    )
