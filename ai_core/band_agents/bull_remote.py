from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_bull_first_pass_agent,
    run_bull_revision_agent,
    run_evaluator_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import (
    build_reply,
    bullet_lines,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    looks_like_blind_first_pass,
    looks_like_revision_request,
    main_for,
    optional_env_handle,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state()
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack

    if looks_like_blind_first_pass(msg):
        bull_output = run_bull_first_pass_agent(evidence_pack)
        case_state["parallel_blind_review"] = True
        case_state["blind_review_status"] = "bull_first_pass_completed"
        case_state["bull_first_pass"] = bull_output
        case_state["bull_output"] = bull_output
        case_state["status"] = "bull_first_pass_completed"
        case_state = persist_dispatch_step(
            case_state,
            {
                "agent": "BullAgent",
                "action": "bull_first_pass_completed",
                "target_agent": "ChairAgent",
                "summary": bull_output["bull_thesis"],
                "evidence_refs": [
                    item["citation_id"]
                    for item in bull_output.get("supporting_points", [])
                ],
            },
        )

        supporting_points = bull_output.get("supporting_points", [])[:3]
        content = f"""BullAgent completed blind first pass.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Mode: blind_first_pass

Thesis:
{bull_output["bull_thesis"]}

Top supporting points:
{bullet_lines(supporting_points, "claim")}

Confidence: {bull_output.get("confidence")}

Next step:
BearAgent please complete your independent blind first pass.
"""
        return build_reply(content, [optional_env_handle("BAND_BEAR_HANDLE")])

    if looks_like_revision_request(msg):
        bull_output = case_state.get("bull_output") or run_bull_agent(evidence_pack)
        bear_output = case_state.get("bear_output") or run_bear_agent(evidence_pack, bull_output)
        risk_output = case_state.get("risk_output") or run_risk_agent(
            evidence_pack,
            bull_output,
            bear_output,
        )
        evaluation_output = run_evaluator_agent(
            evidence_pack,
            bull_output,
            bear_output,
            risk_output,
        )
        revised_output = run_bull_revision_agent(
            evidence_pack,
            bull_output,
            evaluation_output,
        )
        case_state["bull_output"] = bull_output
        case_state["bear_output"] = bear_output
        case_state["risk_output"] = risk_output
        case_state["evaluation_output"] = case_state.get("evaluation_output") or evaluation_output
        case_state["bull_output_v2"] = revised_output
        case_state["final_bull_output"] = revised_output
        case_state["status"] = "bull_revised"
        case_state = persist_dispatch_step(
            case_state,
            {
                "agent": "BullAgent",
                "action": "bull_revised",
                "target_agent": "EvaluatorAgent",
                "summary": revised_output.get("revision_note"),
                "evidence_refs": [
                    item["citation_id"]
                    for item in revised_output.get("supporting_points", [])
                ],
            },
        )

        content = f"""BullAgent generated Bull revision.

Thesis:
{revised_output["bull_thesis"]}

Supporting Points:
{bullet_lines(revised_output.get("supporting_points", []), "claim")}

Revision Note:
{revised_output.get("revision_note")}

Confidence: {revised_output.get("confidence")}

EvaluatorAgent please run the final evaluation on Bull v2.
"""
        return build_reply(content, [optional_env_handle("BAND_EVALUATOR_HANDLE")])

    bull_output = run_bull_agent(evidence_pack)
    case_state["bull_output"] = bull_output
    case_state["status"] = "bull_generated"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "BullAgent",
            "action": "bull_generated",
            "target_agent": "BearAgent",
            "summary": bull_output["bull_thesis"],
            "evidence_refs": [
                item["citation_id"] for item in bull_output.get("supporting_points", [])
            ],
        },
    )

    content = f"""BullAgent generated Bull v1.

Thesis:
{bull_output["bull_thesis"]}

Supporting Points:
{bullet_lines(bull_output.get("supporting_points", []), "claim")}

Key Assumptions:
{chr(10).join(f"- {item}" for item in bull_output.get("key_assumptions", []))}

Confidence: {bull_output.get("confidence")}

BearAgent please critique Bull v1. RiskAgent should wait for BearAgent's critique.
"""
    return build_reply(
        content,
        [optional_env_handle("BAND_BEAR_HANDLE")],
    )


if __name__ == "__main__":
    main_for("bandalpha_bull", "BullAgent", build_response)
