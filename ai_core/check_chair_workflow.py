from ai_core.case_state_store import get_case_path
from ai_core.runner import run_chair_workflow


def main():
    result = run_chair_workflow()
    case_state = result["case_state"]
    case_path = get_case_path(case_state["case_id"])

    assert case_state["final_memo"]
    assert result["audit_log"]
    assert len(result["audit_log"]) >= 8
    assert case_state["evaluation_output"]["revision_required"] is True
    assert case_state["final_evaluation_output"]["revision_required"] is False
    assert case_state["human_status"] == "pending_review"
    assert case_path.exists()

    print("\n=== CHAIR WORKFLOW CHECKS PASSED ===")
    print(f"Case JSON created: {case_path}")
    print(f"Audit events: {len(result['audit_log'])}")
    print("Initial revision required: True")
    print("Final revision required: False")
    print("Human status: pending_review")


if __name__ == "__main__":
    main()
