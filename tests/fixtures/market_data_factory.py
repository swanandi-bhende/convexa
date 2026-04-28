from __future__ import annotations

from datetime import UTC, datetime, timedelta

from utils.market_data import MarketSnapshot


_TOKEN_PAIR = "ETH/USDC"


def _bounded_intensity(intensity: float) -> float:
    return max(0.5, min(1.5, float(intensity)))


def _build_snapshot(
    *,
    round_number: int,
    token_pair: str,
    current_price: float,
    price_change_24h_percent: float,
    price_change_2h_percent: float,
    volume_delta_percent: float,
    large_inflow_count: int,
    large_outflow_count: int,
    lp_net_flow_usd: float,
    funding_rate_proxy: float,
    volume_24h_usd: float,
    volume_48h_usd: float,
    recent_lp_additions_usd: float,
    recent_lp_removals_usd: float,
    pool_tvl_usd: float,
    net_wallet_flow_count: int,
    fetch_errors: list[str] | None = None,
) -> MarketSnapshot:
    timestamp = datetime.now(UTC) - timedelta(minutes=max(0, round_number - 1) * 6)
    price_24h_ago = current_price / (1.0 + (price_change_24h_percent / 100.0)) if price_change_24h_percent > -99.0 else current_price

    return MarketSnapshot(
        token_pair=token_pair,
        timestamp=timestamp,
        current_price=float(current_price),
        price_24h_ago=float(price_24h_ago),
        price_change_24h_percent=float(price_change_24h_percent),
        price_change_2h_percent=float(price_change_2h_percent),
        spot_price=float(current_price * 1.0002),
        reference_index_price=float(current_price * (0.998 if price_change_24h_percent >= 0 else 1.002)),
        funding_rate_proxy=float(funding_rate_proxy),
        volume_24h_usd=float(volume_24h_usd),
        volume_48h_usd=float(volume_48h_usd),
        volume_delta_percent=float(volume_delta_percent),
        pool_tvl_usd=float(pool_tvl_usd),
        recent_lp_additions_usd=float(recent_lp_additions_usd),
        recent_lp_removals_usd=float(recent_lp_removals_usd),
        lp_net_flow_usd=float(lp_net_flow_usd),
        large_inflow_count=int(large_inflow_count),
        large_outflow_count=int(large_outflow_count),
        net_wallet_flow_count=int(net_wallet_flow_count),
        data_freshness_seconds=float(8.0 + (round_number % 4)),
        fetch_errors=list(fetch_errors or []),
    )


def create_bull_market_snapshot(round_number: int, intensity: float) -> MarketSnapshot:
    intensity = _bounded_intensity(intensity)
    current_price = 1800.0 + (120.0 * intensity)
    price_change_24h_percent = 15.0 * intensity
    price_change_2h_percent = 4.5 * intensity
    volume_delta_percent = 25.0 * intensity
    large_inflow_count = int(round(8.0 * intensity))
    large_outflow_count = 2
    lp_net_flow_usd = 5000.0 * intensity
    funding_rate_proxy = 0.8 * intensity
    volume_24h_usd = 4_500_000.0 * intensity
    volume_48h_usd = volume_24h_usd / (1.0 + (volume_delta_percent / 100.0))
    recent_lp_additions_usd = 18_000.0 * intensity
    recent_lp_removals_usd = 7_000.0 * intensity
    pool_tvl_usd = 82_000_000.0 + (1_500_000.0 * intensity)
    net_wallet_flow_count = large_inflow_count - large_outflow_count
    return _build_snapshot(
        round_number=round_number,
        token_pair=_TOKEN_PAIR,
        current_price=current_price,
        price_change_24h_percent=price_change_24h_percent,
        price_change_2h_percent=price_change_2h_percent,
        volume_delta_percent=volume_delta_percent,
        large_inflow_count=large_inflow_count,
        large_outflow_count=large_outflow_count,
        lp_net_flow_usd=lp_net_flow_usd,
        funding_rate_proxy=funding_rate_proxy,
        volume_24h_usd=volume_24h_usd,
        volume_48h_usd=volume_48h_usd,
        recent_lp_additions_usd=recent_lp_additions_usd,
        recent_lp_removals_usd=recent_lp_removals_usd,
        pool_tvl_usd=pool_tvl_usd,
        net_wallet_flow_count=net_wallet_flow_count,
    )


def create_bear_market_snapshot(round_number: int, intensity: float) -> MarketSnapshot:
    intensity = _bounded_intensity(intensity)
    current_price = 1800.0 - (120.0 * intensity)
    price_change_24h_percent = -15.0 * intensity
    price_change_2h_percent = -4.5 * intensity
    volume_delta_percent = -25.0 * intensity
    large_inflow_count = 2
    large_outflow_count = int(round(8.0 * intensity))
    lp_net_flow_usd = -5000.0 * intensity
    funding_rate_proxy = -0.8 * intensity
    volume_24h_usd = 4_500_000.0 * intensity
    volume_48h_usd = volume_24h_usd / max(0.25, 1.0 + (volume_delta_percent / 100.0))
    recent_lp_additions_usd = 7_000.0 * intensity
    recent_lp_removals_usd = 18_000.0 * intensity
    pool_tvl_usd = 82_000_000.0 - (1_500_000.0 * intensity)
    net_wallet_flow_count = large_inflow_count - large_outflow_count
    return _build_snapshot(
        round_number=round_number,
        token_pair=_TOKEN_PAIR,
        current_price=current_price,
        price_change_24h_percent=price_change_24h_percent,
        price_change_2h_percent=price_change_2h_percent,
        volume_delta_percent=volume_delta_percent,
        large_inflow_count=large_inflow_count,
        large_outflow_count=large_outflow_count,
        lp_net_flow_usd=lp_net_flow_usd,
        funding_rate_proxy=funding_rate_proxy,
        volume_24h_usd=volume_24h_usd,
        volume_48h_usd=volume_48h_usd,
        recent_lp_additions_usd=recent_lp_additions_usd,
        recent_lp_removals_usd=recent_lp_removals_usd,
        pool_tvl_usd=pool_tvl_usd,
        net_wallet_flow_count=net_wallet_flow_count,
    )


def create_choppy_market_snapshot(round_number: int) -> MarketSnapshot:
    bullish_round = round_number % 2 == 1
    direction = 1.0 if bullish_round else -1.0
    current_price = 1800.0 + (8.0 * direction)
    price_change_24h_percent = 1.2 * direction
    price_change_2h_percent = 0.35 * direction
    volume_delta_percent = 1.8 * direction
    large_inflow_count = 4 if bullish_round else 3
    large_outflow_count = 3 if bullish_round else 4
    lp_net_flow_usd = 350.0 * direction
    funding_rate_proxy = 0.12 * direction
    volume_24h_usd = 2_400_000.0 + (40_000.0 * direction)
    volume_48h_usd = 2_380_000.0 - (35_000.0 * direction)
    recent_lp_additions_usd = 9_500.0 + (250.0 * direction)
    recent_lp_removals_usd = 9_100.0 - (250.0 * direction)
    pool_tvl_usd = 31_000_000.0 + (12_500.0 * direction)
    net_wallet_flow_count = large_inflow_count - large_outflow_count
    return _build_snapshot(
        round_number=round_number,
        token_pair=_TOKEN_PAIR,
        current_price=current_price,
        price_change_24h_percent=price_change_24h_percent,
        price_change_2h_percent=price_change_2h_percent,
        volume_delta_percent=volume_delta_percent,
        large_inflow_count=large_inflow_count,
        large_outflow_count=large_outflow_count,
        lp_net_flow_usd=lp_net_flow_usd,
        funding_rate_proxy=funding_rate_proxy,
        volume_24h_usd=volume_24h_usd,
        volume_48h_usd=volume_48h_usd,
        recent_lp_additions_usd=recent_lp_additions_usd,
        recent_lp_removals_usd=recent_lp_removals_usd,
        pool_tvl_usd=pool_tvl_usd,
        net_wallet_flow_count=net_wallet_flow_count,
    )


def create_snapshot_sequence(scenario_type: str, num_rounds: int, intensity: float = 1.0) -> list[MarketSnapshot]:
    scenario = scenario_type.strip().lower()
    snapshots: list[MarketSnapshot] = []

    for round_number in range(1, int(num_rounds) + 1):
        if scenario == "bull":
            round_intensity = _bounded_intensity(float(intensity) * (0.6 + 0.1 * round_number))
            snapshots.append(create_bull_market_snapshot(round_number, round_intensity))
        elif scenario == "bear":
            round_intensity = _bounded_intensity(float(intensity) * (0.6 + 0.1 * round_number))
            snapshots.append(create_bear_market_snapshot(round_number, round_intensity))
        elif scenario == "choppy":
            snapshots.append(create_choppy_market_snapshot(round_number))
        else:
            raise ValueError(f"Unsupported scenario_type: {scenario_type}")

    return snapshots
