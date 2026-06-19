from typing import Any, Dict


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


def fetch_company_profile(ticker: str) -> Dict[str, Any]:
    yf = _load_yfinance()
    if not yf:
        return _missing_dependency_payload(ticker)

    info = yf.Ticker(ticker).info or {}
    return {
        "provider": "yfinance",
        "ticker": ticker,
        "company": info.get("longName") or info.get("shortName") or ticker,
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "website": info.get("website"),
    }


def fetch_market_snapshot(ticker: str) -> Dict[str, Any]:
    yf = _load_yfinance()
    if not yf:
        return _missing_dependency_payload(ticker)

    info = yf.Ticker(ticker).info or {}
    return {
        "provider": "yfinance",
        "ticker": ticker,
        "market_cap": info.get("marketCap"),
        "previous_close": info.get("previousClose"),
        "current_price": info.get("currentPrice"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "source_url": f"https://finance.yahoo.com/quote/{ticker}",
    }


def fetch_financial_snapshot(ticker: str) -> Dict[str, Any]:
    yf = _load_yfinance()
    if not yf:
        return _missing_dependency_payload(ticker)

    info = yf.Ticker(ticker).info or {}
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

