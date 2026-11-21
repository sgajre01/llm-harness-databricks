# Full-context LLM versus a focused fulfillment harness

This experiment asks one question: **does a focused, multi-call harness calculate deliverable units more accurately than one LLM call receiving every record?** It scores one integer, with no pricing or invoices.

The code is developed on `experiment/fulfillment-two-arm`. The original three-arm experiment remains on `main`. This is a fresh dataset and a separate experiment; old quantity-only results are not reused.

## The two approaches

- **Baseline:** one call gets all orders, stock records, receipts and shipping lanes, plus the policy and target question.
- **Harness:** deterministic key selection finds the target order's records; one model call calculates unreserved stock, a second calculates the dispatch cutoff and eligible receipts, and a third calculates the capped deliverable quantity.

Both use the same Qwen3 Next Instruct endpoint, temperature 0, JSON Schema output and a 1,200-token ceiling per call. Each response includes a concise `calculation` for inspection. **Only the `ship_units` integer is scored.** Allowing a calculation in the baseline avoids forcing it to guess an integer without working through the problem.

The harness makes three calls versus one. Routing and extra inference are part of the treatment. This comparison does not isolate decomposition from record selection, and does not claim equal inference budgets.

## Data and scoring

There are 50 fresh evaluation worlds (IDs 1000–1049) and 5 pilot worlds from a separate seed (IDs 9000–9004). Every question contains one SKU, one target warehouse, two confirmed receipts and a shipping lane. Archived inventory snapshots and cancelled receipts must be ignored. Unrelated records and same-SKU stock at another warehouse are distractors. The two distraction levels (32 or 64 unrelated records per table) keep target-order complexity identical.

The rule is explicit: latest dispatch = delivery deadline minus transit; negative dispatch means zero units. Otherwise available stock = max(0, on-hand minus reserved) plus receipts arriving by the cutoff, inclusive. Deliver the minimum of ordered and available units. Expected answers come from deterministic Python and are checked by a separately written reference plus hand-calculated edge cases.

A correct answer is an exact nonnegative JSON integer equal to the expected units. No numerical tolerance, answer repair, model judge, or correctness-based retries are used. Malformed model answers count as wrong. Infrastructure failures interrupt execution for later resume. Three application-level attempts are allowed for transient errors; the SDK can also retry HTTP requests internally.

The pilot checks integration and calibration before prompts/model/settings are frozen. Pilot changes are documented separately. The evaluation runs regardless of the direction of the measured difference; a harness win is a hypothesis, not a guaranteed result.

## Run in Databricks Free Edition

Preserve this directory layout in your workspace. Open `notebooks/run.py` as a Databricks notebook and select serverless compute. The notebook uses the current identity through `WorkspaceClient()`; do not put tokens in code.

1. Run widgets `dataset=pilot`, `output_name=my_pilot`.
2. After reviewing the independent pilot, freeze settings and run `dataset=examples`, `output_name=my_evaluation`.
3. Outputs are saved under `outputs/<output_name>/`: raw calls, predictions, config hashes, runtime, CSV, report, summary and validation.
4. Resume using the same output name and unchanged code/data/config. If you change those, use a new output directory.

The runner executes the seven tests on Databricks before making model calls. For local checks, run from this directory:

```bash
python -m unittest discover -s tests -v
```

`python scenario.py` regenerates the seeded data and hashes. Do not regenerate or edit a frozen evaluation dataset during a run.

## Reporting

Report correct/50 and accuracy for each arm, percentage-point gain, paired wins/losses/ties, a seeded paired-bootstrap interval, and an exact two-sided paired test. Include tokens, latency and per-question answers. One run and one synthetic generator limit generalization. If both arms fail or saturate, disclose that limitation instead of claiming proof.

This branch contains code and experiment evidence only. No blog is part of this iteration.
