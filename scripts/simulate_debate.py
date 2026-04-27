from __future__ import annotations

import json
import random
from datetime import datetime
from uuid import uuid4

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db_manager import init_database, get_session
from agents.memory import AgentMemory, PerformanceTracker
from agents.strategy_adapter import StrategyAdapter
from utils.db.schema import StrategyAdaptation, ArgumentPerformance, AgentMemorySnapshot


def simulate():
    init_database()
    session_id = str(uuid4())
    print(f"Simulating debate session: {session_id}")

    bull_mem = AgentMemory("bull", session_id)
    bear_mem = AgentMemory("bear", session_id)
    perf = PerformanceTracker()
    bull_adapter = StrategyAdapter("bull", session_id, perf)
    bear_adapter = StrategyAdapter("bear", session_id, perf)

    # Define two metrics that will be predictive at different times
    metrics_pool = ["24h price change", "large_inflow_count", "funding rate proxy", "volume delta percent"]

    # Simulate 9 rounds
    for r in range(1, 10):
        # Create an argument for each agent that cites 2 metrics; vary citation probability over rounds
        bull_metric = random.choice(metrics_pool if r < 5 else metrics_pool[:2])
        bear_metric = random.choice(metrics_pool if r < 5 else metrics_pool[2:])

        bull_arg = {
            "argument": f"Bull round {r} citing {bull_metric}",
            "confidence": random.randint(30, 90),
            "keyMetrics": [f"{bull_metric}: {random.uniform(0,10):.2f}", f"{metrics_pool[0]}: {random.uniform(-5,5):.2f}%"],
        }

        bear_arg = {
            "argument": f"Bear round {r} citing {bear_metric}",
            "confidence": random.randint(30, 90),
            "keyMetrics": [f"{bear_metric}: {random.uniform(0,10):.2f}", f"{metrics_pool[1]}: {random.uniform(0,20):.2f}%"],
        }

        # Synthetic judge score: favor bull if bull_metric == metrics_pool[1] (large_inflow_count), else random
        bull_score = 60 + (10 if "large_inflow_count" in bull_arg["keyMetrics"][0] else 0) + random.randint(-5, 5)
        bear_score = 60 + (10 if "funding rate proxy" in bear_arg["keyMetrics"][0] else 0) + random.randint(-5, 5)

        # Normalize
        bull_score = max(0, min(100, int(bull_score)))
        bear_score = max(0, min(100, int(bear_score)))

        # Determine winner
        winner = "bull" if bull_score > bear_score else "bear" if bear_score > bull_score else "draw"

        # Add to memory and persist
        market_summary = f"Round {r} market snapshot"
        bull_mem.add_round(r, market_summary, bull_arg, bull_score)
        bear_mem.add_round(r, market_summary, bear_arg, bear_score)
        bull_mem.save_snapshot(r)
        bear_mem.save_snapshot(r)

        # Record performance
        perf.record_round(session_id, "bull", r, bull_arg, bull_score, won_round=(winner == "bull"), accuracy_bonus=False)
        perf.record_round(session_id, "bear", r, bear_arg, bear_score, won_round=(winner == "bear"), accuracy_bonus=False)
        perf.update_metric_correlations(session_id, "bull")
        perf.update_metric_correlations(session_id, "bear")

        # Apply adaptations every 3 rounds
        bull_adapter.apply_adaptation(r)
        bear_adapter.apply_adaptation(r)

        print(f"Simulated round {r}: bull_score={bull_score} bear_score={bear_score} winner={winner}")

    # After simulation, run checks
    with get_session() as s:
        adaptations = s.query(StrategyAdaptation).filter(StrategyAdaptation.session_id == session_id).all()
        perf_rows = s.query(ArgumentPerformance).filter(ArgumentPerformance.session_id == session_id).all()
        snapshots = s.query(AgentMemorySnapshot).filter(AgentMemorySnapshot.session_id == session_id).all()

        print(f"\nPost-simulation checks for session {session_id}:")
        print(f"Strategy adaptations count: {len(adaptations)}")
        for a in adaptations:
            print(f"- Round {a.adaptation_round}: reasoning={a.reasoning}")

        print(f"Argument performance rows: {len(perf_rows)}")
        if perf_rows:
            first = perf_rows[0]
            last = perf_rows[-1]
            print(f"First argument text: {first.argument_text}")
            print(f"Last argument text: {last.argument_text}")

        print(f"Agent memory snapshots count: {len(snapshots)}")
        if snapshots:
            print(f"Latest bull memory snapshot exists: {any(x.agent=='bull' for x in snapshots)}")


if __name__ == "__main__":
    simulate()
