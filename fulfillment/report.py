"""One accuracy comparison, paired uncertainty, and a per-example table."""

import csv, json, math, random, statistics
from pathlib import Path


def build(out):
    out = Path(out)
    rows = [json.loads(s) for s in (out / "predictions.jsonl").read_text().splitlines()]
    assert len({(r["id"], r["arm"]) for r in rows}) == len(rows)
    grouped = {}
    for r in rows:
        grouped.setdefault(r["id"], {})[r["arm"]] = r
    summary = {"observations": len(rows), "questions": len(grouped), "arms": {}}
    for arm in ("baseline", "harness"):
        a = [r for r in rows if r["arm"] == arm]
        summary["arms"][arm] = {
            "n": len(a),
            "correct": sum(r["correct"] for r in a),
            "accuracy": sum(r["correct"] for r in a) / len(a),
            "median_seconds": statistics.median(r["elapsed_seconds"] for r in a),
            "successful_calls": sum(r["successful_calls"] for r in a),
            "prompt_tokens": sum(r["prompt_tokens"] for r in a),
            "completion_tokens": sum(r["completion_tokens"] for r in a),
            "invalid_answers": sum(r["status"] == "invalid_answer" for r in a),
        }
    pairs = [
        (g["baseline"]["correct"], g["harness"]["correct"])
        for g in grouped.values()
        if len(g) == 2
    ]
    diffs = [int(h) - int(b) for b, h in pairs]
    n = len(pairs)
    wins = sum(d == 1 for d in diffs)
    losses = sum(d == -1 for d in diffs)
    disc = wins + losses
    rng = random.Random(731)
    draws = sorted(sum(rng.choices(diffs, k=n)) / n * 100 for _ in range(10000))
    summary["paired"] = {
        "n": n,
        "wins": wins,
        "losses": losses,
        "ties": n - wins - losses,
        "improvement_pp": sum(diffs) / n * 100,
        "bootstrap_95_ci_pp": [draws[249], draws[9749]],
        "exact_two_sided_p": min(
            1,
            2 * sum(math.comb(disc, k) for k in range(min(wins, losses) + 1)) / 2**disc,
        )
        if disc
        else 1,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    with (out / "comparison.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "ground_truth",
                "baseline",
                "harness",
                "baseline_correct",
                "harness_correct",
            ]
        )
        for k, g in grouped.items():
            w.writerow(
                [
                    k,
                    g["baseline"]["ground_truth"],
                    g["baseline"]["answer"],
                    g["harness"]["answer"],
                    g["baseline"]["correct"],
                    g["harness"]["correct"],
                ]
            )
    lines = [
        "# Full context versus focused harness",
        "",
        "One endpoint: exact deliverable quantity.",
        "",
        "| Approach | Correct | Accuracy | Median seconds | Input tokens | Output tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, a in summary["arms"].items():
        lines.append(
            f"| {arm} | {a['correct']}/{a['n']} | {a['accuracy']:.1%} | {a['median_seconds']:.2f} | {a['prompt_tokens']:,} | {a['completion_tokens']:,} |"
        )
    p = summary["paired"]
    lo, hi = p["bootstrap_95_ci_pp"]
    lines += [
        "",
        f"Harness improvement: **{p['improvement_pp']:+.1f} percentage points**. Paired wins/losses/ties: {wins}/{losses}/{p['ties']}. Paired-bootstrap 95% interval: [{lo:+.1f}, {hi:+.1f}] pp. Exact paired p={p['exact_two_sided_p']:.4f}.",
        "",
        "10,000 paired-bootstrap draws. One model and one observation per approach/question; synthetic cases from one generator. A degenerate bootstrap interval does not establish equivalence.",
        "",
        "| Question | Expected | Full context | Harness |",
        "|---|---:|---:|---:|",
    ]
    for k, g in grouped.items():
        lines.append(
            f"| {k} | {g['baseline']['ground_truth']} | {g['baseline']['answer']} {'✓' if g['baseline']['correct'] else '✗'} | {g['harness']['answer']} {'✓' if g['harness']['correct'] else '✗'} |"
        )
    (out / "report.md").write_text("\n".join(lines) + "\n")
    return summary
