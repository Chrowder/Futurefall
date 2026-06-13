import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_core.sample_case import sample_evidence_pack
from ai_core.mock_band import MockBandRoom, wrap_message
from ai_core.agents import (
    valid_citations,
    run_bull_agent,
    run_bull_revision_agent,
    run_bear_agent,
    run_risk_agent,
    run_evaluator_agent,
    run_memo_agent,
)


def create_initial_case_state(
    evidence_pack: Dict[str, Any] = sample_evidence_pack,
) -> Dict[str, Any]:
    return {
        "case_id": evidence_pack["case_id"],
        "ticker": evidence_pack["ticker"],
        "evidence_pack": evidence_pack,
    }


def run_agent(agent_name: str, case_state: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case_state["case_id"]
    evidence_pack = case_state["evidence_pack"]

    if agent_name == "bull":
        payload = run_bull_agent(evidence_pack)
        return wrap_message(case_id, "BullAgent", payload)

    if agent_name == "bear":
        payload = run_bear_agent(evidence_pack, case_state["bull_output"])
        return wrap_message(case_id, "BearAgent", payload)

    if agent_name == "risk":
        payload = run_risk_agent(
            evidence_pack,
            case_state["bull_output"],
            case_state["bear_output"],
        )
        return wrap_message(case_id, "RiskAgent", payload)

    if agent_name == "evaluator":
        payload = run_evaluator_agent(
            evidence_pack,
            case_state["bull_output"],
            case_state["bear_output"],
            case_state.get("risk_output"),
        )
        return wrap_message(
            case_id,
            "EvaluatorAgent",
            payload,
            message_type="revision_request" if payload["revision_required"] else "agent_result",
            to_agent=payload.get("target_agent"),
            revision_required=payload["revision_required"],
            target_agent=payload.get("target_agent"),
        )

    if agent_name == "bull_revision":
        payload = run_bull_revision_agent(
            evidence_pack,
            case_state["bull_output"],
            case_state["evaluation_output"],
        )
        return wrap_message(
            case_id,
            "BullAgent",
            payload,
            message_type="agent_result",
        )

    if agent_name == "memo":
        payload = run_memo_agent(
            evidence_pack,
            case_state["final_bull_output"],
            case_state["bear_output"],
            case_state["risk_output"],
            case_state["final_evaluation_output"],
        )
        return wrap_message(
            case_id,
            "MemoAgent",
            payload,
            message_type="final_memo",
        )

    raise ValueError(f"Unknown agent name: {agent_name}")


def handle_band_message(
    message: Dict[str, Any],
    case_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Lightweight adapter for future Band integration.

    This does not call the real Band SDK yet.
    It maps Band-style incoming messages to the local AI Core agent runner.
    """

    target_agent = message.get("to_agent")
    message_type = message.get("message_type")

    if target_agent == "BullAgent":
        if message_type == "revision_request":
            if "evaluation_output" not in case_state:
                case_state["evaluation_output"] = message.get("payload", {})
            return run_agent("bull_revision", case_state)

        return run_agent("bull", case_state)

    if target_agent == "BearAgent":
        return run_agent("bear", case_state)

    if target_agent == "RiskAgent":
        return run_agent("risk", case_state)

    if target_agent == "EvaluatorAgent":
        return run_agent("evaluator", case_state)

    if target_agent == "MemoAgent":
        return run_agent("memo", case_state)

    raise ValueError(f"Unsupported or missing target agent: {target_agent}")


def run_full_research_case() -> Dict[str, Any]:
    room = MockBandRoom("local-bandalpha-demo")
    case_state = create_initial_case_state(sample_evidence_pack)

    room.send_message(
        wrap_message(
            case_state["case_id"],
            "DataStewardAgent",
            sample_evidence_pack,
        )
    )

    bull_msg = run_agent("bull", case_state)
    room.send_message(bull_msg)
    case_state["bull_output"] = bull_msg["payload"]

    bear_msg = run_agent("bear", case_state)
    room.send_message(bear_msg)
    case_state["bear_output"] = bear_msg["payload"]

    risk_msg = run_agent("risk", case_state)
    room.send_message(risk_msg)
    case_state["risk_output"] = risk_msg["payload"]

    evaluator_msg = run_agent("evaluator", case_state)
    room.send_message(evaluator_msg)
    case_state["evaluation_output"] = evaluator_msg["payload"]

    if case_state["evaluation_output"]["revision_required"]:
        print("\n=== Revision Loop Triggered ===")

        revision_msg = run_agent("bull_revision", case_state)
        room.send_message(revision_msg)
        case_state["bull_output_v2"] = revision_msg["payload"]

        case_state_for_v2 = {
            **case_state,
            "bull_output": case_state["bull_output_v2"],
        }

        evaluator_v2_msg = run_agent("evaluator", case_state_for_v2)
        room.send_message(evaluator_v2_msg)
        case_state["evaluation_output_v2"] = evaluator_v2_msg["payload"]

    case_state["final_bull_output"] = case_state.get("bull_output_v2", case_state["bull_output"])
    case_state["final_evaluation_output"] = case_state.get(
        "evaluation_output_v2",
        case_state["evaluation_output"],
    )

    memo_msg = run_agent("memo", case_state)
    room.send_message(memo_msg)
    case_state["final_memo"] = memo_msg["payload"]

    return {
        "case_state": case_state,
        "messages": room.messages,
        "final_memo": case_state["final_memo"],
    }


def main():
    result = run_full_research_case()
    case_state = result["case_state"]

    print("\n=== DONE ===")
    print(f"Initial revision required: {case_state['evaluation_output']['revision_required']}")

    if "evaluation_output_v2" in case_state:
        print(f"After revision required: {case_state['evaluation_output_v2']['revision_required']}")
        print(f"Final hallucination risk: {case_state['evaluation_output_v2']['hallucination_risk']}")

    print(f"Final memo generated: {'final_memo' in case_state}")
    print(f"Human review required: {case_state['final_memo']['human_review_required']}")


if __name__ == "__main__":
    main()