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

from agents.bull_agent import generate_bull_argument
from agents.bear_agent import generate_bear_argument
from agents.judge_agent import score_round
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


def _extract_metrics_from_argument(argument_text: str) -> list[str]:
    """
    Extract metric mentions from argument text.
    Looks for patterns like "metric_name: value" or metric names in brackets.
    """
    metrics = []
    
    # Look for patterns like "[metric_name]" or "metric_name: value"
    import re
    
    # Patterns to match metric names and values
    metric_patterns = [
        r'(\w+(?:_\w+)*)\s*:\s*([+-]?\d+(?:\.\d+)?[%]?)',  # metric: value
        r'\[([^\]]+)\]',  # [metric_name]
        r'(price_change|volume_delta|inflow|outflow|lp_net_flow|funding_rate|large_inflow|large_outflow|tvl)',  # specific metrics
    ]
    
    for pattern in metric_patterns:
        matches = re.findall(pattern, argument_text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                # Multi-group match
                metric_str = match[0] if match[0] else match[1] if len(match) > 1 else ""
            else:
                metric_str = match
            
            if metric_str and metric_str not in metrics:
                metrics.append(metric_str.lower())
    
    # If no metrics found via regex, at least flag that argument was processed
    if not metrics:
        metrics = ["qualitative_only"]
    
    return list(set(metrics))  # Remove duplicates


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


def run_stress_test() -> None:
    """Run 50-round stress test and collect baseline data."""
    print("\n" + "=" * 80)
    print("STRESS TEST RUNNER - 50 ROUNDS EVALUATION")
    print("=" * 80)
    print(f"Round interval: {ROUND_INTERVAL_SECONDS} seconds")
    print(f"Expected runtime: ~250-300 seconds (accounting for Groq latency)")
    print(f"Data source: Real Groq API (llama3-70b-8192)")
    print("=" * 80 + "\n")
    
    init_database()
    
    previous_conviction_delta = None
    all_results = []
    
    for round_num in range(1, 51):
        round_start = time.time()
        
        # Determine market condition and create snapshot
        if round_num <= 20:
            market_condition = "bull"
            intensity = 0.5 + (round_num / 20) * 0.5  # Increasing intensity
            snapshot = create_bull_market_snapshot(round_num, intensity)
            print(f"\n[ROUND {round_num:02d}] Bull-dominant market (Phase 1)")
        elif round_num <= 40:
            market_condition = "bear"
            intensity = 0.5 + ((round_num - 20) / 20) * 0.5  # Increasing intensity
            snapshot = create_bear_market_snapshot(round_num, intensity)
            print(f"\n[ROUND {round_num:02d}] Bear-dominant market (Phase 2)")
        else:
            market_condition = "choppy"
            snapshot = create_choppy_market_snapshot(round_num)
            print(f"\n[ROUND {round_num:02d}] Choppy/sideways market (Phase 3)")
        
        # Run Bull agent
        bull_start = time.time()
        bull_result = {}
        try:
            bull_result = generate_bull_argument(snapshot, round_num)
            bull_json_valid = _is_valid_json(json.dumps(bull_result), dict)
            bull_argument = bull_result.get("argument", "")
            bull_metrics = _extract_metrics_from_argument(bull_argument)
            bull_confidence = bull_result.get("confidence", 50)
        except Exception as e:
            print(f"  Bull agent failed: {e}")
            bull_json_valid = False
            bull_result = {}
            bull_argument = f"Error: {str(e)}"
            bull_metrics = ["error"]
            bull_confidence = 0
        
        # Run Bear agent
        bear_start = time.time()
        bear_result = {}
        try:
            bear_result = generate_bear_argument(snapshot, round_num)
            bear_json_valid = _is_valid_json(json.dumps(bear_result), dict)
            bear_argument = bear_result.get("argument", "")
            bear_metrics = _extract_metrics_from_argument(bear_argument)
            bear_confidence = bear_result.get("confidence", 50)
        except Exception as e:
            print(f"  Bear agent failed: {e}")
            bear_json_valid = False
            bear_result = {}
            bear_argument = f"Error: {str(e)}"
            bear_metrics = ["error"]
            bear_confidence = 0
        
        # Calculate metric overlap
        metric_overlap = _calculate_metric_overlap(bull_metrics, bear_metrics)
        
        # Run Judge agent
        judge_start = time.time()
        try:
            judge_result = score_round(
                bull_argument_dict=bull_result if bull_result else {"argument": bull_argument},
                bear_argument_dict=bear_result if bear_result else {"argument": bear_argument},
                round_number=round_num,
                market_snapshot=snapshot,
            )
            judge_bull_score = judge_result.get("bullScore", 50)
            judge_bear_score = judge_result.get("bearScore", 50)
            judge_winner = judge_result.get("winner", "bull" if judge_bull_score >= judge_bear_score else "bear")
            judge_reasoning = judge_result.get("reasoning", "")
        except Exception as e:
            print(f"  Judge agent failed: {e}")
            judge_bull_score = 50
            judge_bear_score = 50
            judge_winner = "draw"
            judge_reasoning = f"Judge error: {str(e)}"
        
        judge_end = time.time()
        groq_latency = (judge_end - judge_start) * 1000
        
        # Ensure judge_winner is valid
        if not judge_winner or judge_winner not in ("bull", "bear"):
            judge_winner = "bull" if judge_bull_score >= judge_bear_score else "bear"
        
        # Calculate conviction metrics
        conviction_delta = float(judge_bull_score - judge_bear_score)
        conviction_delta_from_prev = conviction_delta - previous_conviction_delta if previous_conviction_delta is not None else None
        previous_conviction_delta = conviction_delta
        
        # Create result record
        result = {
            "round_number": round_num,
            "market_condition": market_condition,
            "bull_argument_text": bull_argument,
            "bear_argument_text": bear_argument,
            "bull_metrics_cited": bull_metrics,
            "bear_metrics_cited": bear_metrics,
            "metric_overlap_count": metric_overlap,
            "bull_json_valid": bull_json_valid,
            "bear_json_valid": bear_json_valid,
            "judge_bull_score": judge_bull_score,
            "judge_bear_score": judge_bear_score,
            "judge_winner": judge_winner,
            "judge_reasoning": judge_reasoning,
            "conviction_delta": conviction_delta,
            "conviction_delta_from_prev": conviction_delta_from_prev,
            "bull_confidence": bull_confidence,
            "bear_confidence": bear_confidence,
            "groq_latency_ms": groq_latency,
        }
        
        # Print round summary
        winner_str = str(judge_winner).upper() if judge_winner else "DRAW"
        print(f"  Bull score: {judge_bull_score:3d} | Bear score: {judge_bear_score:3d} | Winner: {winner_str:4s}")
        print(f"  Metrics (overlap: {metric_overlap}): Bull={bull_metrics[:2]} Bear={bear_metrics[:2]}")
        print(f"  Latency: {groq_latency:.0f}ms | JSON valid: Bull={bull_json_valid} Bear={bear_json_valid}")
        
        # Store in database
        try:
            insert_stress_test_result(
                round_number=round_num,
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
                conviction_delta=conviction_delta,
                conviction_delta_from_prev=conviction_delta_from_prev,
                bull_confidence=bull_confidence,
                bear_confidence=bear_confidence,
                qualitative_notes="",
                groq_latency_ms=groq_latency,
            )
        except Exception as e:
            print(f"  Database insert failed: {e}")
        
        all_results.append(result)
        
        # Sleep between rounds (except last)
        if round_num < 50:
            elapsed = time.time() - round_start
            sleep_time = max(0, ROUND_INTERVAL_SECONDS - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    # Fetch all results from database
    print("\n" + "=" * 80)
    print("FETCHING ALL RESULTS FROM DATABASE...")
    print("=" * 80)
    
    db_results = get_all_stress_test_results()
    
    # Calculate baseline metrics
    print("\nCALCULATING BASELINE METRICS...")
    
    # Threshold 1: Metric Overlap
    overlap_rounds = sum(1 for r in db_results if r["metric_overlap_count"] >= 1)
    overlap_pct = (overlap_rounds / len(db_results)) * 100 if db_results else 0
    overlap_pass = overlap_pct <= 30
    
    # Threshold 2: Judge Score Variance
    min_variance = float('inf')
    for i in range(len(db_results) - 4):
        window = db_results[i:i+5]
        bull_scores = [r["judge_bull_score"] for r in window]
        bear_scores = [r["judge_bear_score"] for r in window]
        bull_variance = max(bull_scores) - min(bull_scores)
        bear_variance = max(bear_scores) - min(bear_scores)
        min_variance = min(min_variance, bull_variance, bear_variance)
    
    variance_pass = min_variance >= 5.0
    
    # Threshold 3: JSON Parse Failures
    parse_failures = sum(1 for r in db_results if not r["bull_json_valid"] or not r["bear_json_valid"])
    parse_fail_pct = (parse_failures / len(db_results)) * 100 if db_results else 0
    parse_pass = parse_fail_pct <= 10
    
    # Threshold 4: Conviction Delta Progression
    conviction_deltas = [abs(r["conviction_delta"]) for r in db_results]
    avg_conviction = sum(conviction_deltas) / len(conviction_deltas) if conviction_deltas else 0
    conviction_pass = avg_conviction >= 3.0
    
    # Print comprehensive baseline report
    print("\n" + "=" * 80)
    print("STRESS TEST BASELINE RESULTS")
    print("=" * 80)
    print(f"Total rounds executed: {len(db_results)}")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    print()
    
    print("FAILURE MODE METRICS")
    print("-" * 80)
    print(f"\n[{'PASS' if overlap_pass else 'FAIL'}] Threshold 1 - Metric Overlap")
    print(f"  Metric overlap rate: {overlap_pct:.1f}% of rounds (limit: ≤30%)")
    print(f"  Details: {overlap_rounds} of {len(db_results)} rounds have overlap ≥ 1 metric")
    
    print(f"\n[{'PASS' if variance_pass else 'FAIL'}] Threshold 2 - Judge Score Variance")
    print(f"  Min variance in any 5-round window: {min_variance:.1f} points (limit: ≥5.0)")
    print(f"  Interpretation: Judge should vary scores by at least 5 points across consecutive rounds")
    
    print(f"\n[{'PASS' if parse_pass else 'FAIL'}] Threshold 3 - JSON Parse Failures")
    print(f"  Parse failure rate: {parse_fail_pct:.1f}% of rounds (limit: ≤10%)")
    print(f"  Details: {parse_failures} of {len(db_results)} rounds had JSON parse errors")
    
    print(f"\n[{'PASS' if conviction_pass else 'FAIL'}] Threshold 4 - Conviction Delta Progression")
    print(f"  Average |conviction_delta|: {avg_conviction:.2f} points per round (limit: ≥3.0)")
    print(f"  Interpretation: Judge verdicts should meaningfully separate Bull from Bear")
    
    # Market phase summary
    print("\n" + "-" * 80)
    print("MARKET CONDITION SUMMARY")
    print("-" * 80)
    
    bull_phase = [r for r in db_results if r["market_condition"] == "bull"]
    bear_phase = [r for r in db_results if r["market_condition"] == "bear"]
    choppy_phase = [r for r in db_results if r["market_condition"] == "choppy"]
    
    print(f"\nPhase 1 (Bull-dominant, rounds 1-20): {len(bull_phase)} rounds")
    if bull_phase:
        bull_wins = sum(1 for r in bull_phase if r["judge_winner"] == "bull")
        print(f"  Bull won: {bull_wins}/{len(bull_phase)} rounds ({100*bull_wins//len(bull_phase)}%)")
        print(f"  Avg Bull score: {sum(r['judge_bull_score'] for r in bull_phase)/len(bull_phase):.1f}")
    
    print(f"\nPhase 2 (Bear-dominant, rounds 21-40): {len(bear_phase)} rounds")
    if bear_phase:
        bear_wins = sum(1 for r in bear_phase if r["judge_winner"] == "bear")
        print(f"  Bear won: {bear_wins}/{len(bear_phase)} rounds ({100*bear_wins//len(bear_phase)}%)")
        print(f"  Avg Bear score: {sum(r['judge_bear_score'] for r in bear_phase)/len(bear_phase):.1f}")
    
    print(f"\nPhase 3 (Choppy, rounds 41-50): {len(choppy_phase)} rounds")
    if choppy_phase:
        bull_wins = sum(1 for r in choppy_phase if r["judge_winner"] == "bull")
        bear_wins = sum(1 for r in choppy_phase if r["judge_winner"] == "bear")
        print(f"  Bull/Bear split: {bull_wins} Bull vs {bear_wins} Bear")
    
    # Export to CSV
    print("\n" + "-" * 80)
    print("EXPORTING BASELINE DATA TO CSV...")
    print("-" * 80)
    
    csv_path = PROJECT_ROOT / "tests" / "stress_test_baseline.csv"
    try:
        import csv
        with open(csv_path, "w", newline="") as f:
            if db_results:
                writer = csv.DictWriter(f, fieldnames=db_results[0].keys())
                writer.writeheader()
                # Convert lists to JSON strings for CSV
                for row in db_results:
                    csv_row = dict(row)
                    csv_row["bull_metrics_cited"] = json.dumps(csv_row["bull_metrics_cited"])
                    csv_row["bear_metrics_cited"] = json.dumps(csv_row["bear_metrics_cited"])
                    writer.writerow(csv_row)
        print(f"✓ Baseline CSV exported to: {csv_path}")
    except Exception as e:
        print(f"✗ Failed to export CSV: {e}")
    
    # Write STRESS_TEST_REPORT.md
    print("\nWRITING STRESS_TEST_REPORT.md...")
    
    report_path = PROJECT_ROOT / "tests" / "STRESS_TEST_REPORT.md"
    report_content = f"""# Stress Test Baseline Report

Generated: {datetime.now(UTC).isoformat()}

## Baseline Results

### Threshold 1 - Metric Overlap
- **Status:** {'PASS' if overlap_pass else 'FAIL'}
- **Metric overlap rate:** {overlap_pct:.1f}% of rounds
- **Threshold:** ≤ 30%
- **Details:** {overlap_rounds} of {len(db_results)} rounds have metric overlap ≥ 1

### Threshold 2 - Judge Score Variance
- **Status:** {'PASS' if variance_pass else 'FAIL'}
- **Min variance (5-round window):** {min_variance:.1f} points
- **Threshold:** ≥ 5.0 points
- **Interpretation:** Judge should differentiate argument quality across rounds

### Threshold 3 - JSON Parse Failures
- **Status:** {'PASS' if parse_pass else 'FAIL'}
- **Parse failure rate:** {parse_fail_pct:.1f}% of rounds
- **Threshold:** ≤ 10%
- **Details:** {parse_failures} of {len(db_results)} rounds had JSON errors

### Threshold 4 - Conviction Delta Progression
- **Status:** {'PASS' if conviction_pass else 'FAIL'}
- **Average |conviction_delta|:** {avg_conviction:.2f} points per round
- **Threshold:** ≥ 3.0 points
- **Interpretation:** Judge verdicts should meaningfully separate Bull from Bear

## Overall Status

- **Total Thresholds Passed:** {sum([overlap_pass, variance_pass, parse_pass, conviction_pass])}/4
- **Critical Failures:** {'None' if all([overlap_pass, variance_pass, parse_pass, conviction_pass]) else 'See above'}

## Failure Modes Identified

{_format_failure_modes(overlap_pass, variance_pass, parse_pass, conviction_pass)}

## Market Phase Performance

- **Bull Phase (Rounds 1-20):** {len(bull_phase)} rounds, Bull win rate: {100*sum(1 for r in bull_phase if r['judge_winner']=='bull')//max(1,len(bull_phase))}%
- **Bear Phase (Rounds 21-40):** {len(bear_phase)} rounds, Bear win rate: {100*sum(1 for r in bear_phase if r['judge_winner']=='bear')//max(1,len(bear_phase))}%
- **Choppy Phase (Rounds 41-50):** {len(choppy_phase)} rounds

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
"""
    
    try:
        with open(report_path, "w") as f:
            f.write(report_content)
        print(f"✓ Report written to: {report_path}")
    except Exception as e:
        print(f"✗ Failed to write report: {e}")
    
    print("\n" + "=" * 80)
    print("STRESS TEST COMPLETE")
    print("=" * 80)


def _format_failure_modes(overlap_pass: bool, variance_pass: bool, parse_pass: bool, conviction_pass: bool) -> str:
    """Format identified failure modes."""
    failures = []
    if not overlap_pass:
        failures.append("- **Metric Overlap:** Bull and Bear arguments cite overlapping metrics (should be distinct)")
    if not variance_pass:
        failures.append("- **Judge Anchoring:** Judge scores show insufficient variance across consecutive rounds")
    if not parse_pass:
        failures.append("- **JSON Parse Failures:** Agent outputs are not reliably parseable as valid JSON")
    if not conviction_pass:
        failures.append("- **Weak Conviction Delta:** Judge verdicts do not sufficiently differentiate Bull from Bear")
    
    if not failures:
        failures.append("None identified - all thresholds passed!")
    
    return "\n".join(failures)


if __name__ == "__main__":
    run_stress_test()
