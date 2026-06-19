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
MAX_BAND_MESSAGE_CHARS = 2400

BandReply = str | dict[str, Any]
ResponseBuilder = Callable[[PlatformMessage], BandReply]
_PRIMARY_REPLY_SENT_MESSAGE_IDS: set[str] = set()
_EXTRA_HANDOFF_SENT_MESSAGE_IDS: set[str] = set()


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


def normalize_handle(handle: str) -> str:
    return str(handle or "").strip().lstrip("@").lower()


def handle_in_participants(handle: str, participants_msg: str | None) -> bool:
    if not participants_msg:
        return False

    normalized_handle = normalize_handle(handle)
    normalized_participants = normalize_handle(participants_msg)
    return normalized_handle in normalized_participants


def trim_band_message(content: Any, max_chars: int = MAX_BAND_MESSAGE_CHARS) -> str:
    text = str(content or "").strip()
    if len(text) <= max_chars:
        return text

    return text[: max_chars - 80].rstrip() + "\n\n[truncated for Band room readability]"


def safe_mentions_for_room(
    mentions: list[str] | None,
    participants_msg: str | None,
) -> tuple[list[str], bool]:
    requested_mentions = sanitize_mentions(mentions)
    if not participants_msg:
        return requested_mentions, False

    user_handle = get_band_user_handle()
    safe_mentions = []
    missing_target = False

    for mention in requested_mentions:
        if normalize_handle(mention) == normalize_handle(user_handle):
            safe_mentions.append(mention)
            continue

        if handle_in_participants(mention, participants_msg):
            safe_mentions.append(mention)
            continue

        missing_target = True

    if not safe_mentions:
        safe_mentions = [user_handle]

    return safe_mentions, missing_target


def prepare_outgoing_message(
    content: Any,
    mentions: list[str] | None,
    participants_msg: str | None,
) -> tuple[str, list[str], bool]:
    safe_mentions, missing_target = safe_mentions_for_room(mentions, participants_msg)
    safe_content = trim_band_message(content)

    if missing_target:
        warning = (
            "Next agent is not present in this room. "
            "Please add it to continue handoff."
        )
        if warning not in safe_content:
            safe_content = trim_band_message(f"{safe_content}\n\n{warning}")

    return safe_content, safe_mentions, missing_target


def build_reply(
    content: str,
    mentions: list[str] | None = None,
    extra_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    reply = {
        "content": content,
        "mentions": sanitize_mentions(mentions),
    }

    if extra_messages:
        reply["extra_messages"] = [
            {
                "content": str(message.get("content", "")),
                "mentions": sanitize_mentions(message.get("mentions")),
            }
            for message in extra_messages
        ]

    return reply


def resolve_reply(reply: BandReply) -> tuple[str, list[str]]:
    if isinstance(reply, dict):
        content = str(reply.get("content", ""))
        mentions = sanitize_mentions(reply.get("mentions"))
        return content, mentions

    return str(reply), sanitize_mentions()


def resolve_extra_messages(reply: BandReply) -> list[tuple[str, list[str]]]:
    if not isinstance(reply, dict):
        return []

    messages = []
    for message in reply.get("extra_messages", []) or []:
        if not isinstance(message, dict):
            continue
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        messages.append((content, sanitize_mentions(message.get("mentions"))))

    return messages


def get_incoming_text(msg: PlatformMessage) -> str:
    content = getattr(msg, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or content)

    return str(content or "")


def get_message_id(msg: PlatformMessage) -> str:
    for attr_name in ("message_id", "id", "platform_message_id"):
        value = getattr(msg, attr_name, None)
        if value:
            return str(value)

    return ""


def looks_like_revision_request(msg: PlatformMessage) -> bool:
    text = get_incoming_text(msg).lower()
    return "revision_request" in text or "revise" in text or "revision" in text


def looks_like_blind_first_pass(msg: PlatformMessage) -> bool:
    return "blind_first_pass" in get_incoming_text(msg).lower()


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

    async def send_event_safely(
        self,
        tools: AgentToolsProtocol,
        content: str,
        message_type: str,
    ) -> None:
        try:
            await tools.send_event(content=content, message_type=message_type)
        except Exception as exc:
            print(f"[{self.agent_name}] send_event skipped: {exc}")

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
        primary_reply_sent = False
        incoming_message_id = get_message_id(msg)
        if incoming_message_id and incoming_message_id in _PRIMARY_REPLY_SENT_MESSAGE_IDS:
            print(
                f"[{self.agent_name}] duplicate delivery skipped "
                f"message_id={incoming_message_id}"
            )
            return

        try:
            await self.send_event_safely(
                tools,
                self.start_message,
                "task",
            )

            reply = self.response_builder(msg)
            response_text, mentions = resolve_reply(reply)
            requested_mentions = sanitize_mentions(mentions)
            response_text, mentions, missing_target = prepare_outgoing_message(
                response_text,
                mentions,
                participants_msg,
            )
            print(
                f"[{self.agent_name}] sending reply "
                f"requested_mentions={requested_mentions} "
                f"final_mentions={mentions}"
            )

            await tools.send_message(
                content=response_text,
                mentions=mentions,
            )
            primary_reply_sent = True
            if incoming_message_id:
                _PRIMARY_REPLY_SENT_MESSAGE_IDS.add(incoming_message_id)
            print(
                f"[{self.agent_name}] reply sent mentions={len(mentions)} "
                f"fallback_used={missing_target}"
            )

            if incoming_message_id and incoming_message_id in _EXTRA_HANDOFF_SENT_MESSAGE_IDS:
                print(
                    f"[{self.agent_name}] dispatch skipped for retried "
                    f"message_id={incoming_message_id}"
                )
            else:
                for extra_content, extra_mentions in resolve_extra_messages(reply):
                    requested_extra_mentions = sanitize_mentions(extra_mentions)
                    extra_content, extra_mentions, extra_missing_target = (
                        prepare_outgoing_message(
                            extra_content,
                            extra_mentions,
                            participants_msg,
                        )
                    )
                    print(
                        f"[{self.agent_name}] sending dispatch "
                        f"requested_mentions={requested_extra_mentions} "
                        f"final_mentions={extra_mentions}"
                    )
                    try:
                        await tools.send_message(
                            content=extra_content,
                            mentions=extra_mentions,
                        )
                        print(
                            f"[{self.agent_name}] dispatch message sent "
                            f"mentions={len(extra_mentions)} "
                            f"fallback_used={extra_missing_target}"
                        )
                        if incoming_message_id:
                            _EXTRA_HANDOFF_SENT_MESSAGE_IDS.add(incoming_message_id)
                    except Exception as exc:
                        print(f"[{self.agent_name}] dispatch message skipped: {exc}")

            await self.send_event_safely(
                tools,
                self.done_message,
                "task",
            )

        except Exception as exc:
            if primary_reply_sent:
                print(f"[{self.agent_name}] post-reply error suppressed: {exc}")
                return

            await self.send_event_safely(
                tools,
                f"{self.agent_name} failed: {exc}",
                "error",
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
