import os

from ai_core.agents import (
    run_bear_agent,
    run_bull_agent,
    run_bull_revision_agent,
    run_evaluator_agent,
    run_risk_agent,
)
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
    original_use_llm = os.environ.get("USE_LLM_AGENTS")
    os.environ["USE_LLM_AGENTS"] = "false"

    try:
        evidence_pack = build_evidence_pack(provider="stub")
        evidence_items = evidence_pack["evidence_items"]
        citation_ids = {item["citation_id"] for item in evidence_items}

        assert evidence_pack["case_id"] == "AAPL-001"
        assert evidence_pack["ticker"] == "AAPL"
        assert evidence_pack["company"] == "Apple Inc."
        assert citation_ids == {"E1", "E2", "E3", "E4", "E5", "E6"}

        for item in evidence_items:
            assert REQUIRED_ITEM_FIELDS.issubset(item.keys())
            assert item["provider"] == "stub"

        bull_output = run_bull_agent(evidence_pack)
        bear_output = run_bear_agent(evidence_pack, bull_output)
        risk_output = run_risk_agent(evidence_pack, bull_output, bear_output)
        evaluation_output = run_evaluator_agent(
            evidence_pack,
            bull_output,
            bear_output,
            risk_output,
        )

        assert evaluation_output["revision_required"] is True
        assert evaluation_output["target_agent"] == "BullAgent"

        bull_output_v2 = run_bull_revision_agent(
            evidence_pack,
            bull_output,
            evaluation_output,
        )
        final_evaluation_output = run_evaluator_agent(
            evidence_pack,
            bull_output_v2,
            bear_output,
            risk_output,
        )

        assert final_evaluation_output["revision_required"] is False
        assert final_evaluation_output["hallucination_risk"] == "low"
    finally:
        if original_use_llm is None:
            os.environ.pop("USE_LLM_AGENTS", None)
        else:
            os.environ["USE_LLM_AGENTS"] = original_use_llm

    print("\n=== EVIDENCE BUILDER CHECKS PASSED ===")
    print("Stub evidence pack built: True")
    print("E1-E6 present: True")
    print("Required evidence metadata present: True")
    print("Revision loop still works with stub provider: True")


if __name__ == "__main__":
    main()
