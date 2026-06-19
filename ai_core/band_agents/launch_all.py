import asyncio

from thenvoi.config import load_agent_config

from ai_core.band_agents import (
    bear_remote,
    bull_remote,
    chair_remote,
    data_steward_remote,
    evaluator_remote,
    memo_remote,
    risk_remote,
)
from ai_core.band_agents.common import load_band_environment, run_remote_agent

AGENTS = [
    ("bandalpha_chair", "ChairAgent", chair_remote.build_response),
    ("bandalpha_data_steward", "DataStewardAgent", data_steward_remote.build_response),
    ("bandalpha_bull", "BullAgent", bull_remote.build_response),
    ("bandalpha_bear", "BearAgent", bear_remote.build_response),
    ("bandalpha_risk", "RiskAgent", risk_remote.build_response),
    ("bandalpha_evaluator", "EvaluatorAgent", evaluator_remote.build_response),
    ("bandalpha_memo", "MemoAgent", memo_remote.build_response),
]


def configured_agents() -> list[tuple[str, str, object]]:
    available = []
    seen_config_keys = set()

    for agent_config_key, agent_name, response_builder in AGENTS:
        if agent_config_key in seen_config_keys:
            print(f"Skipping duplicate config key: {agent_config_key}")
            continue
        seen_config_keys.add(agent_config_key)

        try:
            load_agent_config(agent_config_key)
        except Exception as exc:
            print(f"Skipping {agent_name}: {agent_config_key} is not configured ({exc})")
            continue
        available.append((agent_config_key, agent_name, response_builder))

    return available


async def main() -> None:
    load_band_environment()
    agents = configured_agents()
    tasks = []

    if not agents:
        print("No BandAlpha multi-agent credentials found in agent_config.yaml.")
        print("Add the bandalpha_* keys from agent_config.example.yaml, then rerun.")
        return

    print(f"Launching {len(agents)} BandAlpha remote agent(s).")
    tasks = [
        asyncio.create_task(
            run_remote_agent(agent_config_key, agent_name, response_builder),
            name=agent_name,
        )
        for agent_config_key, agent_name, response_builder in agents
    ]

    try:
        await asyncio.gather(*tasks)
    except (asyncio.CancelledError, KeyboardInterrupt):
        print("Shutting down BandAlpha agents...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        pending_tasks = [task for task in tasks if not task.done()]
        if pending_tasks:
            print("Shutting down BandAlpha agents...")
            for task in pending_tasks:
                task.cancel()
            await asyncio.gather(*pending_tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down BandAlpha agents...")
