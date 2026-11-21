# Calibration history

Five separate pilot questions use IDs 9000–9004 and a seed independent of evaluation. The 50 evaluation IDs 1000–1049 have not been queried during calibration.

1. **Pilot v1:** one current stock record, two confirmed receipts, 12/30 unrelated records per table. Both approaches scored 5/5. This exposed a ceiling rather than an accuracy advantage.
2. **Pilot v2:** added clearly marked archived stock snapshots and cancelled receipts; increased unrelated records to 32/64 per table. Both approaches again scored 5/5. Arithmetic and the final one-integer task stayed unchanged.
3. **Pilot v3:** increased unrelated records to 128/256 per table without changing target facts, arithmetic, prompts or model. Baseline scored 4/5 and harness scored 5/5. This was the final calibration. Regardless of its score direction, the 50-question evaluation uses these frozen settings; no further tuning is allowed against evaluation outcomes.

The pilot versions, raw prompts/responses, configuration and data are retained. The pilot-v1 source snapshot was reformatted after execution without semantic changes; its config retains the original execution hashes. Pilot-v2 has a source/data archive. Neither pilot is included in evaluation accuracy. The final experiment has its own frozen source/data manifest and independently checked answers.

A baseline call includes a concise calculation, just as each harness call does. There are two arms, one exact-integer accuracy metric, and no invoice or secondary endpoint. The harness has engineered record filtering and three calls, so any advantage describes that combined system design.
