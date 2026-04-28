from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict

from utils.db.schema import StrategyAdaptation
from utils.db_manager import get_session
from utils.db.schema import MetricCorrelation
import json


class StrategyAdapter:
    def __init__(self, agent_name: str, session_id: str, performance_tracker) -> None:
        self.agent_name = agent_name
        self.session_id = session_id
        self.performance_tracker = performance_tracker

    def should_adapt(self, round_number: int) -> bool:
        # Adapt only every 3 rounds and require at least 3 rounds of data
        if round_number % 3 != 0:
            return False

        # Check there are at least 3 rounds of performance data
        recent = self.performance_tracker.get_recent_performance(self.session_id, self.agent_name, last_n_rounds=3)
        # recent['win_rate'] will be None if no rows
        return recent is not None and recent.get("win_rate") is not None

    def calculate_new_weights(self, session_id: str | None = None, agent: str | None = None) -> Dict[str, float]:
        session_id = session_id or self.session_id
        agent = agent or self.agent_name

        win_rates = self.performance_tracker.get_metric_win_rates(session_id, agent)
        new_weights: Dict[str, float] = {}

        for metric, win_rate in win_rates.items():
            # Base weight 1.0; add (win_rate - 0.5) * 2
            w = 1.0 + (float(win_rate) - 0.5) * 2.0
            # Cap between 0.3 and 2.0
            if w < 0.3:
                w = 0.3
            if w > 2.0:
                w = 2.0
            new_weights[metric] = round(w, 4)

        return new_weights

    def apply_adaptation(self, round_number: int) -> None:
        if not self.should_adapt(round_number):
            return

        # Compute new weights
        new_weights = self.calculate_new_weights()

        # Fetch previous weights
        with get_session() as session:
            existing_rows = (
                session.query(MetricCorrelation)
                .filter(MetricCorrelation.session_id == self.session_id)
                .filter(MetricCorrelation.agent == self.agent_name)
                .all()
            )

            previous_weights = {r.metric_name: float(r.current_weight) for r in existing_rows}

            # Determine most increased and most decreased
            deltas: dict[str, float] = {}
            metrics = set(previous_weights.keys()) | set(new_weights.keys())
            for m in metrics:
                prev = float(previous_weights.get(m, 1.0))
                new = float(new_weights.get(m, prev))
                deltas[m] = new - prev

            if deltas:
                top_metric = max(deltas.items(), key=lambda kv: kv[1])[0]
                bottom_metric = min(deltas.items(), key=lambda kv: kv[1])[0]
                top_rate = self.performance_tracker.get_metric_win_rates(self.session_id, self.agent_name).get(top_metric, 0.0)
                bottom_rate = self.performance_tracker.get_metric_win_rates(self.session_id, self.agent_name).get(bottom_metric, 0.0)
            else:
                top_metric = "n/a"
                bottom_metric = "n/a"
                top_rate = 0.0
                bottom_rate = 0.0

            reasoning = (
                f"Increased emphasis on {top_metric} (win rate: {top_rate*100:.1f}%). "
                f"Reduced emphasis on {bottom_metric} (win rate: {bottom_rate*100:.1f}%). "
                f"Based on last 3 rounds of performance data."
            )

            # Persist new weights into MetricCorrelation rows
            for metric, weight in new_weights.items():
                row = (
                    session.query(MetricCorrelation)
                    .filter(MetricCorrelation.session_id == self.session_id)
                    .filter(MetricCorrelation.agent == self.agent_name)
                    .filter(MetricCorrelation.metric_name == metric)
                    .one_or_none()
                )
                if row is None:
                    row = MetricCorrelation(
                        session_id=self.session_id,
                        agent=self.agent_name,
                        metric_name=metric,
                        times_cited=0,
                        times_cited_in_winning_round=0,
                        win_rate=0.0,
                        current_weight=float(weight),
                        last_updated=datetime.now(UTC),
                    )
                    session.add(row)
                else:
                    row.current_weight = float(weight)
                    row.last_updated = datetime.now(UTC)

            # Write strategy_adaptations audit row
            adaptation = StrategyAdaptation(
                session_id=self.session_id,
                agent=self.agent_name,
                adaptation_round=round_number,
                previous_weights_json=json.dumps(previous_weights),
                new_weights_json=json.dumps(new_weights),
                reasoning=reasoning,
                timestamp=datetime.now(UTC),
            )
            session.add(adaptation)
            session.commit()

            # Print reasoning for demo visibility
            print(f"[STRATEGY] Round {round_number} adaptation: {reasoning}")

    def get_current_weights(self, session_id: str | None = None, agent: str | None = None) -> Dict[str, float]:
        session_id = session_id or self.session_id
        agent = agent or self.agent_name
        with get_session() as session:
            rows = (
                session.query(MetricCorrelation)
                .filter(MetricCorrelation.session_id == session_id)
                .filter(MetricCorrelation.agent == agent)
                .all()
            )
            return {r.metric_name: float(r.current_weight) for r in rows}
