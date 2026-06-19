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
from ai_core.case_state_store import approve_case, create_or_reset_case, request_case_revision
from ai_core.runner import run_chair_workflow, run_parallel_blind_workflow


def is_approval_message(text: str) -> bool:
    return "approve" in text or "approved" in text or "批准" in text


def is_revision_message(text: str) -> bool:
    return (
        "request revision" in text
        or "revise" in text
        or "修改" in text
        or "重新修改" in text
    )


def is_parallel_blind_message(text: str) -> bool:
    return (
        "blind review" in text
        or "blind" in text
        or "parallel" in text
        or "并行" in text
        or "盲评" in text
    )


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

Memo:
{final_memo.get("summary")}

Disclaimer:
{final_memo.get("disclaimer")}

Human review required. Reply @BandAlpha Chair approve to approve, or @BandAlpha Chair request revision: <comment> to request changes.
"""
    return build_reply(content, [get_band_user_handle()])


def build_parallel_blind_response() -> dict:
    result = run_parallel_blind_workflow()
    case_state = result["case_state"]
    final_memo = result["final_memo"]
    initial_eval = case_state["evaluation_output"]
    final_eval = case_state["final_evaluation_output"]

    content = f"""Parallel blind review completed.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Workflow status: {case_state["status"]}
Blind review status: {case_state.get("blind_review_status")}
Initial revision required: {initial_eval.get("revision_required")}
Final hallucination risk: {final_eval.get("hallucination_risk")}
Audit events: {len(result["audit_log"])}

Bull: {case_state["bull_first_pass"].get("bull_thesis")}

Bear: {case_state["bear_first_pass"].get("bear_thesis")}

Memo:
{final_memo.get("summary")}

Disclaimer:
{final_memo.get("disclaimer")}

Human review required. Reply @BandAlpha Chair approve to approve, or @BandAlpha Chair request revision: <comment> to request changes.
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


def build_approval_response() -> dict:
    case_state = approve_case(DEFAULT_CASE_ID)
    content = f"""ChairAgent recorded human approval.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Human status: {case_state["human_status"]}
Audit events: {len(case_state.get("audit_log", []))}
"""
    return build_reply(content, [get_band_user_handle()])


def build_revision_request_response(msg) -> dict:
    comment = get_incoming_text(msg).strip()
    case_state = request_case_revision(DEFAULT_CASE_ID, comment=comment)
    content = f"""ChairAgent recorded a human revision request.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Human status: {case_state["human_status"]}
Revision comment: {case_state.get("human_revision_comment", "")}
Audit events: {len(case_state.get("audit_log", []))}
"""
    return build_reply(content, [get_band_user_handle()])


def build_response(msg):
    text = get_incoming_text(msg).lower()

    if is_revision_message(text):
        print("[ChairAgent] mode selected: human_revision_request")
        return build_revision_request_response(msg)

    if is_approval_message(text):
        print("[ChairAgent] mode selected: human_approval")
        return build_approval_response()

    if is_parallel_blind_message(text):
        print("[ChairAgent] mode selected: parallel_blind")
        return build_parallel_blind_response()

    if get_chair_mode(msg) == "dispatch":
        print("[ChairAgent] mode selected: dispatch")
        return build_dispatch_response()

    print("[ChairAgent] mode selected: internal")
    return build_internal_response()


if __name__ == "__main__":
    main_for("bandalpha_chair", "ChairAgent", build_response)
