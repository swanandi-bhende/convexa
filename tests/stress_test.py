"""
Stress Test Runner: 50-round evaluation of Bull, Bear, and Judge agents.

Runs three market phases:
- Rounds 1-20: Bull-dominant market conditions
- Rounds 21-40: Bear-dominant market conditions  
- Rounds 41-50: Choppy/sideways market conditions

Uses REAL Groq API to evaluate LLM output quality. Writes one evaluation record
to stress_test_results table per round. At completion, produces a baseline report
with pass/fail status against four failure thresholds.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import bear_agent, bull_agent, judge_agent
from tests.fixtures.market_data_factory import (
    create_bull_market_snapshot,
    create_bear_market_snapshot,
    create_choppy_market_snapshot,
)
from utils.db_manager import init_database, insert_stress_test_result, get_all_stress_test_results
from utils.market_data import MarketSnapshot

load_dotenv()

ROUND_INTERVAL_SECONDS = 5
TOKEN_PAIR = "ETH/USDC"


def _normalize_metric(metric: Any) -> str:
    metric_text = str(metric).strip().lower()
    if not metric_text:
        return ""
    if ":" in metric_text:
        metric_text = metric_text.split(":", 1)[0].strip()
    return metric_text


def _extract_metrics_from_argument(argument_text: str, key_metrics: list[Any] | None = None) -> list[str]:
    metrics: list[str] = []

    for metric in key_metrics or []:
        normalized = _normalize_metric(metric)
        if normalized and normalized not in metrics:
            metrics.append(normalized)

    if metrics:
        return metrics

    import re

    for match in re.findall(r"(\w+(?:_\w+)*)\s*:\s*([+-]?\d+(?:\.\d+)?[%]?)", argument_text, re.IGNORECASE):
        normalized = _normalize_metric(match[0])
        if normalized and normalized not in metrics:
            metrics.append(normalized)

    if metrics:
        return metrics

    for match in re.findall(r"\[([^\]]+)\]", argument_text):
        normalized = _normalize_metric(match)
        if normalized and normalized not in metrics:
            metrics.append(normalized)

    return metrics or ["qualitative_only"]


def _parse_status(agent_module: Any) -> str:
    status = getattr(agent_module, "LAST_GENERATION_STATUS", {})
    if not isinstance(status, dict):
        return "unknown"
    return str(status.get("status") or "unknown")


def _parse_valid(agent_module: Any) -> bool:
    status = getattr(agent_module, "LAST_GENERATION_STATUS", {})
    if not isinstance(status, dict):
        return False
    return bool(status.get("parse_valid", False))


def _calculate_metric_overlap(bull_metrics: list[str], bear_metrics: list[str]) -> int:
    """Count metrics appearing in both argument lists."""
    bull_set = set(m.lower().strip() for m in bull_metrics)
    bear_set = set(m.lower().strip() for m in bear_metrics)
    overlap = bull_set & bear_set
    # Don't count "qualitative_only" as an overlap
    overlap.discard("qualitative_only")
    return len(overlap)


def _is_valid_json(text: str, schema: type) -> bool:
    """Check if text is valid JSON matching the given schema."""
    try:
        parsed = json.loads(text)
        # Try to validate with pydantic if possible
        if hasattr(schema, "model_validate"):
            schema.model_validate(parsed)
        return True
    except (json.JSONDecodeError, ValueError, TypeError):
        return False


def _judge_score_variance(results: list[dict[str, Any]]) -> float:
    if len(results) < 5:
        return 0.0

    min_window_spread = float("inf")
    for start_index in range(len(results) - 4):
        window = results[start_index : start_index + 5]
        bull_scores = [int(row["judge_bull_score"]) for row in window]
        bear_scores = [int(row["judge_bear_score"]) for row in window]
        min_window_spread = min(
            min_window_spread,
            float(max(bull_scores) - min(bull_scores)),
            float(max(bear_scores) - min(bear_scores)),
        )

    return 0.0 if min_window_spread == float("inf") else min_window_spread


def run_stress_test() -> None:
    """Run 50 synthetic rounds and write the baseline evaluation artifacts."""
    print("\n" + "=" * 80)
    print("STRESS TEST RUNNER - 50 ROUNDS EVALUATION")
    print("=" * 80)
    print(f"Round interval: {ROUND_INTERVAL_SECONDS} seconds")
    print("Expected runtime: ~250-300 seconds including Groq latency")
    print("Data source: Real Groq API")
    print("=" * 80 + "\n")

    init_database()

    previous_conviction_gap: float | None = None
    for round_number in range(1, 51):
        round_start = time.time()

        if round_number <= 20:
            market_condition = "bull"
            intensity = 0.5 + (round_number / 20.0) * 0.5
            snapshot = create_bull_market_snapshot(round_number, intensity)
        elif round_number <= 40:
            market_condition = "bear"
            intensity = 0.5 + ((round_number - 20) / 20.0) * 0.5
            snapshot = create_bear_market_snapshot(round_number, intensity)
        else:
            market_condition = "choppy"
            snapshot = create_choppy_market_snapshot(round_number)

        print(f"\n[ROUND {round_number:02d}] {market_condition.upper()} phase")

        bull_result = bull_agent.generate_bull_argument(snapshot, round_number)
        bear_result = bear_agent.generate_bear_argument(snapshot, round_number)
        judge_result = judge_agent.score_round(
            bull_argument_dict=bull_result,
            bear_argument_dict=bear_result,
            round_number=round_number,
            market_snapshot=snapshot,
        )

        bull_json_valid = _parse_valid(bull_agent)
        bear_json_valid = _parse_valid(bear_agent)
        bull_status = _parse_status(bull_agent)
        bear_status = _parse_status(bear_agent)
        judge_status = _parse_status(judge_agent)

        bull_argument = str(bull_result.get("argument", ""))
        bear_argument = str(bear_result.get("argument", ""))
        bull_metrics = _extract_metrics_from_argument(bull_argument, bull_result.get("keyMetrics", []))
        bear_metrics = _extract_metrics_from_argument(bear_argument, bear_result.get("keyMetrics", []))
        metric_overlap = _calculate_metric_overlap(bull_metrics, bear_metrics)

        judge_bull_score = int(judge_result.get("bullScore", 50))
        judge_bear_score = int(judge_result.get("bearScore", 50))
        judge_winner = str(judge_result.get("winner", "bull" if judge_bull_score >= judge_bear_score else "bear"))
        judge_reasoning = str(judge_result.get("reasoning", ""))
        judge_gap = float(abs(judge_bull_score - judge_bear_score))
        conviction_delta_from_prev = (
            judge_gap - previous_conviction_gap if previous_conviction_gap is not None else None
        )
        previous_conviction_gap = judge_gap

        bull_confidence = int(bull_result.get("confidence", 50))
        bear_confidence = int(bear_result.get("confidence", 50))
        groq_latency_ms = (time.time() - round_start) * 1000.0

        qualitative_notes = "; ".join(
            note
            for note in [
                f"bull_parse={bull_status}",
                f"bear_parse={bear_status}",
                f"judge_parse={judge_status}",
                "metric_overlap" if metric_overlap > 0 else "",
            ]
            if note
        )

        print(
            f"  Bull {judge_bull_score:3d} | Bear {judge_bear_score:3d} | "
            f"Winner: {judge_winner.upper():4s} | Overlap: {metric_overlap} | "
            f"Bull JSON: {bull_json_valid} | Bear JSON: {bear_json_valid}"
        )

        insert_stress_test_result(
            round_number=round_number,
            market_condition=market_condition,
            bull_argument_text=bull_argument,
            bear_argument_text=bear_argument,
            bull_metrics_cited=bull_metrics,
            bear_metrics_cited=bear_metrics,
            metric_overlap_count=metric_overlap,
            bull_json_valid=bull_json_valid,
            bear_json_valid=bear_json_valid,
            judge_bull_score=judge_bull_score,
            judge_bear_score=judge_bear_score,
            judge_winner=judge_winner,
            judge_reasoning=judge_reasoning,
            conviction_delta=judge_gap,
            conviction_delta_from_prev=conviction_delta_from_prev,
            bull_confidence=bull_confidence,
            bear_confidence=bear_confidence,
            qualitative_notes=qualitative_notes,
            groq_latency_ms=groq_latency_ms,
        )

        if round_number < 50:
            elapsed = time.time() - round_start
            sleep_for = max(0.0, ROUND_INTERVAL_SECONDS - elapsed)
            if sleep_for > 0:
                time.sleep(sleep_for)

    db_results = get_all_stress_test_results()
    overlap_rounds = sum(1 for row in db_results if int(row["metric_overlap_count"]) >= 1)
    overlap_pct = (overlap_rounds / len(db_results) * 100.0) if db_results else 0.0
    judge_variance = _judge_score_variance(db_results)
    parse_failures = sum(1 for row in db_results if not row["bull_json_valid"] or not row["bear_json_valid"])
    parse_fail_pct = (parse_failures / len(db_results) * 100.0) if db_results else 0.0

    conviction_deltas = [abs(float(row["conviction_delta_from_prev"])) for row in db_results if row["conviction_delta_from_prev"] is not None]
    avg_conviction_delta = sum(conviction_deltas) / len(conviction_deltas) if conviction_deltas else 0.0

    overlap_pass = overlap_pct <= 30.0
    variance_pass = judge_variance >= 5.0
    parse_pass = parse_fail_pct <= 10.0
    conviction_pass = avg_conviction_delta >= 3.0

    bull_phase = [row for row in db_results if row["market_condition"] == "bull"]
    bear_phase = [row for row in db_results if row["market_condition"] == "bear"]
    choppy_phase = [row for row in db_results if row["market_condition"] == "choppy"]

    print("\n" + "=" * 80)
    print("STRESS TEST BASELINE RESULTS")
    print("=" * 80)
    print(f"Total rounds executed: {len(db_results)}")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    print()
    print("FAILURE MODE METRICS")
    print("-" * 80)
    print(f"[{'PASS' if overlap_pass else 'FAIL'}] Threshold 1 - Metric Overlap")
    print(f"  Metric overlap rate: {overlap_pct:.1f}% of rounds")
    print(f"  Threshold: ≤ 30%")
    print(f"  Status: {'PASS' if overlap_pass else 'FAIL'}")
    print(f"  Failure rounds: {[row['round_number'] for row in db_results if int(row['metric_overlap_count']) >= 1]}")
    print()
    print(f"[{'PASS' if variance_pass else 'FAIL'}] Threshold 2 - Judge Score Variance")
    print(f"  Min variance in any 5-round window: {judge_variance:.1f} points")
    print(f"  Threshold: ≥ 5.0 points")
    print(f"  Status: {'PASS' if variance_pass else 'FAIL'}")
    print()
    print(f"[{'PASS' if parse_pass else 'FAIL'}] Threshold 3 - JSON Parse Failures")
    print(f"  Parse failure rate: {parse_fail_pct:.1f}% of rounds")
    print(f"  Threshold: ≤ 10%")
    print(f"  Status: {'PASS' if parse_pass else 'FAIL'}")
    print(f"  Failure rounds: {[row['round_number'] for row in db_results if not row['bull_json_valid'] or not row['bear_json_valid']]}")
    print()
    print(f"[{'PASS' if conviction_pass else 'FAIL'}] Threshold 4 - Conviction Delta Progression")
    print(f"  Average |conviction_delta_from_prev|: {avg_conviction_delta:.2f} points per round")
    print(f"  Threshold: ≥ 3.0 points")
    print(f"  Status: {'PASS' if conviction_pass else 'FAIL'}")

    print("\n" + "-" * 80)
    print("MARKET CONDITION SUMMARY")
    print("-" * 80)
    print(f"Bull Phase (Rounds 1-20): {len(bull_phase)} rounds, Bull win rate: {100 * sum(1 for row in bull_phase if row['judge_winner'] == 'bull') // max(1, len(bull_phase))}%")
    print(f"Bear Phase (Rounds 21-40): {len(bear_phase)} rounds, Bear win rate: {100 * sum(1 for row in bear_phase if row['judge_winner'] == 'bear') // max(1, len(bear_phase))}%")
    print(f"Choppy Phase (Rounds 41-50): {len(choppy_phase)} rounds")

    csv_path = PROJECT_ROOT / "tests" / "stress_test_baseline.csv"
    import csv

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        if db_results:
            writer = csv.DictWriter(handle, fieldnames=list(db_results[0].keys()))
            writer.writeheader()
            for row in db_results:
                csv_row = dict(row)
                csv_row["bull_metrics_cited"] = json.dumps(csv_row["bull_metrics_cited"])
                csv_row["bear_metrics_cited"] = json.dumps(csv_row["bear_metrics_cited"])
                writer.writerow(csv_row)

    report_path = PROJECT_ROOT / "tests" / "STRESS_TEST_REPORT.md"
    report_content = f"""# Stress Test Baseline Report

Generated: {datetime.now(UTC).isoformat()}

## Baseline Results

### Threshold 1 - Metric Overlap
- **Status:** {'PASS' if overlap_pass else 'FAIL'}
- **Metric overlap rate:** {overlap_pct:.1f}% of rounds
- **Threshold:** ≤ 30%

### Threshold 2 - Judge Score Variance
- **Status:** {'PASS' if variance_pass else 'FAIL'}
- **Min variance (5-round window):** {judge_variance:.1f} points
- **Threshold:** ≥ 5.0 points

### Threshold 3 - JSON Parse Failures
- **Status:** {'PASS' if parse_pass else 'FAIL'}
- **Parse failure rate:** {parse_fail_pct:.1f}% of rounds
- **Threshold:** ≤ 10%

### Threshold 4 - Conviction Delta Progression
- **Status:** {'PASS' if conviction_pass else 'FAIL'}
- **Average |conviction_delta_from_prev|:** {avg_conviction_delta:.2f} points per round
- **Threshold:** ≥ 3.0 points

## Overall Status

- **Total Thresholds Passed:** {sum([overlap_pass, variance_pass, parse_pass, conviction_pass])}/4
- **Critical Failures:** {'None' if all([overlap_pass, variance_pass, parse_pass, conviction_pass]) else 'See failure modes above'}

## Failure Modes Identified

- Metric overlap rate: {overlap_pct:.1f}%
- Judge min 5-round variance: {judge_variance:.1f}
- JSON parse failure rate: {parse_fail_pct:.1f}%
- Average conviction delta from previous round: {avg_conviction_delta:.2f}

## Market Phase Performance

- Bull Phase (Rounds 1-20): {len(bull_phase)} rounds, Bull win rate: {100 * sum(1 for row in bull_phase if row['judge_winner'] == 'bull') // max(1, len(bull_phase))}%
- Bear Phase (Rounds 21-40): {len(bear_phase)} rounds, Bear win rate: {100 * sum(1 for row in bear_phase if row['judge_winner'] == 'bear') // max(1, len(bear_phase))}%
- Choppy Phase (Rounds 41-50): {len(choppy_phase)} rounds

## Data Location

- SQLite results: `utils/db/debate.db` → `stress_test_results`
- CSV export: `tests/stress_test_baseline.csv`
- This report: `tests/STRESS_TEST_REPORT.md`
"""

    report_path.write_text(report_content, encoding="utf-8")
    print("\n" + "=" * 80)
    print("STRESS TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_stress_test()
