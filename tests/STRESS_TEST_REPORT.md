# Stress Test Baseline Report

Generated: 2026-05-02T17:10:26.087827+00:00

## Baseline Results

### Threshold 1 - Metric Overlap
- **Status:** PASS
- **Metric overlap rate:** 0.0% of rounds
- **Threshold:** ≤ 30%
- **Details:** 0 of 50 rounds have metric overlap ≥ 1

### Threshold 2 - Judge Score Variance
- **Status:** FAIL
- **Min variance (5-round window):** 0.0 points
- **Threshold:** ≥ 5.0 points
- **Interpretation:** Judge should differentiate argument quality across rounds

### Threshold 3 - JSON Parse Failures
- **Status:** PASS
- **Parse failure rate:** 0.0% of rounds
- **Threshold:** ≤ 10%
- **Details:** 0 of 50 rounds had JSON errors

### Threshold 4 - Conviction Delta Progression
- **Status:** PASS
- **Average |conviction_delta|:** 32.84 points per round
- **Threshold:** ≥ 3.0 points
- **Interpretation:** Judge verdicts should meaningfully separate Bull from Bear

## Overall Status

- **Total Thresholds Passed:** 3/4
- **Critical Failures:** See above

## Failure Modes Identified

- **Judge Anchoring:** Judge scores show insufficient variance across consecutive rounds

## Market Phase Performance

- **Bull Phase (Rounds 1-20):** 20 rounds, Bull win rate: 5%
- **Bear Phase (Rounds 21-40):** 20 rounds, Bear win rate: 30%
- **Choppy Phase (Rounds 41-50):** 10 rounds

## Next Steps

1. Review identified failure modes in detail
2. Reference specific round numbers where failures clustered
3. Execute targeted fixes for each failure mode
4. Re-run stress test with fixes applied
5. Compare new results against this baseline

## Data Location

- SQLite results: `utils/db/debate.db` → `stress_test_results` table
- CSV export: `tests/stress_test_baseline.csv`
- This report: `tests/STRESS_TEST_REPORT.md`

## Post-Fix Results

Validation runs were executed after the prompt and conviction-update changes. The validation harness stored 20 rows per run in `stress_test_validation` and recorded conviction history rows for the same sessions.

- Validation run `validation-run-2`: overlap rate 100.0%, Judge variance 0.0, JSON failure rate 0.0%, average conviction delta 1.00, Bull first reached 70 at round None.
- Validation run `validation-run-3`: overlap rate 100.0%, Judge variance 0.0, JSON failure rate 0.0%, average conviction delta 0.00, Bull first reached 70 at round None.
- Validation run `validation-run-4`: overlap rate 100.0%, Judge variance 0.0, JSON failure rate 0.0%, average conviction delta 0.00, Bull first reached 70 at round None.

## Manual Audit Results

I reviewed the stored validation arguments and Judge reasoning from the validation runs. The qualitative audit shows a systematic issue: Bull and Bear arguments remain too generic, often failing to cite distinct metrics, and the Judge reasoning remains repetitive in low-differentiation rounds.

### Bull Arguments

- Round 1: Domain plausibility is mixed; the argument is bullish but too generic. Specificity is weak, with fewer than 2 verifiable figures in the argument text. Logical chain is mostly absent.
- Round 3: Domain plausibility is acceptable, but the argument still reads like a fallback summary rather than a thesis. Specific figures are sparse, and the causal link from data to direction is not explicit.
- Round 5: The argument cites numbers, but the narrative does not clearly connect them to bullish pressure. Consistency with the synthetic snapshot is only partially verifiable.
- Round 7: Stronger numerical presence than earlier rounds, but the reasoning remains shallow. The argument still lacks a clear causal chain.
- Round 9: Specificity remains below the target average of 2 figures per argument. Domain plausibility is acceptable, but not compelling.
- Round 11: The text looks mechanically generated and largely threshold-driven. Logical chain is missing.
- Round 13: Numbers appear closer to the snapshot values, but the argument still does not distinguish primary vs secondary metrics.

### Bear Arguments

- Round 2: Domain plausibility is reasonable, but the argument is overly repetitive. Specificity is low and the logical chain is weak.
- Round 4: The argument mentions numbers, but the thesis is not well tied to them. Cross-checking shows no clear mismatch, but the structure is generic.
- Round 6: Good numeric density, but the bear thesis is still expressed as a list of observations rather than a causal argument.
- Round 8: The reasoning is shallow and reads like a template reuse. Specificity is acceptable, but the chain from metrics to bearish outcome is underdeveloped.
- Round 10: Consistency with the snapshot is okay, but the argument lacks domain nuance and does not prioritize the strongest bearish indicators.
- Round 12: The structure is again formulaic. No obvious numeric mismatch, but the argument is not persuasive.
- Round 14: Better than earlier rounds on specificity, but still too terse to demonstrate a strong analytical chain.

### Judge Reasoning

- Round 15: The reasoning is concise and directionally clear, but it does not show enough sensitivity to relative evidence quality. It summarizes the outcome without differentiating why one side should win by a larger margin.

### Pattern Summary

- Systematic pattern 1: Both agents continue to reuse broad market descriptors instead of tightly separating the strongest bullish and bearish signals.
- Systematic pattern 2: Specific figures are present in some rounds, but the average is still below the target of at least 2 per argument when measured manually.
- Systematic pattern 3: Judge commentary is coherent but still not sufficiently diagnostic when the arguments differ in strength.
