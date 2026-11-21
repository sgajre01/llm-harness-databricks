# Full-context LLM versus a focused fulfillment harness

This branch contains the simplified two-approach experiment in [`fulfillment/`](fulfillment/README.md).

Each question asks how many units of one product can be delivered by a deadline. Both approaches return one scored integer. The baseline receives the full record packet in one call; the harness filters relevant records and uses three focused calls.

Start with [`fulfillment/README.md`](fulfillment/README.md), the [Databricks runner](fulfillment/notebooks/run.py), and the [results](fulfillment/results/main_v1/report.md).

The original three-approach invoice experiment remains preserved on [`main`](https://github.com/sgajre01/llm-harness-databricks/tree/main). Its root-level source files are historical; use the `fulfillment/` directory for this branch's new experiment. No blog is part of this iteration.
