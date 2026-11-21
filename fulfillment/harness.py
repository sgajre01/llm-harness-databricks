"""Public key selection, then three bounded calls. No numerical tools or oracle access."""

import json
from scenario import select_records


def run_harness(e, client):
    records = select_records(e)
    common = f"POLICY: {e['policy']}\nQUESTION: {e['question']}\n"
    stock = client.call_llm(
        common
        + f"""TASK: Compute base_available = max(0,on_hand-reserved) for the exact target SKU/warehouse.
Do not include incoming receipts yet. Also extract ordered_qty. Give a concise calculation.
RECORDS: {json.dumps({k: records[k] for k in ("orders", "inventory")})}""",
        f"{e['id']}/harness/stock",
        "stock",
    )
    delivery = client.call_llm(
        common
        + f"""TASK: Compute latest_dispatch_day = deliver_by_day - transit_days.
If it is negative set eligible_incoming to 0; otherwise sum receipt quantities with arrival_day <= latest_dispatch_day.
Do not add on_hand stock here. Give a concise calculation.
RECORDS: {json.dumps({k: records[k] for k in ("orders", "shipping_lanes", "receipts")})}""",
        f"{e['id']}/harness/delivery",
        "delivery",
    )
    answer = client.call_llm(
        common
        + f"""TASK: Combine the completed steps. If latest_dispatch_day < 0, ship_units=0.
Otherwise ship_units=min(ordered_qty,base_available+eligible_incoming). Give a concise calculation.
STOCK RESULT: {json.dumps(stock)}
DELIVERY RESULT: {json.dumps(delivery)}""",
        f"{e['id']}/harness/final",
    )
    return answer, {"selected_records": records, "stock": stock, "delivery": delivery}
