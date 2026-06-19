import os

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
    assert case_state["evaluation_output"]["revision_required"] is True
    assert case_state["final_evaluation_output"]["revision_required"] is False

    print("\n=== LLM ENABLED SMOKE CHECK PASSED ===")
    print("LLM agents enabled: True")
    print(f"Bull provider: {os.getenv('BULL_PROVIDER', 'aimlapi')}")
    print(f"Bear provider: {os.getenv('BEAR_PROVIDER', 'aimlapi')}")
    print(f"Risk provider: {os.getenv('RISK_PROVIDER', 'featherless')}")
    print(f"Memo provider: {os.getenv('MEMO_PROVIDER', 'aimlapi')}")
    print("Final memo generated: True")
    print("Initial revision required: True")
    print("Final revision required: False")


if __name__ == "__main__":
    main()
