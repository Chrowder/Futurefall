# Band Multi-Agent Setup

BandAlpha can run as one smoke-test Remote Agent or as six separate Band Remote Agents that call the same deterministic local AI Core.

## Setup

1. Create six Remote Agents in Band:
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

## Run One Agent

```bash
python -m ai_core.band_agents.bull_remote
```

Replace `bull_remote` with any of:

```text
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

## Notes

- These wrappers do not add shared Band room state yet.
- Each agent uses deterministic sample data from `ai_core.sample_case`.
- The existing single-agent fallback still runs with:

```bash
python -m ai_core.band_remote_agent
```

- Final memo language remains research support only and is not investment advice.
