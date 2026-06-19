from typing import Any, Dict


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "sec",
        "ticker": ticker,
        "note": "SEC company profile lookup is reserved for a future provider implementation.",
        "source_url": "https://www.sec.gov/edgar/search/",
    }


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "sec",
        "ticker": ticker,
        "note": "SEC filings do not provide live market snapshots.",
    }


def fetch_financial_snapshot(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "sec",
        "ticker": ticker,
        "note": "Future implementation can parse recent 10-K/10-Q XBRL facts.",
        "source_url": "https://www.sec.gov/edgar/search/",
    }


def fetch_recent_filings(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "sec",
        "ticker": ticker,
        "filings": [],
        "note": "Placeholder only. Do not scrape SEC aggressively from the demo.",
        "source_url": "https://www.sec.gov/edgar/search/",
    }

