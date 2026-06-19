import os

from ai_core.env_config import load_local_env

load_local_env()

from ai_core.runner import run_full_research_case


def main():
    original_use_llm = os.environ.get("USE_LLM_AGENTS")
    key_names = (
        "AIMLAPI_API_KEY",
        "AIMLAPI_BASE_URL",
        "FEATHERLESS_API_KEY",
        "FEATHERLESS_BASE_URL",
        "BULL_MODEL",
        "BEAR_MODEL",
        "RISK_MODEL",
        "MEMO_MODEL",
    )
    original_keys = {key: os.environ.get(key) for key in key_names}

    try:
        os.environ["USE_LLM_AGENTS"] = "false"
        for key in key_names:
            os.environ.pop(key, None)

        result = run_full_research_case()
        case_state = result["case_state"]

        assert case_state["final_memo"]
        assert case_state["evaluation_output"]["revision_required"] is True
        assert case_state["final_evaluation_output"]["revision_required"] is False

        print("\n=== LLM FALLBACK CHECKS PASSED ===")
        print("USE_LLM_AGENTS forced to false: True")
        print("Workflow completed without provider API keys: True")
        print("Final memo generated: True")
        print("Initial revision required: True")
        print("Final revision required: False")

    finally:
        if original_use_llm is None:
            os.environ.pop("USE_LLM_AGENTS", None)
        else:
            os.environ["USE_LLM_AGENTS"] = original_use_llm

        for key, value in original_keys.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


if __name__ == "__main__":
    main()
