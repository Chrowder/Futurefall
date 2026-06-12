from typing import Any, List

from ai_core.run_demo import run_full_research_case, valid_citations


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
    result = run_full_research_case()
    case_state = result["case_state"]
    messages = result["messages"]
    final_memo = result["final_memo"]

    valid_ids = valid_citations(case_state["evidence_pack"])

    used_citation_ids = collect_citation_ids(messages)
    invalid_citation_ids = sorted(
        {cid for cid in used_citation_ids if cid not in valid_ids}
    )

    revision_messages = [
        msg
        for msg in messages
        if msg.get("message_type") == "revision_request"
    ]

    final_memo_messages = [
        msg
        for msg in messages
        if msg.get("message_type") == "final_memo"
    ]

    assert case_state["evaluation_output"]["revision_required"] is True
    assert case_state["evaluation_output"]["target_agent"] == "BullAgent"

    assert "evaluation_output_v2" in case_state
    assert case_state["evaluation_output_v2"]["revision_required"] is False
    assert case_state["evaluation_output_v2"]["hallucination_risk"] == "low"

    assert len(revision_messages) == 1
    assert revision_messages[0]["to_agent"] == "BullAgent"

    assert len(final_memo_messages) == 1
    assert final_memo["human_review_required"] is True
    assert final_memo["disclaimer"] == "This is a research support memo, not investment advice."

    assert invalid_citation_ids == []

    print("\n=== CHECKS PASSED ===")
    print("Initial revision required: True")
    print("After revision required: False")
    print("Final memo generated: True")
    print("All citation IDs are valid: True")


if __name__ == "__main__":
    main()