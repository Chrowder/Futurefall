import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from thenvoi import Agent
from thenvoi.config import load_agent_config
from thenvoi.core.protocols import AgentToolsProtocol
from thenvoi.core.simple_adapter import SimpleAdapter
from thenvoi.core.types import PlatformMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_core.runner import run_full_research_case


def format_band_response(result: Dict[str, Any]) -> str:
    case_state = result["case_state"]
    final_memo = result["final_memo"]
    initial_eval = case_state["evaluation_output"]
    final_eval = case_state["final_evaluation_output"]

    risk_flags = final_memo.get("risk_flags", [])
    risk_text = "\n".join(
        f"- [{item.get('severity', 'unknown')}] {item.get('risk')} ({item.get('citation_id')})"
        for item in risk_flags
    )

    return f"""BandAlpha AI Core completed the research workflow.

Ticker: {final_memo.get("ticker")}
Company: {final_memo.get("company")}

Summary:
{final_memo.get("summary")}

Evaluation:
- Initial revision required: {initial_eval.get("revision_required")}
- Final revision required: {final_eval.get("revision_required")}
- Final hallucination risk: {final_eval.get("hallucination_risk")}
- Citation coverage: {final_eval.get("citation_coverage")}

Key Risk Flags:
{risk_text}

Human review required: {final_memo.get("human_review_required")}

Disclaimer:
{final_memo.get("disclaimer")}
"""


class BandAlphaAdapter(SimpleAdapter[list[dict]]):
    def __init__(self):
        super().__init__(history_converter=None)

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
                content="Running BandAlpha AI Core workflow...",
                message_type="task",
            )

            result = run_full_research_case()
            response_text = format_band_response(result)

            user_handle = os.getenv("BAND_USER_HANDLE")

            if not user_handle:
                raise ValueError("BAND_USER_HANDLE is missing from .env")

            await tools.send_message(
                content=response_text,
                mentions=[user_handle],
            )

            await tools.send_event(
                content="BandAlpha AI Core workflow completed.",
                message_type="task",
            )

        except Exception as exc:
            await tools.send_event(
                content=f"BandAlpha AI Core failed: {exc}",
                message_type="error",
            )
            raise


async def main():
    print("Loading environment...")
    load_dotenv()

    print("Loading Band agent config...")
    agent_id, api_key = load_agent_config("bandalpha_ai_core")
    print(f"Loaded agent_id: {agent_id[:8]}...")

    adapter = BandAlphaAdapter()

    print("Creating Band remote agent...")

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    print("BandAlpha remote agent is running. Keep this terminal open.")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())