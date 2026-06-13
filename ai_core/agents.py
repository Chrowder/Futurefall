from typing import Dict, Any, Optional


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


def run_bear_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
) -> Dict[str, Any]:
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