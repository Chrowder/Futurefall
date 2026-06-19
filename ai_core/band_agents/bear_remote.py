from ai_core.agents import run_bear_agent, run_bull_agent
from ai_core.band_agents.common import (
    build_reply,
    bullet_lines,
    get_dispatch_evidence_pack,
    get_env_handle,
    load_dispatch_case_state,
    main_for,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state()
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack
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
    return build_reply(content, [get_env_handle("BAND_RISK_HANDLE")])


if __name__ == "__main__":
    main_for("bandalpha_bear", "BearAgent", build_response)
