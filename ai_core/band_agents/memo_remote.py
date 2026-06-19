from ai_core.agents import (
    _apply_bull_rebuttal,
    run_bear_agent,
    run_bull_agent,
    run_evaluator_agent,
    run_memo_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import (
    build_reply,
    chunk_for_band,
    format_memo_for_band,
    get_band_user_handle,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    main_for,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state(msg)
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

    # Detect the distributed blind workflow: if the Phase-2 rebuttal exchange ran,
    # fold it into the final Bull position and emit the 11-section blind memo.
    bull_rebuttal = case_state.get("bull_rebuttal")
    bear_rebuttal = case_state.get("bear_rebuttal")
    blind_context = None
    if case_state.get("bull_first_pass") and bull_rebuttal and bear_rebuttal:
        bull_output = _apply_bull_rebuttal(bull_output, bull_rebuttal)
        blind_context = {
            "bull_first_pass": case_state.get("bull_first_pass"),
            "bear_first_pass": case_state.get("bear_first_pass"),
            "bull_rebuttal": bull_rebuttal,
            "bear_rebuttal": bear_rebuttal,
            "phase1_elapsed": "N/A",
            "phase2_elapsed": "N/A",
        }

    final_memo = run_memo_agent(
        evidence_pack,
        bull_output,
        bear_output,
        risk_output,
        evaluation_output,
        blind_context=blind_context,
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

    summary = format_memo_for_band(final_memo.get("summary", ""))
    chunks = chunk_for_band(summary)
    total = len(chunks)

    header = f"""MemoAgent generated the final research support memo.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

Human review required: {final_memo.get("human_review_required")}
Disclaimer: {final_memo.get("disclaimer")}

Full memo follows in {total} part(s).
"""

    extra_messages = [
        {
            "content": f"[Research Memo — part {index}/{total}]\n\n{chunk}",
            "mentions": [],
        }
        for index, chunk in enumerate(chunks, start=1)
    ]

    return build_reply(header, [get_band_user_handle()], extra_messages=extra_messages)


if __name__ == "__main__":
    main_for("bandalpha_memo", "MemoAgent", build_response)
