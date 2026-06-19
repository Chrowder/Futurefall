import asyncio
import contextlib
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator

from thenvoi import Agent
from thenvoi.config import load_agent_config
from thenvoi.core.protocols import AgentToolsProtocol
from thenvoi.core.simple_adapter import SimpleAdapter
from thenvoi.core.types import PlatformMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_core.case_state_store import append_audit_event, load_case_state, save_case_state
from ai_core.env_config import load_local_env
from ai_core.data_providers.evidence_builder import build_evidence_pack

DEFAULT_CASE_ID = "AAPL-001"
DEFAULT_TICKER = "AAPL"

BandReply = str | dict[str, Any]
ResponseBuilder = Callable[[PlatformMessage], BandReply]


def load_band_environment() -> None:
    load_local_env()


def get_band_user_handle() -> str:
    return get_env_handle("BAND_USER_HANDLE")


def get_env_handle(env_name: str) -> str:
    handle = os.getenv(env_name)
    if not handle:
        raise ValueError(f"{env_name} is missing from .env")
    return handle


def optional_env_handle(env_name: str) -> str | None:
    return os.getenv(env_name)


def sanitize_mentions(mentions: list[str] | None = None) -> list[str]:
    cleaned = []

    for mention in mentions or []:
        if not mention:
            continue

        mention_text = str(mention).strip()
        if mention_text:
            cleaned.append(mention_text)

    if cleaned:
        return cleaned

    return [get_band_user_handle()]


def build_reply(content: str, mentions: list[str] | None = None) -> dict[str, Any]:
    return {
        "content": content,
        "mentions": sanitize_mentions(mentions),
    }


def resolve_reply(reply: BandReply) -> tuple[str, list[str]]:
    if isinstance(reply, dict):
        content = str(reply.get("content", ""))
        mentions = sanitize_mentions(reply.get("mentions"))
        return content, mentions

    return str(reply), sanitize_mentions()


def get_incoming_text(msg: PlatformMessage) -> str:
    content = getattr(msg, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or content)

    return str(content or "")


def looks_like_revision_request(msg: PlatformMessage) -> bool:
    text = get_incoming_text(msg).lower()
    return "revision_request" in text or "revise" in text or "revision" in text


def persist_dispatch_step(case_state: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    case_id = case_state["case_id"]
    save_case_state(case_id, case_state)
    return append_audit_event(case_id, event)


def load_dispatch_case_state() -> dict[str, Any]:
    case_state = load_case_state(DEFAULT_CASE_ID)
    save_case_state(case_state["case_id"], case_state)
    return case_state


def get_dispatch_evidence_pack(case_state: dict[str, Any]) -> dict[str, Any]:
    evidence_pack = case_state.get("evidence_pack")
    if evidence_pack:
        return evidence_pack

    return build_evidence_pack(DEFAULT_TICKER, provider="stub")


def bullet_lines(items: list[dict[str, Any]], key: str) -> str:
    if not items:
        return "- None"

    lines = []
    for item in items:
        citation = item.get("citation_id")
        suffix = f" ({citation})" if citation else ""
        lines.append(f"- {item.get(key, item)}{suffix}")
    return "\n".join(lines)


def format_scalar(value: Any) -> str:
    if value is None:
        return "None"
    return str(value)


def runtime_lock_path(agent_config_key: str) -> Path:
    safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in agent_config_key)
    return Path(tempfile.gettempdir()) / f"bandalpha_{safe_key}.lock"


@contextlib.contextmanager
def single_instance_lock(agent_config_key: str, agent_name: str) -> Iterator[None]:
    lock_path = runtime_lock_path(agent_config_key)
    lock_file = lock_path.open("w", encoding="utf-8")

    try:
        try:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                f"{agent_name} appears to already be running. Stop the other instance first."
            ) from exc
        except ImportError:
            pass

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        yield
    finally:
        try:
            lock_file.close()
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


class BandAlphaRemoteAdapter(SimpleAdapter[list[dict]]):
    def __init__(
        self,
        agent_name: str,
        start_message: str,
        done_message: str,
        response_builder: ResponseBuilder,
    ) -> None:
        super().__init__(history_converter=None)
        self.agent_name = agent_name
        self.start_message = start_message
        self.done_message = done_message
        self.response_builder = response_builder

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history,
        contacts_msg: str | None = None,
        participants_msg: str | None = None,
        *,
        is_session_bootstrap: bool = False,
        room_id: str = "",
        **kwargs,
    ) -> None:
        print(f"[{self.agent_name}] on_message received room_id={room_id}")
        try:
            await tools.send_event(
                content=self.start_message,
                message_type="task",
            )

            response_text, mentions = resolve_reply(self.response_builder(msg))
            mentions = sanitize_mentions(mentions)

            await tools.send_message(
                content=response_text,
                mentions=mentions,
            )
            print(f"[{self.agent_name}] reply sent mentions={len(mentions)}")

            await tools.send_event(
                content=self.done_message,
                message_type="task",
            )

        except Exception as exc:
            await tools.send_event(
                content=f"{self.agent_name} failed: {exc}",
                message_type="error",
            )
            raise


async def run_remote_agent(
    agent_config_key: str,
    agent_name: str,
    response_builder: ResponseBuilder,
) -> None:
    load_band_environment()

    print(f"Loading Band agent config for {agent_config_key}...")
    agent_id, api_key = load_agent_config(agent_config_key)
    print(f"Loaded {agent_name} agent_id: {agent_id[:8]}...")

    adapter = BandAlphaRemoteAdapter(
        agent_name=agent_name,
        start_message=f"Running {agent_name}...",
        done_message=f"{agent_name} completed.",
        response_builder=response_builder,
    )

    with single_instance_lock(agent_config_key, agent_name):
        agent = Agent.create(
            adapter=adapter,
            agent_id=agent_id,
            api_key=api_key,
            ws_url=os.getenv("THENVOI_WS_URL"),
            rest_url=os.getenv("THENVOI_REST_URL"),
        )

        print(f"[{agent_name}] agent started. Keep this terminal open.")
        try:
            await agent.run()
        except asyncio.CancelledError:
            print(f"[{agent_name}] shutdown started.")
            raise
        finally:
            print(f"[{agent_name}] stopped.")


def main_for(
    agent_config_key: str,
    agent_name: str,
    response_builder: ResponseBuilder,
) -> None:
    try:
        asyncio.run(run_remote_agent(agent_config_key, agent_name, response_builder))
    except KeyboardInterrupt:
        print("Shutting down BandAlpha agents...")
