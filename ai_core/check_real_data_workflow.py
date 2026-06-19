import os
from typing import Any, List

from ai_core.agents import valid_citations
from ai_core.runner import run_full_research_case


def collect_citation_ids(obj: Any) -> List[str]:
    citation_ids = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "citation_id" and isinstance(value, str):
                citation_ids.append(value)
            else:
                citation_ids.extend(collect_citation_ids(value))

    elif isinstance(obj, list):
        for item in obj:
            citation_ids.extend(collect_citation_ids(item))

    return citation_ids


def main():
    original_provider = os.environ.get("EVIDENCE_PROVIDER")
    original_use_llm = os.environ.get("USE_LLM_AGENTS")

    try:
        os.environ["EVIDENCE_PROVIDER"] = "hybrid"
        os.environ["USE_LLM_AGENTS"] = "false"

        result = run_full_research_case()
        case_state = result["case_state"]
        evidence_pack = case_state["evidence_pack"]

        evidence_ids = [item["citation_id"] for item in evidence_pack["evidence_items"]]
        providers = {item.get("provider") for item in evidence_pack["evidence_items"]}
        valid_ids = valid_citations(evidence_pack)
        used_citation_ids = collect_citation_ids(result["messages"])
        invalid_citation_ids = sorted({cid for cid in used_citation_ids if cid not in valid_ids})

        assert evidence_pack["ticker"] == "AAPL"
        assert evidence_ids[:8] == [f"E{index}" for index in range(1, 9)]
        assert "stub" not in providers
        assert {"sec", "hybrid"}.issubset(providers)
        assert evidence_pack.get("provider_payloads")
        assert case_state["final_memo"]
        assert case_state["final_evaluation_output"]["revision_required"] is False
        assert case_state["final_evaluation_output"]["hallucination_risk"] == "low"
        assert invalid_citation_ids == []

        print("\n=== REAL DATA WORKFLOW CHECKS PASSED ===")
        print("Evidence provider: hybrid")
        print(f"Evidence refs: {', '.join(evidence_ids)}")
        print(f"Evidence providers: {', '.join(sorted(provider for provider in providers if provider))}")
        print("Workflow completed: True")
        print("Final revision required: False")
        print("All citation IDs are valid: True")
    finally:
        if original_provider is None:
            os.environ.pop("EVIDENCE_PROVIDER", None)
        else:
            os.environ["EVIDENCE_PROVIDER"] = original_provider

        if original_use_llm is None:
            os.environ.pop("USE_LLM_AGENTS", None)
        else:
            os.environ["USE_LLM_AGENTS"] = original_use_llm


if __name__ == "__main__":
    main()
