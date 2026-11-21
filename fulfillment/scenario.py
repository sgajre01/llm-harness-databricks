"""Single-product fulfillment worlds. No prices or invoices."""

import json
import random

POLICY = """Today is day 0. All dates are integer calendar-day offsets; deadlines are inclusive.
Find the order by order_id. Use only inventory and receipts for its exact SKU and warehouse,
and the shipping lane for its destination region. Only inventory with snapshot_day == 0 is current;
negative snapshot_day values are archived snapshots and must never be used or added together.
Only receipts with status == "confirmed" count; cancelled receipts never count.
Latest dispatch day = deliver_by_day - transit_days. If latest dispatch day < 0, deliver zero units.
Otherwise available units = max(0, on_hand - reserved) plus the quantities of receipts whose
arrival_day <= latest dispatch day. On-hand inventory excludes all listed receipts. Ignore receipts
after the cutoff. Deliver min(ordered_qty, available units). Partial fulfillment is allowed.
Never use stock from other warehouses, products, or orders. The answer is one nonnegative integer."""


def generate(index, split="evaluation", seed=739021):
    r = random.Random(seed + index * 104729)
    sku, warehouse, region = f"SKU-{index:04}", f"WH-{index % 4}", f"ZONE-{index % 5}"
    order = {
        "order_id": f"FUL-{index:04}",
        "sku": sku,
        "warehouse": warehouse,
        "region": region,
        "ordered_qty": r.randint(10, 65),
        "deliver_by_day": r.choice([1, 2, 3, 5, 7]),
    }
    inv = {
        "sku": sku,
        "warehouse": warehouse,
        "on_hand": r.randint(0, 55),
        "reserved": r.randint(0, 18),
        "snapshot_day": 0,
    }
    lane = {"region": region, "transit_days": r.randint(1, 4)}
    receipts = [
        {
            "receipt_id": f"IN-{index}-{j}",
            "sku": sku,
            "warehouse": warehouse,
            "quantity": r.randint(3, 22),
            "arrival_day": r.choice([0, 1, 2, 4, 8]),
            "status": "confirmed",
        }
        for j in range(2)
    ]
    t = {
        "orders": [order],
        "inventory": [inv],
        "receipts": receipts,
        "shipping_lanes": [lane],
    }
    # Same product at a different warehouse is a realistic distractor.
    t["inventory"].append(
        {"sku": sku, "warehouse": "WH-UNRELATED", "on_hand": 999, "reserved": 0}
    )
    for j in range(8):
        t["inventory"].append(
            {
                "sku": sku,
                "warehouse": warehouse,
                "on_hand": r.randint(80, 200),
                "reserved": r.randint(0, 10),
                "snapshot_day": -j - 1,
            }
        )
    for j in range(2):
        t["receipts"].append(
            {
                "receipt_id": f"CANCELLED-{index}-{j}",
                "sku": sku,
                "warehouse": warehouse,
                "quantity": r.randint(20, 60),
                "arrival_day": 0,
                "status": "cancelled",
            }
        )
    n = 128 if index % 2 == 0 else 256
    for j in range(n):
        other_s, other_w, other_z = f"OTHER-SKU-{j}", f"OTHER-WH-{j}", f"OTHER-ZONE-{j}"
        t["orders"].append(
            {
                "order_id": f"OTHER-ORDER-{j}",
                "sku": other_s,
                "warehouse": other_w,
                "region": other_z,
                "ordered_qty": r.randint(10, 99),
                "deliver_by_day": r.randint(1, 8),
            }
        )
        t["inventory"].append(
            {
                "sku": other_s,
                "warehouse": other_w,
                "on_hand": r.randint(0, 100),
                "reserved": r.randint(0, 20),
                "snapshot_day": 0,
            }
        )
        t["receipts"].append(
            {
                "receipt_id": f"OTHER-IN-{j}",
                "sku": other_s,
                "warehouse": other_w,
                "quantity": r.randint(1, 50),
                "arrival_day": r.randint(0, 8),
                "status": "confirmed",
            }
        )
        t["shipping_lanes"].append({"region": other_z, "transit_days": r.randint(1, 6)})
    for table in t.values():
        r.shuffle(table)
    public = {
        "id": f"{split}-{index:04}",
        "split": split,
        "order_id": order["order_id"],
        "distraction_records_per_table": n,
        "policy": POLICY,
        "question": f"How many units for order {order['order_id']} can be delivered by day {order['deliver_by_day']}?",
        "tables": t,
    }
    return {**public, "ground_truth": oracle(public)}


def oracle(e):
    t = e["tables"]
    o = next(x for x in t["orders"] if x["order_id"] == e["order_id"])
    inv = next(
        x
        for x in t["inventory"]
        if x["sku"] == o["sku"]
        and x["warehouse"] == o["warehouse"]
        and x.get("snapshot_day") == 0
    )
    lane = next(x for x in t["shipping_lanes"] if x["region"] == o["region"])
    cutoff = o["deliver_by_day"] - lane["transit_days"]
    if cutoff < 0:
        return 0
    incoming = sum(
        x["quantity"]
        for x in t["receipts"]
        if x["sku"] == o["sku"]
        and x["warehouse"] == o["warehouse"]
        and x["arrival_day"] <= cutoff
        and x["status"] == "confirmed"
    )
    return min(o["ordered_qty"], max(0, inv["on_hand"] - inv["reserved"]) + incoming)


def public(e):
    return {k: v for k, v in e.items() if k != "ground_truth"}


def select_records(e):
    """Relational key selection only. No calculations and no label access."""
    t = e["tables"]
    o = next(x for x in t["orders"] if x["order_id"] == e["order_id"])
    return {
        "orders": [o],
        "inventory": [
            x
            for x in t["inventory"]
            if x["sku"] == o["sku"]
            and x["warehouse"] == o["warehouse"]
            and x.get("snapshot_day") == 0
        ],
        "receipts": [
            x
            for x in t["receipts"]
            if x["sku"] == o["sku"]
            and x["warehouse"] == o["warehouse"]
            and x["status"] == "confirmed"
        ],
        "shipping_lanes": [
            x for x in t["shipping_lanes"] if x["region"] == o["region"]
        ],
    }


def packet(e, focused=False):
    return json.dumps(
        select_records(e) if focused else e["tables"], separators=(",", ":")
    )


if __name__ == "__main__":
    from pathlib import Path
    import hashlib

    root = Path(__file__).parent / "data"
    sets = {
        "examples": [generate(i + 1000) for i in range(50)],
        "pilot": [generate(i + 9000, "pilot", seed=510083) for i in range(5)],
    }
    for name, rows in sets.items():
        (root / f"{name}.json").write_text(json.dumps(rows, indent=2) + "\n")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                name: hashlib.sha256((root / f"{name}.json").read_bytes()).hexdigest()
                for name in sets
            },
            indent=2,
        )
    )
