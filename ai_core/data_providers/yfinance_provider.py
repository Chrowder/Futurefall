import os
import json
from typing import Any, Dict
from urllib import error, request

from ai_core.env_config import load_local_env

DEFAULT_YFINANCE_TIMEOUT_SECONDS = 4
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"


def _load_yfinance():
    try:
        import yfinance as yf
    except ImportError:
        return None

    return yf


def _missing_dependency_payload(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "yfinance",
        "ticker": ticker,
        "error": "yfinance is not installed. Install it to enable this optional provider.",
    }


def _timeout() -> float:
    load_local_env()
    return float(os.getenv("YFINANCE_TIMEOUT_SECONDS", str(DEFAULT_YFINANCE_TIMEOUT_SECONDS)))


def _provider_error_payload(ticker: str, exc: Exception) -> Dict[str, Any]:
    return {
        "provider": "yfinance",
        "ticker": ticker,
        "error": f"yfinance request failed: {exc}",
        "source_url": f"https://finance.yahoo.com/quote/{ticker}",
    }


def _safe_info(ticker: str) -> Dict[str, Any]:
    yf = _load_yfinance()
    if not yf:
        return _missing_dependency_payload(ticker)

    try:
        return yf.Ticker(ticker).info or {}
    except Exception as exc:
        return _provider_error_payload(ticker, exc)


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    info = _safe_info(ticker)
    if info.get("error"):
        return info

    return {
        "provider": "yfinance",
        "ticker": ticker,
        "company": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
    }


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    url = f"{YAHOO_CHART_URL}/{ticker}?range=5d&interval=1d"
    http_request = request.Request(
        url=url,
        headers={
            "User-Agent": "Futurefall BandAlpha demo",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with request.urlopen(http_request, timeout=_timeout()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        return _provider_error_payload(ticker, exc)
    except error.URLError as exc:
        return _provider_error_payload(ticker, exc)
    except (OSError, json.JSONDecodeError) as exc:
        return _provider_error_payload(ticker, exc)

    try:
        result = payload["chart"]["result"][0]
        meta = result.get("meta", {})
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        closes = [value for value in quote.get("close", []) if value is not None]
    except (KeyError, IndexError, TypeError) as exc:
        return {
            "provider": "yfinance",
            "ticker": ticker,
            "error": f"Yahoo Finance chart response was missing expected fields: {exc}",
            "source_url": f"https://finance.yahoo.com/quote/{ticker}",
        }

    if not closes:
        return {
            "provider": "yfinance",
            "ticker": ticker,
            "error": "Yahoo Finance chart returned no recent closing prices.",
            "source_url": f"https://finance.yahoo.com/quote/{ticker}",
        }

    current_price = meta.get("regularMarketPrice") or closes[-1]
    previous_close = meta.get("previousClose") or (closes[-2] if len(closes) >= 2 else closes[-1])

    return {
        "provider": "yfinance",
        "ticker": ticker,
        "market_cap": meta.get("marketCap"),
        "previous_close": float(previous_close),
        "current_price": float(current_price),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
        "source_url": f"https://finance.yahoo.com/quote/{ticker}",
    }


def fetch_financial_snapshot(ticker: str) -> Dict[str, Any]:
    info = _safe_info(ticker)
    if info.get("error"):
        return info

    return {
        "provider": "yfinance",
        "ticker": ticker,
        "total_revenue": info.get("totalRevenue"),
        "gross_margins": info.get("grossMargins"),
        "profit_margins": info.get("profitMargins"),
        "free_cashflow": info.get("freeCashflow"),
        "source_url": f"https://finance.yahoo.com/quote/{ticker}/financials",
    }


def fetch_recent_filings(ticker: str) -> Dict[str, Any]:
    return {
        "provider": "yfinance",
        "ticker": ticker,
        "note": "yfinance does not provide SEC filing documents in this lightweight provider.",
    }
