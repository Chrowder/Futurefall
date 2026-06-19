import os

from ai_core.case_state_store import get_case_path
from ai_core.runner import run_chair_workflow


def main():
    original_provider = os.environ.get("EVIDENCE_PROVIDER")
    os.environ["EVIDENCE_PROVIDER"] = "stub"

    try:
        result = run_chair_workflow()
        case_state = result["case_state"]
        case_path = get_case_path(case_state["case_id"])

        assert case_state["final_memo"]
        assert result["audit_log"]
        assert len(result["audit_log"]) >= 8
        assert case_state["evaluation_output"]["revision_required"] is True
        assert case_state["evaluation_output"]["confidence_calibration"] == "overconfident"
        assert case_state["final_evaluation_output"]["revision_required"] is False
        assert "risk_coverage_score" in case_state["final_evaluation_output"]
        assert "confidence_calibration" in case_state["final_evaluation_output"]
        assert "risk_coverage_score" in case_state["final_memo"]["evaluation_summary"]
        assert "confidence_calibration" in case_state["final_memo"]["evaluation_summary"]
        assert "revision_reasons" in case_state["final_memo"]["evaluation_summary"]
        assert "evaluation_notes" in case_state["final_memo"]["evaluation_summary"]
        assert case_state["human_status"] == "pending_review"
        assert case_path.exists()

        print("\n=== CHAIR WORKFLOW CHECKS PASSED ===")
        print(f"Case JSON created: {case_path}")
        print(f"Audit events: {len(result['audit_log'])}")
        print("Initial revision required: True")
        print("Initial confidence calibration: overconfident")
        print("Final revision required: False")
        print("Enhanced evaluation summary present: True")
        print("Human status: pending_review")
    finally:
        if original_provider is None:
            os.environ.pop("EVIDENCE_PROVIDER", None)
        else:
            os.environ["EVIDENCE_PROVIDER"] = original_provider


if __name__ == "__main__":
    main()
