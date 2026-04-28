from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
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


class SwapQuote(Base):
    """Stores each quote request/response pair for micro and final settlement swaps."""

    __tablename__ = "swap_quotes"
    __table_args__ = (
        CheckConstraint(
            "swap_type IN ('micro_settlement', 'final_settlement')",
            name="ck_swap_quotes_swap_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    swap_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    token_in: Mapped[str] = mapped_column(String(66), nullable=False)
    token_out: Mapped[str] = mapped_column(String(66), nullable=False)
    amount_in_wei: Mapped[str] = mapped_column(String(128), nullable=False)
    quoted_amount_out_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quoted_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    route_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gas_estimate_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    slippage_tolerance_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    quote_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    quote_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class SwapExecution(Base):
    """Stores transaction execution outcomes linked to previously fetched swap quotes."""

    __tablename__ = "swap_executions"
    __table_args__ = (
        CheckConstraint(
            "swap_type IN ('micro_settlement', 'final_settlement')",
            name="ck_swap_executions_swap_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'failed', 'pending_timeout')",
            name="ck_swap_executions_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    swap_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("swap_quotes.id"), nullable=True, index=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    token_in: Mapped[str] = mapped_column(String(66), nullable=False)
    token_out: Mapped[str] = mapped_column(String(66), nullable=False)
    amount_in_actual_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount_out_actual_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage_realized_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    gas_used_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gas_price_gwei: Mapped[float | None] = mapped_column(Float, nullable=True)
    keeperhub_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SwapWarning(Base):
    """Stores anomalous execution warnings for post-trade analysis and reporting."""

    __tablename__ = "swap_warnings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    warning_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("swap_quotes.id"), nullable=True, index=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("swap_executions.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class KeeperHubJob(Base):
    """Tracks KeeperHub-submitted execution jobs for swaps and conviction updates."""

    __tablename__ = "keeperhub_jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('micro_settlement', 'final_settlement', 'conviction_update')",
            name="ck_keeperhub_jobs_job_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    job_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    swap_quote_id: Mapped[int | None] = mapped_column(ForeignKey("swap_quotes.id"), nullable=True, index=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    max_gas_price_gwei: Mapped[float | None] = mapped_column(Float, nullable=True)
    deadline_timestamp: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_policy_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[str] = mapped_column(String(32), nullable=False, default="submitted", index=True)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    actual_gas_price_gwei: Mapped[float | None] = mapped_column(Float, nullable=True)
    keeperhub_fee_wei: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class KeeperHubRetry(Base):
    """Normalized retry history for KeeperHub jobs."""

    __tablename__ = "keeperhub_retries"

    job_id: Mapped[str] = mapped_column(ForeignKey("keeperhub_jobs.job_id"), primary_key=True)
    retry_attempt_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    retry_reason: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retry_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    retry_outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SafetyEvent(Base):
    """Logs all risk management decisions and safety events during debate rounds."""

    __tablename__ = "safety_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('stale_data', 'conviction_drift', 'low_stake', 'debate_timeout', 'invalid_axl_signature', 'gas_spike', 'data_source_failure', 'axl_message_timeout')",
            name="ck_safety_events_event_type",
        ),
        CheckConstraint(
            "severity IN ('warning', 'pause', 'halt')",
            name="ck_safety_events_severity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(128), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class ConvictionHistory(Base):
    """Tracks conviction score movements across rounds to detect drift patterns."""

    __tablename__ = "conviction_history"
    __table_args__ = (
        CheckConstraint("bull_score >= 0 AND bull_score <= 100", name="ck_conviction_history_bull_score"),
        CheckConstraint("bear_score >= 0 AND bear_score <= 100", name="ck_conviction_history_bear_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    bull_score: Mapped[int] = mapped_column(Integer, nullable=False)
    bear_score: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_from_previous_bull: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delta_from_previous_bear: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drift_flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AXLMessageAudit(Base):
    """Audits all AXL messages received from Judge with validation status and acceptance."""

    __tablename__ = "axl_message_audit"
    __table_args__ = (
        CheckConstraint(
            "sender_claimed IN ('bull', 'bear')",
            name="ck_axl_message_audit_sender_claimed",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sender_claimed: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    sender_peer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    message_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    signature_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class AgentMemorySnapshot(Base):
    """Persistent serialized snapshots of an agent's LangChain memory."""

    __tablename__ = "agent_memory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_json: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class ArgumentPerformance(Base):
    """Raw per-argument performance records used for learning."""

    __tablename__ = "argument_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    argument_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_submitted: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_score_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_cited: Mapped[str] = mapped_column(Text, nullable=False)
    won_round: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    accuracy_bonus_received: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class MetricCorrelation(Base):
    """Derived per-metric statistics used by StrategyAdapter."""

    __tablename__ = "metric_correlations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    times_cited: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    times_cited_in_winning_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class StrategyAdaptation(Base):
    """Auditable record of strategy weight adaptations performed by agents."""

    __tablename__ = "strategy_adaptations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    adaptation_round: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    new_weights_json: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class GasPriceHistory(Base):
    """Rolling history of gas prices for spike detection and baseline calculation."""

    __tablename__ = "gas_price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    gas_price_gwei: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
