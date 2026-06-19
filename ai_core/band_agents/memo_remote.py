from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_evaluator_agent,
    run_memo_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import (
    build_reply,
    get_band_user_handle,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    main_for,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state()
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack
    bull_output = (
        case_state.get("final_bull_output")
        or case_state.get("bull_output_v2")
        or case_state.get("bull_output")
        or run_bull_agent(evidence_pack)
    )
    bear_output = case_state.get("bear_output") or run_bear_agent(evidence_pack, bull_output)
    risk_output = case_state.get("risk_output") or run_risk_agent(
        evidence_pack,
        bull_output,
        bear_output,
    )
    evaluation_output = (
        case_state.get("final_evaluation_output")
        or case_state.get("evaluation_output_v2")
        or case_state.get("evaluation_output")
        or run_evaluator_agent(evidence_pack, bull_output, bear_output, risk_output)
    )
    final_memo = run_memo_agent(
        evidence_pack,
        bull_output,
        bear_output,
        risk_output,
        evaluation_output,
    )

    case_state["final_bull_output"] = bull_output
    case_state["bear_output"] = bear_output
    case_state["risk_output"] = risk_output
    case_state["final_evaluation_output"] = evaluation_output
    case_state["final_memo"] = final_memo
    case_state["human_status"] = "pending_review"
    case_state["status"] = "pending_human_review"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "MemoAgent",
            "action": "memo_generated",
            "target_agent": "HumanReviewer",
            "summary": final_memo["summary"],
            "evidence_refs": [
                item["citation_id"] for item in evidence_pack["evidence_items"]
            ],
        },
    )
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "human_review_pending",
            "target_agent": "HumanReviewer",
            "summary": "Final memo is ready for human review.",
            "evidence_refs": [
                item["citation_id"] for item in evidence_pack["evidence_items"]
            ],
        },
    )

    content = f"""MemoAgent generated the final research support memo.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

Summary:
{final_memo.get("summary")}

Human review required: {final_memo.get("human_review_required")}

Disclaimer:
{final_memo.get("disclaimer")}
"""
    return build_reply(content, [get_band_user_handle()])


if __name__ == "__main__":
    main_for("bandalpha_memo", "MemoAgent", build_response)
