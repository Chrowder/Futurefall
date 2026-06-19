# Futurefall / BandAlpha

BandAlpha is a Band-native multi-agent research workflow demo.

It coordinates specialized agents to gather evidence, generate bull and bear views, flag risks, check grounding, revise unsupported claims, write a research memo, and wait for human approval.

This is a human-in-the-loop research support workflow. It is not financial advice.

## What It Does

- Runs local deterministic research workflows for stable demos and checks.
- Runs multiple real Band Remote Agents: Chair, Data Steward, Bull, Bear, Risk, Evaluator, and Memo.
- Supports real-data Evidence Packs through SEC EDGAR plus optional market data.
- Supports optional LLM-backed agent text generation with deterministic fallback.
- Keeps EvaluatorAgent rule-based for citation, grounding, risk coverage, and revision checks.
- Stores local case state and audit logs as JSON.
- Supports human approval or revision requests from Band.

## Main Workflows

Stable local demo:

```bash
python3 ai_core/run_demo.py
```

Parallel blind review demo:

```bash
EVIDENCE_PROVIDER=hybrid python3 -m ai_core.run_blind_demo TSLA
```

Launch all configured Band agents:

```bash
.venv/bin/python -u -m ai_core.band_agents.launch_all
```

In Band:

```text
@BandAlpha Chair internal AAPL
@BandAlpha Chair dispatch MSFT
@BandAlpha Chair blind TSLA
@BandAlpha Chair blind memo NVDA
```

After MemoAgent finishes:

```text
@BandAlpha Chair approve
@BandAlpha Chair request revision: tighten the risk section
```

## Setup

Create and install the local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the Band config template:

```bash
cp agent_config.example.yaml agent_config.yaml
```

Create `.env` locally. Typical values:

```bash
EVIDENCE_PROVIDER=hybrid
SEC_USER_AGENT="Your Name your@email.com"
USE_LLM_AGENTS=false
BAND_CHAIR_MODE=internal
```

For LLM mode, set `USE_LLM_AGENTS=true` and provide the configured provider keys/models in `.env`.

Never commit:

```text
.env
agent_config.yaml
.venv/
API keys
runtime case JSON
provider cache files
```

## Data Modes

Use stable fixture data:

```bash
EVIDENCE_PROVIDER=stub python3 ai_core/run_demo.py
```

Use real data:

```bash
EVIDENCE_PROVIDER=hybrid python3 -m ai_core.check_real_data_workflow
```

`hybrid` uses SEC EDGAR as the primary source and optional market snapshot data where available. Runtime data cache is ignored by git.

## Checks

Core checks:

```bash
python3 -m ai_core.check_demo
python3 -m ai_core.check_chair_workflow
python3 -m ai_core.check_human_approval
USE_LLM_AGENTS=false python3 -m ai_core.check_parallel_blind_review
python3 -m ai_core.check_evidence_builder
```

Real-data checks:

```bash
python3 -m ai_core.check_evidence_hybrid
python3 -m ai_core.check_real_data_workflow
```

LLM checks:

```bash
python3 -m ai_core.check_llm_fallback
python3 -m ai_core.check_llm_enabled
```

`check_llm_enabled` skips cleanly if required provider settings are missing.

## Useful Docs

- [Project map](docs/project_map.md)
- [Checks and exports](docs/checks.md)
- [Band multi-agent setup](docs/band_multi_agent_setup.md)
- [Milestones](docs/milestones.md)

## Current Milestone

The current demo supports real-data Evidence Packs and a parallel blind-review workflow. The strongest demo path is:

```bash
EVIDENCE_PROVIDER=hybrid USE_LLM_AGENTS=true .venv/bin/python -u -m ai_core.band_agents.launch_all
```

Then in Band:

```text
@BandAlpha Chair blind TSLA
```

The final memo should remain evidence-linked, auditable, and explicitly framed as research support, not investment advice.
