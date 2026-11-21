# Two-approach fulfillment experiment: results

**The accuracy hypothesis was not established.** On 50 fresh questions, the full-context LLM answered 45 correctly (90%) and the focused harness answered 46 correctly (92%). The observed gain was 2 percentage points, with a paired-bootstrap 95% interval from -6 to +10 points. There were 3 harness wins, 2 losses and 45 ties; exact paired p=1.0.

There is one metric: whether the single deliverable-quantity integer is exactly correct. No partial-answer or invoice metric is involved. All 100 scored outputs were valid JSON with an integer answer.

| Approach | Correct / 50 | Accuracy | Model calls | Total input + output tokens | Median seconds per question |
|---|---:|---:|---:|---:|---:|
| One full-context call | 45/50 | 90% | 50 | 1,454,925 | 2.42 |
| Focused three-call harness | 46/50 | 92% | 150 | 95,796 | 3.23 |

The harness used **93.4% fewer tokens**, while taking more calls and about 34% higher median elapsed time. No dollar costs were inferred from Free Edition usage. Timing includes orchestration and log writes from a single serial run, not a serving-throughput benchmark. The accuracy difference remains uncertain; this does not establish non-inferiority or equivalence either.

## What was tested

All model calls ran on Databricks Free Edition serverless compute using `databricks-qwen3-next-80b-a3b-instruct`, temperature 0 and a 1,200-token output limit per call. Each approach could produce a concise calculation before its answer. The baseline received the complete packet; the harness selected current inventory and confirmed receipts by public metadata, then used stock, delivery-eligibility and final-quantity calls. Filtering and additional inference are part of the treatment.

The final dataset contains one product per question, two confirmed receipts, eight archived inventory snapshots, two cancelled receipts, same-product stock at another warehouse and 128 or 256 unrelated records per table. The two packet sizes preserve the same target complexity. Baseline input averaged 28,941 tokens per question, compared with about 1,781 input tokens across all three harness calls.

Expected answers were checked with independent Python logic and hand-calculated edge cases. Seven tests passed on Databricks. The final audit verified 50 questions, 100 unique question/approach observations, 200 successful model calls, one provider model, matching frozen hashes, and no ground-truth keys in prompts. The evaluation and audit jobs both succeeded.

## A win and a loss

- **evaluation-1033:** expected 54. Baseline answered 55 after counting a receipt arriving on day 2 even though the dispatch cutoff was day 1. The harness excluded that receipt and returned 54.
- **evaluation-1016:** expected 0. Baseline correctly excluded receipts after the day-0 cutoff. The harness's delivery step counted a day-2 receipt and returned 20. Shorter context did not prevent the same class of error.

Both cases, including the calculations and source records, are retained in the raw predictions. They illustrate why a three-win/two-loss comparison cannot support a strong accuracy claim.

## Boundaries

The separate pilot was calibrated twice because both approaches initially scored 5/5. Final settings were frozen before any of the 50 evaluation questions were sent to the model. See [calibration history](CALIBRATION.md); pilots are excluded from reported accuracy. No tuning or rescoring followed the evaluation.

This is one model, one synthetic generator and one observation per approach/question. Both arms achieved 90% or higher accuracy. A larger independent evaluation would be needed to assess a small accuracy difference. The defensible finding is a large token reduction with an uncertain accuracy difference on this dataset—not proof of an accuracy advantage.

## Inspect the evidence

- [Complete per-question report](results/main_v1/report.md)
- [CSV comparison](results/main_v1/comparison.csv)
- [Raw model calls](results/main_v1/calls.jsonl) and [predictions](results/main_v1/predictions.jsonl)
- [Summary](results/main_v1/summary.json), [configuration](results/main_v1/config.json), [runtime](results/main_v1/runtime.json), and [final audit](results/main_v1/audit.json)
- [Frozen source/data manifest](data/frozen_manifest.json) and [pilot audit archive](results/pilot_audit.zip)
