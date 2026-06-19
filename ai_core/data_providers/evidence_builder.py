import copy
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_core.env_config import load_local_env
from ai_core.data_providers import sec_provider, stub_provider, yfinance_provider

PROVIDERS = {
    "stub": stub_provider,
    "yfinance": yfinance_provider,
    "sec": sec_provider,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_case_id(ticker: str) -> str:
    return f"{ticker.upper()}-001"


def enrich_evidence_item(
    item: Dict[str, Any],
    provider: str,
    fetched_at: str,
) -> Dict[str, Any]:
    enriched = copy.deepcopy(item)
    enriched.setdefault("provider", provider)
    enriched.setdefault("source_url", None)
    enriched["fetched_at"] = fetched_at
    return enriched


def build_stub_evidence_pack(ticker: str, fetched_at: str) -> Dict[str, Any]:
    evidence_pack = stub_provider.fetch_evidence_pack(ticker)
    evidence_pack["case_id"] = normalize_case_id(ticker)
    evidence_pack["evidence_items"] = [
        enrich_evidence_item(item, "stub", fetched_at)
        for item in evidence_pack["evidence_items"]
    ]
    return evidence_pack


def evidence_item(
    citation_id: str,
    claim: str,
    source: str,
    provider: str,
    fetched_at: str,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "citation_id": citation_id,
        "claim": claim,
        "source": source,
        "date": fetched_at[:10],
        "provider": provider,
        "source_url": source_url,
        "fetched_at": fetched_at,
    }


def format_money(value: Any) -> str:
    if value is None:
        return "not available"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return str(value)

    if abs(numeric_value) >= 1_000_000_000:
        return f"${numeric_value / 1_000_000_000:.1f}B"
    if abs(numeric_value) >= 1_000_000:
        return f"${numeric_value / 1_000_000:.1f}M"
    return f"${numeric_value:,.0f}"


def fact_claim(label: str, fact: Optional[Dict[str, Any]]) -> str:
    if not fact:
        return f"{label} was unavailable in the latest SEC companyfacts payload."

    fiscal_period = "/".join(
        str(part)
        for part in [fact.get("fy"), fact.get("fp")]
        if part is not None
    )
    fiscal_text = f"SEC FY/FP {fiscal_period}" if fiscal_period else "SEC fiscal period unavailable"
    end_text = f", period end {fact.get('end')}" if fact.get("end") else ""
    filed_text = f", filed {fact.get('filed')}" if fact.get("filed") else ""
    return (
        f"Latest reported {label.lower()} value was {format_money(fact.get('value'))} "
        f"based on SEC concept {fact.get('concept')} "
        f"({fiscal_text}{end_text}{filed_text})."
    )


def build_hybrid_evidence_pack(ticker: str, fetched_at: str) -> Dict[str, Any]:
    ticker_upper = ticker.upper()
    company_profile = sec_provider.fetch_company_profile(ticker_upper)
    financial_snapshot = sec_provider.fetch_financial_snapshot(ticker_upper)
    filings = sec_provider.fetch_recent_filings(ticker_upper)
    market_snapshot = yfinance_provider.fetch_market_snapshot(ticker_upper)

    company = (
        company_profile.get("company")
        or financial_snapshot.get("company")
        or ticker_upper
    )
    evidence_items: List[Dict[str, Any]] = []

    if company_profile.get("error"):
        profile_claim = f"SEC company profile unavailable for {ticker_upper}: {company_profile['error']}"
    else:
        exchanges = ", ".join(company_profile.get("exchanges", [])) or "unknown exchange"
        profile_claim = (
            f"{company} maps to SEC CIK {company_profile.get('cik_padded')} "
            f"and trades on {exchanges}."
        )
    evidence_items.append(
        evidence_item(
            "E1",
            profile_claim,
            "SEC submissions",
            "sec",
            fetched_at,
            company_profile.get("source_url"),
        )
    )

    latest_periodic = filings.get("latest_periodic") or {}
    if filings.get("error"):
        filing_claim = f"SEC recent filings unavailable for {ticker_upper}: {filings['error']}"
    elif latest_periodic:
        filing_claim = (
            f"Latest periodic SEC filing is {latest_periodic.get('form')} "
            f"filed on {latest_periodic.get('filing_date')} "
            f"for report date {latest_periodic.get('report_date')}."
        )
    else:
        filing_claim = f"No recent 10-K or 10-Q filing metadata was found for {ticker_upper}."
    evidence_items.append(
        evidence_item(
            "E2",
            filing_claim,
            "SEC submissions",
            "sec",
            fetched_at,
            latest_periodic.get("source_url") or filings.get("source_url"),
        )
    )

    evidence_items.append(
        evidence_item(
            "E3",
            fact_claim("Revenue", financial_snapshot.get("revenue")),
            "SEC companyfacts",
            "sec",
            fetched_at,
            financial_snapshot.get("source_url"),
        )
    )
    evidence_items.append(
        evidence_item(
            "E4",
            fact_claim("Net income", financial_snapshot.get("net_income")),
            "SEC companyfacts",
            "sec",
            fetched_at,
            financial_snapshot.get("source_url"),
        )
    )

    balance_claim_parts = [
        fact_claim("Assets", financial_snapshot.get("assets")),
        fact_claim("Cash", financial_snapshot.get("cash")),
    ]
    evidence_items.append(
        evidence_item(
            "E5",
            " ".join(balance_claim_parts),
            "SEC companyfacts",
            "sec",
            fetched_at,
            financial_snapshot.get("source_url"),
        )
    )

    if market_snapshot.get("error"):
        market_claim = f"Market snapshot unavailable for {ticker_upper}: {market_snapshot['error']}"
    else:
        market_claim = (
            f"Market snapshot shows previous close {format_money(market_snapshot.get('previous_close'))}, "
            f"current price {format_money(market_snapshot.get('current_price'))}, "
            f"and market cap {format_money(market_snapshot.get('market_cap'))}."
        )
    evidence_items.append(
        evidence_item(
            "E6",
            market_claim,
            "Yahoo Finance via yfinance",
            "yfinance",
            fetched_at,
            market_snapshot.get("source_url"),
        )
    )

    latest_current = filings.get("latest_current") or {}
    if latest_current:
        current_claim = (
            f"Latest SEC 8-K was filed on {latest_current.get('filing_date')} "
            f"with accession {latest_current.get('accession_number')}."
        )
    else:
        current_claim = f"No recent 8-K metadata was included in the fetched SEC submissions payload."
    evidence_items.append(
        evidence_item(
            "E7",
            current_claim,
            "SEC submissions",
            "sec",
            fetched_at,
            latest_current.get("source_url") or filings.get("source_url"),
        )
    )

    provider_notes = []
    if company_profile.get("error"):
        provider_notes.append("SEC profile error")
    if financial_snapshot.get("error"):
        provider_notes.append("SEC companyfacts error")
    if filings.get("error"):
        provider_notes.append("SEC filings error")
    if market_snapshot.get("error"):
        provider_notes.append("yfinance market snapshot unavailable")
    provider_status = ", ".join(provider_notes) if provider_notes else "SEC and optional market provider payloads fetched or loaded from local cache."
    evidence_items.append(
        evidence_item(
            "E8",
            f"Data freshness note: fetched_at={fetched_at}. {provider_status}",
            "Provider status",
            "hybrid",
            fetched_at,
            None,
        )
    )

    return {
        "case_id": normalize_case_id(ticker_upper),
        "ticker": ticker_upper,
        "company": company,
        "evidence_items": evidence_items,
        "provider_payloads": {
            "sec_company_profile": company_profile,
            "sec_financial_snapshot": financial_snapshot,
            "sec_recent_filings": filings,
            "market_snapshot": market_snapshot,
        },
    }


def build_provider_evidence_pack(ticker: str, provider: str, fetched_at: str) -> Dict[str, Any]:
    provider_module = PROVIDERS[provider]
    company_profile = provider_module.fetch_company_profile(ticker)
    market_snapshot = provider_module.fetch_market_snapshot(ticker)
    financial_snapshot = provider_module.fetch_financial_snapshot(ticker)
    filings = provider_module.fetch_recent_filings(ticker)

    company = company_profile.get("company") or ticker.upper()
    evidence_items: List[Dict[str, Any]] = []

    provider_payloads = [
        ("E1", "Company profile", company_profile),
        ("E2", "Market snapshot", market_snapshot),
        ("E3", "Financial snapshot", financial_snapshot),
        ("E4", "Recent filings", filings),
    ]

    for citation_id, label, payload in provider_payloads:
        if payload.get("error"):
            claim = f"{label} unavailable for {ticker.upper()}: {payload['error']}"
        else:
            claim = f"{label} fetched for {ticker.upper()} from {provider} provider."

        evidence_items.append(
            evidence_item(
                citation_id=citation_id,
                claim=claim,
                source=provider,
                provider=provider,
                fetched_at=fetched_at,
                source_url=payload.get("source_url"),
            )
        )

    return {
        "case_id": normalize_case_id(ticker),
        "ticker": ticker.upper(),
        "company": company,
        "evidence_items": evidence_items,
        "provider_payloads": {
            "company_profile": company_profile,
            "market_snapshot": market_snapshot,
            "financial_snapshot": financial_snapshot,
            "recent_filings": filings,
        },
    }


def build_evidence_pack(ticker: str = "AAPL", provider: str = "env") -> Dict[str, Any]:
    load_local_env()

    selected_provider = provider
    if selected_provider == "env":
        selected_provider = os.getenv("EVIDENCE_PROVIDER", "hybrid")

    selected_provider = (selected_provider or "stub").lower()
    fetched_at = utc_now()

    if selected_provider == "stub":
        return build_stub_evidence_pack(ticker, fetched_at)

    if selected_provider == "hybrid":
        return build_hybrid_evidence_pack(ticker, fetched_at)

    if selected_provider not in PROVIDERS:
        raise ValueError(f"Unsupported evidence provider: {selected_provider}")

    return build_provider_evidence_pack(ticker, selected_provider, fetched_at)
