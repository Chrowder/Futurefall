from ai_core.data_providers.evidence_builder import build_evidence_pack


REQUIRED_ITEM_FIELDS = {
    "citation_id",
    "claim",
    "source",
    "date",
    "provider",
    "fetched_at",
}


def main():
    evidence_pack = build_evidence_pack(ticker="AAPL", provider="hybrid")
    evidence_items = evidence_pack["evidence_items"]
    citation_ids = {item["citation_id"] for item in evidence_items}

    assert evidence_pack["case_id"] == "AAPL-001"
    assert evidence_pack["ticker"] == "AAPL"
    assert evidence_pack["company"]
    assert citation_ids == {"E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"}
    assert "provider_payloads" in evidence_pack

    for item in evidence_items:
        assert REQUIRED_ITEM_FIELDS.issubset(item.keys())
        assert item["claim"]
        assert item["provider"] in {"sec", "yfinance", "hybrid"}

    providers = {item["provider"] for item in evidence_items}
    assert "sec" in providers
    assert "hybrid" in providers

    print("\n=== HYBRID EVIDENCE CHECKS PASSED ===")
    print("Hybrid evidence pack built: True")
    print("E1-E8 present: True")
    print("Required evidence metadata present: True")
    print("Provider payloads included: True")


if __name__ == "__main__":
    main()
