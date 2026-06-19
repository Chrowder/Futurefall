"""Run the parallel blind review workflow with REAL data and print the full memo.

Unlike `check_parallel_blind_review`, this entry point does NOT force stub mode —
it honors EVIDENCE_PROVIDER (defaults to hybrid, i.e. real SEC EDGAR + yfinance).

Usage:
    EVIDENCE_PROVIDER=hybrid python -m ai_core.run_blind_demo            # real data
    EVIDENCE_PROVIDER=hybrid python -m ai_core.run_blind_demo MSFT       # another ticker
    EVIDENCE_PROVIDER=stub   python -m ai_core.run_blind_demo            # fixture data
"""

import os
import sys

from ai_core.runner import run_parallel_blind_workflow


def main():
    ticker = (sys.argv[1] if len(sys.argv) > 1 else "AAPL").upper()
    case_id = f"{ticker}-001"

    # Default to real data unless the caller explicitly set a provider.
    provider = os.environ.setdefault("EVIDENCE_PROVIDER", "hybrid")
    print(f"[BlindDemo] Provider: {provider} | Ticker: {ticker} | Case: {case_id}")
    print(f"[BlindDemo] LLM agents: {os.environ.get('USE_LLM_AGENTS', 'false')}")
    print("─" * 80)

    result = run_parallel_blind_workflow(case_id=case_id, ticker=ticker)
    case_state = result["case_state"]

    print(case_state["final_memo"]["summary"])

    print("\n" + "─" * 80)
    print("PARALLEL BLIND REVIEW — RUN STATUS")
    print("─" * 80)
    print(f"  Data provider:              {provider}")
    print(f"  Phase 1 (first passes):     {result.get('phase1_elapsed', 'N/A')}s  [parallel]")
    print(f"  Phase 2 (rebuttals):        {result.get('phase2_elapsed', 'N/A')}s  [parallel]")
    total = result.get("phase1_elapsed", 0) + result.get("phase2_elapsed", 0)
    print(f"  Total parallel agent time:  {total:.2f}s")
    print(f"  Initial revision required:  {case_state['evaluation_output']['revision_required']}")
    print(f"  Final revision required:    {case_state['final_evaluation_output']['revision_required']}")
    print(f"  Human review required:      {case_state['final_memo'].get('human_review_required', True)}")
    print(f"  Audit events:               {len(result['audit_log'])}")


if __name__ == "__main__":
    main()
