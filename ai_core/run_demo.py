from typing import Dict, Any, List, Optional


sample_evidence_pack = {
    "case_id": "AAPL-001",
    "ticker": "AAPL",
    "company": "Apple Inc.",
    "evidence_items": [
        {
            "citation_id": "E1",
            "claim": "FY26Q2 revenue was $96.4B, YoY +4.2%; services revenue was $26.8B, YoY +11.5%.",
            "source": "STUB-10Q",
            "date": "2026-05-02",
        },
        {
            "citation_id": "E2",
            "claim": "Gross margin was 46.9%; services gross margin was 74.1%.",
            "source": "STUB-10Q",
            "date": "2026-05-02",
        },
        {
            "citation_id": "E3",
            "claim": "Greater China revenue was $15.1B, YoY -8.3%.",
            "source": "STUB-10Q",
            "date": "2026-05-02",
        },
        {
            "citation_id": "E4",
            "claim": "The company announced a new $110B buyback authorization.",
            "source": "STUB-Company Announcement",
            "date": "2026-05-02",
        },
        {
            "citation_id": "E5",
            "claim": "Apple Intelligence 2 adoption reached 61% on eligible devices after iOS 20 release.",
            "source": "STUB-News",
            "date": "2026-04-18",
        },
        {
            "citation_id": "E6",
            "claim": "Supply chain data shows FY26H2 iPhone shipment estimate down 5%.",
            "source": "STUB-Supply Chain Research",
            "date": "2026-05-20",
        },
    ],
}


class MockBandRoom:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.messages: List[Dict[str, Any]] = []

    def send_message(self, message: Dict[str, Any]) -> None:
        self.messages.append(message)
        print(
            f"\n[MockBand: {self.room_id}] "
            f"{message['from_agent']} -> {message.get('to_agent') or 'ALL'}"
        )
        print(message)


def wrap_message(
    case_id: str,
    from_agent: str,
    payload: Dict[str, Any],
    message_type: str = "agent_result",
    to_agent: Optional[str] = None,
    revision_required: bool = False,
    target_agent: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "case_id": case_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "status": "completed",
        "payload": payload,
        "revision_required": revision_required,
        "target_agent": target_agent,
    }


def valid_citations(evidence_pack: Dict[str, Any]) -> set:
    return {item["citation_id"] for item in evidence_pack["evidence_items"]}

def create_initial_case_state(
    evidence_pack: Dict[str, Any] = sample_evidence_pack,
) -> Dict[str, Any]:
    return {
        "case_id": evidence_pack["case_id"],
        "ticker": evidence_pack["ticker"],
        "evidence_pack": evidence_pack,
    }

def run_bull_agent(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "bull_thesis": (
            "AAPL has a constructive medium-term setup supported by services growth, "
            "high-margin revenue mix, and shareholder returns."
        ),
        "supporting_points": [
            {
                "claim": "Services revenue grew 11.5% YoY, supporting recurring revenue strength.",
                "citation_id": "E1",
            },
            {
                "claim": "Services gross margin remained high at 74.1%, supporting profitability quality.",
                "citation_id": "E2",
            },
            {
                "claim": "The $110B buyback authorization supports shareholder return.",
                "citation_id": "E4",
            },
            {
                "claim": "Apple Intelligence adoption will significantly boost iPhone demand.",
                "citation_id": "E5",
            },
        ],
        "key_assumptions": [
            "Services growth remains stable.",
            "Apple Intelligence adoption can support future device engagement.",
        ],
        "confidence": 0.78,
    }

def run_bull_revision_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
) -> Dict[str, Any]:
    revised_points = []

    for point in bull_output.get("supporting_points", []):
        claim = point.get("claim", "")

        # 如果 Evaluator 认为这句话过度推断，就改得更谨慎
        if "significantly boost iPhone demand" in claim:
            revised_points.append(
                {
                    "claim": (
                        "Apple Intelligence adoption may support future device engagement, "
                        "but current evidence does not yet prove a significant iPhone demand boost."
                    ),
                    "citation_id": "E5",
                }
            )
        else:
            revised_points.append(point)

    return {
        "bull_thesis": (
            "AAPL has a constructive but balanced medium-term setup supported by services growth, "
            "high-margin revenue mix, and shareholder returns, while device demand recovery remains uncertain."
        ),
        "supporting_points": revised_points,
        "key_assumptions": [
            "Services growth remains stable.",
            "Apple Intelligence adoption may support engagement, but demand impact requires further evidence.",
        ],
        "confidence": 0.68,
        "revision_note": "Revised based on Evaluator feedback: lowered confidence and softened unsupported demand claim.",
    }

def run_bear_agent(evidence_pack: Dict[str, Any], bull_output: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "bear_thesis": (
            "The bull case is weakened by regional revenue pressure and uncertain device upgrade demand."
        ),
        "attack_points": [
            {
                "target_claim": "AAPL has a constructive medium-term setup.",
                "critique": "Greater China revenue declined 8.3% YoY, which weakens the growth narrative.",
                "citation_id": "E3",
            },
            {
                "target_claim": "Apple Intelligence adoption can support future device engagement.",
                "critique": (
                    "Supply chain data still indicates FY26H2 iPhone shipment estimate down 5%, "
                    "so adoption does not yet prove demand recovery."
                ),
                "citation_id": "E6",
            },
        ],
        "missed_risks": [
            {
                "risk": "AI feature adoption may not translate into near-term iPhone upgrades.",
                "citation_id": "E6",
            }
        ],
        "confidence": 0.78,
    }

def run_risk_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "risk_summary": (
            "The main risks are regional revenue weakness, uncertain device demand, "
            "and the possibility that AI feature adoption does not translate into near-term upgrades."
        ),
        "risk_flags": [
            {
                "risk": "Greater China revenue declined 8.3% YoY, creating regional growth pressure.",
                "severity": "high",
                "citation_id": "E3",
            },
            {
                "risk": "FY26H2 iPhone shipment estimate is down 5%, suggesting device demand uncertainty.",
                "severity": "high",
                "citation_id": "E6",
            },
            {
                "risk": (
                    "Apple Intelligence adoption may improve engagement, but current evidence does not "
                    "prove near-term iPhone upgrade demand."
                ),
                "severity": "medium",
                "citation_id": "E5",
            },
        ],
        "confidence": 0.82,
    }
    
def run_evaluator_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    citations = valid_citations(evidence_pack)
    unsupported_claims = []
    total_claims = 0
    cited_claims = 0

    # 1. Check BullAgent supporting points
    for point in bull_output.get("supporting_points", []):
        total_claims += 1
        cid = point.get("citation_id")
        claim = point.get("claim", "")

        if cid:
            cited_claims += 1

        if cid not in citations:
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": claim,
                    "reason": f"Citation {cid} does not exist in Evidence Pack.",
                    "required_action": "Revise with valid citation.",
                }
            )

        # Key hallucination / over-claim check:
        # Evidence E5 only supports adoption rate, not direct iPhone demand growth.
        claim_lower = claim.lower()
        if "significantly boost" in claim_lower and "iphone demand" in claim_lower:
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": claim,
                    "reason": (
                        "Evidence supports Apple Intelligence adoption rate, "
                        "but does not directly prove future iPhone demand growth."
                    ),
                    "required_action": "Lower confidence or rewrite with more cautious wording.",
                }
            )

    # 2. Check BearAgent attack points
    for point in bear_output.get("attack_points", []):
        total_claims += 1
        cid = point.get("citation_id")
        critique = point.get("critique", "")

        if cid:
            cited_claims += 1

        if cid not in citations:
            unsupported_claims.append(
                {
                    "source_agent": "BearAgent",
                    "claim": critique,
                    "reason": f"Citation {cid} does not exist in Evidence Pack.",
                    "required_action": "Revise with valid citation.",
                }
            )

    # 3. Check RiskAgent risk flags
    if risk_output:
        for point in risk_output.get("risk_flags", []):
            total_claims += 1
            cid = point.get("citation_id")
            risk = point.get("risk", "")

            if cid:
                cited_claims += 1

            if cid not in citations:
                unsupported_claims.append(
                    {
                        "source_agent": "RiskAgent",
                        "claim": risk,
                        "reason": f"Citation {cid} does not exist in Evidence Pack.",
                        "required_action": "Revise with valid citation.",
                    }
                )

    citation_coverage = cited_claims / total_claims if total_claims else 0
    revision_required = len(unsupported_claims) > 0

    return {
        "faithfulness_score": 0.82 if revision_required else 0.92,
        "citation_coverage": round(citation_coverage, 2),
        "unsupported_claims": unsupported_claims,
        "hallucination_risk": "medium" if revision_required else "low",
        "revision_required": revision_required,
        "target_agent": "BullAgent" if revision_required else None,
    }

def run_memo_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "company": evidence_pack["company"],
        "ticker": evidence_pack["ticker"],
        "summary": (
            "AAPL shows a balanced research profile. The bull case is supported by services growth, "
            "high services margin, and shareholder returns. However, the bear and risk agents highlight "
            "regional weakness, iPhone shipment uncertainty, and limited evidence that AI adoption directly "
            "drives near-term demand."
        ),
        "bull_case": bull_output,
        "bear_case": bear_output,
        "risk_flags": risk_output.get("risk_flags", []),
        "evaluation_summary": {
            "faithfulness_score": evaluation_output["faithfulness_score"],
            "citation_coverage": evaluation_output["citation_coverage"],
            "hallucination_risk": evaluation_output["hallucination_risk"],
            "revision_required": evaluation_output["revision_required"],
        },
        "human_review_required": True,
        "disclaimer": "This is a research support memo, not investment advice.",
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