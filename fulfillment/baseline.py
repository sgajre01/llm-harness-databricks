from scenario import packet


def run_baseline(e, client):
    return client.call_llm(
        f"""POLICY: {e["policy"]}
QUESTION: {e["question"]}
SOURCE RECORDS: {packet(e)}
Identify the exact target order. Calculate the shipping cutoff, unreserved stock, eligible receipts,
and the final quantity capped at ordered_qty. You have all necessary records. Check each calculation.
Give a concise calculation and the final ship_units integer.""",
        f"{e['id']}/baseline",
    )
