from ai_core.band_agents.common import (
    build_reply,
    get_dispatch_evidence_pack,
    get_env_handle,
    load_dispatch_case_state,
    main_for,
    persist_dispatch_step,
)


def build_response(msg):
    case_state = load_dispatch_case_state()
    evidence_pack = get_dispatch_evidence_pack(case_state)
    case_state["evidence_pack"] = evidence_pack
    case_state["status"] = "evidence_pack_ready"
    case_state = persist_dispatch_step(
        case_state,
        {
            "agent": "DataStewardAgent",
            "action": "evidence_pack_ready",
            "target_agent": "BullAgent",
            "summary": "Prepared the mock Evidence Pack and handed off to BullAgent.",
            "evidence_refs": [
                item["citation_id"] for item in evidence_pack["evidence_items"]
            ],
        },
    )

    evidence_items = evidence_pack["evidence_items"]
    evidence_text = "\n".join(
        (
            f"- {item['citation_id']}: {item['claim']} "
            f"[{item['source']}, {item['date']}]"
        )
        for item in evidence_items
    )

    content = f"""DataStewardAgent prepared the mock Evidence Pack.

Case: {case_state["case_id"]}
Ticker: {case_state["ticker"]}
Company: {evidence_pack["company"]}

Evidence:
{evidence_text}

BullAgent please generate Bull v1 from this Evidence Pack, then hand off to BearAgent.
"""
    return build_reply(content, [get_env_handle("BAND_BULL_HANDLE")])


if __name__ == "__main__":
    main_for("bandalpha_data_steward", "DataStewardAgent", build_response)
