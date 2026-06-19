# Futurefall / BandAlpha

BandAlpha is a Band-native multi-agent research workflow demo.

It coordinates specialized Band Remote Agents to prepare evidence, generate bull and bear views, flag risks, evaluate grounding, revise unsupported claims, produce a final memo, and wait for human approval.

This is a **human-in-the-loop research support workflow**. It is **not financial advice**.

## Agents

- `ChairAgent`: starts and coordinates the workflow
- `DataStewardAgent`: prepares the Evidence Pack
- `BullAgent`: generates the bullish case
- `BearAgent`: critiques the bull case
- `RiskAgent`: extracts risk flags
- `EvaluatorAgent`: checks citations, unsupported claims, risk coverage, and revision needs
- `MemoAgent`: writes the final research support memo

## Main Demo Paths

Run the stable local demo:

```bash
python3 ai_core/run_demo.py
```

Run all Band Remote Agents:

```bash
.venv/bin/python -u -m ai_core.band_agents.launch_all
```

In Band:

```text
@BandAlpha Chair dispatch AAPL
```

For the stable one-click Chair demo:

```text
@BandAlpha Chair internal AAPL
```

For non-blocking blind dispatch:

```text
@BandAlpha Chair blind AAPL
```

After MemoAgent finishes:

```text
@BandAlpha Chair approve
@BandAlpha Chair request revision: make the memo shorter
```

## Setup

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy config template:

```bash
cp agent_config.example.yaml agent_config.yaml
```

Create a local `.env` with Band URLs, Band handles, `EVIDENCE_PROVIDER=hybrid`, `SEC_USER_AGENT`, and optional LLM provider keys. Do not commit secrets.

Never commit:

```text
.env
agent_config.yaml
.venv/
real API keys
```

## Useful Checks

```bash
python3 -m ai_core.check_demo
python3 -m ai_core.check_chair_workflow
python3 -m ai_core.check_human_approval
python3 -m ai_core.check_parallel_blind_review
python3 -m ai_core.check_evidence_builder
python3 -m ai_core.check_evidence_hybrid
python3 -m ai_core.check_real_data_workflow
python3 -m ai_core.check_llm_fallback
```

Optional live LLM smoke test:

```bash
python3 -m ai_core.check_llm_enabled
```

## More Docs

- [Project map](docs/project_map.md)
- [Checks and exports](docs/checks.md)
- [Band multi-agent setup](docs/band_multi_agent_setup.md)

## Notes

- Default data mode is `hybrid`: SEC EDGAR plus optional yfinance market data.
- `stub` evidence remains available for stable regression checks.
- Optional LLM mode is controlled by `USE_LLM_AGENTS=true`.
- EvaluatorAgent remains rule-based for stable grounding checks.
- Runtime case state is stored under `ai_core/cases/`.
- Final memo disclaimer: `This is a research support memo, not investment advice.`

Force deterministic stub mode when needed:

```bash
EVIDENCE_PROVIDER=stub python3 ai_core/run_demo.py
```

See [milestones](docs/milestones.md) for the project progress log.
