import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error, request

from ai_core.env_config import load_local_env

SEC_SUBMISSIONS_BASE_URL = "https://data.sec.gov/submissions"
SEC_COMPANYFACTS_BASE_URL = "https://data.sec.gov/api/xbrl/companyfacts"
SEC_TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"

DATA_CACHE_DIR = Path(__file__).resolve().parents[1] / "data_cache"
SEC_CACHE_DIR = DATA_CACHE_DIR / "sec"
DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_CACHE_TTL_HOURS = 12


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sec_user_agent() -> str:
    load_local_env()
    return os.getenv(
        "SEC_USER_AGENT",
        "Futurefall BandAlpha demo contact@example.com",
    )


def _cache_ttl() -> timedelta:
    load_local_env()
    hours = float(os.getenv("SEC_CACHE_TTL_HOURS", str(DEFAULT_CACHE_TTL_HOURS)))
    return timedelta(hours=hours)


def _timeout() -> float:
    load_local_env()
    return float(os.getenv("SEC_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))


def _cache_path(cache_key: str) -> Path:
    safe_key = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in cache_key)
    return SEC_CACHE_DIR / f"{safe_key}.json"


def _read_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    path = _cache_path(cache_key)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text())
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
    except Exception:
        return None

    if _utc_now() - fetched_at > _cache_ttl():
        return None

    return payload.get("data")


def _write_cache(cache_key: str, data: Dict[str, Any]) -> None:
    SEC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_key)
    path.write_text(
        json.dumps(
            {
                "fetched_at": _utc_now().isoformat(),
                "data": data,
            },
            indent=2,
        )
    )


def _fetch_json(url: str, cache_key: str) -> Dict[str, Any]:
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached

    http_request = request.Request(
        url=url,
        headers={
            "User-Agent": _sec_user_agent(),
            "Accept-Encoding": "identity",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(http_request, timeout=_timeout()) as response:
            raw = response.read().decode("utf-8")
    except error.HTTPError as exc:
        return {
            "error": f"SEC returned HTTP {exc.code}",
            "source_url": url,
            "provider": "sec",
        }
    except error.URLError as exc:
        return {
            "error": f"SEC request failed: {exc.reason}",
            "source_url": url,
            "provider": "sec",
        }
    except OSError as exc:
        return {
            "error": f"SEC request failed: {exc}",
            "source_url": url,
            "provider": "sec",
        }

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "error": f"SEC response was not valid JSON: {exc}",
            "source_url": url,
            "provider": "sec",
        }

    _write_cache(cache_key, data)
    return data


def _ticker_map() -> Dict[str, Any]:
    return _fetch_json(SEC_TICKER_MAP_URL, "company_tickers")


def lookup_cik(ticker: str) -> Dict[str, Any]:
    ticker_upper = ticker.upper()
    mapping = _ticker_map()
    if mapping.get("error"):
        return mapping

    for item in mapping.values():
        if str(item.get("ticker", "")).upper() == ticker_upper:
            cik = int(item["cik_str"])
            return {
                "provider": "sec",
                "ticker": ticker_upper,
                "cik": cik,
                "cik_padded": f"{cik:010d}",
                "company": item.get("title") or ticker_upper,
                "source_url": SEC_TICKER_MAP_URL,
            }

    return {
        "provider": "sec",
        "ticker": ticker_upper,
        "error": f"Ticker {ticker_upper} was not found in SEC company_tickers.json.",
        "source_url": SEC_TICKER_MAP_URL,
    }


def _fetch_submissions_for_cik(cik_padded: str) -> Dict[str, Any]:
    url = f"{SEC_SUBMISSIONS_BASE_URL}/CIK{cik_padded}.json"
    return _fetch_json(url, f"submissions_{cik_padded}")


def _fetch_companyfacts_for_cik(cik_padded: str) -> Dict[str, Any]:
    url = f"{SEC_COMPANYFACTS_BASE_URL}/CIK{cik_padded}.json"
    return _fetch_json(url, f"companyfacts_{cik_padded}")


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    cik_lookup = lookup_cik(ticker)
    if cik_lookup.get("error"):
        return cik_lookup

    submissions = _fetch_submissions_for_cik(cik_lookup["cik_padded"])
    if submissions.get("error"):
        return {
            **cik_lookup,
            "error": submissions["error"],
            "source_url": submissions.get("source_url"),
        }

    return {
        "provider": "sec",
        "ticker": ticker.upper(),
        "cik": cik_lookup["cik"],
        "cik_padded": cik_lookup["cik_padded"],
        "company": submissions.get("name") or cik_lookup["company"],
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "exchanges": submissions.get("exchanges", []),
        "tickers": submissions.get("tickers", []),
        "source_url": f"{SEC_SUBMISSIONS_BASE_URL}/CIK{cik_lookup['cik_padded']}.json",
    }


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "sec",
        "ticker": ticker.upper(),
        "note": "SEC EDGAR does not provide live market price data.",
    }


def _latest_recent_filing(submissions: Dict[str, Any], forms: set[str]) -> Optional[Dict[str, Any]]:
    recent = submissions.get("filings", {}).get("recent", {})
    form_values = recent.get("form", [])
    accession_values = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for index, form in enumerate(form_values):
        if form not in forms:
            continue

        accession = accession_values[index]
        accession_no_dashes = accession.replace("-", "")
        cik = str(submissions.get("cik")).zfill(10).lstrip("0")
        primary_doc = primary_docs[index] if index < len(primary_docs) else ""
        filing_url = (
            f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{accession_no_dashes}/{primary_doc}"
        )
        return {
            "form": form,
            "accession_number": accession,
            "filing_date": filing_dates[index] if index < len(filing_dates) else None,
            "report_date": report_dates[index] if index < len(report_dates) else None,
            "primary_document": primary_doc,
            "source_url": filing_url,
        }

    return None


def _latest_usd_fact(companyfacts: Dict[str, Any], concepts: list[str]) -> Optional[Dict[str, Any]]:
    us_gaap = companyfacts.get("facts", {}).get("us-gaap", {})

    for concept in concepts:
        concept_payload = us_gaap.get(concept)
        if not concept_payload:
            continue

        usd_facts = concept_payload.get("units", {}).get("USD", [])
        filed_facts = [
            item
            for item in usd_facts
            if item.get("filed") and item.get("val") is not None
        ]
        if not filed_facts:
            continue

        latest = sorted(filed_facts, key=lambda item: item["filed"], reverse=True)[0]
        return {
            "concept": concept,
            "label": concept_payload.get("label") or concept,
            "value": latest.get("val"),
            "form": latest.get("form"),
            "filed": latest.get("filed"),
            "fy": latest.get("fy"),
            "fp": latest.get("fp"),
            "end": latest.get("end"),
            "accession_number": latest.get("accn"),
        }

    return None


def fetch_financial_snapshot(ticker: str) -> Dict[str, Any]:
    cik_lookup = lookup_cik(ticker)
    if cik_lookup.get("error"):
        return cik_lookup

    companyfacts = _fetch_companyfacts_for_cik(cik_lookup["cik_padded"])
    if companyfacts.get("error"):
        return {
            **cik_lookup,
            "error": companyfacts["error"],
            "source_url": companyfacts.get("source_url"),
        }

    revenue = _latest_usd_fact(
        companyfacts,
        ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
    )
    net_income = _latest_usd_fact(companyfacts, ["NetIncomeLoss"])
    assets = _latest_usd_fact(companyfacts, ["Assets"])
    cash = _latest_usd_fact(
        companyfacts,
        ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    )

    return {
        "provider": "sec",
        "ticker": ticker.upper(),
        "cik": cik_lookup["cik"],
        "cik_padded": cik_lookup["cik_padded"],
        "company": cik_lookup["company"],
        "revenue": revenue,
        "net_income": net_income,
        "assets": assets,
        "cash": cash,
        "source_url": f"{SEC_COMPANYFACTS_BASE_URL}/CIK{cik_lookup['cik_padded']}.json",
    }


def fetch_recent_filings(ticker: str) -> Dict[str, Any]:
    cik_lookup = lookup_cik(ticker)
    if cik_lookup.get("error"):
        return cik_lookup

    submissions = _fetch_submissions_for_cik(cik_lookup["cik_padded"])
    if submissions.get("error"):
        return {
            **cik_lookup,
            "error": submissions["error"],
            "source_url": submissions.get("source_url"),
        }

    latest_periodic = _latest_recent_filing(submissions, {"10-K", "10-Q"})
    latest_current = _latest_recent_filing(submissions, {"8-K"})

    return {
        "provider": "sec",
        "ticker": ticker.upper(),
        "cik": cik_lookup["cik"],
        "company": submissions.get("name") or cik_lookup["company"],
        "latest_periodic": latest_periodic,
        "latest_current": latest_current,
        "source_url": f"{SEC_SUBMISSIONS_BASE_URL}/CIK{cik_lookup['cik_padded']}.json",
    }
