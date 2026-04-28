from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Dict, List

try:
    from langchain.memory import ConversationBufferMemory
    from langchain.schema import AIMessage, HumanMessage
except Exception:
    # Minimal fallback if langchain isn't installed (simulation mode)
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content

    class AIMessage:
        def __init__(self, content: str):
            self.content = content

    class _SimpleChatMemory:
        def __init__(self):
            self.messages: list = []

        def add_user_message(self, content: str) -> None:
            self.messages.append(HumanMessage(content))

        def add_ai_message(self, content: str) -> None:
            self.messages.append(AIMessage(content))

    class ConversationBufferMemory:
        def __init__(self, return_messages: bool = True, memory_key: str | None = None):
            self.return_messages = return_messages
            self.memory_key = memory_key or "debate_history"
            self.chat_memory = _SimpleChatMemory()

        def load_memory_variables(self, _: dict | None = None) -> dict:
            # Return a simple serialized debate_history
            out = []
            for m in self.chat_memory.messages:
                role = "ai" if isinstance(m, AIMessage) else "human"
                out.append({"role": role, "content": getattr(m, "content", str(m))})
            return {self.memory_key: json.dumps(out)}

from utils.db_manager import get_session
from utils.db.schema import (
    AgentMemorySnapshot,
    ArgumentPerformance,
    MetricCorrelation,
)


class AgentMemory:
    def __init__(self, agent_name: str, session_id: str, max_history: int = 5):
        self.agent_name = agent_name
        self.session_id = session_id
        self.max_history = int(max_history)

        # Try to restore from latest snapshot for this session & agent
        with get_session() as session:
            stmt = (
                session.query(AgentMemorySnapshot)
                .filter(AgentMemorySnapshot.session_id == session_id)
                .filter(AgentMemorySnapshot.agent == agent_name)
                .order_by(AgentMemorySnapshot.round_number.desc())
                .limit(1)
            )
            row = stmt.one_or_none()

        self.memory = ConversationBufferMemory(return_messages=True, memory_key="debate_history")

        if row is not None:
            try:
                msgs = json.loads(row.memory_json)
                for m in msgs:
                    role = m.get("role")
                    content = m.get("content", "")
                    if role == "human":
                        try:
                            self.memory.chat_memory.add_user_message(content)
                        except Exception:
                            pass
                    elif role == "ai":
                        try:
                            self.memory.chat_memory.add_ai_message(content)
                        except Exception:
                            pass
            except Exception:
                # If restoration fails, start with empty memory
                self.memory = ConversationBufferMemory(return_messages=True, memory_key="debate_history")

    def add_round(self, round_number: int, market_data_summary: str, argument_dict: Dict[str, Any], judge_score: int) -> None:
        # Market data as human turn
        if not isinstance(market_data_summary, str):
            market_data_summary = json.dumps(market_data_summary)

        # Argument text extraction
        argument_text = argument_dict.get("argument_text") or argument_dict.get("argument") or str(argument_dict)
        argument_with_score = f"{argument_text}\nJudge score: {judge_score}"

        # Append to LangChain memory
        try:
            self.memory.chat_memory.add_user_message(market_data_summary)
        except Exception:
            pass
        try:
            self.memory.chat_memory.add_ai_message(argument_with_score)
        except Exception:
            pass

        # Trim to max_history pairs (human+ai)
        try:
            msgs = list(self.memory.chat_memory.messages)
            max_msgs = self.max_history * 2
            if len(msgs) > max_msgs:
                trimmed = msgs[-max_msgs:]
                # Replace underlying messages list if possible
                try:
                    self.memory.chat_memory.messages = trimmed
                except Exception:
                    # No fallback; leave as-is
                    pass
        except Exception:
            pass

        # Persist snapshot after adding
        self.save_snapshot(round_number)

    def save_snapshot(self, round_number: int) -> None:
        # Serialize chat history as simple list of dicts
        serialized: List[Dict[str, str]] = []
        try:
            for m in list(self.memory.chat_memory.messages):
                # Determine role and content
                role = "human"
                if isinstance(m, AIMessage):
                    role = "ai"
                elif isinstance(m, HumanMessage):
                    role = "human"
                else:
                    # fallback: inspect attributes
                    role = getattr(m, "type", getattr(m, "role", "human"))

                content = getattr(m, "content", str(m))
                serialized.append({"role": role, "content": content})
        except Exception:
            serialized = []

        memory_json = json.dumps(serialized)

        with get_session() as session:
            existing = (
                session.query(AgentMemorySnapshot)
                .filter(AgentMemorySnapshot.session_id == self.session_id)
                .filter(AgentMemorySnapshot.agent == self.agent_name)
                .order_by(AgentMemorySnapshot.round_number.desc())
                .limit(1)
                .one_or_none()
            )

            if existing is None:
                new_row = AgentMemorySnapshot(
                    session_id=self.session_id,
                    agent=self.agent_name,
                    round_number=round_number,
                    memory_json=memory_json,
                    timestamp=datetime.now(UTC),
                )
                session.add(new_row)
            else:
                existing.round_number = round_number
                existing.memory_json = memory_json
                existing.timestamp = datetime.now(UTC)

            session.commit()


class PerformanceTracker:
    def record_round(
        self,
        session_id: str,
        agent: str,
        round_number: int,
        argument_dict: Dict[str, Any],
        judge_score: int | None,
        won_round: bool,
        accuracy_bonus: bool,
    ) -> None:
        # Extract key metrics from argument_dict
        key_metrics_raw = argument_dict.get("keyMetrics") or argument_dict.get("key_metrics") or []
        parsed: List[str] = []
        for s in key_metrics_raw:
            if not isinstance(s, str):
                continue
            name = s.split(":", 1)[0].strip()
            if name:
                parsed.append(name)

        with get_session() as session:
            row = ArgumentPerformance(
                session_id=session_id,
                agent=agent,
                round_number=round_number,
                argument_text=argument_dict.get("argument_text") or argument_dict.get("argument") or json.dumps(argument_dict),
                confidence_submitted=argument_dict.get("confidence"),
                judge_score_received=judge_score,
                metrics_cited=json.dumps(parsed),
                won_round=bool(won_round),
                accuracy_bonus_received=bool(accuracy_bonus),
                timestamp=datetime.now(UTC),
            )
            session.add(row)
            session.commit()

    def get_recent_performance(self, session_id: str, agent: str, last_n_rounds: int = 5) -> Dict[str, Any]:
        with get_session() as session:
            stmt = (
                session.query(ArgumentPerformance)
                .filter(ArgumentPerformance.session_id == session_id)
                .filter(ArgumentPerformance.agent == agent)
                .order_by(ArgumentPerformance.round_number.desc())
                .limit(last_n_rounds)
            )
            rows = stmt.all()

        if not rows:
            return {"average_judge_score": None, "win_rate": None, "metrics": {}}

        total_score = 0
        score_count = 0
        wins = 0
        metrics_counts: Dict[str, Dict[str, int]] = {}

        for r in rows:
            if r.judge_score_received is not None:
                total_score += int(r.judge_score_received)
                score_count += 1
            if r.won_round:
                wins += 1
            try:
                metrics = json.loads(r.metrics_cited)
            except Exception:
                metrics = []
            for m in metrics:
                entry = metrics_counts.setdefault(m, {"count": 0, "wins": 0})
                entry["count"] += 1
                if r.won_round:
                    entry["wins"] += 1

        avg_score = (total_score / score_count) if score_count > 0 else None
        win_rate = wins / len(rows)

        return {"average_judge_score": avg_score, "win_rate": win_rate, "metrics": metrics_counts}

    def get_metric_win_rates(self, session_id: str, agent: str) -> Dict[str, float]:
        with get_session() as session:
            stmt = (
                session.query(MetricCorrelation)
                .filter(MetricCorrelation.session_id == session_id)
                .filter(MetricCorrelation.agent == agent)
            )
            rows = stmt.all()

        return {r.metric_name: float(r.win_rate) for r in rows}

    def update_metric_correlations(self, session_id: str, agent: str) -> None:
        # Recompute metrics stats from argument_performance and upsert into metric_correlations
        from utils.db.schema import ArgumentPerformance, MetricCorrelation

        counts: Dict[str, Dict[str, int]] = {}
        with get_session() as session:
            stmt = (
                session.query(ArgumentPerformance)
                .filter(ArgumentPerformance.session_id == session_id)
                .filter(ArgumentPerformance.agent == agent)
            )
            rows = stmt.all()

            for r in rows:
                try:
                    metrics = json.loads(r.metrics_cited)
                except Exception:
                    metrics = []
                for m in metrics:
                    entry = counts.setdefault(m, {"times_cited": 0, "wins": 0})
                    entry["times_cited"] += 1
                    if r.won_round:
                        entry["wins"] += 1

            # Upsert metric_correlations
            for metric, data in counts.items():
                times = data["times_cited"]
                wins = data["wins"]
                win_rate = (wins / times) if times > 0 else 0.0

                existing = (
                    session.query(MetricCorrelation)
                    .filter(MetricCorrelation.session_id == session_id)
                    .filter(MetricCorrelation.agent == agent)
                    .filter(MetricCorrelation.metric_name == metric)
                    .one_or_none()
                )

                if existing is None:
                    existing = MetricCorrelation(
                        session_id=session_id,
                        agent=agent,
                        metric_name=metric,
                        times_cited=times,
                        times_cited_in_winning_round=wins,
                        win_rate=win_rate,
                        current_weight=1.0,
                        last_updated=datetime.now(UTC),
                    )
                    session.add(existing)
                else:
                    existing.times_cited = times
                    existing.times_cited_in_winning_round = wins
                    existing.win_rate = win_rate
                    existing.last_updated = datetime.now(UTC)

            session.commit()
