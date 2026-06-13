import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_core.runner import run_full_research_case


def main():
    result = run_full_research_case()
    case_state = result["case_state"]

    print("\n=== DONE ===")
    print(f"Initial revision required: {case_state['evaluation_output']['revision_required']}")

    if "evaluation_output_v2" in case_state:
        print(f"After revision required: {case_state['evaluation_output_v2']['revision_required']}")
        print(f"Final hallucination risk: {case_state['evaluation_output_v2']['hallucination_risk']}")

    print(f"Final memo generated: {'final_memo' in case_state}")
    print(f"Human review required: {case_state['final_memo']['human_review_required']}")


if __name__ == "__main__":
    main()