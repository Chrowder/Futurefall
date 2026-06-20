from ai_core.band_agents.common import (
    build_reply,
    case_id_for_ticker,
    extract_case_id,
    extract_ticker,
    get_band_user_handle,
    get_incoming_text,
    main_for,
    optional_env_handle,
    persist_dispatch_step,
)
from ai_core.case_state_store import approve_case, create_or_reset_case, request_case_revision


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


def case_context_from_message(msg) -> tuple[str, str]:
    text = get_incoming_text(msg)
    ticker = extract_ticker(text)
    case_id = extract_case_id(text) or case_id_for_ticker(ticker)
    return case_id, ticker


def build_parallel_blind_response(msg) -> dict:
    case_id, ticker = case_context_from_message(msg)
    case_state = create_or_reset_case(case_id, ticker)
    case_state["parallel_blind_review"] = True
    case_state["blind_review_status"] = "dispatched"
    case_state["status"] = "blind_review_dispatched"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "blind_review_dispatched",
            "target_agent": "BullAgent,BearAgent",
            "summary": "ChairAgent dispatched a Band-native blind first pass.",
            "evidence_refs": [],
        },
    )

    ticker = case_state["ticker"]
    case_id = case_state["case_id"]
    dispatch_content = f"""BullAgent and BearAgent please start the blind first pass in parallel.

case_id: {case_id}
ticker: {ticker}
mode: blind_first_pass
instruction: independently analyze the Evidence Pack without reading the other side's output. BearAgent should trigger BullAgent rebuttal after both first passes are posted.
"""

    content = (
        f"Parallel blind review started for {ticker}. "
        "Dispatching BullAgent and BearAgent for independent first passes."
    )
    return build_reply(
        content,
        [get_band_user_handle()],
        extra_messages=[
            {
                "content": dispatch_content,
                "mentions": [
                    optional_env_handle("BAND_BULL_HANDLE"),
                    optional_env_handle("BAND_BEAR_HANDLE"),
                ],
            }
        ],
    )


def build_dispatch_response(msg) -> dict:
    case_id, ticker = case_context_from_message(msg)
    case_state = create_or_reset_case(case_id, ticker)
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
    return build_reply(content, [optional_env_handle("BAND_DATA_STEWARD_HANDLE")])


def build_approval_response(msg) -> dict:
    case_id, _ticker = case_context_from_message(msg)
    case_state = approve_case(case_id)
    content = f"""ChairAgent recorded human approval.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Human status: {case_state["human_status"]}
Audit events: {len(case_state.get("audit_log", []))}
"""
    return build_reply(content, [get_band_user_handle()])


def build_revision_request_response(msg) -> dict:
    comment = get_incoming_text(msg).strip()
    case_id, _ticker = case_context_from_message(msg)
    case_state = request_case_revision(case_id, comment=comment)
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
        return build_approval_response(msg)

    # Two distributed modes remain. "blind" runs the parallel blind review
    # (independent first passes -> rebuttal exchange); anything else dispatches
    # the standard sequential workflow. Both stream agent-by-agent in the room.
    if is_parallel_blind_message(text):
        print("[ChairAgent] mode selected: blind (distributed)")
        return build_parallel_blind_response(msg)

    print("[ChairAgent] mode selected: dispatch (distributed)")
    return build_dispatch_response(msg)


if __name__ == "__main__":
    main_for("bandalpha_chair", "ChairAgent", build_response)
