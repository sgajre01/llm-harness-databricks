import copy, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from scenario import generate, oracle, select_records, public
from evaluate import answer_value, run
from baseline import run_baseline
from harness import run_harness
from llm_client import parse


class Fake:
    def __init__(self, *a, **k):
        self.records = []
        self.prompts = []

    def call_llm(self, prompt, tag, stage="answer"):
        self.prompts.append(prompt)
        self.records.append(
            {"response": {"usage": {"prompt_tokens": 1, "completion_tokens": 1}}}
        )
        if stage == "stock":
            return {"calculation": "x", "base_available": 8, "ordered_qty": 20}
        if stage == "delivery":
            return {
                "calculation": "x",
                "latest_dispatch_day": 1,
                "eligible_incoming": 4,
            }
        return {"calculation": "8+4=12", "ship_units": 12}


class Tests(unittest.TestCase):
    def test_hand_calculated_boundaries(self):
        e = generate(1)
        t = select_records(e)
        e["tables"] = t
        o = t["orders"][0]
        o.update(ordered_qty=20, deliver_by_day=3)
        t["shipping_lanes"][0]["transit_days"] = 2
        t["inventory"][0].update(on_hand=10, reserved=2)
        for receipt, qty, day in zip(t["receipts"], [4, 7], [1, 2]):
            receipt.update(quantity=qty, arrival_day=day)
        self.assertEqual(oracle(e), 12)
        o["ordered_qty"] = 5
        self.assertEqual(oracle(e), 5)
        o.update(ordered_qty=20, deliver_by_day=1)
        self.assertEqual(oracle(e), 0)
        o["deliver_by_day"] = 3
        t["inventory"][0]["reserved"] = 100
        self.assertEqual(oracle(e), 4)

    def test_independent_reference_fifty(self):
        for i in range(1000, 1050):
            e = generate(i)
            t = e["tables"]
            o = [r for r in t["orders"] if r["order_id"] == e["order_id"]][0]
            inv = [
                r
                for r in t["inventory"]
                if (r["sku"], r["warehouse"]) == (o["sku"], o["warehouse"])
                and r.get("snapshot_day") == 0
            ][0]
            transit = [
                r["transit_days"]
                for r in t["shipping_lanes"]
                if r["region"] == o["region"]
            ][0]
            cutoff = o["deliver_by_day"] - transit
            available = inv["on_hand"] - min(inv["reserved"], inv["on_hand"])
            for r in t["receipts"]:
                if (
                    (r["sku"], r["warehouse"]) == (o["sku"], o["warehouse"])
                    and r["arrival_day"] <= cutoff
                    and r["status"] == "confirmed"
                ):
                    available += r["quantity"]
            self.assertEqual(
                e["ground_truth"],
                0 if cutoff < 0 else sorted([available, o["ordered_qty"]])[0],
            )

    def test_archived_inventory_and_cancelled_receipts_ignored(self):
        e = generate(1003)
        before = oracle(e)
        o = next(r for r in e["tables"]["orders"] if r["order_id"] == e["order_id"])
        e["tables"]["inventory"].insert(
            0,
            {
                "sku": o["sku"],
                "warehouse": o["warehouse"],
                "on_hand": 99999,
                "reserved": 0,
                "snapshot_day": -1,
            },
        )
        e["tables"]["receipts"].insert(
            0,
            {
                "sku": o["sku"],
                "warehouse": o["warehouse"],
                "quantity": 99999,
                "arrival_day": 0,
                "status": "cancelled",
            },
        )
        self.assertEqual(oracle(e), before)
        self.assertEqual(oracle(dict(e, tables=select_records(e))), before)

    def test_routing_label_independent(self):
        e = generate(1000)
        changed = copy.deepcopy(e)
        changed["ground_truth"] = -999
        self.assertEqual(select_records(e), select_records(changed))
        self.assertNotIn("ground_truth", public(e))
        self.assertEqual(oracle(dict(e, tables=select_records(e))), e["ground_truth"])

    def test_integer_scoring(self):
        self.assertEqual(answer_value({"ship_units": 3, "calculation": "x"}), 3)
        for value in (True, 3.0, "3", -1, None):
            with self.assertRaises(ValueError):
                answer_value({"ship_units": value})
        with self.assertRaises(ValueError):
            parse('{"ship_units":2,"ship_units":3}')

    def test_calls_and_context(self):
        e = public(generate(1000))
        b, h = Fake(), Fake()
        run_baseline(e, b)
        run_harness(e, h)
        self.assertEqual(len(b.records), 1)
        self.assertEqual(len(h.records), 3)
        self.assertIn("OTHER-SKU", b.prompts[0])
        self.assertNotIn("OTHER-SKU", "".join(h.prompts))
        self.assertNotIn("ground_truth", "".join(b.prompts + h.prompts))

    def test_resume_and_config_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "d.json"
            d.write_text(json.dumps([generate(1000)]))
            out = Path(tmp) / "out"
            with patch("evaluate.LLMClient", Fake):
                one = run(d, out)
                self.assertEqual(one, run(d, out))
                self.assertEqual(len(one), 2)
                d.write_text(json.dumps([generate(1001)]))
                with self.assertRaises(ValueError):
                    run(d, out)
