from ai_core.case_state_store import approve_case, request_case_revision
from ai_core.runner import run_chair_workflow


def main():
    result = run_chair_workflow()
    case_state = result["case_state"]
    case_id = case_state["case_id"]

    assert case_state["human_status"] == "pending_review"

    approved_state = approve_case(case_id)
    assert approved_state["human_status"] == "approved"

    revision_state = request_case_revision(
        case_id,
        comment="Please make the memo more concise.",
    )
    assert revision_state["human_status"] == "revision_requested"
    assert revision_state["human_revision_comment"] == "Please make the memo more concise."

    audit_actions = [event.get("action") for event in revision_state.get("audit_log", [])]
    assert "human_approved" in audit_actions
    assert "human_revision_requested" in audit_actions

    print("\n=== HUMAN APPROVAL CHECKS PASSED ===")
    print("Initial human status: pending_review")
    print("After approve_case: approved")
    print("After request_case_revision: revision_requested")
    print("Audit includes human_approved: True")
    print("Audit includes human_revision_requested: True")


if __name__ == "__main__":
    main()
