import json
from pathlib import Path
from typing import Any, Dict, List

from ai_core.runner import run_full_research_case


def summarize_message(message: Dict[str, Any]) -> str:
    from_agent = message.get("from_agent")
    payload = message.get("payload", {})

    if from_agent == "DataStewardAgent":
        evidence_items = payload.get("evidence_items", [])
        ticker = payload.get("ticker", "unknown ticker")
        return f"Mock evidence pack for {ticker} with {len(evidence_items)} evidence items."

    if from_agent == "BullAgent":
        if "revision_note" in payload:
            return payload.get("revision_note", "BullAgent revised the thesis.")
        return payload.get("bull_thesis", "BullAgent generated a bullish thesis.")

    if from_agent == "BearAgent":
        return payload.get("bear_thesis", "BearAgent generated an adversarial critique.")

    if from_agent == "RiskAgent":
        return payload.get("risk_summary", "RiskAgent identified key risks.")

    if from_agent == "EvaluatorAgent":
        if payload.get("revision_required"):
            unsupported_count = len(payload.get("unsupported_claims", []))
            return f"EvaluatorAgent found {unsupported_count} unsupported claim(s) and requested revision."
        return "EvaluatorAgent passed the revised output with low hallucination risk."

    if from_agent == "MemoAgent":
        return "MemoAgent generated the final human-review research memo."

    return "Agent message generated."


def get_message_title(message: Dict[str, Any]) -> str:
    from_agent = message.get("from_agent")
    message_type = message.get("message_type")

    if from_agent == "DataStewardAgent":
        return "Evidence Pack Ready"

    if from_agent == "BullAgent" and "revision_note" in message.get("payload", {}):
        return "Bull Thesis Revised"

    if from_agent == "BullAgent":
        return "Bull Thesis Generated"

    if from_agent == "BearAgent":
        return "Bear Critique Generated"

    if from_agent == "RiskAgent":
        return "Risk Flags Generated"

    if from_agent == "EvaluatorAgent" and message_type == "revision_request":
        return "Revision Requested"

    if from_agent == "EvaluatorAgent":
        return "Evaluation Passed"

    if from_agent == "MemoAgent":
        return "Final Memo Generated"

    return "Agent Message"


def build_frontend_timeline(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    timeline = []

    for index, message in enumerate(messages, start=1):
        timeline.append(
            {
                "step": index,
                "agent": message.get("from_agent"),
                "target": message.get("to_agent") or "ALL",
                "message_type": message.get("message_type"),
                "title": get_message_title(message),
                "summary": summarize_message(message),
                "status": message.get("status"),
                "revision_required": message.get("revision_required", False),
            }
        )

    return timeline


def main():
    result = run_full_research_case()
    case_state = result["case_state"]
    messages = result["messages"]

    export_payload = {
        "case_id": case_state["case_id"],
        "ticker": case_state["ticker"],
        "messages": messages,
        "frontend_timeline": build_frontend_timeline(messages),
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
    print(f"Timeline events exported: {len(export_payload['frontend_timeline'])}")
    print(f"Final memo generated: {'final_memo' in export_payload}")


if __name__ == "__main__":
    main()