from typing import Any, Dict, List, Optional, TypedDict


class EvidenceItem(TypedDict):
    citation_id: str
    claim: str
    source: str
    date: str


class EvidencePack(TypedDict):
    case_id: str
    ticker: str
    company: str
    evidence_items: List[EvidenceItem]


class AgentMessage(TypedDict):
    case_id: str
    from_agent: str
    to_agent: Optional[str]
    message_type: str
    status: str
    payload: Dict[str, Any]
    revision_required: bool
    target_agent: Optional[str]


class CaseState(TypedDict, total=False):
    case_id: str
    ticker: str
    evidence_pack: EvidencePack

    bull_output: Dict[str, Any]
    bear_output: Dict[str, Any]
    risk_output: Dict[str, Any]
    evaluation_output: Dict[str, Any]

    bull_output_v2: Dict[str, Any]
    evaluation_output_v2: Dict[str, Any]

    final_bull_output: Dict[str, Any]
    final_evaluation_output: Dict[str, Any]
    final_memo: Dict[str, Any]


class FrontendTimelineItem(TypedDict):
    step: int
    agent: str
    target: str
    message_type: str
    title: str
    summary: str
    status: str
    revision_required: bool