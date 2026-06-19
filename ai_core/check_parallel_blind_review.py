import os

from ai_core.runner import run_parallel_blind_workflow


def main():
    original_provider = os.environ.get("EVIDENCE_PROVIDER")
    os.environ["EVIDENCE_PROVIDER"] = "stub"

    try:
        result = run_parallel_blind_workflow()
        case_state = result["case_state"]
        audit_actions = {event.get("action") for event in result["audit_log"]}

        assert case_state["parallel_blind_review"] is True
        assert case_state["blind_review_status"] == "completed"
        assert case_state["bull_first_pass"]
        assert case_state["bear_first_pass"]
        assert case_state["bull_rebuttal"]
        assert case_state["bear_rebuttal"]
        assert "blind_review_started" in audit_actions
        assert "bull_first_pass_completed" in audit_actions
        assert "bear_first_pass_completed" in audit_actions
        assert "bull_rebuttal_completed" in audit_actions
        assert "bear_rebuttal_completed" in audit_actions
        assert "blind_review_completed" in audit_actions
        assert case_state["final_memo"]
        assert case_state["evaluation_output"]["revision_required"] is True
        assert case_state["final_evaluation_output"]["revision_required"] is False

        print("\n=== PARALLEL BLIND REVIEW CHECKS PASSED ===")
        print("Parallel blind review enabled: True")
        print("Bull first pass exists: True")
        print("Bear first pass exists: True")
        print("Bull rebuttal exists: True")
        print("Bear rebuttal exists: True")
        print("Initial revision required: True")
        print("Final revision required: False")
        print(f"Audit events: {len(result['audit_log'])}")
    finally:
        if original_provider is None:
            os.environ.pop("EVIDENCE_PROVIDER", None)
        else:
            os.environ["EVIDENCE_PROVIDER"] = original_provider


if __name__ == "__main__":
    main()
