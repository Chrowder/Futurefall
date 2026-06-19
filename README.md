# Futurefall

Futurefall is the hackathon repo for **BandAlpha**, a Band-native multi-agent research workflow demo.

BandAlpha coordinates specialized agents through Band Remote Agents:

- `ChairAgent` coordinates the workflow.
- `DataStewardAgent` prepares the Evidence Pack.
- `BullAgent` builds the bullish case.
- `BearAgent` critiques the bull case.
- `RiskAgent` extracts risk flags.
- `EvaluatorAgent` performs rule-based grounding and citation checks.
- `MemoAgent` writes the final research support memo.

The project is a **human-in-the-loop research support workflow**. It is **not financial advice**.

## What This Demo Shows

- Band-native multi-agent handoffs using real Band Remote Agents.
- A stable deterministic local AI Core for demos and tests.
- Optional LLM-backed Bull, Bear, Risk, and Memo agents with deterministic fallback.
- A rule-based EvaluatorAgent that checks citations, unsupported claims, risk coverage, and confidence calibration.
- A revision loop: EvaluatorAgent asks BullAgent to revise unsupported wording, then evaluates again.
- Case state persistence and audit logging in local JSON files.
- Human approval or revision request after the final memo.
- Evidence Provider Layer with deterministic stub data and future hooks for real providers.

## Repository Structure

```text
ai_core/
  agents.py                     Core deterministic and optional LLM agent logic
  runner.py                     Local workflow orchestration
  case_state_store.py            JSON case state and audit log store
  sample_case.py                 Mock AAPL Evidence Pack
  band_remote_agent.py           Single-agent Band smoke test
  band_agents/                  Multi-agent Band Remote Agent wrappers
  data_providers/               Evidence provider layer
  llm_clients/                  OpenAI-compatible provider client
  check_*.py                    Local checks and smoke tests
docs/
  band_multi_agent_setup.md      Band Remote Agent setup notes
```

Generated runtime case files are written under:

```text
ai_core/cases/
```

## Safety And Scope

BandAlpha is intentionally scoped for a hackathon demo:

- No frontend in this repo.
- No database.
- No vector DB.
- No Docker requirement.
- No required paid data API.
- No real investment recommendation.
- EvaluatorAgent remains rule-based for stable grounding checks.
- DataStewardAgent defaults to deterministic stub evidence.

Final memo disclaimer:

```text
This is a research support memo, not investment advice.
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy local config templates:

```bash
cp agent_config.example.yaml agent_config.yaml
```

Create a local `.env` file. Do not commit it.

Minimum local `.env` values for Band:

```bash
THENVOI_REST_URL=https://app.band.ai
THENVOI_WS_URL=wss://app.band.ai/api/v1/socket/websocket
BAND_USER_HANDLE=your_band_handle

BAND_DATA_STEWARD_HANDLE=your_data_steward_handle
BAND_BULL_HANDLE=your_bull_handle
BAND_BEAR_HANDLE=your_bear_handle
BAND_RISK_HANDLE=your_risk_handle
BAND_EVALUATOR_HANDLE=your_evaluator_handle
BAND_MEMO_HANDLE=your_memo_handle

BAND_CHAIR_MODE=internal
USE_LLM_AGENTS=false
EVIDENCE_PROVIDER=stub
```

For real Band Remote Agents, create one Remote Agent per role and copy each UUID/API key into `agent_config.yaml` using `agent_config.example.yaml` as the template.

Never commit:

```text
.env
agent_config.yaml
.venv/
real API keys
```

## Run The Local Demo

The stable deterministic workflow runs without LLM provider keys:

```bash
python3 ai_core/run_demo.py
```

Core checks:

```bash
python3 -m ai_core.check_demo
python3 -m ai_core.check_chair_workflow
python3 -m ai_core.check_human_approval
python3 -m ai_core.check_parallel_blind_review
python3 -m ai_core.check_evidence_builder
python3 -m ai_core.check_llm_fallback
```

Export demo output:

```bash
python3 -m ai_core.export_demo_output
python3 -m ai_core.export_audit_report
```

Outputs:

```text
ai_core/demo_output.json
ai_core/audit_report.json
```

## Run Band Remote Agents

Run all configured Band Remote Agents:

```bash
.venv/bin/python -u -m ai_core.band_agents.launch_all
```

The `-u` flag is recommended so logs flush immediately.

Run one agent:

```bash
.venv/bin/python -u -m ai_core.band_agents.chair_remote
.venv/bin/python -u -m ai_core.band_agents.bull_remote
```

Single-agent fallback smoke test:

```bash
.venv/bin/python -u -m ai_core.band_remote_agent
```

## ChairAgent Modes

### Internal Mode

Internal mode runs the whole workflow inside ChairAgent. This is the stable one-click demo.

Band message:

```text
@BandAlpha Chair internal AAPL
```

Or set:

```bash
BAND_CHAIR_MODE=internal
```

### Dispatch Mode

Dispatch mode is Band-native. ChairAgent starts the workflow and each agent mentions the next agent.

Band message:

```text
@BandAlpha Chair dispatch AAPL
```

Expected handoff path:

```text
Chair -> Data Steward -> Bull -> Bear -> Risk -> Evaluator -> Bull revision -> Evaluator -> Memo -> Human review
```

### Blind Mode

Blind mode is non-blocking for ChairAgent. ChairAgent quickly dispatches BullAgent and BearAgent for independent first-pass analysis.

Band messages:

```text
@BandAlpha Chair blind AAPL
@BandAlpha Chair parallel AAPL
```

BullAgent and BearAgent handle:

```text
mode: blind_first_pass
```

The local full blind workflow is still available:

```bash
python3 -m ai_core.check_parallel_blind_review
```

## Human Approval

After MemoAgent produces the final memo, the case waits for human review.

Approve:

```text
@BandAlpha Chair approve
```

Request changes:

```text
@BandAlpha Chair request revision: make the memo shorter
```

This updates local case state and appends audit events:

- `human_approved`
- `human_revision_requested`

## Optional LLM Mode

The default path is deterministic. Set `USE_LLM_AGENTS=true` to enable provider-backed generation where configured.

Current routing:

- BullAgent: AI/ML API via OpenAI-compatible client
- BearAgent: AI/ML API via OpenAI-compatible client
- RiskAgent: Featherless AI via OpenAI-compatible client
- MemoAgent: AI/ML API via OpenAI-compatible client
- EvaluatorAgent: rule-based only
- DataStewardAgent: deterministic only

Example `.env` keys:

```bash
USE_LLM_AGENTS=true

AIMLAPI_API_KEY=your_aimlapi_key
AIMLAPI_BASE_URL=your_aimlapi_openai_compatible_base_url
FEATHERLESS_API_KEY=your_featherless_key
FEATHERLESS_BASE_URL=your_featherless_openai_compatible_base_url

BULL_PROVIDER=aimlapi
BULL_MODEL=your_bull_model
BEAR_PROVIDER=aimlapi
BEAR_MODEL=your_bear_model
RISK_PROVIDER=featherless
RISK_MODEL=your_risk_model
MEMO_PROVIDER=aimlapi
MEMO_MODEL=your_memo_model

LLM_TIMEOUT_SECONDS=20
```

LLM smoke check:

```bash
python3 -m ai_core.check_llm_enabled
```

If provider keys, base URLs, or model IDs are missing, agents fall back to deterministic output. If `check_llm_enabled` fails with provider HTTP errors, verify provider/model/API settings.

## Evidence Providers

The default provider is `stub`, which preserves the E1-E6 Evidence Pack used by the evaluator and revision loop.

Build evidence locally:

```python
from ai_core.data_providers.evidence_builder import build_evidence_pack

evidence_pack = build_evidence_pack(ticker="AAPL", provider="stub")
```

Provider hooks:

- `stub`: deterministic mock data, default
- `yfinance`: optional real data provider if installed
- `sec`: placeholder shape for future SEC data

Check:

```bash
python3 -m ai_core.check_evidence_builder
```

## Audit And Case State

Case state is stored as local JSON:

```text
ai_core/cases/AAPL-001.json
```

The audit log records handoffs and decisions such as:

- `case_created`
- `evidence_pack_ready`
- `bull_generated`
- `bear_generated`
- `risk_generated`
- `evaluation_completed`
- `revision_requested`
- `bull_revised`
- `final_evaluation_completed`
- `memo_generated`
- `human_review_pending`

Export an audit report:

```bash
python3 -m ai_core.export_audit_report
```

## Band Troubleshooting

Use a fresh Band chat room when testing a clean workflow. Old rooms may contain failed or unprocessed messages that Band resyncs after restart.

Recommended startup:

```bash
.venv/bin/python -u -m ai_core.band_agents.launch_all
```

Useful log lines:

```text
on_message received
sending reply requested_mentions=...
reply sent mentions=...
fallback_used=True/False
WebSocket disconnected: received 1002
Failed to mark message ... as processed: 422 validation_error
```

Notes:

- `reply sent` means the agent did send a Band reply.
- A later `processed: 422` comes from the SDK/platform message lifecycle.
- If an agent handle is not present in the room, the wrapper falls back to `BAND_USER_HANDLE` and warns that the next agent should be added.
- If an agent appears gray in Band but logs show `reply sent`, check the terminal and local case state before assuming the workflow failed.

Inspect case state:

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("ai_core/cases/AAPL-001.json")
data = json.loads(p.read_text())
print("status:", data.get("status"))
print("human_status:", data.get("human_status"))
print("has_final_memo:", bool(data.get("final_memo")))
print("audit_actions:", [e.get("action") for e in data.get("audit_log", [])])
PY
```

Clean local runtime state:

```bash
find ai_core/cases -maxdepth 1 -name '*.json' -print -delete
find /tmp -maxdepth 1 -name 'bandalpha_*.lock' -print -delete
```
