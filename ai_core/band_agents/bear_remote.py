from ai_core.agents import run_bear_agent, run_bear_first_pass_agent, run_bull_agent
from ai_core.band_agents.common import (
    build_reply,
    bullet_lines,
    get_band_user_handle,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    looks_like_blind_first_pass,
    main_for,
    optional_env_handle,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state()
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack

    if looks_like_blind_first_pass(msg):
        bear_output = run_bear_first_pass_agent(evidence_pack)
        case_state["parallel_blind_review"] = True
        case_state["blind_review_status"] = "bear_first_pass_completed"
        case_state["bear_first_pass"] = bear_output
        case_state["bear_output"] = bear_output
        case_state["status"] = "bear_first_pass_completed"
        case_state = persist_dispatch_step(
            case_state,
            {
                "agent": "BearAgent",
                "action": "bear_first_pass_completed",
                "target_agent": "ChairAgent",
                "summary": bear_output["bear_thesis"],
                "evidence_refs": [
                    item["citation_id"]
                    for item in bear_output.get("attack_points", [])
                ],
            },
        )

        content = f"""BearAgent completed blind first pass.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Mode: blind_first_pass

Thesis:
{bear_output["bear_thesis"]}

Attack Points:
{bullet_lines(bear_output.get("attack_points", []), "critique")}

Missed Risks:
{bullet_lines(bear_output.get("missed_risks", []), "risk")}

Confidence: {bear_output.get("confidence")}
"""
        return build_reply(content, [get_band_user_handle()])

    bull_output = case_state.get("bull_output") or run_bull_agent(evidence_pack)
    bear_output = run_bear_agent(evidence_pack, bull_output)
    case_state["bull_output"] = bull_output
    case_state["bear_output"] = bear_output
    case_state["status"] = "bear_generated"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "BearAgent",
            "action": "bear_generated",
            "target_agent": "RiskAgent",
            "summary": bear_output["bear_thesis"],
            "evidence_refs": [
                item["citation_id"] for item in bear_output.get("attack_points", [])
            ],
        },
    )

    content = f"""BearAgent generated an adversarial critique.

Thesis:
{bear_output["bear_thesis"]}

Attack Points:
{bullet_lines(bear_output.get("attack_points", []), "critique")}

Missed Risks:
{bullet_lines(bear_output.get("missed_risks", []), "risk")}

Confidence: {bear_output.get("confidence")}

RiskAgent please generate risk flags using the Evidence Pack, Bull thesis, and Bear critique.
"""
    return build_reply(content, [optional_env_handle("BAND_RISK_HANDLE")])


if __name__ == "__main__":
    main_for("bandalpha_bear", "BearAgent", build_response)
