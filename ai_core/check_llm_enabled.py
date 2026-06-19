import os
from typing import Any, List

from ai_core.agents import valid_citations
from ai_core.env_config import env_presence, load_local_env
from ai_core.runner import run_full_research_case

load_local_env()


PROVIDER_REQUIREMENTS = {
    "aimlapi": ("AIMLAPI_API_KEY", "AIMLAPI_BASE_URL"),
    "featherless": ("FEATHERLESS_API_KEY", "FEATHERLESS_BASE_URL"),
}

AGENT_DEFAULT_PROVIDERS = {
    "BULL": "aimlapi",
    "BEAR": "aimlapi",
    "RISK": "featherless",
    "MEMO": "aimlapi",
}


def required_env_names():
    required = {"USE_LLM_AGENTS"}

    for agent, default_provider in AGENT_DEFAULT_PROVIDERS.items():
        provider = os.getenv(f"{agent}_PROVIDER", default_provider).lower()
        provider_requirements = PROVIDER_REQUIREMENTS.get(provider, ())
        required.update(provider_requirements)
        required.add(f"{agent}_MODEL")

    return sorted(required)


def print_env_presence() -> None:
    presence = env_presence(required_env_names())
    print("LLM env presence:")
    for key in sorted(presence):
        print(f"- {key}: {presence[key]}")


def missing_llm_settings():
    missing = []

    for agent, default_provider in AGENT_DEFAULT_PROVIDERS.items():
        provider = os.getenv(f"{agent}_PROVIDER", default_provider).lower()
        provider_requirements = PROVIDER_REQUIREMENTS.get(provider)
        if not provider_requirements:
            missing.append(f"{agent}_PROVIDER valid provider")
            continue

        for key in provider_requirements:
            if not os.getenv(key):
                missing.append(key)

        if not os.getenv(f"{agent}_MODEL"):
            missing.append(f"{agent}_MODEL")

    return sorted(set(missing))


def collect_citation_ids(obj: Any) -> List[str]:
    citation_ids = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "citation_id" and isinstance(value, str):
                citation_ids.append(value)
            else:
                citation_ids.extend(collect_citation_ids(value))

    elif isinstance(obj, list):
        for item in obj:
            citation_ids.extend(collect_citation_ids(item))

    return citation_ids


def main():
    print_env_presence()

    if os.getenv("USE_LLM_AGENTS", "false").lower() != "true":
        print("Skipping LLM enabled check: USE_LLM_AGENTS is not true.")
        return

    missing = missing_llm_settings()
    if missing:
        print(f"Skipping LLM enabled check: missing {', '.join(missing)}.")
        return

    original_strict = os.environ.get("LLM_STRICT_ERRORS")
    os.environ["LLM_STRICT_ERRORS"] = "true"

    try:
        result = run_full_research_case()
        case_state = result["case_state"]
    finally:
        if original_strict is None:
            os.environ.pop("LLM_STRICT_ERRORS", None)
        else:
            os.environ["LLM_STRICT_ERRORS"] = original_strict

    assert case_state["final_memo"]
    assert case_state["evaluation_output"]
    assert case_state["final_evaluation_output"]
    assert case_state["final_memo"]["summary"]
    assert case_state["final_memo"]["disclaimer"] == "This is a research support memo, not investment advice."
    assert case_state["final_evaluation_output"]["hallucination_risk"] in {"low", "medium"}

    valid_ids = valid_citations(case_state["evidence_pack"])
    used_citation_ids = collect_citation_ids(case_state)
    invalid_citation_ids = sorted({cid for cid in used_citation_ids if cid and cid not in valid_ids})
    assert invalid_citation_ids == []

    print("\n=== LLM ENABLED SMOKE CHECK PASSED ===")
    print("LLM agents enabled: True")
    print(f"Bull provider: {os.getenv('BULL_PROVIDER', 'aimlapi')}")
    print(f"Bear provider: {os.getenv('BEAR_PROVIDER', 'aimlapi')}")
    print(f"Risk provider: {os.getenv('RISK_PROVIDER', 'featherless')}")
    print(f"Memo provider: {os.getenv('MEMO_PROVIDER', 'aimlapi')}")
    print("Final memo generated: True")
    print(f"Initial revision required: {case_state['evaluation_output']['revision_required']}")
    print(f"Final revision required: {case_state['final_evaluation_output']['revision_required']}")
    print(f"Final hallucination risk: {case_state['final_evaluation_output']['hallucination_risk']}")
    print("All citation IDs are valid: True")


if __name__ == "__main__":
    main()
