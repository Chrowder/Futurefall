from typing import Dict, Any, Optional

from ai_core.data_providers.evidence_builder import build_evidence_pack
from ai_core.mock_band import MockBandRoom, wrap_message
from ai_core.agents import (
    run_bull_agent,
    run_bull_first_pass_agent,
    run_bull_revision_agent,
    run_bear_agent,
    run_bear_first_pass_agent,
    run_bull_rebuttal_agent,
    run_bear_rebuttal_agent,
    run_risk_agent,
    run_evaluator_agent,
    run_memo_agent,
)
from ai_core.case_state_store import append_audit_event, create_or_reset_case, save_case_state
from ai_core.schemas import AgentMessage, CaseState

def create_initial_case_state(
    evidence_pack: Optional[Dict[str, Any]] = None,
    ticker: str = "AAPL",
    provider: str = "env",
) -> CaseState:
    if evidence_pack is None:
        evidence_pack = build_evidence_pack(ticker=ticker, provider=provider)

    return {
        "case_id": evidence_pack["case_id"],
        "ticker": evidence_pack["ticker"],
        "evidence_pack": evidence_pack,
    }

def run_agent(agent_name: str, case_state: CaseState) -> AgentMessage:
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
    message: AgentMessage,
    case_state: CaseState,
) -> AgentMessage:
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
    evidence_pack = build_evidence_pack(provider="env")
    case_state = create_initial_case_state(evidence_pack)

    room.send_message(
        wrap_message(
            case_state["case_id"],
            "DataStewardAgent",
            evidence_pack,
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


def _persist_chair_step(case_state: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case_state["case_id"]
    save_case_state(case_id, case_state)
    return append_audit_event(case_id, event)


def run_chair_workflow(case_id: str = "AAPL-001", ticker: str = "AAPL") -> Dict[str, Any]:
    case_state = create_or_reset_case(case_id, ticker)

    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "case_created",
            "target_agent": "DataStewardAgent",
            "summary": f"Created research case {case_id} for {ticker}.",
            "evidence_refs": [],
        },
    )

    evidence_pack = case_state["evidence_pack"]
    evidence_refs = [item["citation_id"] for item in evidence_pack["evidence_items"]]
    case_state["status"] = "evidence_pack_ready"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "DataStewardAgent",
            "action": "evidence_pack_ready",
            "target_agent": "BullAgent",
            "summary": f"Prepared Evidence Pack with {len(evidence_refs)} items.",
            "evidence_refs": evidence_refs,
        },
    )

    bull_msg = run_agent("bull", case_state)
    case_state["bull_output"] = bull_msg["payload"]
    case_state["status"] = "bull_generated"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BullAgent",
            "action": "bull_generated",
            "target_agent": "BearAgent",
            "summary": case_state["bull_output"]["bull_thesis"],
            "evidence_refs": [
                item["citation_id"]
                for item in case_state["bull_output"].get("supporting_points", [])
            ],
        },
    )

    bear_msg = run_agent("bear", case_state)
    case_state["bear_output"] = bear_msg["payload"]
    case_state["status"] = "bear_generated"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BearAgent",
            "action": "bear_generated",
            "target_agent": "RiskAgent",
            "summary": case_state["bear_output"]["bear_thesis"],
            "evidence_refs": [
                item["citation_id"]
                for item in case_state["bear_output"].get("attack_points", [])
            ],
        },
    )

    risk_msg = run_agent("risk", case_state)
    case_state["risk_output"] = risk_msg["payload"]
    case_state["status"] = "risk_generated"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "RiskAgent",
            "action": "risk_generated",
            "target_agent": "EvaluatorAgent",
            "summary": case_state["risk_output"]["risk_summary"],
            "evidence_refs": [
                item["citation_id"]
                for item in case_state["risk_output"].get("risk_flags", [])
            ],
        },
    )

    evaluator_msg = run_agent("evaluator", case_state)
    case_state["evaluation_output"] = evaluator_msg["payload"]
    case_state["status"] = "evaluation_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "EvaluatorAgent",
            "action": "evaluation_completed",
            "target_agent": case_state["evaluation_output"].get("target_agent"),
            "summary": (
                "Initial evaluation completed. "
                f"Revision required: {case_state['evaluation_output']['revision_required']}."
            ),
            "evidence_refs": [],
        },
    )

    if case_state["evaluation_output"]["revision_required"]:
        unsupported_refs = [
            item.get("citation_id")
            for item in case_state["evaluation_output"].get("unsupported_claims", [])
            if item.get("citation_id")
        ]
        case_state["status"] = "revision_requested"
        case_state = _persist_chair_step(
            case_state,
            {
                "agent": "EvaluatorAgent",
                "action": "revision_requested",
                "target_agent": case_state["evaluation_output"].get("target_agent"),
                "summary": "Evaluator requested a BullAgent revision for an unsupported demand claim.",
                "evidence_refs": unsupported_refs or ["E5"],
            },
        )

        revision_msg = run_agent("bull_revision", case_state)
        case_state["bull_output_v2"] = revision_msg["payload"]
        case_state["status"] = "bull_revised"
        case_state = _persist_chair_step(
            case_state,
            {
                "agent": "BullAgent",
                "action": "bull_revised",
                "target_agent": "EvaluatorAgent",
                "summary": case_state["bull_output_v2"].get("revision_note"),
                "evidence_refs": [
                    item["citation_id"]
                    for item in case_state["bull_output_v2"].get("supporting_points", [])
                ],
            },
        )

    case_state["final_bull_output"] = case_state.get("bull_output_v2") or case_state["bull_output"]
    case_state_for_final_eval = {
        **case_state,
        "bull_output": case_state["final_bull_output"],
    }
    evaluator_v2_msg = run_agent("evaluator", case_state_for_final_eval)
    case_state["evaluation_output_v2"] = evaluator_v2_msg["payload"]
    case_state["final_evaluation_output"] = case_state["evaluation_output_v2"]
    case_state["status"] = "final_evaluation_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "EvaluatorAgent",
            "action": "final_evaluation_completed",
            "target_agent": "MemoAgent",
            "summary": (
                "Final evaluation completed. "
                f"Revision required: {case_state['final_evaluation_output']['revision_required']}."
            ),
            "evidence_refs": [],
        },
    )

    memo_msg = run_agent("memo", case_state)
    case_state["final_memo"] = memo_msg["payload"]
    case_state["status"] = "memo_generated"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "MemoAgent",
            "action": "memo_generated",
            "target_agent": "HumanReviewer",
            "summary": case_state["final_memo"]["summary"],
            "evidence_refs": evidence_refs,
        },
    )

    case_state["human_status"] = "pending_review"
    case_state["status"] = "pending_human_review"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "human_review_pending",
            "target_agent": "HumanReviewer",
            "summary": "Final memo is ready for human review.",
            "evidence_refs": evidence_refs,
        },
    )

    return {
        "case_state": case_state,
        "final_memo": case_state["final_memo"],
        "audit_log": case_state["audit_log"],
    }


def run_parallel_blind_workflow(case_id: str = "AAPL-001", ticker: str = "AAPL") -> Dict[str, Any]:
    case_state = create_or_reset_case(case_id, ticker)
    case_state["parallel_blind_review"] = True
    case_state["blind_review_status"] = "started"
    case_state["status"] = "blind_review_started"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "blind_review_started",
            "target_agent": "BullAgent,BearAgent",
            "summary": f"Started parallel blind review for {case_id} / {ticker}.",
            "evidence_refs": [],
        },
    )

    evidence_pack = case_state["evidence_pack"]
    evidence_refs = [item["citation_id"] for item in evidence_pack["evidence_items"]]
    case_state["status"] = "evidence_pack_ready"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "DataStewardAgent",
            "action": "evidence_pack_ready",
            "target_agent": "BullAgent,BearAgent",
            "summary": f"Prepared Evidence Pack with {len(evidence_refs)} items for blind review.",
            "evidence_refs": evidence_refs,
        },
    )

    bull_first_pass = run_bull_first_pass_agent(evidence_pack)
    case_state["bull_first_pass"] = bull_first_pass
    case_state["bull_output"] = bull_first_pass
    case_state["blind_review_status"] = "bull_first_pass_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BullAgent",
            "action": "bull_first_pass_completed",
            "target_agent": "BearAgent",
            "summary": bull_first_pass["bull_thesis"],
            "evidence_refs": [
                item["citation_id"]
                for item in bull_first_pass.get("supporting_points", [])
            ],
        },
    )

    bear_first_pass = run_bear_first_pass_agent(evidence_pack)
    case_state["bear_first_pass"] = bear_first_pass
    case_state["bear_output"] = bear_first_pass
    case_state["blind_review_status"] = "bear_first_pass_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BearAgent",
            "action": "bear_first_pass_completed",
            "target_agent": "BullAgent",
            "summary": bear_first_pass["bear_thesis"],
            "evidence_refs": [
                item["citation_id"]
                for item in bear_first_pass.get("attack_points", [])
            ],
        },
    )

    case_state["blind_review_status"] = "rebuttal_exchange_started"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "rebuttal_exchange_started",
            "target_agent": "BullAgent,BearAgent",
            "summary": "Blind first-pass outputs completed; rebuttal exchange started.",
            "evidence_refs": [],
        },
    )

    bull_rebuttal = run_bull_rebuttal_agent(
        evidence_pack,
        bull_first_pass,
        bear_first_pass,
    )
    case_state["bull_rebuttal"] = bull_rebuttal
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BullAgent",
            "action": "bull_rebuttal_completed",
            "target_agent": "RiskAgent",
            "summary": bull_rebuttal["rebuttal_summary"],
            "evidence_refs": ["E1", "E3", "E5"],
        },
    )

    bear_rebuttal = run_bear_rebuttal_agent(
        evidence_pack,
        bull_first_pass,
        bear_first_pass,
    )
    case_state["bear_rebuttal"] = bear_rebuttal
    case_state["blind_review_status"] = "rebuttal_exchange_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "BearAgent",
            "action": "bear_rebuttal_completed",
            "target_agent": "RiskAgent",
            "summary": bear_rebuttal["rebuttal_summary"],
            "evidence_refs": ["E3", "E4", "E6"],
        },
    )

    case_state["blind_review_status"] = "completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "blind_review_completed",
            "target_agent": "RiskAgent",
            "summary": "Parallel blind review and rebuttal exchange completed.",
            "evidence_refs": evidence_refs,
        },
    )

    risk_bull_context = {
        **bull_first_pass,
        "rebuttal": bull_rebuttal,
    }
    risk_bear_context = {
        **bear_first_pass,
        "rebuttal": bear_rebuttal,
    }
    risk_output = run_risk_agent(evidence_pack, risk_bull_context, risk_bear_context)
    case_state["risk_output"] = risk_output
    case_state["status"] = "risk_generated"
    case_state = _persist_chair_step(
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

    evaluator_output = run_evaluator_agent(
        evidence_pack,
        bull_first_pass,
        bear_first_pass,
        risk_output,
    )
    case_state["evaluation_output"] = evaluator_output
    case_state["status"] = "evaluation_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "EvaluatorAgent",
            "action": "evaluation_completed",
            "target_agent": evaluator_output.get("target_agent"),
            "summary": (
                "Initial evaluation completed after blind review. "
                f"Revision required: {evaluator_output['revision_required']}."
            ),
            "evidence_refs": [],
        },
    )

    if evaluator_output["revision_required"]:
        case_state["status"] = "revision_requested"
        case_state = _persist_chair_step(
            case_state,
            {
                "agent": "EvaluatorAgent",
                "action": "revision_requested",
                "target_agent": evaluator_output.get("target_agent"),
                "summary": "Evaluator requested BullAgent revision after blind review.",
                "evidence_refs": ["E5"],
            },
        )

        bull_output_v2 = run_bull_revision_agent(
            evidence_pack,
            bull_first_pass,
            evaluator_output,
        )
        case_state["bull_output_v2"] = bull_output_v2
        case_state["status"] = "bull_revised"
        case_state = _persist_chair_step(
            case_state,
            {
                "agent": "BullAgent",
                "action": "bull_revised",
                "target_agent": "EvaluatorAgent",
                "summary": bull_output_v2.get("revision_note"),
                "evidence_refs": [
                    item["citation_id"]
                    for item in bull_output_v2.get("supporting_points", [])
                ],
            },
        )

    case_state["final_bull_output"] = case_state.get("bull_output_v2") or bull_first_pass
    final_evaluation_output = run_evaluator_agent(
        evidence_pack,
        case_state["final_bull_output"],
        bear_first_pass,
        risk_output,
    )
    case_state["evaluation_output_v2"] = final_evaluation_output
    case_state["final_evaluation_output"] = final_evaluation_output
    case_state["status"] = "final_evaluation_completed"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "EvaluatorAgent",
            "action": "final_evaluation_completed",
            "target_agent": "MemoAgent",
            "summary": (
                "Final evaluation completed after blind review. "
                f"Revision required: {final_evaluation_output['revision_required']}."
            ),
            "evidence_refs": [],
        },
    )

    memo_output = run_memo_agent(
        evidence_pack,
        case_state["final_bull_output"],
        bear_first_pass,
        risk_output,
        final_evaluation_output,
    )
    case_state["final_memo"] = memo_output
    case_state["status"] = "memo_generated"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "MemoAgent",
            "action": "memo_generated",
            "target_agent": "HumanReviewer",
            "summary": memo_output["summary"],
            "evidence_refs": evidence_refs,
        },
    )

    case_state["human_status"] = "pending_review"
    case_state["status"] = "pending_human_review"
    case_state = _persist_chair_step(
        case_state,
        {
            "agent": "ChairAgent",
            "action": "human_review_pending",
            "target_agent": "HumanReviewer",
            "summary": "Parallel blind review memo is ready for human review.",
            "evidence_refs": evidence_refs,
        },
    )

    return {
        "case_state": case_state,
        "final_memo": case_state["final_memo"],
        "audit_log": case_state["audit_log"],
    }
