# Project Map

This repo keeps the hackathon demo intentionally small. Most files are plain Python modules rather than a larger framework.

## Core Workflow

- `ai_core/agents.py`: deterministic agent logic plus optional LLM text generation
- `ai_core/runner.py`: local workflow orchestration
- `ai_core/case_state_store.py`: JSON case state and audit log persistence
- `ai_core/sample_case.py`: deterministic AAPL Evidence Pack
- `ai_core/mock_band.py`: local mock Band message wrapper
- `ai_core/schemas.py`: shared TypedDict schemas

## Band Remote Agents

- `ai_core/band_agents/common.py`: shared Band adapter helpers, message formatting, safe mentions, shutdown behavior
- `ai_core/band_agents/chair_remote.py`: ChairAgent internal, dispatch, blind, approval, and revision handlers
- `ai_core/band_agents/data_steward_remote.py`: Evidence Pack handoff
- `ai_core/band_agents/bull_remote.py`: Bull v1, Bull revision, and blind first pass
- `ai_core/band_agents/bear_remote.py`: Bear critique and blind first pass
- `ai_core/band_agents/risk_remote.py`: risk flags
- `ai_core/band_agents/evaluator_remote.py`: rule-based evaluation and revision routing
- `ai_core/band_agents/memo_remote.py`: final memo
- `ai_core/band_agents/launch_all.py`: starts all configured Band agents
- `ai_core/band_remote_agent.py`: legacy single-agent Band smoke test

## Data Providers

- `ai_core/data_providers/evidence_builder.py`: Evidence Pack builder
- `ai_core/data_providers/stub_provider.py`: stable deterministic provider
- `ai_core/data_providers/yfinance_provider.py`: optional market snapshot provider
- `ai_core/data_providers/sec_provider.py`: SEC provider placeholder

Default provider:

```bash
EVIDENCE_PROVIDER=stub
```

## LLM Clients

- `ai_core/llm_clients/openai_compatible_client.py`: current OpenAI-compatible client used by routed agents
- `ai_core/llm_client.py`: legacy OpenAI-only compatibility wrapper

Default mode:

```bash
USE_LLM_AGENTS=false
```

## Runtime Artifacts

- `ai_core/cases/*.json`: local generated case state, ignored by git
- `ai_core/demo_output.json`: exported frontend/demo payload
- `ai_core/audit_report.json`: exported audit report

## Design Constraint

Do not move core modules casually during the hackathon. Existing commands such as `python3 -m ai_core.check_demo` are used as acceptance checks.
