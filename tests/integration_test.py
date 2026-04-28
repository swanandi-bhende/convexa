# Mock every external boundary: Groq, Alchemy RPC, The Graph GraphQL, Uniswap, KeeperHub, AXL HTTP, and web3 contract calls are replaced with deterministic in-memory doubles.
# Isolation rule: every test gets a fresh in-memory SQLite database, fresh module patches, and clean mock state so failures cannot leak across scenarios.
# Assertion rule: bull dominance means at least 5 of 7 judge wins, a final bull lead of at least 15 points, and bull confidence in rounds 5-7 averaging at least 5 points above rounds 1-3.

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import bear_agent, bull_agent, judge_agent, orchestrator
from tests.fixtures.market_data_factory import create_snapshot_sequence
from tests.fixtures.mocks import MockAXLNode, MockDebateRuntime, MockKeeperHubClient, MockRiskManager
from utils.db.schema import (
    ArgumentPerformance,
    Base,
    BearRound,
    BullRound,
    ConvictionHistory,
    DebateSession,
    JudgeVerdict,
    KeeperHubJob,
    KeeperHubRetry,
    RoundTrace,
    SafetyEvent,
    StrategyAdaptation,
)
import utils.db_manager as db_manager


@dataclass(slots=True)
class ScenarioConfig:
    scenario_type: str
    num_rounds: int
    intensity: float = 1.0
    token_pair: str = "ETH/USDC"
    round_interval_seconds: int = 1
    bull_failure_after_messages: int | None = None
    keeperhub_gas_spike_mode: bool = False


@dataclass(slots=True)
class ScenarioResult:
    session_id: str
    database_state: dict[str, Any]
    debate_session: dict[str, Any] | None
    bull_rounds: list[dict[str, Any]]
    bear_rounds: list[dict[str, Any]]
    judge_verdicts: list[dict[str, Any]]
    round_traces: list[dict[str, Any]]
    conviction_history: list[dict[str, Any]]
    strategy_adaptations: list[dict[str, Any]]
    safety_events: list[dict[str, Any]]
    argument_performance: list[dict[str, Any]]
    keeperhub_jobs: list[dict[str, Any]]
    keeperhub_retries: list[dict[str, Any]]
    stdout: str


class _DummySettlementContract:
    class _Functions:
        class _CallFalse:
            @staticmethod
            def call() -> bool:
                return False

        def isSettlementTriggered(self) -> "_DummySettlementContract._Functions._CallFalse":
            return self._CallFalse()

    def __init__(self) -> None:
        self.functions = self._Functions()


class _DummyWeb3:
    class _Eth:
        chain_id = 1301

    def __init__(self) -> None:
        self.eth = self._Eth()


class TestHarness:
    __test__ = False

    def __init__(self) -> None:
        self.monkeypatch = pytest.MonkeyPatch()
        self.engine = None
        self.SessionLocal = None
        self.runtime: MockDebateRuntime | None = None
        self.clock = self._VirtualClock()

    @dataclass(slots=True)
    class _VirtualClock:
        current: float = 0.0

        def time(self) -> float:
            return self.current

        def sleep(self, seconds: float) -> None:
            self.current += max(0.0, float(seconds))

    def _require_runtime(self) -> MockDebateRuntime:
        if self.runtime is None:
            raise RuntimeError("Mock runtime has not been initialized")
        return self.runtime

    def setup(self) -> None:
        os.environ["DATABASE_URL"] = "sqlite://"
        self._original_initialize_debate_session = orchestrator.initialize_debate_session
        self._original_run_bull_round = orchestrator.run_bull_round
        self.engine = create_engine(
            "sqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        db_manager._ENGINE = self.engine
        db_manager._SessionLocal = self.SessionLocal
        Base.metadata.create_all(bind=self.engine)

        self.monkeypatch.setattr(orchestrator.execution_handler, "test_connection", lambda: None, raising=False)
        self.monkeypatch.setattr(orchestrator, "startup_axl_nodes", lambda dry_run: None)
        self.monkeypatch.setattr(orchestrator, "shutdown_axl_nodes", lambda: None)
        self.monkeypatch.setattr(orchestrator, "run_stake_collection_window", lambda session_id, duration_seconds=120: True)
        self.monkeypatch.setattr(orchestrator, "_ping_axl_node", lambda base_url: (True, f"mock:{base_url}"))
        self.monkeypatch.setattr(orchestrator, "_start_debate_contracts", lambda session_id, duration_seconds: {"escrow_tx_hash": "0xmockescrow", "conviction_tx_hash": "0xmockconviction"})
        self.monkeypatch.setattr(orchestrator, "_get_web3_and_conviction_contract", lambda: (_DummyWeb3(), _DummySettlementContract()))
        self.monkeypatch.setattr(orchestrator, "_get_debate_escrow_contract", lambda: (_DummyWeb3(), _DummySettlementContract()))
        self.monkeypatch.setattr(orchestrator, "_read_onchain_scores", lambda: self._require_runtime().current_scores)
        self.monkeypatch.setattr(orchestrator, "execute_final_settlement", self._final_settlement)
        self.monkeypatch.setattr(orchestrator.swap_executor, "execute_micro_settlement", self._micro_settlement)
        self.monkeypatch.setattr(orchestrator, "RiskManager", MockRiskManager)
        self.monkeypatch.setattr(orchestrator, "run_bull_round", self._run_bull_round)
        self.monkeypatch.setattr(orchestrator.time, "time", self.clock.time, raising=False)
        self.monkeypatch.setattr(orchestrator.time, "sleep", self.clock.sleep, raising=False)
        self.monkeypatch.setattr(orchestrator, "initialize_debate_session", self._initialize_debate_session)

        self.monkeypatch.setattr(orchestrator, "fetch_snapshot", self._fetch_snapshot)
        self.monkeypatch.setattr(bull_agent, "fetch_snapshot", self._snapshot_for_round)
        self.monkeypatch.setattr(bear_agent, "fetch_snapshot", self._snapshot_for_round)
        self.monkeypatch.setattr(judge_agent, "fetch_snapshot", self._snapshot_for_round)

        self.monkeypatch.setattr(bull_agent, "generate_bull_argument", self._generate_bull_argument)
        self.monkeypatch.setattr(bear_agent, "generate_bear_argument", self._generate_bear_argument)
        self.monkeypatch.setattr(bull_agent, "publish_to_judge", self._publish_bull_argument)
        self.monkeypatch.setattr(bear_agent, "publish_to_judge", self._publish_bear_argument)
        self.monkeypatch.setattr(judge_agent, "wait_for_both_arguments", self._wait_for_both_arguments)
        self.monkeypatch.setattr(judge_agent, "score_round", self._score_round)
        self.monkeypatch.setattr(judge_agent, "_post_verdict_to_destination", lambda *args, **kwargs: True)
        self.monkeypatch.setattr(judge_agent, "_update_conviction_onchain", self._update_conviction_onchain)
        self.monkeypatch.setattr(judge_agent, "publish_verdict", judge_agent.publish_verdict)

    def _initialize_debate_session(self, token_pair: str, max_rounds: int, round_interval_seconds: int) -> str:
        session_id = self._original_initialize_debate_session(token_pair, max_rounds, round_interval_seconds)
        if self.runtime is not None:
            self.runtime.session_id = session_id
        return session_id

    def teardown(self) -> None:
        self.monkeypatch.undo()
        if self.engine is not None:
            self.engine.dispose()

    def _fetch_snapshot(self, token_pair: str) -> Any:
        return self._require_runtime().next_snapshot(token_pair)

    def _snapshot_for_round(self, token_pair: str) -> Any:
        return self._require_runtime().snapshot_for_round(token_pair)

    def _generate_bull_argument(self, snapshot: Any, round_number: int, memory: Any | None = None, weights: dict | None = None) -> dict[str, Any]:
        return self._require_runtime().bull_argument(snapshot, round_number, memory=memory, weights=weights)

    def _generate_bear_argument(self, snapshot: Any, round_number: int, memory: Any | None = None, weights: dict | None = None) -> dict[str, Any]:
        return self._require_runtime().bear_argument(snapshot, round_number, memory=memory, weights=weights)

    def _publish_bull_argument(self, argument_dict: dict[str, Any], round_number: int) -> bool:
        return self._require_runtime().store_message("bull", round_number, argument_dict)

    def _publish_bear_argument(self, argument_dict: dict[str, Any], round_number: int) -> bool:
        return self._require_runtime().store_message("bear", round_number, argument_dict)

    def _run_bull_round(self, session_id: str, round_number: int, token_pair: str) -> dict[str, Any]:
        result = self._original_run_bull_round(session_id, round_number, token_pair)
        runtime = self._require_runtime()
        cutoff = runtime.bull_failure_after_messages
        if not bool(result.get("axl_delivery_success", True)):
            result = dict(result)
            if cutoff is not None and round_number <= cutoff:
                # Keep rounds up to the configured cutoff deterministic and non-fallback.
                snapshot = runtime.snapshot_for_round(token_pair)
                result["argument"] = runtime.bull_argument(snapshot, round_number)
                result["axl_delivery_success"] = True
            else:
                result["argument"] = {
                    "argument": "No bull argument received before timeout. Neutral placeholder used.",
                    "confidence": 50,
                    "keyMetrics": ["timeout fallback"],
                }
        return result

    def _wait_for_both_arguments(self, round_number: int, timeout_seconds: int = 120) -> tuple[dict[str, dict[str, Any] | None], bool]:
        runtime = self._require_runtime()
        bucket, timed_out = runtime.wait_for_both_arguments(round_number, timeout_seconds)

        if runtime.bull_failure_after_messages is not None and round_number <= runtime.bull_failure_after_messages and bucket.get("bull") is None:
            snapshot = runtime.snapshot_for_round("ETH/USDC")
            bucket["bull"] = {
                "sender": "bull",
                "round": round_number,
                "payload": {
                    "sender": "bull",
                    "round": round_number,
                    "argument": runtime.bull_argument(snapshot, round_number),
                    "sender_peer_id": "mock-bull-peer-id",
                    "message_hash": f"synthetic-bull-{round_number}",
                    "signature": f"synthetic-signature-bull-{round_number}",
                },
            }

        if bucket.get("bear") is None:
            snapshot = runtime.snapshot_for_round("ETH/USDC")
            bucket["bear"] = {
                "sender": "bear",
                "round": round_number,
                "payload": {
                    "sender": "bear",
                    "round": round_number,
                    "argument": runtime.bear_argument(snapshot, round_number),
                    "sender_peer_id": "mock-bear-peer-id",
                    "message_hash": f"synthetic-bear-{round_number}",
                    "signature": f"synthetic-signature-bear-{round_number}",
                },
            }

        missing_sides = [side for side in ("bull", "bear") if bucket.get(side) is None]
        if missing_sides and runtime.session_id is not None:
            with db_manager.get_session() as session:
                session.add(
                    SafetyEvent(
                        session_id=runtime.session_id,
                        round_number=round_number,
                        event_type="axl_message_timeout",
                        severity="warning",
                        details_json=json.dumps({"missing_sides": missing_sides}),
                        action_taken="used_neutral_fallback",
                        resolved_at=None,
                    )
                )
                session.commit()
            timed_out = True
        return bucket, timed_out

    def _score_round(
        self,
        bull_argument_dict: dict[str, Any],
        bear_argument_dict: dict[str, Any],
        round_number: int,
        market_snapshot: Any,
    ) -> dict[str, Any]:
        return self._require_runtime().judge_verdict(bull_argument_dict, bear_argument_dict, round_number, market_snapshot)

    def _update_conviction_onchain(self, verdict_dict: dict[str, Any], round_number: int, session_id: str) -> tuple[bool, str]:
        return self._require_runtime().update_conviction_onchain(verdict_dict, round_number, session_id)

    def _micro_settlement(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        runtime = self._require_runtime()
        round_number = int(kwargs.get("round_number") or 0)
        session_id = str(kwargs.get("session_id") or runtime.session_id or "test-session")
        if runtime.keeperhub_client.gas_spike_mode:
            backoff_seconds = 15
            job_id = f"mock-keeperhub-{round_number:02d}"
            with db_manager.get_session() as session:
                session.add(
                    KeeperHubJob(
                        session_id=session_id,
                        round_number=round_number,
                        job_id=job_id,
                        job_type="micro_settlement",
                        swap_quote_id=None,
                        submitted_at=orchestrator._utcnow(),
                        max_gas_price_gwei=90.0,
                        deadline_timestamp=None,
                        retry_policy_json=json.dumps({"backoffSeconds": backoff_seconds}),
                        current_status="submitted",
                        last_polled_at=orchestrator._utcnow(),
                        confirmed_at=None,
                        tx_hash=None,
                        actual_gas_price_gwei=None,
                        keeperhub_fee_wei=None,
                        error_message=None,
                    )
                )
                session.add(
                    KeeperHubRetry(
                        job_id=job_id,
                        retry_attempt_number=1,
                        retry_reason="gas_too_high",
                        retry_timestamp=orchestrator._utcnow(),
                        retry_outcome="retrying",
                    )
                )
                session.add(
                    KeeperHubRetry(
                        job_id=job_id,
                        retry_attempt_number=2,
                        retry_reason="gas_too_high",
                        retry_timestamp=orchestrator._utcnow(),
                        retry_outcome="retrying",
                    )
                )
                session.commit()
            self.clock.sleep(backoff_seconds * 2 + 1)
            with db_manager.get_session() as session:
                row = session.query(KeeperHubJob).filter(KeeperHubJob.job_id == job_id).one_or_none()
                if row is not None:
                    row.current_status = "confirmed"
                    row.confirmed_at = orchestrator._utcnow()
                    row.tx_hash = f"0xmockkeeperhub{round_number:02d}"
                    row.last_polled_at = orchestrator._utcnow()
                    session.commit()
            return {"success": True, "tx_hash": f"0xmockkeeperhub{round_number:02d}", "job_id": job_id, "confirmed": True}

        del args, kwargs
        return {"success": True, "tx_hash": "0xmockmicroswap"}

    def _final_settlement(self, session_id: str, winning_side: str, final_scores: tuple[int, int], dry_run: bool) -> str:
        del dry_run
        db_manager.update_debate_session(
            session_id,
            settlement_triggered=True,
            settlement_tx_hash=f"0xmocksettle{winning_side}",
        )
        return f"0xmocksettle{winning_side}"

    def run_debate_scenario(self, scenario_config: ScenarioConfig) -> ScenarioResult:
        self.runtime = MockDebateRuntime(
            scenario_type=scenario_config.scenario_type,
            snapshots=create_snapshot_sequence(
                scenario_config.scenario_type,
                scenario_config.num_rounds,
                intensity=scenario_config.intensity,
            ),
            bull_failure_after_messages=scenario_config.bull_failure_after_messages,
            keeperhub_gas_spike_mode=scenario_config.keeperhub_gas_spike_mode,
        )

        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            session_id = orchestrator.run_debate(
                scenario_config.token_pair,
                max_rounds=scenario_config.num_rounds,
                round_interval_seconds=scenario_config.round_interval_seconds,
            )

        with db_manager.get_session() as session:
            debate_session_row = session.scalar(select(DebateSession).where(DebateSession.session_id == session_id))
            bull_rounds = session.scalars(select(BullRound).order_by(BullRound.round_number)).all()
            bear_rounds = session.scalars(select(BearRound).order_by(BearRound.round_number)).all()
            judge_verdicts = session.scalars(select(JudgeVerdict).order_by(JudgeVerdict.round_number)).all()
            round_traces = session.scalars(select(RoundTrace).order_by(RoundTrace.round_number)).all()
            conviction_history = session.scalars(select(ConvictionHistory).order_by(ConvictionHistory.round_number)).all()
            strategy_adaptations = session.scalars(select(StrategyAdaptation).order_by(StrategyAdaptation.adaptation_round)).all()
            safety_events = session.scalars(select(SafetyEvent).order_by(SafetyEvent.round_number)).all()
            argument_performance = session.scalars(select(ArgumentPerformance).order_by(ArgumentPerformance.round_number)).all()
            keeperhub_jobs = session.scalars(select(KeeperHubJob).order_by(KeeperHubJob.round_number)).all()
            keeperhub_retries = session.scalars(select(KeeperHubRetry).order_by(KeeperHubRetry.retry_attempt_number)).all()

        def _row_to_dict(row: Any) -> dict[str, Any]:
            data = {column.name: getattr(row, column.name) for column in row.__table__.columns}
            return data

        def _parse_jsonish(row_dict: dict[str, Any]) -> dict[str, Any]:
            parsed = dict(row_dict)
            for key in (
                "market_snapshot_json",
                "bull_argument_json",
                "bear_argument_json",
                "judge_verdict_json",
                "previous_weights_json",
                "new_weights_json",
                "details_json",
            ):
                value = parsed.get(key)
                if isinstance(value, str):
                    try:
                        parsed[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            return parsed

        debate_session = _row_to_dict(debate_session_row) if debate_session_row is not None else None
        bull_round_dicts = [_row_to_dict(row) for row in bull_rounds]
        bear_round_dicts = [_row_to_dict(row) for row in bear_rounds]
        judge_verdict_dicts = [_row_to_dict(row) for row in judge_verdicts]
        round_trace_dicts = [_parse_jsonish(_row_to_dict(row)) for row in round_traces]
        conviction_history_dicts = [_row_to_dict(row) for row in conviction_history]
        strategy_adaptation_dicts = [_parse_jsonish(_row_to_dict(row)) for row in strategy_adaptations]
        safety_event_dicts = [_parse_jsonish(_row_to_dict(row)) for row in safety_events]
        argument_performance_dicts = [_row_to_dict(row) for row in argument_performance]
        keeperhub_job_dicts = [_parse_jsonish(_row_to_dict(row)) for row in keeperhub_jobs]
        keeperhub_retry_dicts = [_row_to_dict(row) for row in keeperhub_retries]

        database_state = {
            "counts": {
                "debate_sessions": len([debate_session] if debate_session is not None else []),
                "bull_rounds": len(bull_round_dicts),
                "bear_rounds": len(bear_round_dicts),
                "judge_verdicts": len(judge_verdict_dicts),
                "round_traces": len(round_trace_dicts),
                "conviction_history": len(conviction_history_dicts),
                "strategy_adaptations": len(strategy_adaptation_dicts),
                "safety_events": len(safety_event_dicts),
                "argument_performance": len(argument_performance_dicts),
                "keeperhub_jobs": len(keeperhub_job_dicts),
                "keeperhub_retries": len(keeperhub_retry_dicts),
            },
            "session_status": debate_session.get("status") if debate_session is not None else None,
            "winning_side": debate_session.get("winning_side") if debate_session is not None else None,
        }

        return ScenarioResult(
            session_id=session_id,
            database_state=database_state,
            debate_session=debate_session,
            bull_rounds=bull_round_dicts,
            bear_rounds=bear_round_dicts,
            judge_verdicts=judge_verdict_dicts,
            round_traces=round_trace_dicts,
            conviction_history=conviction_history_dicts,
            strategy_adaptations=strategy_adaptation_dicts,
            safety_events=safety_event_dicts,
            argument_performance=argument_performance_dicts,
            keeperhub_jobs=keeperhub_job_dicts,
            keeperhub_retries=keeperhub_retry_dicts,
            stdout=captured.getvalue(),
        )


@pytest.fixture()
def harness() -> Any:
    test_harness = TestHarness()
    test_harness.setup()
    try:
        yield test_harness
    finally:
        test_harness.teardown()


def test_bull_dominant_market(harness: TestHarness) -> None:
    scenario = ScenarioConfig(scenario_type="bull", num_rounds=7, intensity=1.0)
    result = harness.run_debate_scenario(scenario)

    assert result.debate_session is not None
    assert result.debate_session["winning_side"] == "bull"
    assert result.debate_session["total_rounds"] == 7

    bull_round_wins = sum(1 for verdict in result.judge_verdicts if verdict["winner"] == "bull")
    assert bull_round_wins >= 5

    final_bull_score = int(result.debate_session["final_bull_score"])
    final_bear_score = int(result.debate_session["final_bear_score"])
    assert final_bull_score - final_bear_score >= 15

    assert len(result.round_traces) == 7
    assert all(trace["judge_verdict_json"] is not None for trace in result.round_traces)

    assert any(adaptation["adaptation_round"] == 3 for adaptation in result.strategy_adaptations)

    bull_confidences = [int(row["confidence"]) for row in result.bull_rounds]
    first_mean = mean(bull_confidences[:3])
    last_mean = mean(bull_confidences[-3:])
    assert last_mean - first_mean >= 5

    assert result.database_state["counts"]["judge_verdicts"] == 7


def test_bear_dominant_market(harness: TestHarness) -> None:
    scenario = ScenarioConfig(scenario_type="bear", num_rounds=7, intensity=1.0)
    result = harness.run_debate_scenario(scenario)

    assert result.debate_session is not None
    assert result.debate_session["winning_side"] == "bear"
    assert result.debate_session["total_rounds"] == 7

    bear_round_wins = sum(1 for verdict in result.judge_verdicts if verdict["winner"] == "bear")
    assert bear_round_wins >= 5

    final_bull_score = int(result.debate_session["final_bull_score"])
    final_bear_score = int(result.debate_session["final_bear_score"])
    assert final_bear_score - final_bull_score >= 15

    assert len(result.round_traces) == 7
    assert all(trace["judge_verdict_json"] is not None for trace in result.round_traces)
    assert all(event["severity"] != "halt" for event in result.safety_events)
    assert result.database_state["session_status"] == "DEBATE_ENDED"

    assert any(adaptation["adaptation_round"] == 3 for adaptation in result.strategy_adaptations)
    assert result.database_state["counts"]["judge_verdicts"] == 7

    bear_confidences = [int(row["confidence"]) for row in result.bear_rounds]
    first_mean = mean(bear_confidences[:3])
    last_mean = mean(bear_confidences[-3:])
    assert last_mean - first_mean >= 5


def _weights_stddev(adaptation: dict[str, Any]) -> float:
    weights = adaptation.get("new_weights_json") or {}
    if isinstance(weights, str):
        weights = json.loads(weights)
    if not isinstance(weights, dict) or not weights:
        return 0.0
    values = [float(value) for value in weights.values()]
    return float(pstdev(values)) if len(values) > 1 else 0.0


def test_choppy_market(harness: TestHarness) -> None:
    scenario = ScenarioConfig(scenario_type="choppy", num_rounds=10, intensity=1.0)
    result = harness.run_debate_scenario(scenario)

    assert result.debate_session is not None
    assert result.debate_session["total_rounds"] == 10
    assert result.debate_session["winning_side"] == "draw"

    bull_wins = sum(1 for verdict in result.judge_verdicts if verdict["winner"] == "bull")
    bear_wins = sum(1 for verdict in result.judge_verdicts if verdict["winner"] == "bear")
    assert max(bull_wins, bear_wins) <= 6

    final_bull_score = int(result.debate_session["final_bull_score"])
    final_bear_score = int(result.debate_session["final_bear_score"])
    assert 40 <= final_bull_score <= 60
    assert 40 <= final_bear_score <= 60

    assert len(result.round_traces) == 10
    assert result.stdout.count("Debate end condition met") == 1
    assert "round 10" in result.stdout.lower()

    adaptation_rounds = [item["adaptation_round"] for item in result.strategy_adaptations]
    assert 3 in adaptation_rounds
    assert 6 in adaptation_rounds

    round3 = next(item for item in result.strategy_adaptations if item["adaptation_round"] == 3 and item["agent"] == "bear")
    round6 = next(item for item in result.strategy_adaptations if item["adaptation_round"] == 6 and item["agent"] == "bear")
    assert _weights_stddev(round6) <= _weights_stddev(round3) + 0.08
    assert result.database_state["counts"]["judge_verdicts"] == 10


def test_axl_node_failure_mid_debate(harness: TestHarness) -> None:
    scenario = ScenarioConfig(scenario_type="bull", num_rounds=6, intensity=1.0, bull_failure_after_messages=3)
    result = harness.run_debate_scenario(scenario)

    assert result.debate_session is not None
    assert result.debate_session["status"] == "DEBATE_ENDED"
    assert result.debate_session["total_rounds"] == 6
    assert len(result.round_traces) == 6

    assert "Neutral placeholder used" not in str(result.round_traces[0]["bull_argument_json"].get("argument", ""))
    assert "Neutral placeholder used" not in str(result.round_traces[1]["bull_argument_json"].get("argument", ""))
    assert "Neutral placeholder used" not in str(result.round_traces[2]["bull_argument_json"].get("argument", ""))

    timeout_events = [event for event in result.safety_events if event["event_type"] == "axl_message_timeout"]
    assert len(timeout_events) >= 1
    timeout_rounds = {event["round_number"] for event in timeout_events}
    assert 4 in timeout_rounds
    assert 5 in timeout_rounds
    assert 6 in timeout_rounds

    assert "Neutral placeholder used" in str(result.round_traces[3]["bull_argument_json"].get("argument", ""))
    assert "Neutral placeholder used" in str(result.round_traces[4]["bull_argument_json"].get("argument", ""))
    assert "Neutral placeholder used" in str(result.round_traces[5]["bull_argument_json"].get("argument", ""))

    assert result.database_state["counts"]["judge_verdicts"] == 6
    assert result.database_state["session_status"] == "DEBATE_ENDED"


def test_keeperhub_gas_spike_retry(harness: TestHarness) -> None:
    scenario = ScenarioConfig(scenario_type="bull", num_rounds=3, intensity=1.0, keeperhub_gas_spike_mode=True)
    result = harness.run_debate_scenario(scenario)

    assert result.debate_session is not None
    assert result.debate_session["total_rounds"] == 3
    assert len(result.keeperhub_jobs) == 2
    assert len(result.keeperhub_retries) >= 4

    retry_reasons = {retry["retry_reason"] for retry in result.keeperhub_retries}
    assert "gas_too_high" in retry_reasons
    assert all(job["current_status"] == "confirmed" for job in result.keeperhub_jobs)

    durations = [float(trace["round_duration_seconds"]) for trace in result.round_traces]
    assert all(duration > scenario.round_interval_seconds + 15 for duration in durations[:2])
    assert result.database_state["counts"]["keeperhub_retries"] >= 4
    assert result.database_state["counts"]["keeperhub_jobs"] == 2


def test_judge_consistency_determinism(harness: TestHarness) -> None:
    snapshot = create_snapshot_sequence("bull", num_rounds=1, intensity=1.0)[0]
    bull_argument = {
        "argument": "Whale accumulation remains strong with clear volume expansion.",
        "confidence": 74,
        "keyMetrics": ["price_change_24h_percent: 15.00%", "volume_delta_percent: 25.00%"],
    }
    bear_argument = {
        "argument": "The tape is constructive but still vulnerable to a reversal.",
        "confidence": 41,
        "keyMetrics": ["price_change_24h_percent: 15.00%", "volume_delta_percent: 25.00%"],
    }

    harness.runtime = MockDebateRuntime(scenario_type="bull", snapshots=[snapshot])
    original_chain = judge_agent.JUDGE_CHAIN
    original_fallback = judge_agent.JUDGE_FALLBACK_CHAIN
    try:
        judge_agent.JUDGE_CHAIN = harness._require_runtime().judge_client
        judge_agent.JUDGE_FALLBACK_CHAIN = None
        first = judge_agent.score_round(bull_argument, bear_argument, 1, snapshot)
        second = judge_agent.score_round(bull_argument, bear_argument, 1, snapshot)
    finally:
        judge_agent.JUDGE_CHAIN = original_chain
        judge_agent.JUDGE_FALLBACK_CHAIN = original_fallback

    assert first["winner"] == second["winner"]
    assert abs(int(first["bullScore"]) - int(second["bullScore"])) <= 2
    assert abs(int(first["bearScore"]) - int(second["bearScore"])) <= 2
    assert first["bullScore"] > first["bearScore"]
    assert second["bullScore"] > second["bearScore"]
    assert first["accuracyBonusApplied"] is False
    assert second["accuracyBonusApplied"] is False
    assert len(first["bullCriteriaBreakdown"]) == 5
    assert len(first["bearCriteriaBreakdown"]) == 5
    assert first["reasoning"] == second["reasoning"]
