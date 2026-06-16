from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_evaluator_agent,
    run_risk_agent,
)
from ai_core.band_agents.common import format_scalar, main_for
from ai_core.sample_case import sample_evidence_pack


def build_response(msg) -> str:
    evidence_pack = sample_evidence_pack
    bull_output = run_bull_agent(evidence_pack)
    bear_output = run_bear_agent(evidence_pack, bull_output)
    risk_output = run_risk_agent(evidence_pack, bull_output, bear_output)
    evaluation_output = run_evaluator_agent(
        evidence_pack,
        bull_output,
        bear_output,
        risk_output,
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
    if evaluation_output.get("revision_required"):
        revise_note = "\nBullAgent should revise before MemoAgent produces the final memo."

    return f"""EvaluatorAgent completed evaluation.

revision_required: {evaluation_output.get("revision_required")}
target_agent: {format_scalar(evaluation_output.get("target_agent"))}
hallucination_risk: {evaluation_output.get("hallucination_risk")}
citation_coverage: {evaluation_output.get("citation_coverage")}
faithfulness_score: {evaluation_output.get("faithfulness_score")}

unsupported_claims:
{unsupported_text}
{revise_note}
"""


if __name__ == "__main__":
    main_for("bandalpha_evaluator", "EvaluatorAgent", build_response)

