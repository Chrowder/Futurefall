# Band Multi-Agent Setup

BandAlpha can run as one smoke-test Remote Agent, six separate Band Remote Agents, or a ChairAgent that orchestrates the deterministic local workflow with persisted case state.

## Setup

1. Create seven Remote Agents in Band:
   - ChairAgent
   - DataStewardAgent
   - BullAgent
   - BearAgent
   - RiskAgent
   - EvaluatorAgent
   - MemoAgent
2. Copy each Remote Agent UUID and API key into your local `agent_config.yaml`.
3. Use `agent_config.example.yaml` as the template for the required keys.
4. Keep real secrets local. Never commit `.env` or `agent_config.yaml`.
5. Put your Band handle and Band URLs in local `.env`:
   - `THENVOI_REST_URL=https://app.band.ai`
   - `THENVOI_WS_URL=wss://app.band.ai/api/v1/socket/websocket`
   - `BAND_USER_HANDLE=your_band_handle`
   - `BAND_DATA_STEWARD_HANDLE=your_data_steward_handle`
   - `BAND_BULL_HANDLE=your_bull_handle`
   - `BAND_BEAR_HANDLE=your_bear_handle`
   - `BAND_RISK_HANDLE=your_risk_handle`
   - `BAND_EVALUATOR_HANDLE=your_evaluator_handle`
   - `BAND_MEMO_HANDLE=your_memo_handle`
   - `BAND_CHAIR_MODE=internal`

## Run One Agent

```bash
python -m ai_core.band_agents.bull_remote
```

Replace `bull_remote` with any of:

```text
chair_remote
data_steward_remote
bull_remote
bear_remote
risk_remote
evaluator_remote
memo_remote
```

## Run All Agents

```bash
python -m ai_core.band_agents.launch_all
```

`launch_all.py` starts every configured multi-agent wrapper concurrently. If a key is missing from `agent_config.yaml`, that agent is skipped with a local warning.

## Chair Modes

Internal mode runs the full deterministic workflow inside ChairAgent:

```bash
BAND_CHAIR_MODE=internal python -m ai_core.band_agents.chair_remote
```

Dispatch mode asks ChairAgent to mention the next real Band Remote Agent instead of running every step internally:

```bash
BAND_CHAIR_MODE=dispatch python -m ai_core.band_agents.launch_all
```

Then mention ChairAgent in Band with:

```text
@BandAlpha Chair dispatch AAPL
```

ChairAgent starts by mentioning `BAND_DATA_STEWARD_HANDLE`. Each remote agent then saves deterministic local output, appends an audit event, and mentions the next configured agent handle.

## Parallel Blind Review

Run the local parallel blind Bull/Bear workflow with:

```bash
python -m ai_core.check_parallel_blind_review
```

In Band, mention ChairAgent with:

```text
@BandAlpha Chair blind AAPL
@BandAlpha Chair parallel AAPL
```

ChairAgent runs a stable internal parallel blind workflow: DataStewardAgent prepares evidence, BullAgent and BearAgent produce independent first-pass views, both agents exchange rebuttals, then RiskAgent, EvaluatorAgent, and MemoAgent complete the flow.

## Human Approval

After the final memo is ready, ChairAgent can record a lightweight human decision:

```text
@BandAlpha Chair approve
@BandAlpha Chair request revision: make the memo more concise
```

Approval sets `human_status` to `approved`. A revision request sets `human_status` to `revision_requested`, stores the comment, and appends the decision to the audit log.

## Audit Report

Export the current mock case audit report with:

```bash
python -m ai_core.export_audit_report
```

This writes `ai_core/audit_report.json` with workflow status, human status, audit events, initial/final evaluations, final memo summary, and the research-support disclaimer.

## Evidence Providers

The default Evidence Pack is built through the provider layer with deterministic stub data:

```bash
python -m ai_core.check_evidence_builder
```

Local code can build a pack directly:

```python
from ai_core.data_providers.evidence_builder import build_evidence_pack

evidence_pack = build_evidence_pack(ticker="AAPL", provider="stub")
```

`EVIDENCE_PROVIDER=stub` keeps the demo stable. Optional provider hooks exist for `yfinance` and `sec`, but the deterministic agents and evaluator are calibrated against the stub E1-E6 Evidence Pack.

## Optional LLM Mode

BullAgent, BearAgent, RiskAgent, and MemoAgent can use sponsor-provided OpenAI-compatible APIs while keeping deterministic structured citations and the rule-based EvaluatorAgent. The demo defaults to AI/ML API for BullAgent, BearAgent, and MemoAgent, and Featherless AI for RiskAgent:

```bash
export AIMLAPI_API_KEY=your_aimlapi_api_key
export AIMLAPI_BASE_URL=your_aimlapi_openai_compatible_base_url
export FEATHERLESS_API_KEY=your_featherless_api_key
export FEATHERLESS_BASE_URL=your_featherless_openai_compatible_base_url
export BULL_PROVIDER=aimlapi
export BULL_MODEL=your_bull_model_id
export BEAR_PROVIDER=aimlapi
export BEAR_MODEL=your_bear_model_id
export RISK_PROVIDER=featherless
export RISK_MODEL=your_risk_model_id
export MEMO_PROVIDER=aimlapi
export MEMO_MODEL=your_memo_model_id
export USE_LLM_AGENTS=true
python -m ai_core.check_llm_enabled
```

Leave `USE_LLM_AGENTS=false` for the stable deterministic demo path. If any provider key, base URL, or agent model is missing, that provider-backed agent falls back to deterministic output. DataStewardAgent remains deterministic and EvaluatorAgent remains rule-based.

## Notes

- These wrappers do not add shared Band room state yet.
- Each agent uses deterministic sample data from `ai_core.sample_case`.
- The existing single-agent fallback still runs with:

```bash
python -m ai_core.band_remote_agent
```

- Final memo language remains research support only and is not investment advice.
