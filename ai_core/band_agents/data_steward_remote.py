from ai_core.band_agents.common import main_for
from ai_core.sample_case import sample_evidence_pack


def build_response(msg) -> str:
    evidence_items = sample_evidence_pack["evidence_items"]
    evidence_text = "\n".join(
        (
            f"- {item['citation_id']}: {item['claim']} "
            f"[{item['source']}, {item['date']}]"
        )
        for item in evidence_items
    )

    return f"""DataStewardAgent prepared the mock Evidence Pack.

Case: {sample_evidence_pack["case_id"]}
Ticker: {sample_evidence_pack["ticker"]}
Company: {sample_evidence_pack["company"]}

Evidence:
{evidence_text}

Next: trigger BullAgent to generate the first bull thesis from this Evidence Pack.
"""


if __name__ == "__main__":
    main_for("bandalpha_data_steward", "DataStewardAgent", build_response)

