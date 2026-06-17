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

## Notes

- These wrappers do not add shared Band room state yet.
- Each agent uses deterministic sample data from `ai_core.sample_case`.
- The existing single-agent fallback still runs with:

```bash
python -m ai_core.band_remote_agent
```

- Final memo language remains research support only and is not investment advice.
