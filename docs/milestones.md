# Milestones

## Milestone 1: Deterministic AI Core

- Built local Bull, Bear, Risk, Evaluator, and Memo agents.
- Added deterministic AAPL Evidence Pack.
- Added local runner and demo checks.
- Preserved safety language: research support only, not investment advice.

## Milestone 2: Band Remote Agents

- Added separate Band Remote Agent wrappers for Chair, Data Steward, Bull, Bear, Risk, Evaluator, and Memo.
- Added `launch_all.py` for concurrent local startup.
- Kept the original single-agent Band smoke test.

## Milestone 3: Chair Orchestration And Audit Trail

- Added JSON case state persistence under `ai_core/cases/`.
- Added audit events for agent handoffs, revision decisions, memo generation, and human review.
- Added Chair internal mode for a stable one-click demo.
- Added Band-native dispatch mode for multi-agent handoff.

## Milestone 4: Human Review Gate

- Added human approval and human revision request support.
- ChairAgent can record `approved` or `revision_requested` status from Band messages.
- Added checks for approval and revision audit events.

## Milestone 5: Cross-Model Optional LLM Routing

- Added optional LLM-backed Bull, Bear, Risk, and Memo generation.
- Kept deterministic fallback when `USE_LLM_AGENTS=false` or provider settings are missing.
- Kept EvaluatorAgent rule-based for stable grounding and revision checks.
- Added OpenAI-compatible provider routing for sponsor APIs.

## Milestone 6: Band-Native Blind Dispatch

- Changed Chair blind mode to non-blocking dispatch.
- BullAgent and BearAgent can independently handle `mode: blind_first_pass`.
- Added safer Band message formatting, mention fallback, and retry dedupe.
- Verified full Band workflow through MemoAgent and human review.

## Milestone 7: Production-Style Evidence Provider Layer

- Kept `stub` as the stable regression evidence provider.
- Added `hybrid` evidence mode as the default runtime data path.
- Implemented SEC EDGAR provider support for ticker lookup, submissions metadata, and companyfacts.
- Added optional yfinance market snapshot as auxiliary evidence.
- Added local SEC response caching under ignored `ai_core/data_cache/`.
- Added `check_evidence_hybrid` and `check_real_data_workflow` to verify E1-E8 evidence schema and the real-data workflow path.

## Next Candidates

- Improve SEC financial fact selection and period handling.
- Add a lightweight cache inspection command.
- Add a clean reset command for local runtime state.
