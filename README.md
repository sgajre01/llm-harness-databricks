# Focused context versus a full-context LLM

A reproducible synthetic order-analysis experiment on **Databricks Free Edition**. It compares one full-context call, a harness whose domain solvers receive full context, and a harness whose domain solvers receive focused records.

The purpose is to measure whether decomposition and record routing improve accuracy, and at what token and latency cost. A harness advantage is a hypothesis, not an assumption. This is not a research-paper reproduction or a customer benchmark.

## Experiment

- 50 independent fictional order worlds: 25 primary + 25 confirmation.
- 3 separate pilot examples, excluded from the scored results.
- Same Databricks-hosted Qwen3 Next Instruct endpoint and temperature 0 in every arm.
- One baseline call versus five calls per harness (planner, pricing, fulfillment, charges, synthesis).
- JSON Schema output for all calls; no answer repair or correctness-based retries.
- Independent Decimal and integer-cent calculations validate the expected answers.
- Complete prompts, responses, intermediate outputs, usage and timing are saved.

Read the [protocol](docs/protocol.md), [pilot history](docs/pilot-history.md), and [results](results/main_v1/report.md). The short [blog draft](docs/blog.md) explains the findings and limitations. Result links will be populated when execution completes.

## Run on Databricks Free Edition

1. Clone or download this repository. Create a Git folder in your Databricks workspace, or upload the source and data files. Keep the directory layout intact. The repository contains no credentials.
2. Open `notebooks/run_experiment.py` as a Databricks notebook and select serverless compute.
3. If `databricks-sdk` is unavailable, install `requirements.txt` in the notebook environment. Authentication uses the current notebook identity through `WorkspaceClient()`.
4. Run with widgets `dataset=pilot`, `output_name=my_pilot`, and the available `model` endpoint. This costs quota; it does not deploy a new model.
5. Run with `dataset=examples`, `output_name=my_evaluation`. This runs all 50 frozen examples and three arms. Do not modify prompts or labels between primary and confirmation examples.
6. The notebook writes `outputs/<output_name>/` containing config, runtime metadata, raw calls, predictions, CSV, JSON summary and Markdown report. Re-run with the same output name to resume completed arm observations. Code/data/config changes require a new output name.

Availability and usage quotas vary in Free Edition. If quota or access interrupts the notebook, preserve its outputs and resume once access returns. See [official Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).

### Optional CLI upload/download

Authenticate the Databricks CLI using OAuth in your own environment. Then:

```bash
python scripts/workspace_sync.py upload --workspace /Users/YOUR_USER/llm-harness-databricks --profile YOUR_PROFILE
python scripts/workspace_sync.py download --workspace /Users/YOUR_USER/llm-harness-databricks --profile YOUR_PROFILE --run my_evaluation
```

The upload command creates the source/data folders and imports the runner notebook. Downloaded outputs go under `results/`. CLI and notebook authentication are separate; signing into the browser alone does not necessarily authenticate the CLI.

## Local validation and analysis

No live model calls are needed for these checks:

```bash
python -m unittest discover -s tests -v
python report.py results/main_v1
```

`python scripts/generate_data.py` regenerates the deterministic dataset and manifest. Avoid regenerating or editing data during an active evaluation. The recorded hashes must match the published files.

## Files

| File | Purpose |
|---|---|
| `scenario.py` | Synthetic worlds, source-record routing, Decimal oracle |
| `llm_client.py` | Unified Databricks client, structured output schemas, logging |
| `baseline.py` | Full-context single-call baseline |
| `harness.py` | Planner, sequential domain calls, synthesis |
| `evaluate.py` | Frozen configuration, scoring and resumable checkpoints |
| `report.py` | Paired statistics and comparison reports |
| `notebooks/run_experiment.py` | Databricks serverless entry point |
| `tests/` | Boundary cases, independent label audit, orchestration and resume checks |

## Interpretation

The focused arm includes engineered relational record selection. The experiment measures this system design alongside decomposition; it does not isolate context length from routing quality. Questions share a generator, use one model and one run per arm, and do not establish production reliability. Inspect failures and costs alongside accuracy before adapting the approach.

Current API references: [structured outputs](https://docs.databricks.com/aws/en/machine-learning/model-serving/structured-outputs), [supported models](https://docs.databricks.com/aws/en/machine-learning/foundation-model-apis/supported-models).
