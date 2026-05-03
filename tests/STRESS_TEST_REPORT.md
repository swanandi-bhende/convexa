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

Validation run ID: validation-20260503-064426

- Metric overlap rate: 15.0% (PASS)
- Judge 5-round variance minimum: 0.0 (FAIL)
- JSON parse failure rate: 40.0% (FAIL)
- Average conviction delta from previous round: 2.50 (FAIL)
- Bull first reached 70 at round: 2

## Manual Audit Results

- Bull rounds sampled: 1, 3, 5, 7, 9, 11, 13
- Bear rounds sampled: 2, 4, 6, 8, 10, 12, 14
- Judge reasoning sampled: round 15
- Audit note: the script records the sampled arguments in SQLite; review should focus on numeric specificity, metric alignment, and whether the cited numbers match the underlying snapshot values for those rounds.
