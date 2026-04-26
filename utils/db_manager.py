from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, desc, select
from sqlalchemy.orm import Session, sessionmaker

from utils.db.schema import Base, BearRound, MarketPriceBaseline


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
