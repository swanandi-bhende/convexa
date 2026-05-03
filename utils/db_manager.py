from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import Session, sessionmaker

from utils.db.schema import (
    AccuracyTracking,
    Base,
    BearRound,
    BullRound,
    DebateSession,
    JudgeVerdict,
    MarketPriceBaseline,
    RoundTrace,
    RoundComparison,
    ConvictionHistory,
    StressTestValidation,
)


DEFAULT_DATABASE_URL = "sqlite:///./utils/db/debate.db"
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


def _resolve_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _sqlite_connect_args(database_url: str) -> dict[str, Any]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


_ENGINE = create_engine(_resolve_database_url(), future=True, connect_args=_sqlite_connect_args(_resolve_database_url()))
_SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, future=True)


def init_database() -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(bind=_ENGINE)


def get_session() -> Session:
    """Return a new SQLAlchemy session."""
    return _SessionLocal()


def insert_bear_round(
    *,
    round_number: int,
    token_pair: str,
    argument: str,
    confidence: int,
    key_metrics: list[str],
    raw_market_data: dict[str, Any],
    axl_delivery_status: str = "pending",
) -> BearRound:
    """Insert a bear round log row and return the persisted ORM object."""
    with get_session() as session:
        row = BearRound(
            round_number=round_number,
            token_pair=token_pair,
            argument=argument,
            confidence=confidence,
            key_metrics=json.dumps(key_metrics),
            raw_market_data=json.dumps(raw_market_data),
            axl_delivery_status=axl_delivery_status,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_recent_bear_rounds(limit: int = 20) -> list[BearRound]:
    """Fetch most recent bear round entries."""
    with get_session() as session:
        stmt = select(BearRound).order_by(desc(BearRound.timestamp)).limit(limit)
        return list(session.scalars(stmt).all())


def insert_bull_round(
    *,
    round_number: int,
    token_pair: str,
    argument: str,
    confidence: int,
    key_metrics: list[str],
    raw_market_data: dict[str, Any],
    axl_delivery_status: str = "pending",
) -> BullRound:
    """Insert a bull round log row and return the persisted ORM object."""
    with get_session() as session:
        row = BullRound(
            round_number=round_number,
            token_pair=token_pair,
            argument=argument,
            confidence=confidence,
            key_metrics=json.dumps(key_metrics),
            raw_market_data=json.dumps(raw_market_data),
            axl_delivery_status=axl_delivery_status,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_recent_bull_rounds(limit: int = 20) -> list[BullRound]:
    """Fetch most recent bull round entries."""
    with get_session() as session:
        stmt = select(BullRound).order_by(desc(BullRound.timestamp)).limit(limit)
        return list(session.scalars(stmt).all())


def upsert_round_comparison_from_bull(*, round_number: int, bull_confidence: int, bull_axl_status: str) -> RoundComparison:
    """Upsert comparison state using a completed Bull round, merging Bear state when available."""
    with get_session() as session:
        bear_stmt = (
            select(BearRound)
            .where(BearRound.round_number == round_number)
            .order_by(desc(BearRound.timestamp))
            .limit(1)
        )
        bear_row = session.scalar(bear_stmt)

        comparison_stmt = (
            select(RoundComparison)
            .where(RoundComparison.round_number == round_number)
            .order_by(desc(RoundComparison.id))
            .limit(1)
        )
        comparison = session.scalar(comparison_stmt)

        if comparison is None:
            comparison = RoundComparison(
                round_number=round_number,
                bull_confidence=bull_confidence,
                bear_confidence=(int(bear_row.confidence) if bear_row is not None else None),
                bull_axl_status=bull_axl_status,
                bear_axl_status=(str(bear_row.axl_delivery_status) if bear_row is not None else None),
                both_received=bear_row is not None,
            )
            session.add(comparison)
        else:
            comparison.bull_confidence = bull_confidence
            comparison.bull_axl_status = bull_axl_status
            if bear_row is not None:
                comparison.bear_confidence = int(bear_row.confidence)
                comparison.bear_axl_status = str(bear_row.axl_delivery_status)
                comparison.both_received = True

        session.commit()
        session.refresh(comparison)
        return comparison


def get_market_price_baseline(token_pair: str) -> MarketPriceBaseline | None:
    """Get stored 24h baseline row for a token pair."""
    with get_session() as session:
        stmt = select(MarketPriceBaseline).where(MarketPriceBaseline.token_pair == token_pair)
        return session.scalar(stmt)


def upsert_market_price_baseline(token_pair: str, pool_address: str, baseline_price: float, baseline_timestamp: datetime) -> MarketPriceBaseline:
    """Create or update baseline cache for a token pair."""
    with get_session() as session:
        stmt = select(MarketPriceBaseline).where(MarketPriceBaseline.token_pair == token_pair)
        existing = session.scalar(stmt)
        if existing is None:
            existing = MarketPriceBaseline(
                token_pair=token_pair,
                pool_address=pool_address,
                baseline_price=baseline_price,
                baseline_timestamp=baseline_timestamp,
            )
            session.add(existing)
        else:
            existing.pool_address = pool_address
            existing.baseline_price = baseline_price
            existing.baseline_timestamp = baseline_timestamp

        session.commit()
        session.refresh(existing)
        return existing


def insert_judge_verdict(
    *,
    round_number: int,
    bull_score: int,
    bear_score: int,
    winner: str,
    reasoning: str,
    bull_argument_received: str,
    bear_argument_received: str,
    accuracy_bonus_applied: bool,
    accuracy_bonus_recipient: str | None,
    conviction_update_status: str,
) -> JudgeVerdict:
    """Insert one Judge verdict row and return the persisted ORM object."""
    with get_session() as session:
        row = JudgeVerdict(
            round_number=round_number,
            bull_score=bull_score,
            bear_score=bear_score,
            winner=winner,
            reasoning=reasoning,
            bull_argument_received=bull_argument_received,
            bear_argument_received=bear_argument_received,
            accuracy_bonus_applied=accuracy_bonus_applied,
            accuracy_bonus_recipient=accuracy_bonus_recipient,
            conviction_update_status=conviction_update_status,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def upsert_accuracy_tracking(
    *,
    round_number: int,
    predicted_winner: str,
    actual_price_direction: str,
    prediction_correct: bool,
    bonus_awarded: bool,
) -> AccuracyTracking:
    """Create or update accuracy tracking row for a completed round."""
    with get_session() as session:
        stmt = select(AccuracyTracking).where(AccuracyTracking.round_number == round_number)
        existing = session.scalar(stmt)
        if existing is None:
            existing = AccuracyTracking(
                round_number=round_number,
                predicted_winner=predicted_winner,
                actual_price_direction=actual_price_direction,
                prediction_correct=prediction_correct,
                bonus_awarded=bonus_awarded,
            )
            session.add(existing)
        else:
            existing.predicted_winner = predicted_winner
            existing.actual_price_direction = actual_price_direction
            existing.prediction_correct = prediction_correct
            existing.bonus_awarded = bonus_awarded

        session.commit()
        session.refresh(existing)
        return existing


def upsert_round_comparison_from_judge(
    *,
    round_number: int,
    bull_confidence: int,
    bear_confidence: int,
    bull_axl_status: str,
    bear_axl_status: str,
) -> RoundComparison:
    """Upsert round comparison after Judge receives or synthesizes both sides."""
    with get_session() as session:
        stmt = (
            select(RoundComparison)
            .where(RoundComparison.round_number == round_number)
            .order_by(desc(RoundComparison.id))
            .limit(1)
        )
        existing = session.scalar(stmt)

        both_received = bull_axl_status == "sent" and bear_axl_status == "sent"
        if existing is None:
            existing = RoundComparison(
                round_number=round_number,
                bull_confidence=bull_confidence,
                bear_confidence=bear_confidence,
                bull_axl_status=bull_axl_status,
                bear_axl_status=bear_axl_status,
                both_received=both_received,
            )
            session.add(existing)
        else:
            existing.bull_confidence = bull_confidence
            existing.bear_confidence = bear_confidence
            existing.bull_axl_status = bull_axl_status
            existing.bear_axl_status = bear_axl_status
            existing.both_received = both_received

        session.commit()
        session.refresh(existing)
        return existing


def insert_debate_session(
    *,
    session_id: str,
    token_pair: str,
    start_time: datetime,
    total_rounds: int,
    status: str,
) -> DebateSession:
    """Insert one debate session row and return the persisted ORM object."""
    with get_session() as session:
        row = DebateSession(
            session_id=session_id,
            token_pair=token_pair,
            start_time=start_time,
            end_time=None,
            total_rounds=total_rounds,
            winning_side=None,
            final_bull_score=None,
            final_bear_score=None,
            settlement_triggered=False,
            settlement_tx_hash=None,
            status=status,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_debate_session_by_session_id(session_id: str) -> DebateSession | None:
    """Fetch one debate session by logical session_id UUID."""
    with get_session() as session:
        stmt = select(DebateSession).where(DebateSession.session_id == session_id)
        return session.scalar(stmt)


def update_debate_session(session_id: str, **fields: Any) -> DebateSession:
    """Update one debate session row by session_id and return persisted object."""
    with get_session() as session:
        stmt = select(DebateSession).where(DebateSession.session_id == session_id)
        row = session.scalar(stmt)
        if row is None:
            raise ValueError(f"Debate session not found for session_id={session_id}")

        for key, value in fields.items():
            if not hasattr(row, key):
                raise ValueError(f"DebateSession has no field '{key}'")
            setattr(row, key, value)

        session.commit()
        session.refresh(row)
        return row


def upsert_round_trace(
    *,
    session_id: str,
    round_number: int,
    market_snapshot_json: dict[str, Any] | None = None,
    bull_argument_json: dict[str, Any] | None = None,
    bear_argument_json: dict[str, Any] | None = None,
    judge_verdict_json: dict[str, Any] | None = None,
    bull_score_after_round: int | None = None,
    bear_score_after_round: int | None = None,
    conviction_tx_hash: str | None = None,
    micro_settlement_tx_hash: str | None = None,
    round_duration_seconds: float | None = None,
    timestamp: datetime | None = None,
) -> RoundTrace:
    """Create or update a round audit row for a debate session."""
    with get_session() as session:
        stmt = (
            select(RoundTrace)
            .where(RoundTrace.session_id == session_id, RoundTrace.round_number == round_number)
            .limit(1)
        )
        existing = session.scalar(stmt)

        if existing is None:
            existing = RoundTrace(
                session_id=session_id,
                round_number=round_number,
                market_snapshot_json=(json.dumps(market_snapshot_json, default=str) if market_snapshot_json is not None else None),
                bull_argument_json=(json.dumps(bull_argument_json, default=str) if bull_argument_json is not None else None),
                bear_argument_json=(json.dumps(bear_argument_json, default=str) if bear_argument_json is not None else None),
                judge_verdict_json=(json.dumps(judge_verdict_json, default=str) if judge_verdict_json is not None else None),
                bull_score_after_round=bull_score_after_round,
                bear_score_after_round=bear_score_after_round,
                conviction_tx_hash=conviction_tx_hash,
                micro_settlement_tx_hash=micro_settlement_tx_hash,
                round_duration_seconds=round_duration_seconds,
                timestamp=timestamp or datetime.now(UTC),
            )
            session.add(existing)
        else:
            if market_snapshot_json is not None:
                existing.market_snapshot_json = json.dumps(market_snapshot_json, default=str)
            if bull_argument_json is not None:
                existing.bull_argument_json = json.dumps(bull_argument_json, default=str)
            if bear_argument_json is not None:
                existing.bear_argument_json = json.dumps(bear_argument_json, default=str)
            if judge_verdict_json is not None:
                existing.judge_verdict_json = json.dumps(judge_verdict_json, default=str)
            if bull_score_after_round is not None:
                existing.bull_score_after_round = bull_score_after_round
            if bear_score_after_round is not None:
                existing.bear_score_after_round = bear_score_after_round
            if conviction_tx_hash is not None:
                existing.conviction_tx_hash = conviction_tx_hash
            if micro_settlement_tx_hash is not None:
                existing.micro_settlement_tx_hash = micro_settlement_tx_hash
            if round_duration_seconds is not None:
                existing.round_duration_seconds = round_duration_seconds
            if timestamp is not None:
                existing.timestamp = timestamp

        session.commit()
        session.refresh(existing)
        return existing


def insert_stress_test_result(
    *,
    round_number: int,
    market_condition: str,
    bull_argument_text: str,
    bear_argument_text: str,
    bull_metrics_cited: list[str],
    bear_metrics_cited: list[str],
    metric_overlap_count: int,
    bull_json_valid: bool,
    bear_json_valid: bool,
    judge_bull_score: int,
    judge_bear_score: int,
    judge_winner: str,
    judge_reasoning: str,
    conviction_delta: float,
    conviction_delta_from_prev: float | None,
    bull_confidence: int,
    bear_confidence: int,
    qualitative_notes: str = "",
    groq_latency_ms: float = 0.0,
) -> None:
    """Insert one stress test result record."""
    from utils.db.schema import StressTestResult
    
    with get_session() as session:
        row = StressTestResult(
            round_number=round_number,
            market_condition=market_condition,
            bull_argument_text=bull_argument_text,
            bear_argument_text=bear_argument_text,
            bull_metrics_cited=json.dumps(bull_metrics_cited),
            bear_metrics_cited=json.dumps(bear_metrics_cited),
            metric_overlap_count=metric_overlap_count,
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
            qualitative_notes=qualitative_notes,
            groq_latency_ms=groq_latency_ms,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()


def get_all_stress_test_results() -> list[dict[str, Any]]:
    """Fetch all stress test results as list of dicts."""
    from utils.db.schema import StressTestResult
    
    with get_session() as session:
        stmt = select(StressTestResult).order_by(StressTestResult.round_number)
        rows = session.scalars(stmt).all()
        return [
            {
                "round_number": row.round_number,
                "market_condition": row.market_condition,
                "bull_argument_text": row.bull_argument_text,
                "bear_argument_text": row.bear_argument_text,
                "bull_metrics_cited": json.loads(row.bull_metrics_cited),
                "bear_metrics_cited": json.loads(row.bear_metrics_cited),
                "metric_overlap_count": row.metric_overlap_count,
                "bull_json_valid": row.bull_json_valid,
                "bear_json_valid": row.bear_json_valid,
                "judge_bull_score": row.judge_bull_score,
                "judge_bear_score": row.judge_bear_score,
                "judge_winner": row.judge_winner,
                "judge_reasoning": row.judge_reasoning,
                "conviction_delta": row.conviction_delta,
                "conviction_delta_from_prev": row.conviction_delta_from_prev,
                "bull_confidence": row.bull_confidence,
                "bear_confidence": row.bear_confidence,
                "qualitative_notes": row.qualitative_notes,
                "groq_latency_ms": row.groq_latency_ms,
                "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            }
            for row in rows
        ]


def insert_stress_test_validation_result(
    *,
    validation_run_id: str,
    round_number: int,
    market_condition: str,
    bull_argument_text: str,
    bear_argument_text: str,
    bull_metrics_cited: list[str],
    bear_metrics_cited: list[str],
    metric_overlap_count: int,
    bull_json_valid: bool,
    bear_json_valid: bool,
    judge_bull_score: int,
    judge_bear_score: int,
    judge_winner: str,
    judge_reasoning: str,
    conviction_delta: float,
    bull_conviction: float,
    bear_conviction: float,
    qualitative_notes: str = "",
) -> None:
    with get_session() as session:
        row = StressTestValidation(
            validation_run_id=validation_run_id,
            round_number=round_number,
            market_condition=market_condition,
            bull_argument_text=bull_argument_text,
            bear_argument_text=bear_argument_text,
            bull_metrics_cited=json.dumps(bull_metrics_cited),
            bear_metrics_cited=json.dumps(bear_metrics_cited),
            metric_overlap_count=metric_overlap_count,
            bull_json_valid=bull_json_valid,
            bear_json_valid=bear_json_valid,
            judge_bull_score=judge_bull_score,
            judge_bear_score=judge_bear_score,
            judge_winner=judge_winner,
            judge_reasoning=judge_reasoning,
            conviction_delta=conviction_delta,
            bull_conviction=bull_conviction,
            bear_conviction=bear_conviction,
            qualitative_notes=qualitative_notes,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()


def get_all_stress_test_validation_results() -> list[dict[str, Any]]:
    with get_session() as session:
        stmt = select(StressTestValidation).order_by(StressTestValidation.round_number)
        rows = session.scalars(stmt).all()
        return [
            {
                "validation_run_id": row.validation_run_id,
                "round_number": row.round_number,
                "market_condition": row.market_condition,
                "bull_argument_text": row.bull_argument_text,
                "bear_argument_text": row.bear_argument_text,
                "bull_metrics_cited": json.loads(row.bull_metrics_cited),
                "bear_metrics_cited": json.loads(row.bear_metrics_cited),
                "metric_overlap_count": row.metric_overlap_count,
                "bull_json_valid": row.bull_json_valid,
                "bear_json_valid": row.bear_json_valid,
                "judge_bull_score": row.judge_bull_score,
                "judge_bear_score": row.judge_bear_score,
                "judge_winner": row.judge_winner,
                "judge_reasoning": row.judge_reasoning,
                "conviction_delta": row.conviction_delta,
                "bull_conviction": row.bull_conviction,
                "bear_conviction": row.bear_conviction,
                "qualitative_notes": row.qualitative_notes,
                "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            }
            for row in rows
        ]


def insert_conviction_history(
    *,
    session_id: str,
    round_number: int,
    bull_score: int,
    bear_score: int,
    delta_from_previous_bull: int | None = None,
    delta_from_previous_bear: int | None = None,
    drift_flagged: bool = False,
) -> ConvictionHistory:
    with get_session() as session:
        row = ConvictionHistory(
            session_id=session_id,
            round_number=round_number,
            bull_score=bull_score,
            bear_score=bear_score,
            delta_from_previous_bull=delta_from_previous_bull,
            delta_from_previous_bear=delta_from_previous_bear,
            drift_flagged=drift_flagged,
            timestamp=datetime.now(UTC),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row


def get_conviction_history(session_id: str | None = None) -> list[dict[str, Any]]:
    with get_session() as session:
        stmt = select(ConvictionHistory).order_by(ConvictionHistory.round_number)
        if session_id is not None:
            stmt = stmt.where(ConvictionHistory.session_id == session_id)
        rows = session.scalars(stmt).all()
        return [
            {
                "session_id": row.session_id,
                "round_number": row.round_number,
                "bull_score": row.bull_score,
                "bear_score": row.bear_score,
                "delta_from_previous_bull": row.delta_from_previous_bull,
                "delta_from_previous_bear": row.delta_from_previous_bear,
                "drift_flagged": row.drift_flagged,
                "timestamp": row.timestamp.isoformat() if row.timestamp else "",
            }
            for row in rows
        ]
