import json
from pathlib import Path
from typing import Any, Dict

from ai_core.case_state_store import load_case_state
from ai_core.runner import run_chair_workflow

DEFAULT_CASE_ID = "AAPL-001"
OUTPUT_PATH = Path("ai_core/audit_report.json")


def get_report_case_state(case_id: str = DEFAULT_CASE_ID) -> Dict[str, Any]:
    case_state = load_case_state(case_id)

    if not case_state.get("final_memo"):
        case_state = run_chair_workflow(case_id=case_id)["case_state"]

    return case_state


def build_audit_report(case_state: Dict[str, Any]) -> Dict[str, Any]:
    initial_evaluation = case_state.get("evaluation_output") or {}
    final_evaluation = (
        case_state.get("final_evaluation_output")
        or case_state.get("evaluation_output_v2")
        or initial_evaluation
    )
    final_memo = case_state.get("final_memo") or {}

    return {
        "case_id": case_state.get("case_id"),
        "ticker": case_state.get("ticker"),
        "workflow_status": case_state.get("status"),
        "human_status": case_state.get("human_status"),
        "audit_log": case_state.get("audit_log", []),
        "initial_evaluation": initial_evaluation,
        "final_evaluation": final_evaluation,
        "final_memo_summary": final_memo.get("summary"),
        "revision_required_initial": initial_evaluation.get("revision_required"),
        "revision_required_final": final_evaluation.get("revision_required"),
        "disclaimer": final_memo.get("disclaimer"),
    }


def main() -> None:
    case_state = get_report_case_state()
    report = build_audit_report(case_state)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nAudit report exported to: {OUTPUT_PATH}")
    print(f"Case ID: {report['case_id']}")
    print(f"Workflow status: {report['workflow_status']}")
    print(f"Human status: {report['human_status']}")
    print(f"Audit events exported: {len(report['audit_log'])}")


if __name__ == "__main__":
    main()
