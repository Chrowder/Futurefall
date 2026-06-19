from typing import Any, Dict


class EvidenceProvider:
    def fetch_company_profile(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_market_snapshot(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_financial_snapshot(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

    def fetch_recent_filings(self, ticker: str) -> Dict[str, Any]:
        raise NotImplementedError

