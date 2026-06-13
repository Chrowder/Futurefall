from typing import Any, Dict, List, Optional

from ai_core.schemas import AgentMessage

class MockBandRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.messages: List[AgentMessage] = []

    def send_message(self, message: AgentMessage) -> None:
        self.messages.append(message)
        print(
            f"\n[MockBand: {self.room_id}] "
            f"{message['from_agent']} -> {message.get('to_agent') or 'ALL'}"
        )
        print(message)


def wrap_message(
    case_id: str,
    from_agent: str,
    payload: Dict[str, Any],
    message_type: str = "agent_result",
    to_agent: Optional[str] = None,
    revision_required: bool = False,
    target_agent: Optional[str] = None,
) -> AgentMessage:
    return {
        "case_id": case_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "status": "completed",
        "payload": payload,
        "revision_required": revision_required,
        "target_agent": target_agent,
    }