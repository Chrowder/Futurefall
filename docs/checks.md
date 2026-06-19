# Checks And Exports

Use these commands from the repo root.

## Stable Local Checks

Run the local demo:

```bash
python3 ai_core/run_demo.py
```

Core workflow:

```bash
python3 -m ai_core.check_demo
python3 -m ai_core.check_chair_workflow
python3 -m ai_core.check_human_approval
```

Parallel blind review:

```bash
python3 -m ai_core.check_parallel_blind_review
python3 -m ai_core.check_chair_blind_dispatch
```

Evidence provider layer:

```bash
python3 -m ai_core.check_evidence_builder
python3 -m ai_core.check_evidence_hybrid
python3 -m ai_core.check_real_data_workflow
```

LLM fallback path:

```bash
USE_LLM_AGENTS=false python3 -m ai_core.check_llm_fallback
```

## Optional Live LLM Check

This check requires valid provider keys, base URLs, and model IDs in `.env`.

```bash
python3 -m ai_core.check_llm_enabled
```

If this fails with a provider HTTP error, the local workflow may still be valid. Check provider credentials, model IDs, and base URLs.

## Exports

Frontend/demo payload:

```bash
python3 -m ai_core.export_demo_output
```

Audit report:

```bash
python3 -m ai_core.export_audit_report
```

Outputs:

```text
ai_core/demo_output.json
ai_core/audit_report.json
```

## Band Runtime

Start all configured Band Remote Agents:

```bash
.venv/bin/python -u -m ai_core.band_agents.launch_all
```

Start one agent:

```bash
.venv/bin/python -u -m ai_core.band_agents.chair_remote
```

Stop with `Ctrl+C`. If a previous run left local state behind, clean runtime files:

```bash
find ai_core/cases -maxdepth 1 -name '*.json' -print -delete
find /tmp -maxdepth 1 -name 'bandalpha_*.lock' -print -delete
```
