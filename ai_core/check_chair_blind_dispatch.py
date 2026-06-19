import os
from types import SimpleNamespace

from ai_core.env_config import load_local_env


def main() -> None:
    load_local_env()
    os.environ.setdefault("BAND_USER_HANDLE", "human_reviewer")
    os.environ.setdefault("BAND_BULL_HANDLE", "bandalpha_bull")
    os.environ.setdefault("BAND_BEAR_HANDLE", "bandalpha_bear")

    try:
        from ai_core.band_agents import chair_remote
        from ai_core.band_agents.common import prepare_outgoing_message
    except ModuleNotFoundError as exc:
        if exc.name == "thenvoi":
            print("Skipping Chair blind dispatch check: thenvoi SDK is not installed.")
            return
        raise

    msg = SimpleNamespace(content="@BandAlpha Chair blind AAPL")
    reply = chair_remote.build_response(msg)
    extra_messages = reply.get("extra_messages", [])

    assert "Parallel blind review started for AAPL" in reply["content"]
    assert "completed" not in reply["content"].lower()
    assert extra_messages
    assert "mode: blind_first_pass" in extra_messages[0]["content"]
    assert "case_id: AAPL-001" in extra_messages[0]["content"]
    assert "ticker: AAPL" in extra_messages[0]["content"]
    assert len(extra_messages[0]["mentions"]) == 2

    fallback_content, fallback_mentions, fallback_used = prepare_outgoing_message(
        "BullAgent completed blind first pass.",
        [os.environ["BAND_BEAR_HANDLE"]],
        participants_msg="participants: human_reviewer",
    )
    assert fallback_used is True
    assert fallback_mentions == [os.environ["BAND_USER_HANDLE"]]
    assert "Next agent is not present in this room" in fallback_content

    direct_content, direct_mentions, direct_fallback_used = prepare_outgoing_message(
        "BullAgent completed blind first pass.",
        [os.environ["BAND_BEAR_HANDLE"]],
        participants_msg=f"participants: {os.environ['BAND_BEAR_HANDLE']}",
    )
    assert direct_fallback_used is False
    assert direct_mentions == [os.environ["BAND_BEAR_HANDLE"]]
    assert "Next agent is not present in this room" not in direct_content

    print("\n=== CHAIR BLIND DISPATCH CHECKS PASSED ===")
    print("Chair blind mode returns immediately: True")
    print("Dispatch message includes mode: blind_first_pass")
    print("Dispatch mentions BullAgent and BearAgent: True")
    print("Missing target agent falls back to human reviewer: True")


if __name__ == "__main__":
    main()
