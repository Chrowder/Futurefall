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


def run_evaluator_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
) -> Dict[str, Any]:
    citations = valid_citations(evidence_pack)
    unsupported_claims = []
    total_claims = 0
    cited_claims = 0

    for point in bull_output.get("supporting_points", []):
        total_claims += 1
        cid = point.get("citation_id")

        if cid:
            cited_claims += 1

        if cid not in citations:
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": point.get("claim"),
                    "reason": f"Citation {cid} does not exist in Evidence Pack.",
                    "required_action": "Revise with valid citation.",
                }
            )

        claim_lower = point.get("claim", "").lower()
        if "significantly boost iphone demand" in claim_lower:
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": point.get("claim"),
                    "reason": (
                        "Evidence supports Apple Intelligence adoption rate, "
                        "but does not directly prove future iPhone demand growth."
                    ),
                    "required_action": "Lower confidence or rewrite with more cautious wording.",
                }
            )

    for point in bear_output.get("attack_points", []):
        total_claims += 1
        cid = point.get("citation_id")

        if cid:
            cited_claims += 1

        if cid not in citations:
            unsupported_claims.append(
                {
                    "source_agent": "BearAgent",
                    "claim": point.get("critique"),
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


def run_agent(agent_name: str, case_state: Dict[str, Any]) -> Dict[str, Any]:
    case_id = case_state["case_id"]
    evidence_pack = case_state["evidence_pack"]

    if agent_name == "bull":
        payload = run_bull_agent(evidence_pack)
        return wrap_message(case_id, "BullAgent", payload)

    if agent_name == "bear":
        payload = run_bear_agent(evidence_pack, case_state["bull_output"])
        return wrap_message(case_id, "BearAgent", payload)

    if agent_name == "evaluator":
        payload = run_evaluator_agent(
            evidence_pack,
            case_state["bull_output"],
            case_state["bear_output"],
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
    raise ValueError(f"Unknown agent name: {agent_name}")


def main():
    room = MockBandRoom("local-bandalpha-demo")

    case_state = {
        "case_id": sample_evidence_pack["case_id"],
        "ticker": sample_evidence_pack["ticker"],
        "evidence_pack": sample_evidence_pack,
    }

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
    print("\n=== DONE ===")
    print(f"Initial revision required: {case_state['evaluation_output']['revision_required']}")
    if "evaluation_output_v2" in case_state:
        print(f"After revision required: {case_state['evaluation_output_v2']['revision_required']}")
        print(f"Final hallucination risk: {case_state['evaluation_output_v2']['hallucination_risk']}")

if __name__ == "__main__":
    main()