from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import Session, sessionmaker

from utils.db.schema import Base, BearRound, BullRound, MarketPriceBaseline, RoundComparison


DEFAULT_DATABASE_URL = "sqlite:///./utils/db/debate.db"


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
            timestamp=datetime.utcnow(),
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
            timestamp=datetime.utcnow(),
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
