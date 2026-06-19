import copy
from typing import Any, Dict

from ai_core.sample_case import sample_evidence_pack


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    evidence_pack = copy.deepcopy(sample_evidence_pack)
    return {
        "provider": "stub",
        "ticker": ticker,
        "company": evidence_pack.get("company", "Apple Inc."),
        "source": "sample_case",
        "raw_evidence_pack": evidence_pack,
    }


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "stub",
        "ticker": ticker,
        "source": "sample_case",
        "note": "Market snapshot is represented by deterministic sample evidence.",
    }


def fetch_financial_snapshot(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "stub",
        "ticker": ticker,
        "source": "sample_case",
        "note": "Financial snapshot is represented by deterministic sample evidence.",
    }


def fetch_recent_filings(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "stub",
        "ticker": ticker,
        "source": "sample_case",
        "note": "Recent filings are represented by deterministic sample evidence.",
    }


def fetch_evidence_pack(ticker: str) -> Dict[str, Any]:
    evidence_pack = copy.deepcopy(sample_evidence_pack)
    evidence_pack["ticker"] = ticker
    return evidence_pack

