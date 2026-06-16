from ai_core.band_agents.common import main_for
from ai_core.band_remote_agent import format_band_response
from ai_core.runner import run_full_research_case


def build_response(msg) -> str:
    result = run_full_research_case()
    return format_band_response(result)


if __name__ == "__main__":
    main_for("bandalpha_memo", "MemoAgent", build_response)

