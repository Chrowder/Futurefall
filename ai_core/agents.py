import json
import os
from typing import Dict, Any, Optional

from ai_core.env_config import load_local_env
from ai_core.llm_clients import openai_compatible_client

load_local_env()


def valid_citations(evidence_pack: Dict[str, Any]) -> set:
    return {item["citation_id"] for item in evidence_pack["evidence_items"]}


def llm_agents_enabled() -> bool:
    return os.getenv("USE_LLM_AGENTS", "false").lower() == "true"


PROVIDER_ENV = {
    "aimlapi": {
        "api_key": "AIMLAPI_API_KEY",
        "base_url": "AIMLAPI_BASE_URL",
    },
    "featherless": {
        "api_key": "FEATHERLESS_API_KEY",
        "base_url": "FEATHERLESS_BASE_URL",
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "base_url": "OPENAI_BASE_URL",
    },
}


def llm_config_for_agent(agent_name: str, default_provider: str) -> Optional[Dict[str, str]]:
    if not llm_agents_enabled():
        return None

    env_prefix = agent_name.upper()
    provider = os.getenv(f"{env_prefix}_PROVIDER", default_provider).lower()
    provider_config = PROVIDER_ENV.get(provider)
    if not provider_config:
        return None

    api_key = os.getenv(provider_config["api_key"])
    base_url = os.getenv(provider_config["base_url"])
    model = os.getenv(f"{env_prefix}_MODEL")

    if not api_key or not base_url or not model:
        return None

    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
    }


def generate_agent_text(
    agent_name: str,
    default_provider: str,
    system_prompt: str,
    user_prompt: str,
) -> Optional[str]:
    config = llm_config_for_agent(agent_name, default_provider)
    if not config:
        return None

    try:
        return openai_compatible_client.generate_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            api_key=config["api_key"],
            base_url=config["base_url"],
            model=config["model"],
        )
    except Exception:
        if os.getenv("LLM_STRICT_ERRORS", "false").lower() == "true":
            raise
        return None


def parse_labeled_text(text: str) -> Dict[str, str]:
    parsed = {}

    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().upper().replace(" ", "_")
        parsed[normalized_key] = value.strip()

    return parsed


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def is_stub_evidence_pack(evidence_pack: Dict[str, Any]) -> bool:
    return any(
        item.get("provider") == "stub" or str(item.get("source", "")).startswith("STUB")
        for item in evidence_pack.get("evidence_items", [])
    )


def evidence_items(evidence_pack: Dict[str, Any]) -> list[Dict[str, Any]]:
    return evidence_pack.get("evidence_items", [])


def evidence_claim(evidence_pack: Dict[str, Any], citation_id: str) -> str:
    for item in evidence_items(evidence_pack):
        if item.get("citation_id") == citation_id:
            return item.get("claim", "")
    return ""


def first_evidence_items(evidence_pack: Dict[str, Any], limit: int = 4) -> list[Dict[str, Any]]:
    return evidence_items(evidence_pack)[:limit]


def generic_supporting_points(evidence_pack: Dict[str, Any], limit: int = 4) -> list[Dict[str, str]]:
    return [
        {
            "claim": item.get("claim", ""),
            "citation_id": item.get("citation_id", ""),
        }
        for item in first_evidence_items(evidence_pack, limit)
    ]


def generic_bull_output(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    ticker = evidence_pack["ticker"]
    company = evidence_pack.get("company", ticker)
    return {
        "bull_thesis": (
            f"{company} ({ticker}) has a fact-based research setup supported by "
            "auditable company, filing, financial, and market evidence."
        ),
        "supporting_points": generic_supporting_points(evidence_pack, 4),
        "key_assumptions": [
            "Recent SEC filings and financial facts are relevant to the research case.",
            "Market context should be interpreted alongside filing-grounded fundamentals.",
        ],
        "confidence": 0.7,
    }


def generic_bear_output(evidence_pack: Dict[str, Any], bull_output: Dict[str, Any]) -> Dict[str, Any]:
    points = generic_supporting_points(evidence_pack, 4)
    first_point = points[0] if points else {"claim": "Evidence coverage is limited.", "citation_id": ""}
    second_point = points[1] if len(points) > 1 else first_point
    return {
        "bear_thesis": (
            "The constructive case should be treated cautiously because the Evidence Pack "
            "is limited to fetched company, filing, financial, and market context."
        ),
        "attack_points": [
            {
                "target_claim": bull_output.get("bull_thesis", "Bull thesis"),
                "critique": f"This support depends on the scope and freshness of cited evidence: {first_point['claim']}",
                "citation_id": first_point.get("citation_id", ""),
            },
            {
                "target_claim": "Recent data is sufficient for a complete view.",
                "critique": f"Additional business, segment, and forward-looking context may be needed beyond: {second_point['claim']}",
                "citation_id": second_point.get("citation_id", ""),
            },
        ],
        "missed_risks": [
            {
                "risk": "Provider gaps, stale filings, or missing market data can limit confidence.",
                "citation_id": evidence_items(evidence_pack)[-1].get("citation_id", "") if evidence_items(evidence_pack) else "",
            }
        ],
        "confidence": 0.72,
    }


def generic_risk_output(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    flags = []
    for item in evidence_items(evidence_pack)[:4]:
        claim = item.get("claim", "")
        severity = "medium"
        lowered = claim.lower()
        if "unavailable" in lowered or "not found" in lowered or "error" in lowered:
            severity = "high"
        flags.append(
            {
                "risk": f"Research interpretation depends on this evidence item: {claim}",
                "severity": severity,
                "citation_id": item.get("citation_id", ""),
            }
        )

    if not flags:
        flags.append(
            {
                "risk": "Evidence Pack is empty, so no grounded risk assessment is possible.",
                "severity": "high",
                "citation_id": "",
            }
        )

    return {
        "risk_summary": (
            "Key risks are evidence freshness, provider coverage gaps, and the need to interpret "
            "filing-grounded facts alongside broader business context."
        ),
        "risk_flags": flags,
        "confidence": 0.74,
    }


def generic_bull_rebuttal_output(
    evidence_pack: Dict[str, Any],
    bear_first_pass: Dict[str, Any],
) -> Dict[str, Any]:
    points = generic_supporting_points(evidence_pack, 4)
    first_point = points[0] if points else {"claim": "Evidence coverage is limited.", "citation_id": ""}
    critique = (
        bear_first_pass.get("attack_points", [{}])[0].get("critique")
        if bear_first_pass.get("attack_points")
        else "BearAgent raised evidence coverage concerns."
    )
    return {
        "mode": "rebuttal",
        "rebuttal_summary": (
            "BullAgent accepts the need for caution, but keeps a constructive view only where "
            "the Evidence Pack provides cited support."
        ),
        "accepted_critiques": [
            {
                "critique": critique,
                "citation_id": first_point.get("citation_id", ""),
            }
        ],
        "rejected_critiques": [
            {
                "critique": "The Evidence Pack is too limited to support any constructive read.",
                "reason": f"The case can still cite concrete fetched evidence: {first_point.get('claim', '')}",
                "citation_id": first_point.get("citation_id", ""),
            }
        ],
        "revised_assumptions": [
            "Constructive claims should stay tied to cited evidence items.",
            "Provider gaps and filing freshness should reduce confidence.",
        ],
    }


def generic_bear_rebuttal_output(
    evidence_pack: Dict[str, Any],
    bull_first_pass: Dict[str, Any],
) -> Dict[str, Any]:
    points = generic_supporting_points(evidence_pack, 4)
    first_point = points[0] if points else {"claim": "Evidence coverage is limited.", "citation_id": ""}
    second_point = points[1] if len(points) > 1 else first_point
    return {
        "mode": "rebuttal",
        "rebuttal_summary": (
            "BearAgent concedes that cited evidence can support a research case, but maintains "
            "that provider gaps and limited context should keep conclusions cautious."
        ),
        "remaining_objections": [
            {
                "objection": f"Research confidence depends on data freshness and scope: {second_point.get('claim', '')}",
                "citation_id": second_point.get("citation_id", ""),
            }
        ],
        "conceded_points": [
            {
                "point": bull_first_pass.get("bull_thesis") or first_point.get("claim", ""),
                "citation_id": first_point.get("citation_id", ""),
            }
        ],
        "confidence": 0.72,
    }


def run_bull_agent(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        output = {
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
    else:
        output = generic_bull_output(evidence_pack)

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Write a concise bullish research thesis for {evidence_pack["ticker"]}.
Use only the evidence provided. Do not provide investment advice.
Return exactly:
BULL_THESIS: <one sentence>
KEY_ASSUMPTION_1: <short assumption>
KEY_ASSUMPTION_2: <short assumption>
"""
    generated = generate_agent_text(
        "bull",
        "aimlapi",
        "You are BullAgent in a human-in-the-loop research support workflow.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["bull_thesis"] = parsed.get("BULL_THESIS") or first_nonempty_line(generated) or output["bull_thesis"]
    output["key_assumptions"] = [
        parsed.get("KEY_ASSUMPTION_1") or output["key_assumptions"][0],
        parsed.get("KEY_ASSUMPTION_2") or output["key_assumptions"][1],
    ]
    return output


def run_bull_first_pass_agent(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    output = run_bull_agent(evidence_pack)
    output["mode"] = "blind_first_pass"

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Write a blind first-pass bullish thesis for {evidence_pack["ticker"]}.
Use only the Evidence Pack. Do not read or infer any BearAgent output.
Do not provide investment advice.
Return exactly:
BULL_THESIS: <one sentence>
KEY_ASSUMPTION_1: <short assumption>
KEY_ASSUMPTION_2: <short assumption>
"""
    generated = generate_agent_text(
        "bull",
        "aimlapi",
        "You are BullAgent writing an independent blind first-pass view.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["bull_thesis"] = parsed.get("BULL_THESIS") or first_nonempty_line(generated) or output["bull_thesis"]
    output["key_assumptions"] = [
        parsed.get("KEY_ASSUMPTION_1") or output["key_assumptions"][0],
        parsed.get("KEY_ASSUMPTION_2") or output["key_assumptions"][1],
    ]
    return output


def run_bull_revision_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
) -> Dict[str, Any]:
    if not is_stub_evidence_pack(evidence_pack):
        return {
            "bull_thesis": (
                f"{evidence_pack.get('company', evidence_pack['ticker'])} ({evidence_pack['ticker']}) "
                "has a cautious research case when every constructive point remains tied to cited evidence."
            ),
            "supporting_points": generic_supporting_points(evidence_pack, 4),
            "key_assumptions": [
                "Claims should remain limited to cited provider evidence.",
                "Provider gaps, filing freshness, and missing market data should reduce confidence.",
            ],
            "confidence": 0.64,
            "revision_note": "Revised based on Evaluator feedback: kept claims evidence-bound and lowered confidence.",
        }

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
    if is_stub_evidence_pack(evidence_pack):
        output = {
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
    else:
        output = generic_bear_output(evidence_pack, bull_output)

    if is_stub_evidence_pack(evidence_pack):
        critique_labels = """E3_CRITIQUE: <critique tied to Greater China revenue weakness>
E6_CRITIQUE: <critique tied to iPhone shipment uncertainty>
MISSED_RISK: <one missed risk tied to AI adoption or upgrades>"""
    else:
        critique_labels = """CRITIQUE_1: <critique tied to a cited evidence item>
CRITIQUE_2: <critique tied to another cited evidence item>
MISSED_RISK: <one missed risk tied to provider coverage, filing freshness, or market context>"""

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Bull output:
{json.dumps(bull_output, indent=2)}

Write a concise adversarial critique using only the evidence provided.
Do not provide investment advice.
Return exactly:
BEAR_THESIS: <one sentence>
{critique_labels}
"""
    generated = generate_agent_text(
        "bear",
        "aimlapi",
        "You are BearAgent in a human-in-the-loop research support workflow.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["bear_thesis"] = parsed.get("BEAR_THESIS") or first_nonempty_line(generated) or output["bear_thesis"]
    output["attack_points"][0]["critique"] = (
        parsed.get("E3_CRITIQUE") or parsed.get("CRITIQUE_1") or output["attack_points"][0]["critique"]
    )
    output["attack_points"][1]["critique"] = (
        parsed.get("E6_CRITIQUE") or parsed.get("CRITIQUE_2") or output["attack_points"][1]["critique"]
    )
    output["missed_risks"][0]["risk"] = parsed.get("MISSED_RISK") or output["missed_risks"][0]["risk"]
    return output


def run_bear_first_pass_agent(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        output = {
            "mode": "blind_first_pass",
            "bear_thesis": (
                "AAPL's setup faces pressure from Greater China weakness and uncertain iPhone upgrade demand."
            ),
            "attack_points": [
                {
                    "target_claim": "AAPL has a constructive medium-term setup.",
                    "critique": "Greater China revenue declined 8.3% YoY, creating a direct growth headwind.",
                    "citation_id": "E3",
                },
                {
                    "target_claim": "AI adoption can drive near-term device demand.",
                    "critique": (
                        "FY26H2 iPhone shipment estimates are down 5%, so current evidence does not prove "
                        "an imminent upgrade cycle."
                    ),
                    "citation_id": "E6",
                },
            ],
            "missed_risks": [
                {
                    "risk": "Apple Intelligence adoption may not convert into measurable iPhone upgrades.",
                    "citation_id": "E5",
                }
            ],
            "confidence": 0.76,
        }
    else:
        output = generic_bear_output(evidence_pack, {"bull_thesis": "Independent bullish first pass"})
        output["mode"] = "blind_first_pass"

    if is_stub_evidence_pack(evidence_pack):
        critique_labels = """E3_CRITIQUE: <critique tied to Greater China revenue weakness>
E6_CRITIQUE: <critique tied to iPhone shipment uncertainty>
MISSED_RISK: <one missed risk tied to AI adoption or upgrades>"""
    else:
        critique_labels = """CRITIQUE_1: <critique tied to a cited evidence item>
CRITIQUE_2: <critique tied to another cited evidence item>
MISSED_RISK: <one missed risk tied to provider coverage, filing freshness, or market context>"""

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Write a blind first-pass bearish critique for {evidence_pack["ticker"]}.
Use only the Evidence Pack. Do not read or infer BullAgent output.
Do not provide investment advice.
Return exactly:
BEAR_THESIS: <one sentence>
{critique_labels}
"""
    generated = generate_agent_text(
        "bear",
        "aimlapi",
        "You are BearAgent writing an independent blind first-pass view.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["bear_thesis"] = parsed.get("BEAR_THESIS") or first_nonempty_line(generated) or output["bear_thesis"]
    output["attack_points"][0]["critique"] = (
        parsed.get("E3_CRITIQUE") or parsed.get("CRITIQUE_1") or output["attack_points"][0]["critique"]
    )
    output["attack_points"][1]["critique"] = (
        parsed.get("E6_CRITIQUE") or parsed.get("CRITIQUE_2") or output["attack_points"][1]["critique"]
    )
    output["missed_risks"][0]["risk"] = parsed.get("MISSED_RISK") or output["missed_risks"][0]["risk"]
    return output


def run_bull_rebuttal_agent(
    evidence_pack: Dict[str, Any],
    bull_first_pass: Dict[str, Any],
    bear_first_pass: Dict[str, Any],
) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        output = {
            "mode": "rebuttal",
            "rebuttal_summary": (
                "BullAgent accepts that iPhone demand evidence is not yet decisive, but maintains that "
                "services growth, high services margin, and buybacks support a constructive setup."
            ),
            "accepted_critiques": [
                {
                    "critique": "Greater China weakness should temper the growth narrative.",
                    "citation_id": "E3",
                },
                {
                    "critique": "AI adoption does not yet prove near-term iPhone demand acceleration.",
                    "citation_id": "E5",
                },
            ],
            "rejected_critiques": [
                {
                    "critique": "Services growth and buybacks are not enough to matter.",
                    "reason": "The Evidence Pack supports both services strength and shareholder returns.",
                    "citation_id": "E1",
                }
            ],
            "revised_assumptions": [
                "Services growth remains a key support.",
                "AI adoption may improve engagement, but demand impact requires more evidence.",
                "Greater China weakness remains an important offset.",
            ],
        }
    else:
        output = generic_bull_rebuttal_output(evidence_pack, bear_first_pass)

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Bull first pass:
{json.dumps(bull_first_pass, indent=2)}

Bear first pass:
{json.dumps(bear_first_pass, indent=2)}

Write BullAgent's rebuttal after seeing both blind first-pass outputs.
Use only the provided evidence and agent outputs. Do not provide investment advice.
Return exactly:
REBUTTAL_SUMMARY: <one sentence>
ACCEPTED_CRITIQUE_1: <short critique accepted>
REVISED_ASSUMPTION_1: <short revised assumption>
"""
    generated = generate_agent_text(
        "bull",
        "aimlapi",
        "You are BullAgent writing a concise rebuttal.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["rebuttal_summary"] = (
        parsed.get("REBUTTAL_SUMMARY") or first_nonempty_line(generated) or output["rebuttal_summary"]
    )
    if parsed.get("ACCEPTED_CRITIQUE_1"):
        output["accepted_critiques"][0]["critique"] = parsed["ACCEPTED_CRITIQUE_1"]
    if parsed.get("REVISED_ASSUMPTION_1"):
        output["revised_assumptions"][0] = parsed["REVISED_ASSUMPTION_1"]
    return output


def run_bear_rebuttal_agent(
    evidence_pack: Dict[str, Any],
    bull_first_pass: Dict[str, Any],
    bear_first_pass: Dict[str, Any],
) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        output = {
            "mode": "rebuttal",
            "rebuttal_summary": (
                "BearAgent concedes that services and buybacks are real supports, but maintains that "
                "China weakness and shipment cuts leave the demand recovery unproven."
            ),
            "remaining_objections": [
                {
                    "objection": "Greater China revenue decline remains a material offset.",
                    "citation_id": "E3",
                },
                {
                    "objection": "Shipment estimates still point to uncertain iPhone demand.",
                    "citation_id": "E6",
                },
            ],
            "conceded_points": [
                {
                    "point": "Services revenue growth and high services gross margin support profitability quality.",
                    "citation_id": "E1",
                },
                {
                    "point": "The buyback authorization supports shareholder returns.",
                    "citation_id": "E4",
                },
            ],
            "confidence": 0.74,
        }
    else:
        output = generic_bear_rebuttal_output(evidence_pack, bull_first_pass)

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Bull first pass:
{json.dumps(bull_first_pass, indent=2)}

Bear first pass:
{json.dumps(bear_first_pass, indent=2)}

Write BearAgent's rebuttal after seeing both blind first-pass outputs.
Use only the provided evidence and agent outputs. Do not provide investment advice.
Return exactly:
REBUTTAL_SUMMARY: <one sentence>
REMAINING_OBJECTION_1: <short remaining objection>
CONCEDED_POINT_1: <short conceded point>
"""
    generated = generate_agent_text(
        "bear",
        "aimlapi",
        "You are BearAgent writing a concise rebuttal.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["rebuttal_summary"] = (
        parsed.get("REBUTTAL_SUMMARY") or first_nonempty_line(generated) or output["rebuttal_summary"]
    )
    if parsed.get("REMAINING_OBJECTION_1"):
        output["remaining_objections"][0]["objection"] = parsed["REMAINING_OBJECTION_1"]
    if parsed.get("CONCEDED_POINT_1"):
        output["conceded_points"][0]["point"] = parsed["CONCEDED_POINT_1"]
    return output


def run_risk_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        output = {
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
    else:
        output = generic_risk_output(evidence_pack)

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Bull output:
{json.dumps(bull_output, indent=2)}

Bear output:
{json.dumps(bear_output, indent=2)}

Write one concise risk summary for this human-in-the-loop research workflow.
Use only the provided evidence. Do not provide investment advice.
Return exactly:
RISK_SUMMARY: <one sentence>
"""
    generated = generate_agent_text(
        "risk",
        "featherless",
        "You are RiskAgent in a research support workflow.",
        prompt,
    )
    if not generated:
        return output

    parsed = parse_labeled_text(generated)
    output["risk_summary"] = parsed.get("RISK_SUMMARY") or first_nonempty_line(generated) or output["risk_summary"]
    return output


def run_evaluator_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    citations = valid_citations(evidence_pack)
    stub_mode = is_stub_evidence_pack(evidence_pack)
    unsupported_claims = []
    revision_reasons = []
    evaluation_notes = []
    total_claims = 0
    cited_claims = 0

    for point in bull_output.get("supporting_points", []):
        total_claims += 1
        cid = point.get("citation_id")
        claim = point.get("claim", "")

        if cid:
            cited_claims += 1

        if cid not in citations:
            reason = f"Citation {cid} does not exist in Evidence Pack."
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": claim,
                    "reason": reason,
                    "required_action": "Revise with valid citation.",
                }
            )
            revision_reasons.append(reason)

        claim_lower = claim.lower()
        if "significantly boost" in claim_lower and "iphone demand" in claim_lower:
            reason = (
                "Evidence supports Apple Intelligence adoption rate, "
                "but does not directly prove future iPhone demand growth."
            )
            unsupported_claims.append(
                {
                    "source_agent": "BullAgent",
                    "claim": claim,
                    "reason": reason,
                    "required_action": "Lower confidence or rewrite with more cautious wording.",
                }
            )
            revision_reasons.append(reason)

    for point in bear_output.get("attack_points", []):
        total_claims += 1
        cid = point.get("citation_id")
        critique = point.get("critique", "")

        if cid:
            cited_claims += 1

        if cid not in citations:
            reason = f"Citation {cid} does not exist in Evidence Pack."
            unsupported_claims.append(
                {
                    "source_agent": "BearAgent",
                    "claim": critique,
                    "reason": reason,
                    "required_action": "Revise with valid citation.",
                }
            )
            revision_reasons.append(reason)

    bear_risk_refs = {
        point.get("citation_id")
        for point in bear_output.get("attack_points", []) + bear_output.get("missed_risks", [])
        if point.get("citation_id")
    }
    if stub_mode and bear_risk_refs & {"E3", "E5", "E6"}:
        evaluation_notes.append("BearAgent addressed at least one Evidence Pack risk.")
    elif not stub_mode and bear_risk_refs:
        evaluation_notes.append("BearAgent addressed cited Evidence Pack items.")
    else:
        evaluation_notes.append("BearAgent did not address a cited Evidence Pack item.")
        revision_reasons.append("BearAgent should address at least one cited Evidence Pack item.")

    if stub_mode:
        risk_coverage_checks = {
            "greater_china_weakness": False,
            "iphone_shipment_uncertainty": False,
            "ai_adoption_demand_uncertainty": False,
        }
    else:
        ordered_required_refs = [
            item.get("citation_id")
            for item in evidence_items(evidence_pack)[:3]
            if item.get("citation_id")
        ]
        risk_coverage_checks = {citation_id: False for citation_id in ordered_required_refs}
    if risk_output:
        for point in risk_output.get("risk_flags", []):
            total_claims += 1
            cid = point.get("citation_id")
            risk = point.get("risk", "")

            if cid:
                cited_claims += 1

            if cid not in citations:
                reason = f"Citation {cid} does not exist in Evidence Pack."
                unsupported_claims.append(
                    {
                        "source_agent": "RiskAgent",
                        "claim": risk,
                        "reason": reason,
                        "required_action": "Revise with valid citation.",
                    }
                )
                revision_reasons.append(reason)

            if stub_mode:
                risk_lower = risk.lower()
                if cid == "E3" or "greater china" in risk_lower:
                    risk_coverage_checks["greater_china_weakness"] = True
                if cid == "E6" or "shipment" in risk_lower:
                    risk_coverage_checks["iphone_shipment_uncertainty"] = True
                if cid in {"E5", "E6"} and (
                    "ai" in risk_lower or "apple intelligence" in risk_lower or "upgrade" in risk_lower
                ):
                    risk_coverage_checks["ai_adoption_demand_uncertainty"] = True
            elif cid in risk_coverage_checks:
                risk_coverage_checks[cid] = True
    else:
        revision_reasons.append("RiskAgent output is missing.")

    covered_risks = sum(1 for covered in risk_coverage_checks.values() if covered)
    risk_coverage_score = round(covered_risks / len(risk_coverage_checks), 2)

    if stub_mode:
        if risk_coverage_checks["greater_china_weakness"]:
            evaluation_notes.append("RiskAgent covered Greater China weakness.")
        if risk_coverage_checks["iphone_shipment_uncertainty"]:
            evaluation_notes.append("RiskAgent covered iPhone shipment uncertainty.")
        if risk_coverage_checks["ai_adoption_demand_uncertainty"]:
            evaluation_notes.append("RiskAgent covered AI adoption demand uncertainty.")
    else:
        evaluation_notes.append(
            f"RiskAgent covered {covered_risks} of {len(risk_coverage_checks)} required evidence references."
        )

    missing_risk_checks = [
        name for name, covered in risk_coverage_checks.items() if not covered
    ]
    if missing_risk_checks:
        revision_reasons.append(
            f"RiskAgent should cover missing evidence references: {', '.join(missing_risk_checks)}."
        )

    citation_coverage = cited_claims / total_claims if total_claims else 0
    revision_required = len(unsupported_claims) > 0
    bull_confidence = bull_output.get("confidence", 0)

    if unsupported_claims and bull_confidence >= 0.75:
        confidence_calibration = "overconfident"
        revision_reasons.append("BullAgent confidence is too high for an unsupported causal claim.")
    elif unsupported_claims:
        confidence_calibration = "needs_caution"
    else:
        confidence_calibration = "well_calibrated"

    if citation_coverage == 1:
        evaluation_notes.append("All evaluated claims include citation IDs.")
    else:
        evaluation_notes.append("Some evaluated claims are missing citation IDs.")

    return {
        "faithfulness_score": 0.82 if revision_required else 0.92,
        "citation_coverage": round(citation_coverage, 2),
        "unsupported_claims": unsupported_claims,
        "hallucination_risk": "medium" if revision_required else "low",
        "revision_required": revision_required,
        "target_agent": "BullAgent" if revision_required else None,
        "risk_coverage_score": risk_coverage_score,
        "confidence_calibration": confidence_calibration,
        "evaluation_notes": evaluation_notes,
        "revision_reasons": revision_reasons,
    }


def run_memo_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
) -> Dict[str, Any]:
    if is_stub_evidence_pack(evidence_pack):
        summary = (
            "AAPL shows a balanced research profile. The bull case is supported by services growth, "
            "high services margin, and shareholder returns. However, the bear and risk agents highlight "
            "regional weakness, iPhone shipment uncertainty, and limited evidence that AI adoption directly "
            "drives near-term demand."
        )
    else:
        summary = (
            f"{evidence_pack.get('company', evidence_pack['ticker'])} ({evidence_pack['ticker']}) "
            "has been reviewed using fetched company, filing, financial, and market evidence. "
            "The memo should be treated as research support because provider coverage, filing freshness, "
            "and missing auxiliary market data can affect confidence."
        )

    prompt = f"""Evidence Pack:
{json.dumps(evidence_pack, indent=2)}

Bull case:
{json.dumps(bull_output, indent=2)}

Bear case:
{json.dumps(bear_output, indent=2)}

Risk flags:
{json.dumps(risk_output.get("risk_flags", []), indent=2)}

Evaluation:
{json.dumps(evaluation_output, indent=2)}

Write one concise final memo summary for a human reviewer.
Use only the provided evidence and agent outputs.
Keep the language cautious and make clear this is research support, not investment advice.
Return only the summary paragraph.
"""
    generated = generate_agent_text(
        "memo",
        "aimlapi",
        "You are MemoAgent in a human-in-the-loop research support workflow.",
        prompt,
    )
    summary = generated or summary

    return {
        "company": evidence_pack["company"],
        "ticker": evidence_pack["ticker"],
        "summary": summary,
        "bull_case": bull_output,
        "bear_case": bear_output,
        "risk_flags": risk_output.get("risk_flags", []),
        "evaluation_summary": {
            "faithfulness_score": evaluation_output["faithfulness_score"],
            "citation_coverage": evaluation_output["citation_coverage"],
            "hallucination_risk": evaluation_output["hallucination_risk"],
            "revision_required": evaluation_output["revision_required"],
            "risk_coverage_score": evaluation_output["risk_coverage_score"],
            "confidence_calibration": evaluation_output["confidence_calibration"],
            "revision_reasons": evaluation_output["revision_reasons"],
            "evaluation_notes": evaluation_output["evaluation_notes"],
        },
        "human_review_required": True,
        "disclaimer": "This is a research support memo, not investment advice.",
    }
