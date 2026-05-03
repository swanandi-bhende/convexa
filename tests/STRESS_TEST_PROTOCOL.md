# Stress Test Protocol: 50-Round Evaluation

## Measurement Columns

Each of the 50 rounds will be evaluated and recorded in `stress_test_results` SQLite table with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| round_number | int | Round identifier (1-50) |
| market_condition | str | Market phase: "bull" (1-20), "bear" (21-40), or "choppy" (41-50) |
| bull_argument_text | str | Full bullish argument from Bull agent |
| bear_argument_text | str | Full bearish argument from Bear agent |
| bull_metrics_cited | str (JSON list) | List of metric strings cited by Bull |
| bear_metrics_cited | str (JSON list) | List of metric strings cited by Bear |
| metric_overlap_count | int | Count of metrics appearing in both arguments |
| bull_json_valid | bool | Whether Bull output parsed as valid JSON |
| bear_json_valid | bool | Whether Bear output parsed as valid JSON |
| judge_bull_score | int | Judge's score for Bull (0-100) |
| judge_bear_score | int | Judge's score for Bear (0-100) |
| judge_winner | str | Judge's verdict ("bull" or "bear") |
| judge_reasoning | str | Judge's rationale for verdict |
| conviction_delta | float | Absolute score gap for the round (|judge_bull_score - judge_bear_score|) |
| conviction_delta_from_prev | float | Change in the round score gap relative to the previous round |
| bull_confidence | int | Bull agent's reported confidence (0-100) |
| bear_confidence | int | Bear agent's reported confidence (0-100) |
| qualitative_notes | str | Any anomalies or unusual observations |
| timestamp | str | ISO timestamp of round completion |
| groq_latency_ms | float | Milliseconds for LLM inference |

## Failure Thresholds (Defined Before Seeing Data)

These thresholds are set **before** running any rounds to prevent post-hoc rationalization.

### Threshold 1: Metric Overlap
**Failure Criterion:** If metric overlap exceeds 1 metric in more than 30% of rounds, this is a failure.
- **Measurement:** Count rounds where `metric_overlap_count >= 1`
- **Pass:** ≤ 30% of rounds have overlap ≥ 1 metric
- **Fail:** > 30% of rounds have overlap ≥ 1 metric
- **Interpretation:** Bull and Bear should argue from distinct metric perspectives to show complementary market analysis

### Threshold 2: Judge Score Variance (Anchoring)
**Failure Criterion:** If Judge scores vary by less than 5 points across any 5 consecutive rounds, this is a failure.
- **Measurement:** For each sliding 5-round window, compute max(judge_bull_score) - min(judge_bull_score) and separately for bear
- **Pass:** All 5-round windows show variance ≥ 5 points in both bull AND bear scores
- **Fail:** Any 5-round window shows variance < 5 points in either bull OR bear scores
- **Interpretation:** Judge should differentiate quality across rounds, not mechanically assign 52/48 every round

### Threshold 3: JSON Parse Failures
**Failure Criterion:** If JSON parse failures occur in more than 10% of rounds, this is a failure.
- **Measurement:** Count rounds where `bull_json_valid == false` OR `bear_json_valid == false`
- **Pass:** ≤ 10% of rounds have parse failures
- **Fail:** > 10% of rounds have parse failures
- **Interpretation:** Agent outputs must be reliably parseable for production use

### Threshold 4: Conviction Delta Progression
**Failure Criterion:** If average conviction delta movement per round falls below 3 points, this is a failure.
- **Measurement:** Compute absolute value of `conviction_delta_from_prev` for each round after the first, then average across the run
- **Pass:** Average |conviction_delta_from_prev| ≥ 3.0 points
- **Fail:** Average |conviction_delta_from_prev| < 3.0 points
- **Interpretation:** Judge verdicts should move conviction enough from one round to the next to avoid a flat-line debate

## Summary Report Format

At the end of the run, print:

```
STRESS TEST BASELINE RESULTS
============================
Round Interval: ROUND_INTERVAL_SECONDS = 5 seconds
Total Time: ~250-300 seconds (accounting for Groq latency)
Data Source: Real Groq API (llama3-70b-8192)

FAILURE MODE METRICS
====================

[FAIL/PASS] Threshold 1 - Metric Overlap
  Metric overlap rate: {overlap_pct:.1f}% of rounds
  Threshold: ≤ 30%
  Status: {'PASS' if overlap_pct <= 30 else 'FAIL'}

[FAIL/PASS] Threshold 2 - Judge Score Variance
  Min variance found in any 5-round window: {min_variance:.1f} points
  Threshold: ≥ 5.0 points
  Status: {'PASS' if min_variance >= 5.0 else 'FAIL'}

[FAIL/PASS] Threshold 3 - JSON Parse Failures
  Parse failure rate: {parse_fail_pct:.1f}% of rounds
  Threshold: ≤ 10%
  Status: {'PASS' if parse_fail_pct <= 10 else 'FAIL'}

[FAIL/PASS] Threshold 4 - Conviction Delta Progression
  Average |conviction_delta_from_prev|: {avg_conviction:.2f} points per round
  Threshold: ≥ 3.0 points
  Status: {'PASS' if avg_conviction >= 3.0 else 'FAIL'}

MARKET CONDITION SUMMARY
========================
Phase 1 (Rounds 1-20) - Bull Dominant: {bull_phase_metrics}
Phase 2 (Rounds 21-40) - Bear Dominant: {bear_phase_metrics}
Phase 3 (Rounds 41-50) - Choppy: {choppy_phase_metrics}

FAILURE MODES IDENTIFIED
========================
{identified_failures}
```

## Notes

- Do NOT interrupt the test or fix issues while it is running
- Write one record to the SQLite table immediately after each round completes
- Export the full table to CSV at `/tests/stress_test_baseline.csv` after completion
- Keep the STRESS_TEST_REPORT.md updated with baseline metrics before attempting any fixes
