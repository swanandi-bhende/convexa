from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
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


class MarketPriceBaseline(Base):
    """Caches 24h baseline price for each token pair."""

    __tablename__ = "market_price_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_pair: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    pool_address: Mapped[str] = mapped_column(String(66), nullable=False)
    baseline_price: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
