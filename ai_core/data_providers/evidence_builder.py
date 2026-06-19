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


def build_evidence_pack(ticker: str = "AAPL", provider: str = "stub") -> Dict[str, Any]:
    load_local_env()

    selected_provider = provider
    if selected_provider == "env":
        selected_provider = os.getenv("EVIDENCE_PROVIDER", "stub")

    selected_provider = (selected_provider or "stub").lower()
    fetched_at = utc_now()

    if selected_provider == "stub":
        return build_stub_evidence_pack(ticker, fetched_at)

    if selected_provider not in PROVIDERS:
        raise ValueError(f"Unsupported evidence provider: {selected_provider}")

    return build_provider_evidence_pack(ticker, selected_provider, fetched_at)
