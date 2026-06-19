from ai_core.agents import run_bear_agent, run_bull_agent, run_risk_agent
from ai_core.band_agents.common import (
    build_reply,
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
    bear_output = case_state.get("bear_output") or run_bear_agent(evidence_pack, bull_output)
    risk_output = run_risk_agent(evidence_pack, bull_output, bear_output)
    case_state["bull_output"] = bull_output
    case_state["bear_output"] = bear_output
    case_state["risk_output"] = risk_output
    case_state["status"] = "risk_generated"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "RiskAgent",
            "action": "risk_generated",
            "target_agent": "EvaluatorAgent",
            "summary": risk_output["risk_summary"],
            "evidence_refs": [
                item["citation_id"] for item in risk_output.get("risk_flags", [])
            ],
        },
    )

    risk_flags = "\n".join(
        (
            f"- [{item.get('severity', 'unknown')}] {item.get('risk')} "
            f"({item.get('citation_id')})"
        )
        for item in risk_output.get("risk_flags", [])
    )

    content = f"""RiskAgent generated risk flags.

Risk Summary:
{risk_output["risk_summary"]}

Risk Flags:
{risk_flags}

Confidence: {risk_output.get("confidence")}

EvaluatorAgent please evaluate the current Bull, Bear, and Risk outputs for citation support.
"""
    return build_reply(content, [get_env_handle("BAND_EVALUATOR_HANDLE")])


if __name__ == "__main__":
    main_for("bandalpha_risk", "RiskAgent", build_response)
