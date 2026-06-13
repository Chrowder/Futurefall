import json
from pathlib import Path

from ai_core.runner import run_full_research_case

def main():
    result = run_full_research_case()

    case_state = result["case_state"]

    export_payload = {
        "case_id": case_state["case_id"],
        "ticker": case_state["ticker"],
        "messages": result["messages"],
        "initial_evaluation": case_state["evaluation_output"],
        "final_evaluation": case_state.get(
            "evaluation_output_v2",
            case_state["evaluation_output"],
        ),
        "final_memo": result["final_memo"],
    }

    output_path = Path("ai_core/demo_output.json")

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    print(f"\nDemo output exported to: {output_path}")
    print(f"Messages exported: {len(export_payload['messages'])}")
    print(f"Final memo generated: {'final_memo' in export_payload}")


if __name__ == "__main__":
    main()