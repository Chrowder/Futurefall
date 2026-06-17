import os

from ai_core.band_agents.common import (
    DEFAULT_CASE_ID,
    DEFAULT_TICKER,
    build_reply,
    get_band_user_handle,
    get_env_handle,
    get_incoming_text,
    main_for,
    persist_dispatch_step,
)
from ai_core.case_state_store import create_or_reset_case
from ai_core.runner import run_chair_workflow


def get_chair_mode(msg) -> str:
    text = get_incoming_text(msg).lower()

    if "dispatch" in text:
        return "dispatch"

    if "internal" in text or "one-click" in text:
        return "internal"

    return os.getenv("BAND_CHAIR_MODE", "internal").lower()


def build_internal_response() -> dict:
    result = run_chair_workflow()
    case_state = result["case_state"]
    final_memo = result["final_memo"]
    initial_eval = case_state["evaluation_output"]
    final_eval = case_state["final_evaluation_output"]

    content = f"""ChairAgent completed the BandAlpha workflow.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Workflow status: {case_state["status"]}
Initial revision required: {initial_eval.get("revision_required")}
Final hallucination risk: {final_eval.get("hallucination_risk")}
Audit events: {len(result["audit_log"])}

Final Memo Summary:
{final_memo.get("summary")}

Disclaimer:
{final_memo.get("disclaimer")}
"""
    return build_reply(content, [get_band_user_handle()])


def build_dispatch_response() -> dict:
    case_state = create_or_reset_case(DEFAULT_CASE_ID, DEFAULT_TICKER)
    case_state["status"] = "dispatch_started"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "dispatch_started",
            "target_agent": "DataStewardAgent",
            "summary": "ChairAgent started Band-native dispatch mode.",
            "evidence_refs": [],
        },
    )

    content = f"""DataStewardAgent please prepare the Evidence Pack.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

After completion, hand off to BullAgent with the evidence pack summary.
"""
    return build_reply(content, [get_env_handle("BAND_DATA_STEWARD_HANDLE")])


def build_response(msg):
    if get_chair_mode(msg) == "dispatch":
        return build_dispatch_response()

    return build_internal_response()


if __name__ == "__main__":
    main_for("bandalpha_chair", "ChairAgent", build_response)
