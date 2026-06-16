from ai_core.agents import run_bear_agent, run_bull_agent, run_risk_agent
from ai_core.band_agents.common import main_for
from ai_core.sample_case import sample_evidence_pack


def build_response(msg) -> str:
    evidence_pack = sample_evidence_pack
    bull_output = run_bull_agent(evidence_pack)
    bear_output = run_bear_agent(evidence_pack, bull_output)
    risk_output = run_risk_agent(evidence_pack, bull_output, bear_output)

    risk_flags = "\n".join(
        (
            f"- [{item.get('severity', 'unknown')}] {item.get('risk')} "
            f"({item.get('citation_id')})"
        )
        for item in risk_output.get("risk_flags", [])
    )

    return f"""RiskAgent generated risk flags.

Risk Summary:
{risk_output["risk_summary"]}

Risk Flags:
{risk_flags}

Confidence: {risk_output.get("confidence")}
"""


if __name__ == "__main__":
    main_for("bandalpha_risk", "RiskAgent", build_response)

