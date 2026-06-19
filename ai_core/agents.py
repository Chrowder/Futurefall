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


def _fmt_value(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    if abs(val) >= 1e9:
        return f"${val / 1e9:.1f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:.1f}M"
    return f"${val:,.0f}"


def _extract_financials(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    payloads = evidence_pack.get("provider_payloads", {})
    snap = payloads.get("sec_financial_snapshot", {})
    profile = payloads.get("sec_company_profile", {})
    filings = payloads.get("sec_recent_filings", {})
    market = payloads.get("market_snapshot", {})

    rev = snap.get("revenue") or {}
    ni = snap.get("net_income") or {}
    assets_data = snap.get("assets") or {}
    cash_data = snap.get("cash") or {}

    rev_val = rev.get("value")
    ni_val = ni.get("value")
    assets_val = assets_data.get("value")
    cash_val = cash_data.get("value")

    margin = None
    if rev_val and ni_val and rev_val > 0:
        margin = round(ni_val / rev_val * 100, 1)

    lp = filings.get("latest_periodic") or {}
    lc = filings.get("latest_current") or {}

    market_error = market.get("error", "")
    market_price = market.get("current_price")
    market_cap = market.get("market_cap")
    prev_close = market.get("previous_close")
    week52_high = market.get("fifty_two_week_high")
    week52_low = market.get("fifty_two_week_low")

    return {
        "company": profile.get("company") or evidence_pack.get("company", evidence_pack["ticker"]),
        "ticker": evidence_pack["ticker"],
        "cik": profile.get("cik_padded", ""),
        "exchanges": ", ".join(profile.get("exchanges", [])) or "N/A",
        "sic_description": profile.get("sic_description", ""),
        "revenue_fmt": _fmt_value(rev_val),
        "revenue_val": rev_val,
        "revenue_period": f"{rev.get('fp', '')} FY{rev.get('fy', '')}".strip(),
        "revenue_end": rev.get("end", ""),
        "revenue_filed": rev.get("filed", ""),
        "revenue_form": rev.get("form", ""),
        "net_income_fmt": _fmt_value(ni_val),
        "net_income_val": ni_val,
        "net_income_period": f"{ni.get('fp', '')} FY{ni.get('fy', '')}".strip(),
        "net_income_end": ni.get("end", ""),
        "assets_fmt": _fmt_value(assets_val),
        "assets_val": assets_val,
        "assets_end": assets_data.get("end", ""),
        "cash_fmt": _fmt_value(cash_val),
        "cash_val": cash_val,
        "net_margin_pct": margin,
        "margin_fmt": f"{margin}%" if margin is not None else "N/A",
        "latest_periodic_form": lp.get("form", ""),
        "latest_periodic_filed": lp.get("filing_date", ""),
        "latest_periodic_period": lp.get("report_date", ""),
        "latest_periodic_url": lp.get("source_url", ""),
        "latest_8k_filed": lc.get("filing_date", ""),
        "latest_8k_url": lc.get("source_url", ""),
        "market_available": not bool(market_error),
        "market_cap_available": bool(market_cap),
        "market_error": market_error,
        "price_fmt": _fmt_value(market_price) if market_price else "Unavailable",
        "market_cap_fmt": _fmt_value(market_cap) if market_cap else "Unavailable",
        "prev_close_fmt": _fmt_value(prev_close) if prev_close else "N/A",
        "week52_high_fmt": _fmt_value(week52_high) if week52_high else "N/A",
        "week52_low_fmt": _fmt_value(week52_low) if week52_low else "N/A",
    }


def generic_bull_output(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    f = _extract_financials(evidence_pack)
    ticker = f["ticker"]
    company = f["company"]
    supporting_points = []

    if f.get("revenue_val"):
        supporting_points.append({
            "claim": (
                f"Revenue of {f['revenue_fmt']} ({f['revenue_period']}, period ending "
                f"{f['revenue_end']}, filed {f['revenue_filed']}) establishes {company} "
                "as a large-scale revenue generator with an auditable SEC filing trail."
            ),
            "citation_id": "E3",
        })

    if f.get("net_income_val"):
        margin_note = f" (net profit margin: {f['margin_fmt']})" if f.get("net_margin_pct") else ""
        supporting_points.append({
            "claim": (
                f"Net income of {f['net_income_fmt']}{margin_note} for {f['net_income_period']} "
                f"(period ending {f['net_income_end']}) demonstrates consistent profitability "
                "at scale, grounded in SEC-reported figures."
            ),
            "citation_id": "E4",
        })

    if f.get("assets_val") or f.get("cash_val"):
        parts = []
        if f.get("assets_val"):
            parts.append(f"total assets of {f['assets_fmt']}")
        if f.get("cash_val"):
            parts.append(f"cash and equivalents of {f['cash_fmt']}")
        supporting_points.append({
            "claim": (
                f"{' and '.join(parts).capitalize()} (period ending {f.get('assets_end', 'N/A')}) "
                "provide significant balance sheet depth and financial flexibility."
            ),
            "citation_id": "E5",
        })

    if f.get("latest_periodic_form"):
        supporting_points.append({
            "claim": (
                f"Active SEC filing cadence: {f['latest_periodic_form']} filed "
                f"{f['latest_periodic_filed']} (report period {f['latest_periodic_period']}) "
                "confirms ongoing regulatory compliance and fresh disclosure."
            ),
            "citation_id": "E2",
        })

    thesis_parts = [f"{company} ({ticker}) demonstrates strong financial scale"]
    if f.get("revenue_val"):
        thesis_parts.append(f"with {f['revenue_fmt']} revenue")
    if f.get("net_income_val"):
        thesis_parts.append(f"and {f['net_income_fmt']} net income")
    thesis_parts.append("backed by auditable SEC filings.")

    return {
        "bull_thesis": " ".join(thesis_parts),
        "supporting_points": supporting_points[:4],
        "key_assumptions": [
            "SEC filing data is complete and accurately reflects the company's financial position.",
            "Financial scale (revenue, profitability, asset base) is a relevant input to the research case.",
        ],
        "confidence": 0.70,
    }


def generic_bear_output(evidence_pack: Dict[str, Any], bull_output: Dict[str, Any]) -> Dict[str, Any]:
    f = _extract_financials(evidence_pack)
    ticker = f["ticker"]
    attack_points = []
    missed_risks = []

    # Attack 1: valuation / market data limitations
    if not f["market_available"]:
        attack_points.append({
            "target_claim": bull_output.get("bull_thesis", ""),
            "critique": (
                f"Market price and market cap data are completely unavailable ({f['market_error']}). "
                "Without valuation anchors (P/E, EV/EBITDA, market cap), the financial "
                "scale cited by BullAgent cannot be assessed against current market pricing "
                "or peer multiples."
            ),
            "citation_id": "E6",
        })
    elif not f.get("market_cap_available"):
        attack_points.append({
            "target_claim": bull_output.get("bull_thesis", ""),
            "critique": (
                f"Market price is available ({f['price_fmt']}), but market cap is unavailable. "
                "Without a full market cap figure, enterprise value (EV), P/E ratio, and "
                "Price/Book cannot be computed — preventing any valuation-grounded conclusion."
            ),
            "citation_id": "E6",
        })
    else:
        attack_points.append({
            "target_claim": bull_output.get("bull_thesis", ""),
            "critique": (
                f"Market data ({f['price_fmt']} price, {f['market_cap_fmt']} market cap) "
                "provides only a current snapshot. Without historical price context, peer "
                "comparables, or analyst estimates, market pricing cannot validate or "
                "challenge the fundamental bull thesis."
            ),
            "citation_id": "E6",
        })

    # Attack 2: single-period snapshot — always present
    if f.get("revenue_val"):
        attack_points.append({
            "target_claim": f"Revenue of {f['revenue_fmt']} demonstrates strong performance.",
            "critique": (
                f"The Evidence Pack covers only a single reporting period "
                f"({f['revenue_period']}, period ending {f['revenue_end']}). "
                "Without prior-period comparisons, revenue growth rate, margin trajectory, "
                "or forward guidance, direction and momentum cannot be assessed."
            ),
            "citation_id": "E3",
        })
    else:
        attack_points.append({
            "target_claim": "The financial evidence provides a complete view.",
            "critique": (
                "The Evidence Pack lacks revenue and income data. "
                "The bull case cannot be verified against reported fundamentals."
            ),
            "citation_id": "E8",
        })

    missed_risks.append({
        "risk": (
            "No segment-level revenue breakdown, geographic revenue split, or product-mix "
            "data is available. Key concentration risks and divergence between business units "
            "cannot be identified from the current Evidence Pack alone."
        ),
        "citation_id": "E8",
    })

    return {
        "bear_thesis": (
            f"The constructive case for {ticker} is materially constrained by limited market "
            "valuation data, a single-period financial snapshot, and no segment or trend context."
        ),
        "attack_points": attack_points[:2],
        "missed_risks": missed_risks,
        "confidence": 0.72,
    }


def generic_risk_output(evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
    f = _extract_financials(evidence_pack)
    flags = []

    if not f["market_available"]:
        flags.append({
            "risk": (
                f"Market price and market cap are completely unavailable ({f['market_error']}). "
                "Valuation ratios (P/E, EV/Revenue, Price/Book) cannot be computed, "
                "removing the primary anchor for return analysis and relative comparisons."
            ),
            "severity": "high",
            "citation_id": "E6",
        })
    elif not f.get("market_cap_available"):
        flags.append({
            "risk": (
                f"Market price is partially available ({f['price_fmt']}), "
                "but market cap could not be retrieved. Enterprise value (EV) and "
                "market-cap-based ratios (P/E, EV/EBITDA) cannot be computed, "
                "leaving valuation analysis incomplete."
            ),
            "severity": "high",
            "citation_id": "E6",
        })

    if f.get("revenue_val"):
        flags.append({
            "risk": (
                f"Financial data covers only a single reporting period "
                f"({f['revenue_period']}, period ending {f['revenue_end']}). "
                "Revenue growth rate, margin trajectory, and earnings direction "
                "cannot be derived without multi-period comparisons."
            ),
            "severity": "high",
            "citation_id": "E3",
        })

    if f.get("assets_end") and f.get("revenue_end") and f["assets_end"] != f["revenue_end"]:
        flags.append({
            "risk": (
                f"Income statement data (revenue, net income) references period end "
                f"{f['revenue_end']}, while balance sheet data (assets, cash) references "
                f"period end {f['assets_end']}. Mixed reporting dates may distort ratio "
                "analysis if used together without adjustment."
            ),
            "severity": "medium",
            "citation_id": "E5",
        })

    flags.append({
        "risk": (
            "SEC EDGAR companyfacts provides consolidated financials only. "
            "No segment breakdown, geographic revenue split, or product-line profitability "
            "is available, limiting identification of concentration or divergence risks "
            "within the business."
        ),
        "severity": "medium",
        "citation_id": "E4",
    })

    if not flags:
        flags.append({
            "risk": "Evidence Pack is empty — no grounded risk assessment is possible.",
            "severity": "high",
            "citation_id": "",
        })

    return {
        "risk_summary": (
            "Key risks: (1) missing market price data prevents valuation; "
            "(2) single-period financials prevent trend analysis; "
            "(3) no segment data limits business risk identification."
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


def _apply_bull_rebuttal(
    bull_output: Dict[str, Any],
    bull_rebuttal: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Fold the Phase-2 rebuttal exchange into the Bull's final position.

    Without this, the parallel rebuttal exchange would be cosmetic — its revised
    assumptions and accepted critiques would surface only in the debate narrative
    and never reach the final thesis, assumptions, or confidence. This merges them
    in so the final memo position actually reflects what BullAgent conceded after
    seeing BearAgent's blind first pass.

    Applied at the aggregation point (after any Evaluator-triggered revision), so
    it lands regardless of whether a revision occurred and without altering the
    Evaluator's inputs.
    """
    if not bull_rebuttal:
        return bull_output

    merged = dict(bull_output)

    # 1. Merge the rebuttal's revised assumptions into the final assumptions
    #    (existing first, then any genuinely new ones — dedup by exact text).
    assumptions = list(merged.get("key_assumptions", []))
    seen = {a.strip().lower() for a in assumptions}
    for assumption in bull_rebuttal.get("revised_assumptions", []):
        key = assumption.strip().lower()
        if key and key not in seen:
            assumptions.append(assumption)
            seen.add(key)
    merged["key_assumptions"] = assumptions

    # 2. Carry the conceded / held critiques onto the final position so the memo
    #    can show how the debate moved the Bull's view.
    accepted = bull_rebuttal.get("accepted_critiques", [])
    rejected = bull_rebuttal.get("rejected_critiques", [])
    merged["accepted_critiques"] = accepted
    merged["rejected_critiques"] = rejected

    # 3. Temper confidence to reflect conceded points (small, floored at 0.50).
    if accepted:
        penalty = min(0.02 * len(accepted), 0.10)
        merged["confidence"] = round(max(merged.get("confidence", 0.0) - penalty, 0.50), 2)

    # 4. Human-readable note summarizing the debate's effect on the final view.
    merged["rebuttal_note"] = (
        f"Final position incorporates the Phase-2 rebuttal exchange: BullAgent "
        f"accepted {len(accepted)} of BearAgent's critique(s) and rejected "
        f"{len(rejected)}, revising its assumptions and confidence accordingly."
    )
    return merged


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
    # Advisory quality gaps that do NOT by themselves require a Bull revision
    # (e.g. risk-coverage shortfalls). Kept separate from revision_reasons so the
    # memo never shows "Revision Required: No" alongside a revision reason.
    coverage_gaps = []
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
        coverage_gaps.append("BearAgent should address at least one cited Evidence Pack item.")

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
        coverage_gaps.append("RiskAgent output is missing.")

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
        coverage_gaps.append(
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
        "coverage_gaps": coverage_gaps,
    }


def _build_rich_blind_memo(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
    blind_context: Dict[str, Any],
) -> str:
    """Rich structured memo for the parallel blind review workflow.

    Adds a BLIND REVIEW DEBATE section showing the full evolution of agent views:
    independent first passes → rebuttal exchange → final positions.
    """
    f = _extract_financials(evidence_pack)
    ticker = f["ticker"]
    company = f["company"]
    case_id = evidence_pack.get("case_id", f"{ticker}-001")
    report_date = (evidence_pack.get("evidence_items") or [{}])[0].get("date", "N/A")

    bull_fp = blind_context["bull_first_pass"]
    bear_fp = blind_context["bear_first_pass"]
    bull_rb = blind_context["bull_rebuttal"]
    bear_rb = blind_context["bear_rebuttal"]
    phase1_t = blind_context.get("phase1_elapsed", "N/A")
    phase2_t = blind_context.get("phase2_elapsed", "N/A")

    sep = "═" * 80
    thin = "─" * 80

    def section(title: str) -> str:
        return f"\n{thin}\n{title}\n{thin}"

    def bullet_list(items: list, key: str, cid_key: str = "citation_id") -> str:
        if not items:
            return "  (none)"
        lines = []
        for item in items:
            cid = item.get(cid_key, "")
            suffix = f"  [{cid}]" if cid else ""
            lines.append(f"  • {item.get(key, '')}{suffix}")
        return "\n".join(lines)

    # ── Header ────────────────────────────────────────────────────────────
    header = (
        f"\n{sep}\n"
        f"  RESEARCH SUPPORT MEMO — PARALLEL BLIND REVIEW\n"
        f"  {company} ({ticker})  |  Case: {case_id}  |  Report Date: {report_date}\n"
        f"  Mode: Independent analysis → Cross-disclosure → Rebuttal exchange\n"
        f"{sep}\n"
        f"  ⚠  DISCLAIMER: This is a research support memo, not investment advice.\n"
        f"{sep}"
    )

    # ── 1. Executive Summary ──────────────────────────────────────────────
    rev_note = f"revenue of {f['revenue_fmt']} ({f['revenue_period']})" if f.get("revenue_val") else "financials from SEC filings"
    ni_note = f"net income of {f['net_income_fmt']} (margin: {f['margin_fmt']})" if f.get("net_income_val") else "net income from SEC"
    if not f["market_available"]:
        market_note = f"Market data unavailable ({f['market_error']})."
    elif not f.get("market_cap_available"):
        market_note = f"Price: {f['price_fmt']} (prev close: {f['prev_close_fmt']}); market cap unavailable — P/E cannot be computed."
    else:
        market_note = f"Market cap: {f['market_cap_fmt']}, price: {f['price_fmt']}."

    revision_happened = bool(evaluation_output.get("revision_required") is False and bull_output.get("revision_note"))

    exec_summary = (
        f"{company} ({ticker}) was reviewed under the parallel blind protocol: BullAgent and BearAgent "
        f"independently analyzed the Evidence Pack before seeing each other's output. "
        f"Phase 1 (independent analysis) ran in {phase1_t}s; "
        f"Phase 2 (rebuttal exchange) ran in {phase2_t}s. "
        f"The Evidence Pack establishes {rev_note} and {ni_note}, "
        f"with assets of {f['assets_fmt']} and cash of {f['cash_fmt']}. "
        f"{market_note} "
        + ("A Bull revision was triggered and completed after the Evaluator review. " if revision_happened else "")
        + "No segment or trend data is available."
    )

    rating_line = "  Rating / Stance:      HOLD / WATCHLIST (Research Support Only — Not Investment Advice)"
    timing_line = f"  Parallel Execution:   Phase 1 (first passes): {phase1_t}s | Phase 2 (rebuttals): {phase2_t}s"
    conf_line = f"  Agent Confidence:     Bull {bull_fp.get('confidence', 0):.0%} | Bear {bear_fp.get('confidence', 0):.0%} | Risk {risk_output.get('confidence', 0):.0%}"
    faith_line = f"  Faithfulness Score:   {evaluation_output.get('faithfulness_score', 0):.2f} / 1.00"
    halluc_line = f"  Hallucination Risk:   {evaluation_output.get('hallucination_risk', 'N/A').upper()}"

    # ── 2. Company Profile ────────────────────────────────────────────────
    profile_lines = [
        f"  Company:       {company}",
        f"  Ticker:        {ticker}",
        f"  SEC CIK:       {f['cik'] or 'N/A'}",
        f"  Exchange(s):   {f['exchanges']}",
        f"  Industry:      {f['sic_description'] or 'N/A'}",
        f"  Sources:       E1 (SEC Submissions), E2 (SEC Submissions)",
    ]

    # ── 3. Financial Snapshot ─────────────────────────────────────────────
    col = 26
    fin_rows = []
    if f.get("revenue_val"):
        fin_rows.append(f"  {'Revenue':<{col}} {f['revenue_fmt']:<14} {f['revenue_period']} (end {f['revenue_end']})   E3")
    if f.get("net_income_val"):
        fin_rows.append(f"  {'Net Income':<{col}} {f['net_income_fmt']:<14} {f['net_income_period']} (end {f['net_income_end']})   E4")
    if f.get("net_margin_pct") is not None:
        fin_rows.append(f"  {'Net Profit Margin':<{col}} {f['margin_fmt']:<14} Derived from E3 + E4")
    if f.get("assets_val"):
        fin_rows.append(f"  {'Total Assets':<{col}} {f['assets_fmt']:<14} (end {f.get('assets_end', 'N/A')})   E5")
    if f.get("cash_val"):
        fin_rows.append(f"  {'Cash & Equivalents':<{col}} {f['cash_fmt']:<14} (end {f.get('assets_end', 'N/A')})   E5")
    if not f["market_available"]:
        fin_rows.append(f"  {'Market Data':<{col}} {'Unavailable':<14} E6 ({f['market_error']})")
    elif not f.get("market_cap_available"):
        fin_rows.append(f"  {'Current Price':<{col}} {f['price_fmt']:<14} E6 (market cap unavailable)")
        fin_rows.append(f"  {'52-Week High / Low':<{col}} {f['week52_high_fmt']} / {f['week52_low_fmt']:<10} E6")
    else:
        fin_rows.append(f"  {'Market Cap':<{col}} {f['market_cap_fmt']:<14} E6")
        fin_rows.append(f"  {'Current Price':<{col}} {f['price_fmt']:<14} E6")
        fin_rows.append(f"  {'52-Week High / Low':<{col}} {f['week52_high_fmt']} / {f['week52_low_fmt']:<10} E6")

    fin_header = f"  {'Metric':<{col}} {'Value':<14} Detail"
    fin_sep = "  " + "─" * 74

    # ── 4. Evidence Pack ──────────────────────────────────────────────────
    ev_rows = []
    for item in evidence_items(evidence_pack):
        cid = item.get("citation_id", "")
        src = item.get("source", "")[:22]
        claim = item.get("claim", "")
        short = (claim[:62] + "…") if len(claim) > 63 else claim
        prov = item.get("provider", "")
        ev_rows.append(f"  {cid:<5} {src:<24} {short:<64} {prov}")
    ev_header = f"  {'ID':<5} {'Source':<24} {'Key Fact':<64} {'Provider'}"
    ev_sep = "  " + "─" * 100

    # ── 5. Blind Review Debate ────────────────────────────────────────────
    # 5a: Phase 1 — Independent First Passes
    bull_fp_points = bullet_list(bull_fp.get("supporting_points", []), "claim")
    bear_fp_attacks = []
    for ap in bear_fp.get("attack_points", []):
        cid = ap.get("citation_id", "")
        bear_fp_attacks.append(
            f"  • [{cid}] Against: \"{ap.get('target_claim', '')}\"")
        bear_fp_attacks.append(f"         Critique: {ap.get('critique', '')}")
    bear_fp_attacks_text = "\n".join(bear_fp_attacks) or "  (none)"

    # 5b: Phase 2 — Rebuttal Exchange
    bull_rb_accepted = bullet_list(bull_rb.get("accepted_critiques", []), "critique")
    bull_rb_rejected = []
    for r in bull_rb.get("rejected_critiques", []):
        cid = r.get("citation_id", "")
        bull_rb_rejected.append(f"  • [{cid}] {r.get('critique', '')} — Reason: {r.get('reason', '')}")
    bull_rb_rejected_text = "\n".join(bull_rb_rejected) or "  (none)"
    bull_rb_assumptions = "\n".join(
        f"  {i+1}. {a}" for i, a in enumerate(bull_rb.get("revised_assumptions", []))
    )

    bear_rb_objections = bullet_list(bear_rb.get("remaining_objections", []), "objection")
    bear_rb_conceded = bullet_list(bear_rb.get("conceded_points", []), "point")

    # 5c: Debate outcome — identify convergence vs. persistent disagreement
    bull_concessions = [c.get("critique", "") for c in bull_rb.get("accepted_critiques", [])]
    bear_concessions = [c.get("point", "") for c in bear_rb.get("conceded_points", [])]
    bear_persistent = [o.get("objection", "") for o in bear_rb.get("remaining_objections", [])]

    convergence_lines = []
    for c in bear_concessions:
        convergence_lines.append(f"  • Bear conceded: {c}")
    for c in bull_concessions:
        convergence_lines.append(f"  • Bull accepted: {c}")
    convergence_text = "\n".join(convergence_lines) or "  • No explicit convergence recorded."

    disagreement_lines = [f"  • {o}" for o in bear_persistent]
    disagreement_text = "\n".join(disagreement_lines) or "  • No persistent objections recorded."

    # ── 6. Final Positions ────────────────────────────────────────────────
    final_bull_points = bullet_list(bull_output.get("supporting_points", []), "claim")
    final_bull_assumptions = "\n".join(
        f"  {i+1}. {a}" for i, a in enumerate(bull_output.get("key_assumptions", []))
    )
    # Concessions the Bull made during the Phase-2 rebuttal that now shape the final view.
    final_bull_concessions = bullet_list(bull_output.get("accepted_critiques", []), "critique")
    final_bear_attacks = []
    for ap in bear_output.get("attack_points", []):
        cid = ap.get("citation_id", "")
        final_bear_attacks.append(f"  • [{cid}] Against: \"{ap.get('target_claim', '')}\"")
        final_bear_attacks.append(f"         Critique: {ap.get('critique', '')}")
    final_bear_attacks_text = "\n".join(final_bear_attacks) or "  (none)"
    final_bear_missed = bullet_list(bear_output.get("missed_risks", []), "risk")
    # Points the Bear conceded during the Phase-2 rebuttal (shown for symmetry with the Bull).
    final_bear_conceded = bullet_list(bear_rb.get("conceded_points", []), "point")

    # ── 7. Key Debate ─────────────────────────────────────────────────────
    debate_text = (
        f"  The blind protocol prevents first-pass anchoring bias: BullAgent and BearAgent "
        f"formed their initial views independently before cross-disclosure.\n\n"
        f"  After disclosure, BullAgent accepted {len(bull_rb.get('accepted_critiques', []))} of "
        f"BearAgent's critiques and rejected {len(bull_rb.get('rejected_critiques', []))}. "
        f"BearAgent conceded {len(bear_rb.get('conceded_points', []))} point(s) while maintaining "
        f"{len(bear_rb.get('remaining_objections', []))} persistent objection(s).\n\n"
        f"  Balanced interpretation: The blind protocol surfaced genuine disagreement "
        f"on valuation (market data gap) and evidence scope (single-period snapshot). "
        f"Human judgment is required to weigh the conceded vs. contested points."
    )

    # ── 8. Risk Flags ─────────────────────────────────────────────────────
    risk_flag_lines = []
    for flag in risk_output.get("risk_flags", []):
        sev = flag.get("severity", "medium").upper()
        cid = flag.get("citation_id", "")
        risk_text = flag.get("risk", "")
        risk_flag_lines.append(f"  {f'[{sev}]':<9} [{cid}]  {risk_text}")
    risk_flags_text = "\n".join(risk_flag_lines) or "  (none)"

    # ── 9. Quality Audit ──────────────────────────────────────────────────
    eval_notes = "\n".join(f"  • {n}" for n in evaluation_output.get("evaluation_notes", []))
    revision_reasons = (
        "\n".join(f"  • {r}" for r in evaluation_output.get("revision_reasons", []))
        or "  • None."
    )
    coverage_gaps = (
        "\n".join(f"  • {g}" for g in evaluation_output.get("coverage_gaps", []))
        or "  • None."
    )
    audit_lines = [
        f"  Faithfulness Score:      {evaluation_output.get('faithfulness_score', 0):.2f} / 1.00",
        f"  Citation Coverage:       {evaluation_output.get('citation_coverage', 0):.0%}",
        f"  Hallucination Risk:      {evaluation_output.get('hallucination_risk', 'N/A').upper()}",
        f"  Confidence Calibration:  {evaluation_output.get('confidence_calibration', 'N/A').replace('_', ' ').title()}",
        f"  Risk Coverage Score:     {evaluation_output.get('risk_coverage_score', 0):.0%}",
        f"  Revision Required:       {'Yes' if evaluation_output.get('revision_required') else 'No'}",
        f"  Parallel Timing:         Phase 1: {phase1_t}s | Phase 2: {phase2_t}s",
    ]

    # ── 10. Human Review Checklist ────────────────────────────────────────
    checklist = [
        f"  □  Verify the {f.get('latest_periodic_form', '10-Q')} (period {f.get('latest_periodic_period', 'N/A')}, "
        f"filed {f.get('latest_periodic_filed', 'N/A')}) is the most current filing.",
    ]
    if f.get("revenue_val"):
        checklist.append(
            f"  □  Confirm revenue ({f['revenue_fmt']}) and net income ({f['net_income_fmt']}) against the actual filing."
        )
    if not f["market_available"] or not f.get("market_cap_available"):
        checklist.append(
            "  □  Obtain market cap data to enable P/E and EV valuation before drawing return conclusions."
        )
    if f.get("latest_8k_filed"):
        checklist.append(f"  □  Review 8-K filed {f['latest_8k_filed']} for material disclosures.")
    checklist.append(
        f"  □  Review BearAgent's {len(bear_persistent)} persistent objection(s) that survived the rebuttal exchange."
    )
    checklist.append(
        "  □  Confirm memo conclusions remain within research support scope — not investment advice."
    )
    checklist_text = "\n".join(checklist)

    # ── Assemble ──────────────────────────────────────────────────────────
    memo = "\n".join([
        header,

        section("1.  EXECUTIVE SUMMARY"),
        rating_line,
        timing_line,
        conf_line,
        faith_line,
        halluc_line,
        "",
        exec_summary,

        section("2.  COMPANY PROFILE"),
        "\n".join(profile_lines),

        section("3.  FINANCIAL SNAPSHOT"),
        fin_header,
        fin_sep,
        "\n".join(fin_rows),

        section(f"4.  EVIDENCE PACK  ({len(evidence_items(evidence_pack))} items)"),
        ev_header,
        ev_sep,
        "\n".join(ev_rows),

        section("5.  BLIND REVIEW DEBATE"),
        "  ┌─ PHASE 1: Independent Analysis (no cross-contamination) ─────────────────┐",
        "",
        "  BullAgent First Pass:",
        f"  Thesis:     {bull_fp.get('bull_thesis', '')}",
        f"  Confidence: {bull_fp.get('confidence', 0):.0%}",
        "  Supporting Points:",
        bull_fp_points,
        "",
        "  BearAgent First Pass:",
        f"  Thesis:     {bear_fp.get('bear_thesis', '')}",
        f"  Confidence: {bear_fp.get('confidence', 0):.0%}",
        "  Attack Points:",
        bear_fp_attacks_text,
        "",
        "  └───────────────────────────────────────────────────────────────────────────┘",
        "",
        "  ┌─ PHASE 2: Rebuttal Exchange (both see each other's first-pass output) ────┐",
        "",
        "  BullAgent Rebuttal:",
        f"  Summary:  {bull_rb.get('rebuttal_summary', '')}",
        "  Accepted from BearAgent:",
        bull_rb_accepted,
        "  Rejected from BearAgent:",
        bull_rb_rejected_text,
        "  Revised Assumptions:",
        bull_rb_assumptions or "  (none)",
        "",
        "  BearAgent Rebuttal:",
        f"  Summary:  {bear_rb.get('rebuttal_summary', '')}",
        "  Remaining Objections (not conceded):",
        bear_rb_objections,
        "  Conceded to BullAgent:",
        bear_rb_conceded,
        "",
        "  └───────────────────────────────────────────────────────────────────────────┘",
        "",
        "  ┌─ DEBATE OUTCOME ────────────────────────────────────────────────────────────┐",
        "",
        "  Points of Convergence:",
        convergence_text,
        "",
        "  Persistent Disagreements:",
        disagreement_text,
        "",
        "  └───────────────────────────────────────────────────────────────────────────┘",

        section("6.  FINAL BULL POSITION  (after rebuttal" + (" + revision" if bull_output.get("revision_note") else "") + ")"),
        f"  Thesis:     {bull_output.get('bull_thesis', '')}",
        f"  Confidence: {bull_output.get('confidence', 0):.0%}",
        "",
        "  Supporting Evidence:",
        final_bull_points,
        "",
        "  Key Assumptions (incl. assumptions revised during the rebuttal):",
        final_bull_assumptions,
        "",
        "  Conceded to BearAgent during rebuttal (now folded into the final view):",
        final_bull_concessions,
        *(["", f"  Rebuttal Note: {bull_output.get('rebuttal_note', '')}"] if bull_output.get("rebuttal_note") else []),
        *(["", f"  Revision Note: {bull_output.get('revision_note', '')}"] if bull_output.get("revision_note") else []),

        section("7.  FINAL BEAR POSITION  (blind first pass — BearAgent is not separately revised)"),
        f"  Thesis:     {bear_output.get('bear_thesis', '')}",
        f"  Confidence: {bear_output.get('confidence', 0):.0%}",
        "",
        "  Surviving Attack Points (objections held through the rebuttal):",
        final_bear_attacks_text,
        "",
        "  Conceded to BullAgent during rebuttal:",
        final_bear_conceded,
        "",
        "  Missed / Unaddressed Risks:",
        final_bear_missed,

        section("8.  KEY DEBATE"),
        debate_text,

        section("9.  RISK FLAGS"),
        f"  Risk Summary: {risk_output.get('risk_summary', '')}",
        "",
        risk_flags_text,

        section("10. QUALITY AUDIT"),
        "\n".join(audit_lines),
        "",
        "  Evaluation Notes:",
        eval_notes,
        "",
        "  Revision Reasons (drove a Bull revision):",
        revision_reasons,
        "",
        "  Coverage Gaps (advisory — did not require revision):",
        coverage_gaps,

        section("11. HUMAN REVIEW CHECKLIST"),
        checklist_text,

        f"\n{sep}",
        "  ⚠  DISCLAIMER: This is a research support memo, not investment advice.",
        sep,
    ])

    return memo


def _build_rich_memo(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
) -> str:
    f = _extract_financials(evidence_pack)
    ticker = f["ticker"]
    company = f["company"]
    case_id = evidence_pack.get("case_id", f"{ticker}-001")
    report_date = (evidence_pack.get("evidence_items") or [{}])[0].get("date", "N/A")

    sep = "═" * 80
    thin = "─" * 80

    # ── Section helpers ───────────────────────────────────────────────────
    def section(title: str) -> str:
        return f"\n{thin}\n{title}\n{thin}"

    def bullet_list(items: list, key: str, cid_key: str = "citation_id") -> str:
        if not items:
            return "  (none)"
        lines = []
        for item in items:
            cid = item.get(cid_key, "")
            suffix = f"  [{cid}]" if cid else ""
            lines.append(f"  • {item.get(key, '')}{suffix}")
        return "\n".join(lines)

    # ── 1. Header ─────────────────────────────────────────────────────────
    header = (
        f"\n{sep}\n"
        f"  RESEARCH SUPPORT MEMO\n"
        f"  {company} ({ticker})  |  Case: {case_id}  |  Report Date: {report_date}\n"
        f"{sep}\n"
        f"  ⚠  DISCLAIMER: This is a research support memo, not investment advice.\n"
        f"{sep}"
    )

    # ── 2. Executive Summary ──────────────────────────────────────────────
    rev_note = f"revenue of {f['revenue_fmt']} ({f['revenue_period']})" if f.get("revenue_val") else "revenue data from SEC filings"
    ni_note = f"net income of {f['net_income_fmt']} (margin: {f['margin_fmt']})" if f.get("net_income_val") else "net income from SEC filings"
    if not f["market_available"]:
        market_note = f"Market data is unavailable ({f['market_error']}), preventing valuation ratio analysis."
    elif not f.get("market_cap_available"):
        market_note = (
            f"Market price is {f['price_fmt']} (prev close: {f['prev_close_fmt']}), "
            f"but market cap is unavailable — P/E and EV ratios cannot be computed."
        )
    else:
        market_note = f"Market cap: {f['market_cap_fmt']}, current price: {f['price_fmt']} (prev close: {f['prev_close_fmt']})."
    revision_note = (
        "A revision cycle was triggered and completed by BullAgent."
        if evaluation_output.get("revision_required") is False and evaluation_output.get("faithfulness_score", 0) >= 0.9
        else "No revision was required — initial agent outputs passed evaluation."
    )

    exec_summary = (
        f"{company} ({ticker}) presents a well-documented financial profile grounded in SEC EDGAR filings. "
        f"The Evidence Pack establishes {rev_note} and {ni_note}, "
        f"alongside total assets of {f['assets_fmt']} and cash of {f['cash_fmt']} "
        f"(period ending {f.get('assets_end', 'N/A')}). "
        f"{market_note} "
        f"No segment-level data or forward guidance is included in the current Evidence Pack. "
        f"{revision_note}"
    )

    rating_line = "  Rating / Stance:   HOLD / WATCHLIST (Research Support Only — Not Investment Advice)"
    confidence_line = f"  Agent Confidence:   Bull {bull_output.get('confidence', 0):.0%} | Bear {bear_output.get('confidence', 0):.0%} | Risk {risk_output.get('confidence', 0):.0%}"
    faithfulness = f"  Faithfulness Score: {evaluation_output.get('faithfulness_score', 0):.2f} / 1.00"
    halluc = f"  Hallucination Risk: {evaluation_output.get('hallucination_risk', 'N/A').upper()}"

    # ── 3. Company Profile ────────────────────────────────────────────────
    profile_lines = [
        f"  Company:       {company}",
        f"  Ticker:        {ticker}",
        f"  SEC CIK:       {f['cik'] or 'N/A'}",
        f"  Exchange(s):   {f['exchanges']}",
        f"  Industry:      {f['sic_description'] or 'N/A'}",
        f"  Sources:       E1 (SEC Submissions), E2 (SEC Submissions)",
    ]

    # ── 4. Financial Snapshot ─────────────────────────────────────────────
    col = 26
    fin_rows = []
    if f.get("revenue_val"):
        fin_rows.append(
            f"  {'Revenue':<{col}} {f['revenue_fmt']:<14} "
            f"{f['revenue_period']} (end {f['revenue_end']})   E3 | {f['revenue_form']} filed {f['revenue_filed']}"
        )
    if f.get("net_income_val"):
        fin_rows.append(
            f"  {'Net Income':<{col}} {f['net_income_fmt']:<14} "
            f"{f['net_income_period']} (end {f['net_income_end']})   E4"
        )
    if f.get("net_margin_pct") is not None:
        fin_rows.append(f"  {'Net Profit Margin':<{col}} {f['margin_fmt']:<14} Derived from E3 + E4")
    if f.get("assets_val"):
        fin_rows.append(
            f"  {'Total Assets':<{col}} {f['assets_fmt']:<14} "
            f"(end {f.get('assets_end', 'N/A')})   E5"
        )
    if f.get("cash_val"):
        fin_rows.append(f"  {'Cash & Equivalents':<{col}} {f['cash_fmt']:<14} (end {f.get('assets_end', 'N/A')})   E5")
    if not f["market_available"]:
        fin_rows.append(f"  {'Market Data':<{col}} {'Unavailable':<14} E6 ({f['market_error']})")
    elif not f.get("market_cap_available"):
        fin_rows.append(f"  {'Current Price':<{col}} {f['price_fmt']:<14} E6 (market cap unavailable)")
        fin_rows.append(f"  {'Prev Close':<{col}} {f['prev_close_fmt']:<14} E6")
        fin_rows.append(f"  {'52-Week High / Low':<{col}} {f['week52_high_fmt']} / {f['week52_low_fmt']:<10} E6")
    else:
        fin_rows.append(f"  {'Market Cap':<{col}} {f['market_cap_fmt']:<14} E6")
        fin_rows.append(f"  {'Current Price':<{col}} {f['price_fmt']:<14} E6")
        fin_rows.append(f"  {'52-Week High / Low':<{col}} {f['week52_high_fmt']} / {f['week52_low_fmt']:<10} E6")
    fin_header = f"  {'Metric':<{col}} {'Value':<14} Detail"
    fin_sep = "  " + "─" * 74

    # ── 5. Evidence Pack Table ────────────────────────────────────────────
    ev_rows = []
    for item in evidence_items(evidence_pack):
        cid = item.get("citation_id", "")
        source = item.get("source", "")[:22]
        claim = item.get("claim", "")
        short_claim = (claim[:62] + "…") if len(claim) > 63 else claim
        provider = item.get("provider", "")
        ev_rows.append(f"  {cid:<5} {source:<24} {short_claim:<64} {provider}")
    ev_header = f"  {'ID':<5} {'Source':<24} {'Key Fact':<64} {'Provider'}"
    ev_sep = "  " + "─" * 100

    # ── 6. Bull Case ──────────────────────────────────────────────────────
    bull_points_text = bullet_list(bull_output.get("supporting_points", []), "claim")
    bull_assumptions = "\n".join(
        f"  {i+1}. {a}"
        for i, a in enumerate(bull_output.get("key_assumptions", []))
    )

    # ── 7. Bear Case ──────────────────────────────────────────────────────
    bear_attacks = []
    for ap in bear_output.get("attack_points", []):
        cid = ap.get("citation_id", "")
        bear_attacks.append(
            f"  • Target: \"{ap.get('target_claim', '')}\"  [{cid}]\n"
            f"    Critique: {ap.get('critique', '')}"
        )
    bear_attacks_text = "\n".join(bear_attacks) or "  (none)"
    bear_missed = bullet_list(bear_output.get("missed_risks", []), "risk")

    # ── 8. Key Debate ─────────────────────────────────────────────────────
    debate_text = (
        f"  BullAgent argues that SEC-grounded financial data ({f['revenue_fmt']} revenue, "
        f"{f['net_income_fmt']} net income, {f['margin_fmt']} margin) provides a sufficient "
        f"baseline research frame.\n\n"
        f"  BearAgent's strongest rebuttal: without market pricing data, this financial "
        f"scale cannot be assessed against current expectations or peer multiples. A single "
        f"period snapshot also prevents trend or momentum conclusions.\n\n"
        f"  Balanced interpretation: The Evidence Pack supports a baseline factual research "
        f"view, but not a high-confidence forward-looking conclusion. Human judgment is "
        f"required to bridge the gap between auditable SEC facts and an investment thesis."
    )

    # ── 9. Risk Flags ─────────────────────────────────────────────────────
    risk_flag_lines = []
    for flag in risk_output.get("risk_flags", []):
        sev = flag.get("severity", "medium").upper()
        cid = flag.get("citation_id", "")
        risk_text = flag.get("risk", "")
        sev_badge = f"[{sev}]"
        risk_flag_lines.append(f"  {sev_badge:<9} [{cid}]  {risk_text}")
    risk_flags_text = "\n".join(risk_flag_lines) or "  (none)"

    # ── 10. Quality Audit ─────────────────────────────────────────────────
    eval_notes_text = "\n".join(
        f"  • {note}" for note in evaluation_output.get("evaluation_notes", [])
    )
    revision_reasons_text = (
        "\n".join(f"  • {r}" for r in evaluation_output.get("revision_reasons", []))
        or "  • None — all claims passed evaluation."
    )
    coverage_gaps_text = (
        "\n".join(f"  • {g}" for g in evaluation_output.get("coverage_gaps", []))
        or "  • None."
    )
    audit_lines = [
        f"  Faithfulness Score:      {evaluation_output.get('faithfulness_score', 0):.2f} / 1.00",
        f"  Citation Coverage:       {evaluation_output.get('citation_coverage', 0):.0%}",
        f"  Hallucination Risk:      {evaluation_output.get('hallucination_risk', 'N/A').upper()}",
        f"  Confidence Calibration:  {evaluation_output.get('confidence_calibration', 'N/A').replace('_', ' ').title()}",
        f"  Risk Coverage Score:     {evaluation_output.get('risk_coverage_score', 0):.0%}",
        f"  Revision Required:       {'Yes' if evaluation_output.get('revision_required') else 'No'}",
    ]

    # ── 11. Human Review Checklist ────────────────────────────────────────
    checklist = [
        f"  □  Verify the {f.get('latest_periodic_form', '10-Q')} (period {f.get('latest_periodic_period', 'N/A')}, "
        f"filed {f.get('latest_periodic_filed', 'N/A')}) is the most current available filing.",
    ]
    if f.get("revenue_val"):
        checklist.append(
            f"  □  Confirm revenue ({f['revenue_fmt']}) and net income ({f['net_income_fmt']}) "
            f"figures against the actual {f.get('revenue_form', '')} filing."
        )
    if not f["market_available"]:
        checklist.append(
            "  □  Obtain market price data to enable valuation (install yfinance or provide "
            "manual input) before drawing any return-based conclusions."
        )
    if f.get("latest_8k_filed"):
        checklist.append(
            f"  □  Review the 8-K filed {f['latest_8k_filed']} for material disclosures "
            "that may affect the research frame."
        )
    if f.get("assets_end") and f.get("revenue_end") and f["assets_end"] != f["revenue_end"]:
        checklist.append(
            f"  □  Note mixed period-end dates: income statement ends {f['revenue_end']}, "
            f"balance sheet ends {f['assets_end']}. Adjust if computing cross-statement ratios."
        )
    checklist.append(
        "  □  Confirm that all conclusions remain within research support scope. "
        "Do not convert this memo into a buy/sell recommendation."
    )
    checklist_text = "\n".join(checklist)

    # ── Assemble ──────────────────────────────────────────────────────────
    memo = "\n".join([
        header,

        section("1.  EXECUTIVE SUMMARY"),
        rating_line,
        confidence_line,
        faithfulness,
        halluc,
        "",
        exec_summary,

        section("2.  COMPANY PROFILE"),
        "\n".join(profile_lines),

        section("3.  FINANCIAL SNAPSHOT"),
        fin_header,
        fin_sep,
        "\n".join(fin_rows),

        section("4.  EVIDENCE PACK  (" + str(len(evidence_items(evidence_pack))) + " items)"),
        ev_header,
        ev_sep,
        "\n".join(ev_rows),

        section("5.  BULL CASE"),
        f"  Thesis:     {bull_output.get('bull_thesis', '')}",
        f"  Confidence: {bull_output.get('confidence', 0):.0%}",
        "",
        "  Supporting Evidence:",
        bull_points_text,
        "",
        "  Key Assumptions:",
        bull_assumptions,

        section("6.  BEAR CASE"),
        f"  Thesis:     {bear_output.get('bear_thesis', '')}",
        f"  Confidence: {bear_output.get('confidence', 0):.0%}",
        "",
        "  Attack Points:",
        bear_attacks_text,
        "",
        "  Missed / Unaddressed Risks:",
        bear_missed,

        section("7.  KEY DEBATE"),
        debate_text,

        section("8.  RISK FLAGS"),
        f"  Risk Summary: {risk_output.get('risk_summary', '')}",
        "",
        risk_flags_text,

        section("9.  QUALITY AUDIT"),
        "\n".join(audit_lines),
        "",
        "  Evaluation Notes:",
        eval_notes_text,
        "",
        "  Revision Reasons (drove a Bull revision):",
        revision_reasons_text,
        "",
        "  Coverage Gaps (advisory — did not require revision):",
        coverage_gaps_text,

        section("10. HUMAN REVIEW CHECKLIST"),
        checklist_text,

        f"\n{sep}",
        "  ⚠  DISCLAIMER: This is a research support memo, not investment advice.",
        sep,
    ])

    return memo


def run_memo_agent(
    evidence_pack: Dict[str, Any],
    bull_output: Dict[str, Any],
    bear_output: Dict[str, Any],
    risk_output: Dict[str, Any],
    evaluation_output: Dict[str, Any],
    blind_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    company = evidence_pack.get("company", evidence_pack["ticker"])
    ticker = evidence_pack["ticker"]

    if blind_context:
        # Parallel blind review always gets the full debate memo, regardless of stub/hybrid.
        # Financial sections will be sparse for stub packs but debate section will be complete.
        summary = _build_rich_blind_memo(
            evidence_pack, bull_output, bear_output, risk_output, evaluation_output,
            blind_context,
        )
    elif is_stub_evidence_pack(evidence_pack):
        evidence_lines = "\n".join(
            f"- {item.get('citation_id')}: {item.get('claim')}"
            for item in evidence_items(evidence_pack)[:8]
        )
        bull_points = "\n".join(
            f"- {item.get('claim')} ({item.get('citation_id')})"
            for item in bull_output.get("supporting_points", [])[:4]
        ) or f"- {bull_output.get('bull_thesis')}"
        bear_points = "\n".join(
            f"- {item.get('critique')} ({item.get('citation_id')})"
            for item in bear_output.get("attack_points", [])[:3]
        ) or f"- {bear_output.get('bear_thesis')}"
        risk_flags = risk_output.get("risk_flags", [])
        risk_lines = "\n".join(
            f"- [{item.get('severity', 'unknown')}] {item.get('risk')} ({item.get('citation_id')})"
            for item in risk_flags[:4]
        ) or f"- {risk_output.get('risk_summary')}"
        evaluation_line = (
            f"hallucination risk={evaluation_output.get('hallucination_risk')}; "
            f"citation coverage={evaluation_output.get('citation_coverage')}; "
            f"risk coverage={evaluation_output.get('risk_coverage_score')}; "
            f"revision required={evaluation_output.get('revision_required')}."
        )
        summary = f"""Research Memo: {ticker} — {evidence_pack.get("case_id")}

Rating / Conclusion
Hold / watchlist. The bull case is supported by services growth, services margin, and shareholder returns, but the bear and risk outputs show regional pressure and device-demand uncertainty. This is research support only, not investment advice.

Bull Case
{bull_points}

Bear Case
{bear_points}

Key Debate
The core dispute is not whether the company has quality assets; it is whether the evidence supports the claim that AI adoption will materially lift iPhone demand. Evaluator required that claim to be revised. The revised position is more defensible: AI may improve engagement, but demand impact still requires validation.

Risk Pressure Test
{risk_lines}

Evidence And Audit
{evaluation_line}

Human Review Focus
Review E3/E5/E6 for the boundary between demand evidence, regional pressure, and AI conversion assumptions. Confirm the memo remains research support rather than investment advice."""
    else:
        summary = _build_rich_memo(
            evidence_pack, bull_output, bear_output, risk_output, evaluation_output
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

Write a structured English research memo for a human reviewer.
Use only the provided evidence and agent outputs.
Keep the language cautious and make clear this is research support, not investment advice.
Return only the memo text, not JSON.
Use these exact section headings in English:
Research Memo
Rating / Conclusion
Bull Case
Bear Case
Key Debate
Risk Pressure Test
Evidence Table
Audit And Dissent
Human Review Focus
Keep it specific, evidence-linked, and under 900 words.
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
            "coverage_gaps": evaluation_output.get("coverage_gaps", []),
            "evaluation_notes": evaluation_output["evaluation_notes"],
        },
        "human_review_required": True,
        "disclaimer": "This is a research support memo, not investment advice.",
    }
