from __future__ import annotations

from datetime import UTC, datetime

import pytest

from utils import constants
from utils.market_data import MarketSnapshot, SnapshotCache, _snapshot_from_dict, _snapshot_to_dict


@pytest.fixture(autouse=True)
def _reset_snapshot_cache(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    SnapshotCache._memory = {}
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'market_cache.db'}")


def test_resolve_token_address_handles_literals_and_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    literal = "0x4200000000000000000000000000000000000006"
    assert constants.resolve_token_address(literal, chain_id=1301) == literal

    monkeypatch.setitem(constants.TOKEN_ADDRESS_BY_SYMBOL[1301], "WETH", "0x1111111111111111111111111111111111111111")
    assert constants.resolve_token_address("WETH", chain_id=1301) == "0x1111111111111111111111111111111111111111"


def test_get_universal_router_address_prefers_override(monkeypatch: pytest.MonkeyPatch) -> None:
    assert constants.get_universal_router_address(1301) == constants.UNISWAP_UNIVERSAL_ROUTER_BY_CHAIN[1301]

    monkeypatch.setenv("UNISWAP_UNIVERSAL_ROUTER_ADDRESS", "0x2222222222222222222222222222222222222222")
    assert constants.get_universal_router_address(1301) == "0x2222222222222222222222222222222222222222"


def test_resolve_token_decimals_returns_expected_defaults() -> None:
    assert constants.resolve_token_decimals("ETH") == 18
    assert constants.resolve_token_decimals("USDC") == 6
    assert constants.resolve_token_decimals("UNKNOWN") == 18


def test_snapshot_round_trip_serialization() -> None:
    snapshot = MarketSnapshot(
        token_pair="ETH/USDC",
        timestamp=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
        current_price=1850.5,
        price_24h_ago=1780.0,
        price_change_24h_percent=3.95,
        price_change_2h_percent=1.25,
        spot_price=1851.0,
        reference_index_price=1848.0,
        funding_rate_proxy=0.8,
        volume_24h_usd=4_500_000.0,
        volume_48h_usd=4_200_000.0,
        volume_delta_percent=7.14,
        pool_tvl_usd=82_000_000.0,
        recent_lp_additions_usd=18_000.0,
        recent_lp_removals_usd=7_000.0,
        lp_net_flow_usd=5_000.0,
        large_inflow_count=8,
        large_outflow_count=2,
        net_wallet_flow_count=6,
        data_freshness_seconds=9.0,
        fetch_errors=[],
    )

    payload = _snapshot_to_dict(snapshot)
    restored = _snapshot_from_dict(payload)

    assert restored.token_pair == snapshot.token_pair
    assert restored.timestamp == snapshot.timestamp
    assert restored.current_price == snapshot.current_price
    assert restored.price_change_24h_percent == snapshot.price_change_24h_percent
    assert restored.fetch_errors == snapshot.fetch_errors
    assert snapshot.to_prompt_payload().startswith("{'token_pair': 'ETH/USDC'")


def test_snapshot_cache_round_trip_and_staleness() -> None:
    cache = SnapshotCache()
    cache.set("ETH/USDC", "price", {"price": 1850.5, "source": "mock"}, ttl_seconds=60)

    assert cache.get("ETH/USDC", "price") == {"price": 1850.5, "source": "mock"}
    assert cache.get_any("ETH/USDC", "price") == {"price": 1850.5, "source": "mock"}
    assert cache.is_stale("ETH/USDC", "price", max_age_seconds=120) is False

    SnapshotCache._memory[("ETH/USDC", "price")]["fetched_at"] -= 300.0
    assert cache.is_stale("ETH/USDC", "price", max_age_seconds=120) is True
