import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from ai_core.sample_case import sample_evidence_pack

CASES_DIR = Path(__file__).resolve().parent / "cases"


def get_case_path(case_id: str) -> Path:
    return CASES_DIR / f"{case_id}.json"


def _new_case_state(case_id: str, ticker: str = "AAPL") -> Dict[str, Any]:
    evidence_pack = copy.deepcopy(sample_evidence_pack)
    evidence_pack["case_id"] = case_id
    evidence_pack["ticker"] = ticker

    return {
        "case_id": case_id,
        "ticker": ticker,
        "status": "created",
        "evidence_pack": evidence_pack,
        "bull_output": None,
        "bear_output": None,
        "risk_output": None,
        "evaluation_output": None,
        "bull_output_v2": None,
        "evaluation_output_v2": None,
        "final_bull_output": None,
        "final_evaluation_output": None,
        "final_memo": None,
        "human_status": None,
        "audit_log": [],
    }


def load_case_state(case_id: str) -> Dict[str, Any]:
    case_path = get_case_path(case_id)

    if not case_path.exists():
        return _new_case_state(case_id)

    try:
        with case_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return _new_case_state(case_id)


def save_case_state(case_id: str, case_state: Dict[str, Any]) -> None:
    CASES_DIR.mkdir(parents=True, exist_ok=True)
    case_path = get_case_path(case_id)
    temp_path = case_path.with_name(f".{case_path.name}.{os.getpid()}.tmp")

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(case_state, f, indent=2, ensure_ascii=False)
        f.write("\n")

    temp_path.replace(case_path)


def create_or_reset_case(case_id: str, ticker: str = "AAPL") -> Dict[str, Any]:
    case_state = _new_case_state(case_id, ticker)
    save_case_state(case_id, case_state)
    return case_state


def append_audit_event(case_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    case_state = load_case_state(case_id)
    audit_event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }

    case_state.setdefault("audit_log", []).append(audit_event)
    save_case_state(case_id, case_state)
    return case_state
