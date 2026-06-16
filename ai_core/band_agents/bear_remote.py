from ai_core.agents import run_bear_agent, run_bull_agent
from ai_core.band_agents.common import bullet_lines, main_for
from ai_core.sample_case import sample_evidence_pack


def build_response(msg) -> str:
    evidence_pack = sample_evidence_pack
    bull_output = run_bull_agent(evidence_pack)
    bear_output = run_bear_agent(evidence_pack, bull_output)

    return f"""BearAgent generated an adversarial critique.

Thesis:
{bear_output["bear_thesis"]}

Attack Points:
{bullet_lines(bear_output.get("attack_points", []), "critique")}

Missed Risks:
{bullet_lines(bear_output.get("missed_risks", []), "risk")}

Confidence: {bear_output.get("confidence")}
"""


if __name__ == "__main__":
    main_for("bandalpha_bear", "BearAgent", build_response)

