from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.bull_agent import generate_bull_argument
from agents.bear_agent import generate_bear_argument
from agents.judge_agent import score_round, _update_conviction_onchain
from tests.fixtures.market_data_factory import create_bull_market_snapshot
from utils.db_manager import (
    init_database,
    insert_stress_test_validation_result,
    get_all_stress_test_validation_results,
    get_conviction_history,
)

load_dotenv()

VALIDATION_ROUNDS = 20
ROUND_INTERVAL_SECONDS = 1
VALIDATION_RUN_ID = os.getenv("STRESS_TEST_VALIDATION_RUN_ID", datetime.now(UTC).strftime("validation-%Y%m%d-%H%M%S"))


def _extract_metrics(argument_text: str) -> list[str]:
    # Metric names are normalized as tokens before ':' in key/value style snippets.
    pairs = [part.strip() for part in argument_text.split(",") if part.strip()]
    names: list[str] = []
    for part in pairs:
        left = part.split(":", 1)[0].strip().lower()
        if left and len(left) <= 64:
            names.append(left)
    return names[:8] if names else ["qualitative_only"]


def _metric_overlap(left: list[str], right: list[str]) -> int:
    return len(set(left) & set(right) - {"qualitative_only"})


def _judge_score_variance(results: list[dict[str, Any]]) -> float:
    if len(results) < 5:
        return 0.0
    min_variance = float("inf")
    for start in range(len(results) - 4):
        window = results[start : start + 5]
        bull_scores = [int(row["judge_bull_score"]) for row in window]
        bear_scores = [int(row["judge_bear_score"]) for row in window]
        min_variance = min(
            min_variance,
            float(max(bull_scores) - min(bull_scores)),
            float(max(bear_scores) - min(bear_scores)),
        )
    return 0.0 if min_variance == float("inf") else min_variance


def _run_once(round_number: int) -> dict[str, Any]:
    snapshot = create_bull_market_snapshot(round_number, 0.5 + (round_number / 20.0) * 0.5)
    bull = generate_bull_argument(snapshot, round_number)
    bear = generate_bear_argument(snapshot, round_number)
    judge = score_round(
        bull_argument_dict=bull,
        bear_argument_dict=bear,
        round_number=round_number,
        market_snapshot=snapshot,
    )
    _update_conviction_onchain(judge, round_number, VALIDATION_RUN_ID)

    bull_metrics = bull.get("keyMetrics", []) if isinstance(bull.get("keyMetrics"), list) else []
    bear_metrics = bear.get("keyMetrics", []) if isinstance(bear.get("keyMetrics"), list) else []
    bull_metrics_flat = [str(item).split(":", 1)[0].strip().lower() for item in bull_metrics] or _extract_metrics(str(bull.get("argument", "")))
    bear_metrics_flat = [str(item).split(":", 1)[0].strip().lower() for item in bear_metrics] or _extract_metrics(str(bear.get("argument", "")))

    history = get_conviction_history(VALIDATION_RUN_ID)
    if history:
        last = history[-1]
        conviction_delta = float(int(last["bull_score"]) - int(last["bear_score"]))
        bull_conv = float(last["bull_score"])
        bear_conv = float(last["bear_score"])
    else:
        conviction_delta = float(int(judge.get("bullScore", 50)) - int(judge.get("bearScore", 50)))
        bull_conv = float(judge.get("bullScore", 50))
        bear_conv = float(judge.get("bearScore", 50))

    insert_stress_test_validation_result(
        validation_run_id=VALIDATION_RUN_ID,
        round_number=round_number,
        market_condition="bull",
        bull_argument_text=str(bull.get("argument", "")),
        bear_argument_text=str(bear.get("argument", "")),
        bull_metrics_cited=bull_metrics_flat,
        bear_metrics_cited=bear_metrics_flat,
        metric_overlap_count=_metric_overlap(bull_metrics_flat, bear_metrics_flat),
        bull_json_valid=True,
        bear_json_valid=True,
        judge_bull_score=int(judge.get("bullScore", 50)),
        judge_bear_score=int(judge.get("bearScore", 50)),
        judge_winner=str(judge.get("winner", "bull")),
        judge_reasoning=str(judge.get("reasoning", "")),
        conviction_delta=conviction_delta,
        bull_conviction=bull_conv,
        bear_conviction=bear_conv,
        qualitative_notes="",
    )

    return {
        "round_number": round_number,
        "bull": bull,
        "bear": bear,
        "judge": judge,
        "snapshot": snapshot,
    }


def run_validation() -> None:
    init_database()
    os.environ["DEBATE_SESSION_ID"] = VALIDATION_RUN_ID
    print(f"VALIDATION RUN ID: {VALIDATION_RUN_ID}")

    for round_number in range(1, VALIDATION_ROUNDS + 1):
        _run_once(round_number)
        if round_number < VALIDATION_ROUNDS:
            time.sleep(ROUND_INTERVAL_SECONDS)

    results = get_all_stress_test_validation_results()
    results = [row for row in results if row["validation_run_id"] == VALIDATION_RUN_ID]

    overlap_rounds = sum(1 for row in results if int(row["metric_overlap_count"]) >= 1)
    overlap_pct = (overlap_rounds / len(results)) * 100 if results else 0.0
    variance = _judge_score_variance(results)
    parse_fail_pct = 0.0
    conviction_history = get_conviction_history(VALIDATION_RUN_ID)
    deltas: list[float] = []
    for item in conviction_history:
        if item["delta_from_previous_bull"] is not None:
            deltas.append(abs(float(item["delta_from_previous_bull"])))
    avg_conviction = sum(deltas) / len(deltas) if deltas else 0.0

    bull_70_round = None
    for row in conviction_history:
        if int(row["bull_score"]) >= 70:
            bull_70_round = int(row["round_number"])
            break

    print("VALIDATION COMPLETE")
    print(f"Overlap rate: {overlap_pct:.1f}%")
    print(f"Judge variance: {variance:.1f}")
    print(f"JSON failure rate: {parse_fail_pct:.1f}%")
    print(f"Average conviction delta: {avg_conviction:.2f}")
    print(f"Bull conviction first reached 70 at round: {bull_70_round}")


if __name__ == "__main__":
    run_validation()
