from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


class BearRound(Base):
    """Stores one Bear agent output per round."""

    __tablename__ = "bear_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    token_pair: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    argument: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    key_metrics: Mapped[str] = mapped_column(Text, nullable=False)
    raw_market_data: Mapped[str] = mapped_column(Text, nullable=False)
    axl_delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class BullRound(Base):
    """Stores one Bull agent output per round."""

    __tablename__ = "bull_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    token_pair: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    argument: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    key_metrics: Mapped[str] = mapped_column(Text, nullable=False)
    raw_market_data: Mapped[str] = mapped_column(Text, nullable=False)
    axl_delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class RoundComparison(Base):
    """Tracks whether both Bull and Bear outputs were delivered for each round."""

    __tablename__ = "round_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bull_confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    bear_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bull_axl_status: Mapped[str] = mapped_column(String(16), nullable=False)
    bear_axl_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    both_received: Mapped[bool] = mapped_column(nullable=False, default=False)


class MarketPriceBaseline(Base):
    """Caches 24h baseline price for each token pair."""

    __tablename__ = "market_price_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_pair: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    pool_address: Mapped[str] = mapped_column(String(66), nullable=False)
    baseline_price: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class JudgeVerdict(Base):
    """Stores one Judge verdict per round including delivery and onchain update status."""

    __tablename__ = "judge_verdicts"
    __table_args__ = (
        CheckConstraint("bull_score >= 0 AND bull_score <= 100", name="ck_judge_verdicts_bull_score_0_100"),
        CheckConstraint("bear_score >= 0 AND bear_score <= 100", name="ck_judge_verdicts_bear_score_0_100"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bull_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bear_score: Mapped[int] = mapped_column(Integer, nullable=False)
    winner: Mapped[str] = mapped_column(String(8), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    bull_argument_received: Mapped[str] = mapped_column(Text, nullable=False)
    bear_argument_received: Mapped[str] = mapped_column(Text, nullable=False)
    accuracy_bonus_applied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accuracy_bonus_recipient: Mapped[str | None] = mapped_column(String(8), nullable=True)
    conviction_update_status: Mapped[str] = mapped_column(String(16), nullable=False, default="failed")
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AccuracyTracking(Base):
    """Tracks whether previous round winners predicted the realized market direction correctly."""

    __tablename__ = "accuracy_tracking"

    round_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    predicted_winner: Mapped[str] = mapped_column(String(8), nullable=False)
    actual_price_direction: Mapped[str] = mapped_column(String(8), nullable=False)
    prediction_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    bonus_awarded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DebateSession(Base):
    """Stores top-level lifecycle and settlement details for each debate session."""

    __tablename__ = "debate_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    token_pair: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    winning_side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    final_bull_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_bear_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    settlement_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settlement_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="IDLE", index=True)


class RoundTrace(Base):
    """Complete per-round audit trail with raw artifacts and onchain side effects."""

    __tablename__ = "round_trace"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    round_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    bull_argument_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    bear_argument_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_verdict_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    bull_score_after_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bear_score_after_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conviction_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    micro_settlement_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    round_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
