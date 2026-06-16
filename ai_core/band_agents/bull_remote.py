from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_bull_revision_agent,
    run_evaluator_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import bullet_lines, looks_like_revision_request, main_for
from ai_core.sample_case import sample_evidence_pack


def build_response(msg) -> str:
    evidence_pack = sample_evidence_pack

    if looks_like_revision_request(msg):
        bull_output = run_bull_agent(evidence_pack)
        bear_output = run_bear_agent(evidence_pack, bull_output)
        risk_output = run_risk_agent(evidence_pack, bull_output, bear_output)
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

        return f"""BullAgent generated Bull revision.

Thesis:
{revised_output["bull_thesis"]}

Supporting Points:
{bullet_lines(revised_output.get("supporting_points", []), "claim")}

Revision Note:
{revised_output.get("revision_note")}

Confidence: {revised_output.get("confidence")}
"""

    bull_output = run_bull_agent(evidence_pack)

    return f"""BullAgent generated Bull v1.

Thesis:
{bull_output["bull_thesis"]}

Supporting Points:
{bullet_lines(bull_output.get("supporting_points", []), "claim")}

Key Assumptions:
{chr(10).join(f"- {item}" for item in bull_output.get("key_assumptions", []))}

Confidence: {bull_output.get("confidence")}
"""


if __name__ == "__main__":
    main_for("bandalpha_bull", "BullAgent", build_response)

