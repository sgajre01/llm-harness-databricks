"""Exact-integer scoring with immutable configuration and resumable checkpoints."""

import hashlib, json, random, time
from pathlib import Path
from llm_client import LLMClient, MODEL
from baseline import run_baseline
from harness import run_harness
from scenario import public


def answer_value(answer):
    if (
        not isinstance(answer, dict)
        or type(answer.get("ship_units")) is not int
        or answer["ship_units"] < 0
    ):
        raise ValueError("ship_units must be a nonnegative JSON integer")
    return answer["ship_units"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(dataset, out, model=MODEL):
    root = Path(__file__).parent
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    config = {
        "model": model,
        "temperature": 0,
        "max_tokens_per_call": 1200,
        "dataset_sha256": digest(dataset),
        "source_sha256": {
            n: digest(root / n)
            for n in (
                "scenario.py",
                "llm_client.py",
                "baseline.py",
                "harness.py",
                "evaluate.py",
            )
        },
        "ordering_seed": 3017,
        "scoring": "exact integer ship_units; calculation logged but unscored",
        "arms": ["baseline", "harness"],
    }
    cp = out / "config.json"
    if cp.exists() and json.loads(cp.read_text()) != config:
        raise ValueError("Configuration changed; use a fresh output directory")
    cp.write_text(json.dumps(config, indent=2))
    path = out / "predictions.jsonl"
    rows = (
        [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    )
    done = {(r["id"], r["arm"]) for r in rows}
    examples = json.loads(Path(dataset).read_text())
    rng = random.Random(3017)
    client = LLMClient(out / "calls.jsonl", model)
    for e in examples:
        arms = ["baseline", "harness"]
        rng.shuffle(arms)
        for arm in arms:
            if (e["id"], arm) in done:
                continue
            started = time.time()
            offset = len(client.records)
            prediction = None
            steps = None
            error = None
            try:
                if arm == "baseline":
                    prediction = run_baseline(public(e), client)
                else:
                    prediction, steps = run_harness(public(e), client)
                value = answer_value(prediction)
            except (ValueError, KeyError, TypeError) as exc:
                value = None
                error = str(exc)
            calls = client.records[offset:]
            usage = [r.get("response", {}).get("usage", {}) for r in calls]
            row = {
                "id": e["id"],
                "split": e["split"],
                "arm": arm,
                "ground_truth": e["ground_truth"],
                "answer": value,
                "correct": value == e["ground_truth"],
                "response": prediction,
                "intermediate": steps,
                "status": "invalid_answer" if error else "completed",
                "error": error,
                "elapsed_seconds": time.time() - started,
                "call_attempts": len(calls),
                "successful_calls": sum("response" in c for c in calls),
                "prompt_tokens": sum(u.get("prompt_tokens", 0) for u in usage),
                "completion_tokens": sum(u.get("completion_tokens", 0) for u in usage),
                "usage_available": all("prompt_tokens" in u for u in usage),
            }
            with path.open("a") as f:
                f.write(json.dumps(row) + "\n")
            rows.append(row)
            print(
                e["id"], arm, "answer=", value, "correct=", row["correct"], flush=True
            )
    return rows
