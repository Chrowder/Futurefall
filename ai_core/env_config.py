import os
from pathlib import Path
from typing import Iterable, Dict

_ENV_LOADED = False


def load_dotenv_file(env_path: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv_fallback(env_path)
        return

    load_dotenv(dotenv_path=env_path)


def load_dotenv_fallback(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def load_local_env() -> None:
    global _ENV_LOADED

    if _ENV_LOADED:
        return

    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv_file(env_path)
    _ENV_LOADED = True


def env_presence(var_names: Iterable[str]) -> Dict[str, bool]:
    load_local_env()
    return {name: bool(os.getenv(name)) for name in var_names}
