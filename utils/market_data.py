from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from web3 import Web3

from utils.db_manager import init_database

DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


SLOT0_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]

POOL_TOKENS_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
]

DEFAULT_PRICE_TTL_SECONDS = 30
DEFAULT_WALLET_TTL_SECONDS = 60
DEFAULT_LIQUIDITY_TTL_SECONDS = 120
DEFAULT_FUNDING_TTL_SECONDS = 45
DEFAULT_FULL_SNAPSHOT_TTL_SECONDS = 30


@dataclass(slots=True)
class MarketSnapshot:
    token_pair: str
    timestamp: datetime
    current_price: float
    price_24h_ago: float
    price_change_24h_percent: float
    price_change_2h_percent: float
    spot_price: float
    reference_index_price: float
    funding_rate_proxy: float
    volume_24h_usd: float
    volume_48h_usd: float
    volume_delta_percent: float
    pool_tvl_usd: float
    recent_lp_additions_usd: float
    recent_lp_removals_usd: float
    lp_net_flow_usd: float
    large_inflow_count: int
    large_outflow_count: int
    net_wallet_flow_count: int
    data_freshness_seconds: float
    fetch_errors: list[str]

    def to_prompt_payload(self) -> str:
        return str(asdict(self))


class SnapshotCache:
    _memory: dict[tuple[str, str], dict[str, Any]] = {}

    def __init__(self) -> None:
        self._db_path = _database_sqlite_path()
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_table(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data_cache (
                    token_pair TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    fetched_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (token_pair, data_source)
                )
                """
            )
            con.commit()

    def get(self, token_pair: str, data_source: str) -> dict[str, Any] | None:
        key = (token_pair, data_source)
        now_ts = datetime.now(UTC).timestamp()

        mem = self._memory.get(key)
        if mem is not None and float(mem.get("expires_at", 0.0)) >= now_ts:
            return dict(mem.get("data", {}))

        with self._connect() as con:
            row = con.execute(
                """
                SELECT data_json, fetched_at, expires_at
                FROM market_data_cache
                WHERE token_pair = ? AND data_source = ?
                """,
                (token_pair, data_source),
            ).fetchone()

        if row is None:
            return None

        data_json, fetched_at, expires_at = row
        if float(expires_at) < now_ts:
            return None

        data = _safe_json_loads(str(data_json))
        self._memory[key] = {"data": data, "fetched_at": float(fetched_at), "expires_at": float(expires_at)}
        return data

    def get_any(self, token_pair: str, data_source: str) -> dict[str, Any] | None:
        key = (token_pair, data_source)
        mem = self._memory.get(key)
        if mem is not None:
            return dict(mem.get("data", {}))

        with self._connect() as con:
            row = con.execute(
                """
                SELECT data_json, fetched_at, expires_at
                FROM market_data_cache
                WHERE token_pair = ? AND data_source = ?
                """,
                (token_pair, data_source),
            ).fetchone()

        if row is None:
            return None

        data_json, fetched_at, expires_at = row
        data = _safe_json_loads(str(data_json))
        self._memory[key] = {"data": data, "fetched_at": float(fetched_at), "expires_at": float(expires_at)}
        return data

    def set(self, token_pair: str, data_source: str, data: dict[str, Any], ttl_seconds: int) -> None:
        key = (token_pair, data_source)
        now_ts = datetime.now(UTC).timestamp()
        expires_at = now_ts + float(ttl_seconds)

        self._memory[key] = {"data": dict(data), "fetched_at": now_ts, "expires_at": expires_at}

        with self._connect() as con:
            con.execute(
                """
                INSERT INTO market_data_cache (token_pair, data_source, data_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(token_pair, data_source)
                DO UPDATE SET
                    data_json = excluded.data_json,
                    fetched_at = excluded.fetched_at,
                    expires_at = excluded.expires_at
                """,
                (token_pair, data_source, json.dumps(data), now_ts, expires_at),
            )
            con.commit()

    def is_stale(self, token_pair: str, data_source: str, max_age_seconds: int) -> bool:
        key = (token_pair, data_source)
        now_ts = datetime.now(UTC).timestamp()

        mem = self._memory.get(key)
        if mem is not None:
            return (now_ts - float(mem.get("fetched_at", 0.0))) > float(max_age_seconds)

        with self._connect() as con:
            row = con.execute(
                """
                SELECT fetched_at
                FROM market_data_cache
                WHERE token_pair = ? AND data_source = ?
                """,
                (token_pair, data_source),
            ).fetchone()

        if row is None:
            return True
        return (now_ts - float(row[0])) > float(max_age_seconds)


def _database_sqlite_path() -> Path:
    database_url = os.getenv("DATABASE_URL", "sqlite:///./utils/db/debate.db")
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return Path("./utils/db/debate.db").resolve()
    return Path(database_url[len(prefix) :]).expanduser().resolve()


def _pair_to_env_key(token_pair: str) -> str:
    return token_pair.replace("/", "_").replace("-", "_").upper()


def _safe_json_loads(payload: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _snapshot_to_dict(snapshot: MarketSnapshot) -> dict[str, Any]:
    payload = asdict(snapshot)
    payload["timestamp"] = snapshot.timestamp.isoformat()
    return payload


def _snapshot_from_dict(payload: dict[str, Any]) -> MarketSnapshot:
    timestamp_raw = payload.get("timestamp")
    timestamp = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00")) if timestamp_raw else datetime.now(UTC)
    return MarketSnapshot(
        token_pair=str(payload.get("token_pair") or ""),
        timestamp=timestamp,
        current_price=float(payload.get("current_price") or 0.0),
        price_24h_ago=float(payload.get("price_24h_ago") or 0.0),
        price_change_24h_percent=float(payload.get("price_change_24h_percent") or 0.0),
        price_change_2h_percent=float(payload.get("price_change_2h_percent") or 0.0),
        spot_price=float(payload.get("spot_price") or 0.0),
        reference_index_price=float(payload.get("reference_index_price") or 0.0),
        funding_rate_proxy=float(payload.get("funding_rate_proxy") or 0.0),
        volume_24h_usd=float(payload.get("volume_24h_usd") or 0.0),
        volume_48h_usd=float(payload.get("volume_48h_usd") or 0.0),
        volume_delta_percent=float(payload.get("volume_delta_percent") or 0.0),
        pool_tvl_usd=float(payload.get("pool_tvl_usd") or 0.0),
        recent_lp_additions_usd=float(payload.get("recent_lp_additions_usd") or 0.0),
        recent_lp_removals_usd=float(payload.get("recent_lp_removals_usd") or 0.0),
        lp_net_flow_usd=float(payload.get("lp_net_flow_usd") or 0.0),
        large_inflow_count=int(payload.get("large_inflow_count") or 0),
        large_outflow_count=int(payload.get("large_outflow_count") or 0),
        net_wallet_flow_count=int(payload.get("net_wallet_flow_count") or 0),
        data_freshness_seconds=float(payload.get("data_freshness_seconds") or 0.0),
        fetch_errors=[str(item) for item in (payload.get("fetch_errors") or [])],
    )


def _build_web3_client() -> Web3:
    rpc_url = os.getenv("MARKET_DATA_RPC_URL", os.getenv("ALCHEMY_RPC_URL"))
    if not rpc_url:
        raise ValueError("Missing MARKET_DATA_RPC_URL or ALCHEMY_RPC_URL")
    client = Web3(Web3.HTTPProvider(rpc_url))
    if not client.is_connected():
        raise ConnectionError(f"Could not connect to RPC at {rpc_url}")
    return client


def _token_addresses_for_pair(token_pair: str) -> tuple[str, str]:
    pair_key = _pair_to_env_key(token_pair)
    token_a = os.getenv(f"TOKEN_A_ADDRESS_{pair_key}")
    token_b = os.getenv(f"TOKEN_B_ADDRESS_{pair_key}")
    if token_a and token_b:
        return token_a, token_b

    if token_pair in {"ETH/USDC", "WETH/USDC"}:
        weth = os.getenv("WETH_ADDRESS")
        usdc = os.getenv("USDC_ADDRESS")
        if not weth or not usdc:
            raise ValueError("Missing WETH_ADDRESS/USDC_ADDRESS")
        return weth, usdc

    raise ValueError(f"Missing token addresses for {token_pair}")


def _token_decimals_for_pair(token_pair: str) -> tuple[int, int]:
    defaults = {"ETH/USDC": (18, 6), "WETH/USDC": (18, 6), "ETH/USDT": (18, 6), "WETH/USDT": (18, 6)}
    if token_pair in defaults:
        return defaults[token_pair]

    raw = os.getenv(f"TOKEN_DECIMALS_{_pair_to_env_key(token_pair)}")
    if not raw:
        return 18, 18
    left, right = raw.split(",")
    return int(left.strip()), int(right.strip())


def _pool_address_for_pair(token_pair: str) -> str:
    pool_address = os.getenv(f"UNISWAP_V3_POOL_{_pair_to_env_key(token_pair)}")
    if not pool_address:
        raise ValueError(f"Missing UNISWAP_V3_POOL_{_pair_to_env_key(token_pair)}")
    return pool_address


def _graph_endpoint() -> str:
    endpoint = os.getenv("THEGRAPH_UNISWAP_V3_ENDPOINT", "")
    if not endpoint:
        raise ValueError("Missing THEGRAPH_UNISWAP_V3_ENDPOINT")
    if "gateway.thegraph.com/api/subgraphs/id/" in endpoint:
        graph_key = os.getenv("THEGRAPH_API_KEY", "").strip()
        if not graph_key:
            raise ValueError("THEGRAPH_API_KEY is required for gateway.thegraph.com endpoints")
        endpoint = endpoint.replace("/api/subgraphs/id/", f"/api/{graph_key}/subgraphs/id/")
    return endpoint


def _graphql_request(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        _graph_endpoint(),
        json={"query": query, "variables": variables},
        timeout=20,
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise ValueError(f"GraphQL error: {payload['errors']}")
    return payload.get("data", {})


def _quote_per_base_from_slot0(
    *,
    sqrt_price_x96: int,
    token0: str,
    token1: str,
    base_token: str,
    quote_token: str,
    token0_decimals: int,
    token1_decimals: int,
) -> float:
    raw_price = (float(sqrt_price_x96) / float(2**96)) ** 2
    token1_per_token0 = raw_price * (10 ** (token0_decimals - token1_decimals))
    if token0 == base_token and token1 == quote_token:
        return float(token1_per_token0)
    if token0 == quote_token and token1 == base_token:
        return 0.0 if token1_per_token0 == 0 else float(1.0 / token1_per_token0)
    raise ValueError("Pool token ordering does not match configured pair")


def fetch_price_data(token_pair: str, cache: SnapshotCache | None = None) -> tuple[dict[str, Any], str | None]:
    cache = cache or SnapshotCache()
    source = "price"
    cached = cache.get(token_pair, source)
    if cached is not None and not cache.is_stale(token_pair, source, DEFAULT_PRICE_TTL_SECONDS):
        return cached, None

    try:
        web3_client = _build_web3_client()
        pool_address = _pool_address_for_pair(token_pair)
        pool = web3_client.eth.contract(address=Web3.to_checksum_address(pool_address), abi=SLOT0_ABI)
        pool_tokens = web3_client.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_TOKENS_ABI)

        token0 = Web3.to_checksum_address(pool_tokens.functions.token0().call())
        token1 = Web3.to_checksum_address(pool_tokens.functions.token1().call())

        base_token_raw, quote_token_raw = _token_addresses_for_pair(token_pair)
        base_token = Web3.to_checksum_address(base_token_raw)
        quote_token = Web3.to_checksum_address(quote_token_raw)
        base_decimals, quote_decimals = _token_decimals_for_pair(token_pair)
        decimals_map = {base_token: base_decimals, quote_token: quote_decimals}

        latest_block = int(web3_client.eth.block_number)
        block_24h = max(0, latest_block - 7200)
        block_2h = max(0, latest_block - 600)

        slot_latest = pool.functions.slot0().call()
        slot_24h = pool.functions.slot0().call(block_identifier=block_24h)
        slot_2h = pool.functions.slot0().call(block_identifier=block_2h)

        current_price = _quote_per_base_from_slot0(
            sqrt_price_x96=int(slot_latest[0]),
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            token0_decimals=decimals_map[token0],
            token1_decimals=decimals_map[token1],
        )
        price_24h_ago = _quote_per_base_from_slot0(
            sqrt_price_x96=int(slot_24h[0]),
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            token0_decimals=decimals_map[token0],
            token1_decimals=decimals_map[token1],
        )
        price_2h_ago = _quote_per_base_from_slot0(
            sqrt_price_x96=int(slot_2h[0]),
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            token0_decimals=decimals_map[token0],
            token1_decimals=decimals_map[token1],
        )

        result = {
            "pool_address": pool_address,
            "current_price": float(current_price),
            "price_24h_ago": float(price_24h_ago),
            "price_change_24h_percent": 0.0 if price_24h_ago == 0 else ((current_price - price_24h_ago) / price_24h_ago) * 100.0,
            "price_change_2h_percent": 0.0 if price_2h_ago == 0 else ((current_price - price_2h_ago) / price_2h_ago) * 100.0,
            "spot_price": float(current_price),
            "latest_block": latest_block,
            "block_24h": block_24h,
            "block_2h": block_2h,
            "fetched_at": datetime.now(UTC).timestamp(),
        }
        cache.set(token_pair, source, result, DEFAULT_PRICE_TTL_SECONDS)
        return result, None
    except Exception as exc:  # noqa: BLE001
        stale = cache.get_any(token_pair, source)
        if stale is not None:
            return stale, f"price source failed, used stale cache: {type(exc).__name__}: {exc}"
        raise


def fetch_wallet_flows(token_pair: str, cache: SnapshotCache | None = None) -> tuple[dict[str, Any], str | None]:
    cache = cache or SnapshotCache()
    source = "wallet_flows"
    cached = cache.get(token_pair, source)
    if cached is not None and not cache.is_stale(token_pair, source, DEFAULT_WALLET_TTL_SECONDS):
        return cached, None

    try:
        pool_address = _pool_address_for_pair(token_pair).lower()
        threshold_usd = float(os.getenv("LARGE_SWAP_USD_THRESHOLD", "1000"))
        since_ts = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())

        query = """
        query LargeSwaps($pool: String!, $since: Int!, $threshold: BigDecimal!) {
          swaps(first: 500, orderBy: timestamp, orderDirection: desc, where: { pool: $pool, timestamp_gte: $since, amountUSD_gt: $threshold }) {
            timestamp
            amountUSD
            amount0
            origin
          }
        }
        """

        data = _graphql_request(query, {"pool": pool_address, "since": since_ts, "threshold": str(threshold_usd)})
        swaps = data.get("swaps", [])
        inflow = 0
        outflow = 0
        oldest_ts = int(datetime.now(UTC).timestamp())
        for swap in swaps:
            amount0 = float(swap.get("amount0") or 0.0)
            event_ts = int(swap.get("timestamp") or 0)
            if event_ts > 0:
                oldest_ts = min(oldest_ts, event_ts)
            if amount0 > 0:
                inflow += 1
            elif amount0 < 0:
                outflow += 1

        result = {
            "large_inflow_count": inflow,
            "large_outflow_count": outflow,
            "net_wallet_flow_count": inflow - outflow,
            "oldest_wallet_timestamp": oldest_ts,
            "fetched_at": datetime.now(UTC).timestamp(),
        }
        cache.set(token_pair, source, result, DEFAULT_WALLET_TTL_SECONDS)
        return result, None
    except Exception as exc:  # noqa: BLE001
        stale = cache.get_any(token_pair, source)
        if stale is not None:
            return stale, f"wallet flow source failed, used stale cache: {type(exc).__name__}: {exc}"
        raise


def fetch_liquidity_data(token_pair: str, cache: SnapshotCache | None = None) -> tuple[dict[str, Any], str | None]:
    cache = cache or SnapshotCache()
    source = "liquidity"
    cached = cache.get(token_pair, source)
    if cached is not None and not cache.is_stale(token_pair, source, DEFAULT_LIQUIDITY_TTL_SECONDS):
        return cached, None

    try:
        pool_address = _pool_address_for_pair(token_pair).lower()
        now_ts = int(datetime.now(UTC).timestamp())
        since_2h = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())
        cutoff_48h = int((datetime.now(UTC) - timedelta(hours=48)).timestamp())

        tvl_query = """
        query PoolTvl($pool: String!) {
          pool(id: $pool) {
            id
            totalValueLockedUSD
            totalValueLockedToken0
            totalValueLockedToken1
          }
        }
        """
        events_query = """
        query LiquidityEvents($pool: String!, $since: Int!, $cutoff: Int!) {
          mints(first: 250, orderBy: timestamp, orderDirection: desc, where: { pool: $pool, timestamp_gte: $since }) {
            amountUSD
            timestamp
          }
          burns(first: 250, orderBy: timestamp, orderDirection: desc, where: { pool: $pool, timestamp_gte: $since }) {
            amountUSD
            timestamp
          }
          poolDayDatas(first: 3, orderBy: date, orderDirection: desc, where: { pool: $pool, date_gte: $cutoff }) {
            date
            volumeUSD
          }
        }
        """

        tvl_data = _graphql_request(tvl_query, {"pool": pool_address})
        events_data = _graphql_request(events_query, {"pool": pool_address, "since": since_2h, "cutoff": cutoff_48h})

        pool = tvl_data.get("pool") or {}
        mints = events_data.get("mints", [])
        burns = events_data.get("burns", [])
        day_rows = events_data.get("poolDayDatas", [])

        additions = sum(float(item.get("amountUSD") or 0.0) for item in mints)
        removals = sum(float(item.get("amountUSD") or 0.0) for item in burns)
        volume_24h = 0.0
        volume_48h = 0.0
        oldest_ts = now_ts

        for row in day_rows:
            row_ts = int(row.get("date") or 0)
            row_vol = float(row.get("volumeUSD") or 0.0)
            if row_ts > 0:
                oldest_ts = min(oldest_ts, row_ts)
            if row_ts >= now_ts - 86400:
                volume_24h += row_vol
            else:
                volume_48h += row_vol

        for event_row in mints + burns:
            row_ts = int(event_row.get("timestamp") or 0)
            if row_ts > 0:
                oldest_ts = min(oldest_ts, row_ts)

        volume_delta = 0.0 if volume_48h == 0 else ((volume_24h - volume_48h) / volume_48h) * 100.0
        result = {
            "pool_tvl_usd": float(pool.get("totalValueLockedUSD") or 0.0),
            "pool_tvl_token0": float(pool.get("totalValueLockedToken0") or 0.0),
            "pool_tvl_token1": float(pool.get("totalValueLockedToken1") or 0.0),
            "recent_lp_additions_usd": float(additions),
            "recent_lp_removals_usd": float(removals),
            "lp_net_flow_usd": float(additions - removals),
            "volume_24h_usd": float(volume_24h),
            "volume_48h_usd": float(volume_48h),
            "volume_delta_percent": float(volume_delta),
            "oldest_liquidity_timestamp": oldest_ts,
            "fetched_at": datetime.now(UTC).timestamp(),
        }
        cache.set(token_pair, source, result, DEFAULT_LIQUIDITY_TTL_SECONDS)
        return result, None
    except Exception as exc:  # noqa: BLE001
        stale = cache.get_any(token_pair, source)
        if stale is not None:
            return stale, f"liquidity source failed, used stale cache: {type(exc).__name__}: {exc}"
        raise


def fetch_funding_rate_proxy(token_pair: str, cache: SnapshotCache | None = None) -> tuple[dict[str, Any], str | None]:
    cache = cache or SnapshotCache()
    source = "funding_rate"
    cached = cache.get(token_pair, source)
    if cached is not None and not cache.is_stale(token_pair, source, DEFAULT_FUNDING_TTL_SECONDS):
        return cached, None

    try:
        price_data = cache.get_any(token_pair, "price")
        price_note: str | None = None
        if price_data is None:
            price_data, price_note = fetch_price_data(token_pair, cache=cache)

        uniswap_price = float(price_data.get("spot_price") or price_data.get("current_price") or 0.0)
        coingecko_id = os.getenv("COINGECKO_TOKEN_ID", "ethereum")
        quote_currency = os.getenv("COINGECKO_QUOTE_CURRENCY", "usd")
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": coingecko_id, "vs_currencies": quote_currency},
            timeout=10,
        )

        if response.status_code == 429:
            fallback_proxy = float(price_data.get("price_change_2h_percent") or 0.0)
            fallback = {
                "spot_price": uniswap_price,
                "reference_index_price": uniswap_price,
                "funding_rate_proxy": fallback_proxy,
                "oldest_funding_timestamp": float(price_data.get("fetched_at") or datetime.now(UTC).timestamp()),
                "fetched_at": datetime.now(UTC).timestamp(),
            }
            cache.set(token_pair, source, fallback, DEFAULT_FUNDING_TTL_SECONDS)
            note = "coingecko rate-limited; used slot0 2h change as funding proxy fallback"
            if price_note:
                note = f"{price_note}; {note}"
            return fallback, note

        response.raise_for_status()
        payload = response.json()
        reference_price = float(payload.get(coingecko_id, {}).get(quote_currency) or 0.0)
        if reference_price <= 0:
            raise ValueError("CoinGecko returned non-positive reference price")

        funding_rate_proxy = ((uniswap_price - reference_price) / reference_price) * 100.0
        result = {
            "spot_price": float(uniswap_price),
            "reference_index_price": float(reference_price),
            "funding_rate_proxy": float(funding_rate_proxy),
            "oldest_funding_timestamp": float(price_data.get("fetched_at") or datetime.now(UTC).timestamp()),
            "fetched_at": datetime.now(UTC).timestamp(),
        }
        cache.set(token_pair, source, result, DEFAULT_FUNDING_TTL_SECONDS)
        return result, price_note
    except Exception as exc:  # noqa: BLE001
        stale = cache.get_any(token_pair, source)
        if stale is not None:
            return stale, f"funding source failed, used stale cache: {type(exc).__name__}: {exc}"
        raise


def _compose_snapshot(
    *,
    token_pair: str,
    price_data: dict[str, Any],
    wallet_data: dict[str, Any],
    liquidity_data: dict[str, Any],
    funding_data: dict[str, Any],
    fetch_errors: list[str],
) -> MarketSnapshot:
    now_utc = datetime.now(UTC)
    freshness_points = [
        float(price_data.get("fetched_at") or now_utc.timestamp()),
        float(wallet_data.get("fetched_at") or now_utc.timestamp()),
        float(liquidity_data.get("fetched_at") or now_utc.timestamp()),
        float(funding_data.get("fetched_at") or now_utc.timestamp()),
    ]
    oldest = min(freshness_points) if freshness_points else now_utc.timestamp()

    return MarketSnapshot(
        token_pair=token_pair,
        timestamp=now_utc,
        current_price=float(price_data.get("current_price") or 0.0),
        price_24h_ago=float(price_data.get("price_24h_ago") or 0.0),
        price_change_24h_percent=float(price_data.get("price_change_24h_percent") or 0.0),
        price_change_2h_percent=float(price_data.get("price_change_2h_percent") or 0.0),
        spot_price=float(funding_data.get("spot_price") or price_data.get("spot_price") or 0.0),
        reference_index_price=float(funding_data.get("reference_index_price") or 0.0),
        funding_rate_proxy=float(funding_data.get("funding_rate_proxy") or 0.0),
        volume_24h_usd=float(liquidity_data.get("volume_24h_usd") or 0.0),
        volume_48h_usd=float(liquidity_data.get("volume_48h_usd") or 0.0),
        volume_delta_percent=float(liquidity_data.get("volume_delta_percent") or 0.0),
        pool_tvl_usd=float(liquidity_data.get("pool_tvl_usd") or 0.0),
        recent_lp_additions_usd=float(liquidity_data.get("recent_lp_additions_usd") or 0.0),
        recent_lp_removals_usd=float(liquidity_data.get("recent_lp_removals_usd") or 0.0),
        lp_net_flow_usd=float(liquidity_data.get("lp_net_flow_usd") or 0.0),
        large_inflow_count=int(wallet_data.get("large_inflow_count") or 0),
        large_outflow_count=int(wallet_data.get("large_outflow_count") or 0),
        net_wallet_flow_count=int(wallet_data.get("net_wallet_flow_count") or 0),
        data_freshness_seconds=float(max(0.0, now_utc.timestamp() - oldest)),
        fetch_errors=fetch_errors,
    )


def fetch_snapshot(token_pair: str) -> MarketSnapshot:
    init_database()
    cache = SnapshotCache()

    cached_full = cache.get(token_pair, "full_snapshot")
    if cached_full is not None and not cache.is_stale(token_pair, "full_snapshot", DEFAULT_FULL_SNAPSHOT_TTL_SECONDS):
        return _snapshot_from_dict(cached_full)

    errors: list[str] = []

    price_data, price_note = fetch_price_data(token_pair, cache=cache)
    if price_note:
        errors.append(price_note)

    wallet_data, wallet_note = fetch_wallet_flows(token_pair, cache=cache)
    if wallet_note:
        errors.append(wallet_note)

    liquidity_data, liquidity_note = fetch_liquidity_data(token_pair, cache=cache)
    if liquidity_note:
        errors.append(liquidity_note)

    funding_data, funding_note = fetch_funding_rate_proxy(token_pair, cache=cache)
    if funding_note:
        errors.append(funding_note)

    snapshot = _compose_snapshot(
        token_pair=token_pair,
        price_data=price_data,
        wallet_data=wallet_data,
        liquidity_data=liquidity_data,
        funding_data=funding_data,
        fetch_errors=errors,
    )
    cache.set(token_pair, "full_snapshot", _snapshot_to_dict(snapshot), DEFAULT_FULL_SNAPSHOT_TTL_SECONDS)
    return snapshot


def fetch_market_snapshot(token_pair: str) -> MarketSnapshot:
    return fetch_snapshot(token_pair)


def _metric_lines(snapshot: MarketSnapshot) -> list[str]:
    return [
        f"24h price change: {snapshot.price_change_24h_percent:.2f}%",
        f"2h price change: {snapshot.price_change_2h_percent:.2f}%",
        f"current price: {snapshot.current_price:.2f}",
        f"price 24h ago: {snapshot.price_24h_ago:.2f}",
        f"spot price: {snapshot.spot_price:.2f}",
        f"reference index price: {snapshot.reference_index_price:.2f}",
        f"funding rate proxy: {snapshot.funding_rate_proxy:.2f}%",
        f"24h volume usd: {snapshot.volume_24h_usd:.2f}",
        f"48h prior-window volume usd: {snapshot.volume_48h_usd:.2f}",
        f"volume delta percent: {snapshot.volume_delta_percent:.2f}%",
        f"pool tvl usd: {snapshot.pool_tvl_usd:.2f}",
        f"recent lp additions usd: {snapshot.recent_lp_additions_usd:.2f}",
        f"recent lp removals usd: {snapshot.recent_lp_removals_usd:.2f}",
        f"lp net flow usd: {snapshot.lp_net_flow_usd:.2f}",
        f"large inflow count: {snapshot.large_inflow_count}",
        f"large outflow count: {snapshot.large_outflow_count}",
        f"net wallet flow count: {snapshot.net_wallet_flow_count}",
        f"data freshness seconds: {snapshot.data_freshness_seconds:.2f}",
        f"fetch errors count: {len(snapshot.fetch_errors)}",
    ]


def format_for_bear(snapshot: MarketSnapshot, weights: dict[str, float] | None = None) -> str:
    lines = _metric_lines(snapshot)
    weights = weights or {}

    # Map metric name (before colon) to line
    metric_map: list[tuple[str, str, float]] = []
    for line in lines:
        name = line.split(":", 1)[0].strip()
        w = float(weights.get(name, 1.0))
        metric_map.append((name, line, w))

    # Sort by weight desc
    metric_map.sort(key=lambda t: t[2], reverse=True)

    key_lines = []
    normal_lines = []
    weak_lines = []
    for name, line, w in metric_map:
        if w > 1.5:
            key_lines.append(f"[KEY SIGNAL] {line}")
        elif w < 0.5:
            weak_lines.append(line)
        else:
            normal_lines.append(line)

    ordered = key_lines + normal_lines
    top3 = ordered[:3]
    result_parts = []
    result_parts.append(f"Bear view for {snapshot.token_pair}. Most bearish first: {' | '.join(top3)}.")
    result_parts.append(f"Complete metrics: {' ; '.join(ordered + weak_lines)}.")
    if weak_lines:
        result_parts.append(f"[WEAK SIGNAL] { ' ; '.join(weak_lines)}")
    return " ".join(result_parts)


def format_for_bull(snapshot: MarketSnapshot, weights: dict[str, float] | None = None) -> str:
    lines = _metric_lines(snapshot)
    weights = weights or {}

    metric_map: list[tuple[str, str, float]] = []
    for line in lines:
        name = line.split(":", 1)[0].strip()
        w = float(weights.get(name, 1.0))
        metric_map.append((name, line, w))

    metric_map.sort(key=lambda t: t[2], reverse=True)

    key_lines = []
    normal_lines = []
    weak_lines = []
    for name, line, w in metric_map:
        if w > 1.5:
            key_lines.append(f"[KEY SIGNAL] {line}")
        elif w < 0.5:
            weak_lines.append(line)
        else:
            normal_lines.append(line)

    ordered = key_lines + normal_lines
    top3 = ordered[:3]
    result_parts = []
    result_parts.append(f"Bull view for {snapshot.token_pair}. Most accumulation first: {' | '.join(top3)}.")
    result_parts.append(f"Complete metrics: {' ; '.join(ordered + weak_lines)}.")
    if weak_lines:
        result_parts.append(f"[WEAK SIGNAL] { ' ; '.join(weak_lines)}")
    return " ".join(result_parts)


def _print_snapshot_fields(snapshot: MarketSnapshot) -> None:
    print("\nSnapshot fields with values and types:")
    for field_info in fields(snapshot):
        value = getattr(snapshot, field_info.name)
        print(f"- {field_info.name}: {value} ({type(value).__name__})")


def _print_quality_report(snapshot: MarketSnapshot) -> None:
    suspicious: list[str] = []
    if abs(snapshot.price_change_24h_percent) > 50:
        suspicious.append("price_change_24h_percent outside expected range (>50%)")
    if snapshot.pool_tvl_usd < 1000:
        suspicious.append("pool_tvl_usd below 1000, verify pool address")
    if abs(snapshot.funding_rate_proxy) > 25:
        suspicious.append("funding_rate_proxy unusually large (>25%)")
    if snapshot.data_freshness_seconds > 120:
        suspicious.append("data_freshness_seconds above 120")

    print("\nData quality report:")
    print(f"- freshness_ok: {snapshot.data_freshness_seconds < 120}")
    if suspicious:
        print("- suspicious_fields:")
        for item in suspicious:
            print(f"  - {item}")
    else:
        print("- suspicious_fields: none")


if __name__ == "__main__":
    init_database()
    print("Running market_data validator for ETH/USDC...")

    start_one = time.perf_counter()
    first = fetch_snapshot("ETH/USDC")
    elapsed_one_ms = (time.perf_counter() - start_one) * 1000.0
    _print_snapshot_fields(first)

    start_two = time.perf_counter()
    second = fetch_snapshot("ETH/USDC")
    elapsed_two_ms = (time.perf_counter() - start_two) * 1000.0

    print("\nCache timing check:")
    print(f"- first_call_ms: {elapsed_one_ms:.2f}")
    print(f"- second_call_ms: {elapsed_two_ms:.2f}")
    print(f"- second_call_under_50ms: {elapsed_two_ms < 50.0}")

    print("\nBear formatted output:")
    print(format_for_bear(first))

    print("\nBull formatted output:")
    print(format_for_bull(first))

    print("\nFetch error check:")
    print(f"- fetch_errors_empty: {len(first.fetch_errors) == 0}")
    if first.fetch_errors:
        for error in first.fetch_errors:
            print(f"  - {error}")

    _print_quality_report(first)
    print(f"\nSecond snapshot timestamp: {second.timestamp.isoformat()}")
