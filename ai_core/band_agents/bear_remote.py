from ai_core.agents import (
    run_bear_agent,
    run_bear_first_pass_agent,
    run_bear_rebuttal_agent,
    run_bull_agent,
)
from ai_core.band_agents.common import (
    build_reply,
    bullet_lines,
    get_band_user_handle,
    get_dispatch_evidence_pack,
    load_dispatch_case_state,
    looks_like_blind_first_pass,
    looks_like_blind_rebuttal,
    main_for,
    optional_env_handle,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state(msg)
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack

    if looks_like_blind_rebuttal(msg):
        # Phase 2: BullAgent has rebutted; BearAgent now rebuts, then hands to Risk.
        bull_first_pass = case_state.get("bull_first_pass") or case_state.get("bull_output")
        bear_first_pass = case_state.get("bear_first_pass") or case_state.get("bear_output")
        bear_rebuttal = run_bear_rebuttal_agent(
            evidence_pack, bull_first_pass, bear_first_pass
        )
        case_state["bear_rebuttal"] = bear_rebuttal
        case_state["blind_review_status"] = "rebuttal_exchange_completed"
        case_state["status"] = "rebuttal_exchange_completed"
        case_state = persist_dispatch_step(
            case_state,
            {
                "agent": "BearAgent",
                "action": "bear_rebuttal_completed",
                "target_agent": "RiskAgent",
                "summary": bear_rebuttal["rebuttal_summary"],
                "evidence_refs": [
                    ro.get("citation_id")
                    for ro in bear_rebuttal.get("remaining_objections", [])
                    if ro.get("citation_id")
                ],
            },
        )

        content = f"""BearAgent completed its rebuttal (Phase 2). Blind exchange done.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

Rebuttal summary:
{bear_rebuttal["rebuttal_summary"]}

Remaining objections:
{bullet_lines(bear_rebuttal.get("remaining_objections", []), "objection")}

Conceded to BullAgent:
{bullet_lines(bear_rebuttal.get("conceded_points", []), "point")}

RiskAgent please generate risk flags using the Evidence Pack, Bull, and Bear positions.
"""
        return build_reply(content, [optional_env_handle("BAND_RISK_HANDLE")])

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
                "target_agent": "BullAgent",
                "summary": bear_output["bear_thesis"],
                "evidence_refs": [
                    item["citation_id"]
                    for item in bear_output.get("attack_points", [])
                ],
            },
        )

        content = f"""BearAgent completed its blind first pass. Both first passes are now in.

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

Thesis:
{bear_output["bear_thesis"]}

Attack Points:
{bullet_lines(bear_output.get("attack_points", []), "critique")}

Missed Risks:
{bullet_lines(bear_output.get("missed_risks", []), "risk")}

Confidence: {bear_output.get("confidence")}

BullAgent please start the rebuttal exchange (mode: blind_rebuttal).
"""
        return build_reply(content, [optional_env_handle("BAND_BULL_HANDLE")])

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

Case ID: {case_state["case_id"]}
Ticker: {case_state["ticker"]}

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
