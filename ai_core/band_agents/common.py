import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from thenvoi import Agent
from thenvoi.config import load_agent_config
from thenvoi.core.protocols import AgentToolsProtocol
from thenvoi.core.simple_adapter import SimpleAdapter
from thenvoi.core.types import PlatformMessage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ResponseBuilder = Callable[[PlatformMessage], str]


def load_band_environment() -> None:
    load_dotenv()


def get_band_user_handle() -> str:
    user_handle = os.getenv("BAND_USER_HANDLE")
    if not user_handle:
        raise ValueError("BAND_USER_HANDLE is missing from .env")
    return user_handle


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
        try:
            await tools.send_event(
                content=self.start_message,
                message_type="task",
            )

            response_text = self.response_builder(msg)

            await tools.send_message(
                content=response_text,
                mentions=[get_band_user_handle()],
            )

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

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    print(f"{agent_name} is running. Keep this terminal open.")
    await agent.run()


def main_for(
    agent_config_key: str,
    agent_name: str,
    response_builder: ResponseBuilder,
) -> None:
    asyncio.run(run_remote_agent(agent_config_key, agent_name, response_builder))

