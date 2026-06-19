from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_evaluator_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import (
    build_reply,
    format_scalar,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    main_for,
    optional_env_handle,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state(msg)
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack
    base_bull_output = case_state.get("bull_output") or run_bull_agent(evidence_pack)
    bull_output = case_state.get("bull_output_v2") or base_bull_output
    bear_output = case_state.get("bear_output") or run_bear_agent(evidence_pack, base_bull_output)
    risk_output = case_state.get("risk_output") or run_risk_agent(
        evidence_pack,
        base_bull_output,
        bear_output,
    )
    evaluation_output = run_evaluator_agent(
        evidence_pack,
        bull_output,
        bear_output,
        risk_output,
    )
    case_state["bull_output"] = base_bull_output
    case_state["bear_output"] = bear_output
    case_state["risk_output"] = risk_output

    is_final_evaluation = "bull_output_v2" in case_state and case_state["bull_output_v2"]
    if is_final_evaluation:
        case_state["evaluation_output_v2"] = evaluation_output
        case_state["final_evaluation_output"] = evaluation_output
        case_state["final_bull_output"] = bull_output
        case_state["status"] = "final_evaluation_completed"
        action = "final_evaluation_completed"
    else:
        case_state["evaluation_output"] = evaluation_output
        case_state["status"] = "evaluation_completed"
        action = "evaluation_completed"

    next_agent = "BullAgent" if evaluation_output.get("revision_required") else "MemoAgent"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "EvaluatorAgent",
            "action": action,
            "target_agent": next_agent,
            "summary": (
                "Evaluation completed. "
                f"Revision required: {evaluation_output.get('revision_required')}."
            ),
            "evidence_refs": [],
        },
    )

    if evaluation_output.get("revision_required"):
        case_state["status"] = "revision_requested"
        case_state = persist_dispatch_step(
            case_state,
            {
                "agent": "EvaluatorAgent",
                "action": "revision_requested",
                "target_agent": "BullAgent",
                "summary": "Evaluator requested BullAgent revision for unsupported claim wording.",
                "evidence_refs": ["E5"],
            },
        )

    unsupported_claims = evaluation_output.get("unsupported_claims", [])
    unsupported_text = "\n".join(
        (
            f"- {item.get('source_agent')}: {item.get('claim')} "
            f"Required action: {item.get('required_action')}"
        )
        for item in unsupported_claims
    ) or "- None"

    revise_note = ""
    mentions = [optional_env_handle("BAND_MEMO_HANDLE")]
    if evaluation_output.get("revision_required"):
        mentions = [optional_env_handle("BAND_BULL_HANDLE")]
        revise_note = "\nBullAgent please revise the unsupported claim, then hand back to EvaluatorAgent."
    else:
        revise_note = "\nMemoAgent please produce the final research support memo."

    content = f"""EvaluatorAgent completed evaluation.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

revision_required: {evaluation_output.get("revision_required")}
target_agent: {format_scalar(evaluation_output.get("target_agent"))}
hallucination_risk: {evaluation_output.get("hallucination_risk")}
citation_coverage: {evaluation_output.get("citation_coverage")}
faithfulness_score: {evaluation_output.get("faithfulness_score")}

unsupported_claims:
{unsupported_text}
{revise_note}
"""
    return build_reply(content, mentions)


if __name__ == "__main__":
    main_for("bandalpha_evaluator", "EvaluatorAgent", build_response)
