from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput

from utils.db_manager import get_market_price_baseline, init_database, upsert_market_price_baseline


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

FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"},
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

SWAP_EVENT_ABI = {
    "anonymous": False,
    "inputs": [
        {"indexed": True, "internalType": "address", "name": "sender", "type": "address"},
        {"indexed": True, "internalType": "address", "name": "recipient", "type": "address"},
        {"indexed": False, "internalType": "int256", "name": "amount0", "type": "int256"},
        {"indexed": False, "internalType": "int256", "name": "amount1", "type": "int256"},
        {"indexed": False, "internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
        {"indexed": False, "internalType": "uint128", "name": "liquidity", "type": "uint128"},
        {"indexed": False, "internalType": "int24", "name": "tick", "type": "int24"},
    ],
    "name": "Swap",
    "type": "event",
}


@dataclass(slots=True)
class MarketSnapshot:
    token_pair: str
    pool_address: str
    current_price: float
    baseline_price_24h: float
    price_change_24h_pct: float
    volume_last_24h_usd: float
    volume_prev_24h_usd: float
    volume_delta_24h_pct: float
    wallet_outflow_count_2h: int
    fetched_at: datetime
    raw_market_data: dict[str, Any]

    def to_prompt_payload(self) -> str:
        """Return a compact string representation for LLM prompts."""
        return str(asdict(self))


def _pair_to_env_key(token_pair: str) -> str:
    return token_pair.replace("/", "_").replace("-", "_").upper()


def _is_zero_or_placeholder_address(value: str | None) -> bool:
    if not value:
        return True

    lowered = value.strip().lower()
    return lowered in {
        "",
        "your_uniswap_v3_pool_address",
        "0x0000000000000000000000000000000000000000",
    }


def _token_addresses_for_pair(token_pair: str) -> tuple[str, str]:
    pair_key = _pair_to_env_key(token_pair)
    token_a_env = f"TOKEN_A_ADDRESS_{pair_key}"
    token_b_env = f"TOKEN_B_ADDRESS_{pair_key}"
    token_a = os.getenv(token_a_env)
    token_b = os.getenv(token_b_env)

    if token_a and token_b:
        return token_a, token_b

    if token_pair == "ETH/USDC":
        weth = os.getenv("WETH_ADDRESS")
        usdc = os.getenv("USDC_ADDRESS")
        if not weth or not usdc:
            raise ValueError(
                "Missing WETH_ADDRESS/USDC_ADDRESS for ETH/USDC. "
                f"Alternatively set {token_a_env} and {token_b_env}."
            )
        return weth, usdc

    raise ValueError(
        f"Missing token addresses for {token_pair}. "
        f"Set {token_a_env} and {token_b_env} in environment."
    )


def _pool_fee_tiers() -> list[int]:
    raw_fees = os.getenv("UNISWAP_V3_POOL_FEES", "500,3000,10000")
    try:
        fees = [int(item.strip()) for item in raw_fees.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError("UNISWAP_V3_POOL_FEES must be a comma-separated integer list") from exc

    if not fees:
        raise ValueError("UNISWAP_V3_POOL_FEES produced an empty fee list")
    return fees


def discover_pool_for_pair(token_pair: str, web3_client: Web3 | None = None) -> dict[str, Any]:
    """Find candidate Uniswap V3 pool addresses for a pair across configured fee tiers."""
    web3 = web3_client or _build_web3_client()
    factory_address = os.getenv("UNISWAP_V3_FACTORY_ADDRESS")
    if _is_zero_or_placeholder_address(factory_address) or str(factory_address).startswith("your_"):
        raise ValueError("Missing UNISWAP_V3_FACTORY_ADDRESS in environment")

    token_a, token_b = _token_addresses_for_pair(token_pair)
    if str(token_a).startswith("your_") or str(token_b).startswith("your_"):
        raise ValueError(
            f"Set real token addresses for {token_pair}: TOKEN_A_ADDRESS_{_pair_to_env_key(token_pair)} / "
            f"TOKEN_B_ADDRESS_{_pair_to_env_key(token_pair)} or WETH_ADDRESS / USDC_ADDRESS."
        )

    fees = _pool_fee_tiers()

    chain_id = int(web3.eth.chain_id)
    factory_checksum = Web3.to_checksum_address(factory_address)
    code = web3.eth.get_code(factory_checksum)
    if len(code) == 0:
        raise ValueError(
            "UNISWAP_V3_FACTORY_ADDRESS has no bytecode on current chain. "
            f"chain_id={chain_id}, address={factory_address}. "
            "Use the Unichain Sepolia-specific factory address or switch to a network with Uniswap V3 deployed."
        )

    factory = web3.eth.contract(address=factory_checksum, abi=FACTORY_ABI)
    results: list[dict[str, Any]] = []
    selected_pool: str | None = None
    selected_fee: int | None = None

    for fee in fees:
        try:
            pool = factory.functions.getPool(
                Web3.to_checksum_address(token_a),
                Web3.to_checksum_address(token_b),
                int(fee),
            ).call()
        except BadFunctionCallOutput as exc:
            raise ValueError(
                "Factory contract call failed for getPool(tokenA, tokenB, fee). "
                f"chain_id={chain_id}, factory={factory_address}. "
                "This usually means the address is not a Uniswap V3 factory on this network."
            ) from exc
        normalized_pool = str(pool)
        is_missing = normalized_pool.lower() == "0x0000000000000000000000000000000000000000"
        results.append({"fee": fee, "pool": normalized_pool, "exists": not is_missing})
        if (not is_missing) and selected_pool is None:
            selected_pool = normalized_pool
            selected_fee = fee

    return {
        "token_pair": token_pair,
        "chain_id": chain_id,
        "factory": factory_address,
        "token_a": token_a,
        "token_b": token_b,
        "checked_fees": fees,
        "results": results,
        "selected_pool": selected_pool,
        "selected_fee": selected_fee,
    }


def _pool_address_for_pair(token_pair: str, web3_client: Web3 | None = None) -> tuple[str, dict[str, Any]]:
    env_key = f"UNISWAP_V3_POOL_{_pair_to_env_key(token_pair)}"
    explicit_pool = os.getenv(env_key)
    if not _is_zero_or_placeholder_address(explicit_pool):
        return str(explicit_pool), {"source": "env", "env_key": env_key}

    discovery = discover_pool_for_pair(token_pair, web3_client=web3_client)
    selected_pool = discovery.get("selected_pool")
    if not selected_pool:
        raise ValueError(
            f"No Uniswap V3 pool found for {token_pair} across fee tiers {discovery['checked_fees']}. "
            "Either deploy a pool, switch network, or set a known UNISWAP_V3_POOL_* value."
        )
    return str(selected_pool), {"source": "factory:getPool", "details": discovery}


def _token_decimals_for_pair(token_pair: str) -> tuple[int, int]:
    defaults = {"ETH/USDC": (18, 6), "WETH/USDC": (18, 6), "ETH/USDT": (18, 6), "WETH/USDT": (18, 6)}
    if token_pair in defaults:
        return defaults[token_pair]

    env_key = f"TOKEN_DECIMALS_{_pair_to_env_key(token_pair)}"
    raw = os.getenv(env_key)
    if not raw:
        return 18, 18

    try:
        token0_decimals, token1_decimals = raw.split(",")
        return int(token0_decimals.strip()), int(token1_decimals.strip())
    except ValueError as exc:
        raise ValueError(f"Invalid {env_key}, expected format: 18,6") from exc


def _build_web3_client() -> Web3:
    rpc_url = os.getenv("MARKET_DATA_RPC_URL", os.getenv("ALCHEMY_RPC_URL"))
    if not rpc_url:
        raise ValueError("Missing MARKET_DATA_RPC_URL or ALCHEMY_RPC_URL in environment")

    web3_client = Web3(Web3.HTTPProvider(rpc_url))
    if not web3_client.is_connected():
        raise ConnectionError(f"Could not connect to market data RPC at {rpc_url}")
    return web3_client


def _graph_pool_price(pool_address: str, token_pair: str) -> tuple[float, dict[str, Any]]:
    endpoint = os.getenv("THEGRAPH_UNISWAP_V3_ENDPOINT", "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
    base_token, quote_token = _token_addresses_for_pair(token_pair)

    query = """
    query PoolPrice($pool: String!) {
      pool(id: $pool) {
        id
        token0 {
          id
          symbol
        }
        token1 {
          id
          symbol
        }
        token0Price
        token1Price
      }
    }
    """

    data = _graphql_request(endpoint, query, {"pool": pool_address.lower()})
    pool = data.get("pool")
    if not pool:
        raise ValueError(f"The Graph returned no pool data for {pool_address}")

    token0_id = Web3.to_checksum_address(pool["token0"]["id"])
    token1_id = Web3.to_checksum_address(pool["token1"]["id"])
    base_checksum = Web3.to_checksum_address(base_token)
    quote_checksum = Web3.to_checksum_address(quote_token)

    token0_price = float(pool["token0Price"])
    token1_price = float(pool["token1Price"])

    if token0_id == base_checksum and token1_id == quote_checksum:
        quote_per_base = token0_price
    elif token0_id == quote_checksum and token1_id == base_checksum:
        quote_per_base = token1_price
    else:
        raise ValueError(
            f"Pool token mismatch for {token_pair} in The Graph response. token0={token0_id}, token1={token1_id}"
        )

    return quote_per_base, {
        "pool": pool,
        "source": "thegraph:pool",
    }


def _current_pool_price(token_pair: str) -> tuple[float, dict[str, Any]]:
    fallback_pool_address: str | None = None
    fallback_pool_meta: dict[str, Any] | None = None
    try:
        fallback_pool_address, fallback_pool_meta = _pool_address_for_pair(token_pair, web3_client=None)
    except Exception:
        fallback_pool_address = None
        fallback_pool_meta = None

    try:
        web3_client = _build_web3_client()
        pool_address, pool_meta = _pool_address_for_pair(token_pair, web3_client=web3_client)
    except Exception as exc:
        if fallback_pool_address is None:
            raise

        graph_price, graph_raw = _graph_pool_price(fallback_pool_address, token_pair)
        return graph_price, {
            "pool_address": fallback_pool_address,
            "pool_resolution": fallback_pool_meta or {"source": "env"},
            "rpc_error": f"{type(exc).__name__}: {exc}",
            "fallback_price_source": graph_raw,
        }

    base_decimals, quote_decimals = _token_decimals_for_pair(token_pair)
    base_token, quote_token = _token_addresses_for_pair(token_pair)

    decimals_by_token = {
        Web3.to_checksum_address(base_token): base_decimals,
        Web3.to_checksum_address(quote_token): quote_decimals,
    }

    pool_contract = web3_client.eth.contract(address=Web3.to_checksum_address(pool_address), abi=SLOT0_ABI)
    pool_tokens_contract = web3_client.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_TOKENS_ABI)

    token0 = Web3.to_checksum_address(pool_tokens_contract.functions.token0().call())
    token1 = Web3.to_checksum_address(pool_tokens_contract.functions.token1().call())
    if token0 not in decimals_by_token or token1 not in decimals_by_token:
        raise ValueError(
            f"Pool token mismatch for {token_pair}. "
            f"pool token0={token0}, token1={token1}, expected pair tokens={list(decimals_by_token.keys())}"
        )

    token0_decimals = decimals_by_token[token0]
    token1_decimals = decimals_by_token[token1]

    slot0 = pool_contract.functions.slot0().call()
    sqrt_price_x96 = int(slot0[0])

    raw_ratio = (sqrt_price_x96 * sqrt_price_x96) / (2**192)
    token1_per_token0 = raw_ratio * (10 ** (token0_decimals - token1_decimals))

    base_checksum = Web3.to_checksum_address(base_token)
    quote_checksum = Web3.to_checksum_address(quote_token)
    if token0 == base_checksum and token1 == quote_checksum:
        quote_per_base = token1_per_token0
    elif token0 == quote_checksum and token1 == base_checksum:
        quote_per_base = 0.0 if token1_per_token0 == 0 else (1.0 / token1_per_token0)
    else:
        raise ValueError(
            f"Could not map pool token ordering to pair {token_pair}. token0={token0}, token1={token1}"
        )

    return float(quote_per_base), {
        "slot0": {"sqrtPriceX96": sqrt_price_x96},
        "pool_address": pool_address,
        "token0": token0,
        "token1": token1,
        "pool_resolution": pool_meta,
        "computed_quote_per_base": quote_per_base,
    }


def _graphql_request(endpoint: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    resolved_endpoint = endpoint
    if "gateway.thegraph.com/api/subgraphs/id/" in resolved_endpoint:
        graph_api_key = os.getenv("THEGRAPH_API_KEY")
        if graph_api_key and "/api/subgraphs/id/" in resolved_endpoint:
            resolved_endpoint = resolved_endpoint.replace(
                "/api/subgraphs/id/",
                f"/api/{graph_api_key}/subgraphs/id/",
            )

    response = requests.post(
        resolved_endpoint,
        json={"query": query, "variables": variables},
        timeout=20,
        headers={"Content-Type": "application/json"},
        allow_redirects=False,
    )

    if 300 <= response.status_code < 400:
        location = response.headers.get("Location", "")
        raise ValueError(
            f"Graph endpoint redirected unexpectedly (status {response.status_code}) to {location or 'unknown location'}. "
            "Set a direct endpoint or provide THEGRAPH_API_KEY when using gateway.thegraph.com."
        )

    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        raise ValueError(f"GraphQL error: {payload['errors']}")
    return payload["data"]


def _rpc_block_window(hours: int, web3_client: Web3) -> int:
    avg_block_time_seconds = float(os.getenv("MARKET_DATA_BLOCK_TIME_SECONDS", "12"))
    return max(1, int((hours * 3600) / avg_block_time_seconds))


def _pool_tokens(web3_client: Web3, pool_address: str) -> tuple[str, str]:
    pool_tokens_contract = web3_client.eth.contract(address=Web3.to_checksum_address(pool_address), abi=POOL_TOKENS_ABI)
    token0 = Web3.to_checksum_address(pool_tokens_contract.functions.token0().call())
    token1 = Web3.to_checksum_address(pool_tokens_contract.functions.token1().call())
    return token0, token1


def _swap_usd_value(
    *,
    amount0: int,
    amount1: int,
    token0: str,
    token1: str,
    base_token: str,
    quote_token: str,
    base_decimals: int,
    quote_decimals: int,
    current_price: float,
) -> float:
    if token0 == quote_token:
        return abs(float(amount0)) / (10**quote_decimals)
    if token1 == quote_token:
        return abs(float(amount1)) / (10**quote_decimals)
    if token0 == base_token:
        return (abs(float(amount0)) / (10**base_decimals)) * current_price
    if token1 == base_token:
        return (abs(float(amount1)) / (10**base_decimals)) * current_price
    return 0.0


def _decode_swaps_in_range(web3_client: Web3, pool_address: str, from_block: int, to_block: int) -> list[dict[str, Any]]:
    checksum_pool = Web3.to_checksum_address(pool_address)
    swap_contract = web3_client.eth.contract(address=checksum_pool, abi=[SWAP_EVENT_ABI])
    decoded: list[dict[str, Any]] = []
    start_block = max(0, from_block)
    end_block = max(0, to_block)
    chunk_size = max(20, int(os.getenv("MARKET_DATA_LOG_BLOCK_CHUNK", "500")))
    current_from = start_block

    while current_from <= end_block:
        current_to = min(current_from + chunk_size - 1, end_block)
        try:
            logs = web3_client.eth.get_logs(
                {
                    "address": checksum_pool,
                    "fromBlock": current_from,
                    "toBlock": current_to,
                }
            )
        except Exception:
            if chunk_size > 20:
                chunk_size = max(20, chunk_size // 2)
                continue
            raise

        for log in logs:
            event_data = swap_contract.events.Swap().process_log(log)
            args = event_data["args"]
            decoded.append(
                {
                    "blockNumber": int(log["blockNumber"]),
                    "txHash": log["transactionHash"].hex(),
                    "amount0": int(args["amount0"]),
                    "amount1": int(args["amount1"]),
                }
            )

        current_from = current_to + 1

    return decoded


def _rpc_volume_delta(token_pair: str, pool_address: str, current_price: float) -> tuple[float, float, float, dict[str, Any]]:
    web3_client = _build_web3_client()
    latest_block = int(web3_client.eth.block_number)
    lookback_24h = _rpc_block_window(24, web3_client)
    lookback_48h = _rpc_block_window(48, web3_client)

    last24_from = max(0, latest_block - lookback_24h)
    prev24_from = max(0, latest_block - lookback_48h)
    prev24_to = max(0, last24_from - 1)

    last24_swaps = _decode_swaps_in_range(web3_client, pool_address, last24_from, latest_block)
    prev24_swaps = _decode_swaps_in_range(web3_client, pool_address, prev24_from, prev24_to)

    base_token_raw, quote_token_raw = _token_addresses_for_pair(token_pair)
    base_token = Web3.to_checksum_address(base_token_raw)
    quote_token = Web3.to_checksum_address(quote_token_raw)
    base_decimals, quote_decimals = _token_decimals_for_pair(token_pair)
    token0, token1 = _pool_tokens(web3_client, pool_address)

    last_24h = sum(
        _swap_usd_value(
            amount0=swap["amount0"],
            amount1=swap["amount1"],
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            base_decimals=base_decimals,
            quote_decimals=quote_decimals,
            current_price=current_price,
        )
        for swap in last24_swaps
    )

    prev_24h = sum(
        _swap_usd_value(
            amount0=swap["amount0"],
            amount1=swap["amount1"],
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            base_decimals=base_decimals,
            quote_decimals=quote_decimals,
            current_price=current_price,
        )
        for swap in prev24_swaps
    )

    if prev_24h == 0:
        delta_pct = 0.0 if last_24h == 0 else 100.0
    else:
        delta_pct = ((last_24h - prev_24h) / prev_24h) * 100.0

    return float(last_24h), float(prev_24h), float(delta_pct), {
        "source": "rpc_swaps",
        "latest_block": latest_block,
        "last24": {"from": last24_from, "to": latest_block, "count": len(last24_swaps)},
        "prev24": {"from": prev24_from, "to": prev24_to, "count": len(prev24_swaps)},
    }


def _rpc_wallet_outflow_count(token_pair: str, pool_address: str, current_price: float) -> tuple[int, dict[str, Any]]:
    web3_client = _build_web3_client()
    latest_block = int(web3_client.eth.block_number)
    lookback_2h = _rpc_block_window(2, web3_client)
    from_block = max(0, latest_block - lookback_2h)
    swaps = _decode_swaps_in_range(web3_client, pool_address, from_block, latest_block)

    base_token_raw, quote_token_raw = _token_addresses_for_pair(token_pair)
    base_token = Web3.to_checksum_address(base_token_raw)
    quote_token = Web3.to_checksum_address(quote_token_raw)
    base_decimals, quote_decimals = _token_decimals_for_pair(token_pair)
    token0, token1 = _pool_tokens(web3_client, pool_address)
    large_swap_usd = float(os.getenv("LARGE_SWAP_USD_THRESHOLD", "50000"))

    outflow = 0
    for swap in swaps:
        usd_value = _swap_usd_value(
            amount0=swap["amount0"],
            amount1=swap["amount1"],
            token0=token0,
            token1=token1,
            base_token=base_token,
            quote_token=quote_token,
            base_decimals=base_decimals,
            quote_decimals=quote_decimals,
            current_price=current_price,
        )

        has_pool_outflow = (swap["amount0"] < 0) or (swap["amount1"] < 0)
        if has_pool_outflow and usd_value >= large_swap_usd:
            outflow += 1

    return outflow, {
        "source": "rpc_swaps",
        "from_block": from_block,
        "to_block": latest_block,
        "swap_count": len(swaps),
        "large_swap_usd_threshold": large_swap_usd,
    }


def _gecko_network_slug() -> str:
    return os.getenv("GECKO_NETWORK_SLUG", "eth")


def _gecko_volume_delta(pool_address: str) -> tuple[float, float, float, dict[str, Any]]:
    network = _gecko_network_slug()
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}/ohlcv/hour"
    response = requests.get(url, params={"aggregate": 1, "limit": 48}, timeout=20)
    response.raise_for_status()
    payload = response.json()
    candles = payload.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
    if not candles:
        raise ValueError("GeckoTerminal returned no ohlcv candles")

    # API returns latest first. candle[5] is volume.
    last_24h = sum(float(candle[5]) for candle in candles[:24])
    prev_24h = sum(float(candle[5]) for candle in candles[24:48])

    if prev_24h == 0:
        delta_pct = 0.0 if last_24h == 0 else 100.0
    else:
        delta_pct = ((last_24h - prev_24h) / prev_24h) * 100.0

    return float(last_24h), float(prev_24h), float(delta_pct), {
        "source": "geckoterminal:ohlcv",
        "candles": len(candles),
        "network": network,
    }


def _gecko_outflow_count(pool_address: str) -> tuple[int, dict[str, Any]]:
    network = _gecko_network_slug()
    large_swap_usd = float(os.getenv("LARGE_SWAP_USD_THRESHOLD", "50000"))
    cutoff = datetime.now(UTC) - timedelta(hours=2)

    outflow = 0
    checked = 0
    page = 1
    while page <= 3:
        url = f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool_address}/trades"
        response = requests.get(url, params={"page": page}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        trades = payload.get("data", [])
        if not trades:
            break

        stop = False
        for trade in trades:
            attrs = trade.get("attributes", {})
            ts_raw = attrs.get("block_timestamp")
            if not ts_raw:
                continue

            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if ts < cutoff:
                stop = True
                break

            checked += 1
            volume_usd = float(attrs.get("volume_in_usd") or 0.0)
            kind = str(attrs.get("kind", "")).lower()
            # Treat sells in the recent window as bearish outflow-like pressure.
            if kind == "sell" and volume_usd >= large_swap_usd:
                outflow += 1

        if stop:
            break
        page += 1

    return outflow, {
        "source": "geckoterminal:trades",
        "network": network,
        "checked_trades": checked,
        "large_swap_usd_threshold": large_swap_usd,
    }


def _volume_delta(token_pair: str, pool_address: str, current_price: float) -> tuple[float, float, float, dict[str, Any]]:
    endpoint = os.getenv("THEGRAPH_UNISWAP_V3_ENDPOINT", "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
    now = datetime.now(UTC)
    cutoff_24h = int((now - timedelta(hours=24)).timestamp())
    cutoff_48h = int((now - timedelta(hours=48)).timestamp())

    query = """
    query PoolHourData($pool: String!, $cutoff: Int!) {
      poolHourDatas(
        first: 60
        orderBy: periodStartUnix
        orderDirection: desc
        where: { pool: $pool, periodStartUnix_gte: $cutoff }
      ) {
        periodStartUnix
        volumeUSD
      }
    }
    """

    try:
        data = _graphql_request(endpoint, query, {"pool": pool_address.lower(), "cutoff": cutoff_48h})
    except Exception:
        try:
            return _gecko_volume_delta(pool_address)
        except Exception:
            return _rpc_volume_delta(token_pair, pool_address, current_price)

    hours = data.get("poolHourDatas", [])

    last_24h = 0.0
    prev_24h = 0.0
    for row in hours:
        period = int(row["periodStartUnix"])
        volume_usd = float(row["volumeUSD"])
        if period >= cutoff_24h:
            last_24h += volume_usd
        else:
            prev_24h += volume_usd

    if prev_24h == 0:
        delta_pct = 0.0 if last_24h == 0 else 100.0
    else:
        delta_pct = ((last_24h - prev_24h) / prev_24h) * 100.0

    return last_24h, prev_24h, float(delta_pct), {"poolHourDatas": hours}


def _wallet_outflow_count(token_pair: str, pool_address: str, current_price: float) -> tuple[int, dict[str, Any]]:
    endpoint = os.getenv("THEGRAPH_UNISWAP_V3_ENDPOINT", "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
    large_swap_usd = float(os.getenv("LARGE_SWAP_USD_THRESHOLD", "50000"))
    two_hours_ago = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())

    query = """
    query PoolSwaps($pool: String!, $since: Int!) {
      swaps(
        first: 250
        orderBy: timestamp
        orderDirection: desc
        where: { pool: $pool, timestamp_gte: $since }
      ) {
        timestamp
        amount0
        amount1
        amountUSD
      }
    }
    """

    try:
        data = _graphql_request(endpoint, query, {"pool": pool_address.lower(), "since": two_hours_ago})
    except Exception:
        try:
            return _gecko_outflow_count(pool_address)
        except Exception:
            return _rpc_wallet_outflow_count(token_pair, pool_address, current_price)

    swaps = data.get("swaps", [])

    outflow = 0
    for swap in swaps:
        amount_usd = abs(float(swap["amountUSD"]))
        amount0 = float(swap["amount0"])
        amount1 = float(swap["amount1"])

        # Uniswap swap amounts are signed from pool perspective. Negative means pool sends out token.
        has_pool_outflow = (amount0 < 0) or (amount1 < 0)
        if has_pool_outflow and amount_usd >= large_swap_usd:
            outflow += 1

    return outflow, {"swaps": swaps, "large_swap_usd_threshold": large_swap_usd}


def _price_change_24h(token_pair: str, pool_address: str, current_price: float) -> tuple[float, float]:
    baseline = get_market_price_baseline(token_pair)
    now = datetime.now(UTC).replace(tzinfo=None)

    if baseline is None:
        upsert_market_price_baseline(
            token_pair=token_pair,
            pool_address=pool_address,
            baseline_price=current_price,
            baseline_timestamp=now,
        )
        return current_price, 0.0

    baseline_price = float(baseline.baseline_price)
    if baseline_price == 0:
        change_pct = 0.0
    else:
        change_pct = ((current_price - baseline_price) / baseline_price) * 100.0

    age = now - baseline.baseline_timestamp
    if age >= timedelta(hours=24):
        # Rotate baseline once it has served as the 24h anchor.
        upsert_market_price_baseline(
            token_pair=token_pair,
            pool_address=pool_address,
            baseline_price=current_price,
            baseline_timestamp=now,
        )

    return baseline_price, float(change_pct)


def fetch_market_snapshot(token_pair: str) -> MarketSnapshot:
    """Fetch a typed snapshot of bearish/bullish market signals for a token pair."""
    init_database()

    current_price, price_raw = _current_pool_price(token_pair)
    pool_address = str(price_raw["pool_address"])

    baseline_price = current_price
    price_change_pct = 0.0
    price_change_error: str | None = None
    try:
        baseline_price, price_change_pct = _price_change_24h(token_pair, pool_address, current_price)
    except Exception as exc:  # noqa: BLE001 - keep pipeline alive with partial data
        price_change_error = f"{type(exc).__name__}: {exc}"

    last_24h_volume = 0.0
    prev_24h_volume = 0.0
    volume_delta_pct = 0.0
    volume_raw: dict[str, Any] = {}
    volume_error: str | None = None
    try:
        last_24h_volume, prev_24h_volume, volume_delta_pct, volume_raw = _volume_delta(token_pair, pool_address, current_price)
    except Exception as exc:  # noqa: BLE001 - keep pipeline alive with partial data
        volume_error = f"{type(exc).__name__}: {exc}"

    outflow_count = 0
    outflow_raw: dict[str, Any] = {}
    outflow_error: str | None = None
    try:
        outflow_count, outflow_raw = _wallet_outflow_count(token_pair, pool_address, current_price)
    except Exception as exc:  # noqa: BLE001 - keep pipeline alive with partial data
        outflow_error = f"{type(exc).__name__}: {exc}"

    fetched_at = datetime.now(UTC).replace(tzinfo=None)
    raw_data = {
        "price_source": price_raw,
        "volume_source": volume_raw,
        "outflow_source": outflow_raw,
        "source_errors": {
            "price_change": price_change_error,
            "volume": volume_error,
            "outflow": outflow_error,
        },
    }

    return MarketSnapshot(
        token_pair=token_pair,
        pool_address=pool_address,
        current_price=current_price,
        baseline_price_24h=baseline_price,
        price_change_24h_pct=price_change_pct,
        volume_last_24h_usd=last_24h_volume,
        volume_prev_24h_usd=prev_24h_volume,
        volume_delta_24h_pct=volume_delta_pct,
        wallet_outflow_count_2h=outflow_count,
        fetched_at=fetched_at,
        raw_market_data=raw_data,
    )


def fetch_snapshot(token_pair: str) -> MarketSnapshot:
    """Compatibility wrapper for orchestrator calls."""
    return fetch_market_snapshot(token_pair)


def _wallet_inflow_count_from_snapshot(snapshot: MarketSnapshot) -> int | None:
    outflow_source = snapshot.raw_market_data.get("outflow_source", {})
    swaps = outflow_source.get("swaps")
    if not isinstance(swaps, list):
        return None

    large_swap_usd = float(os.getenv("LARGE_SWAP_USD_THRESHOLD", "50000"))
    inflow = 0
    for swap in swaps:
        amount_usd = abs(float(swap.get("amountUSD") or 0.0))
        amount0 = float(swap.get("amount0") or 0.0)
        amount1 = float(swap.get("amount1") or 0.0)
        has_pool_inflow = (amount0 > 0) or (amount1 > 0)
        if has_pool_inflow and amount_usd >= large_swap_usd:
            inflow += 1

    return inflow


def _recent_large_lp_additions(pool_address: str) -> tuple[int, float, dict[str, Any]]:
    endpoint = os.getenv("THEGRAPH_UNISWAP_V3_ENDPOINT", "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3")
    large_lp_usd = float(os.getenv("LARGE_LP_ADDITION_USD_THRESHOLD", "50000"))
    since = int((datetime.now(UTC) - timedelta(hours=6)).timestamp())

    query = """
    query PoolMints($pool: String!, $since: Int!) {
      mints(
        first: 250
        orderBy: timestamp
        orderDirection: desc
        where: { pool: $pool, timestamp_gte: $since }
      ) {
        timestamp
        amountUSD
      }
    }
    """

    data = _graphql_request(endpoint, query, {"pool": pool_address.lower(), "since": since})
    mints = data.get("mints", [])

    count = 0
    total_usd = 0.0
    for mint in mints:
        amount_usd = float(mint.get("amountUSD") or 0.0)
        if amount_usd >= large_lp_usd:
            count += 1
            total_usd += amount_usd

    return count, float(total_usd), {
        "source": "thegraph:mints",
        "since": since,
        "checked_mints": len(mints),
        "large_lp_usd_threshold": large_lp_usd,
    }


def format_for_bear(snapshot: MarketSnapshot) -> str:
    """Format a neutral/bear-leaning summary from an existing MarketSnapshot."""
    return (
        f"Token pair: {snapshot.token_pair}. "
        f"Current price: {snapshot.current_price:.6f}. "
        f"24h baseline price: {snapshot.baseline_price_24h:.6f}. "
        f"24h price change: {snapshot.price_change_24h_pct:.2f}%. "
        f"Volume delta: {snapshot.volume_delta_24h_pct:.2f}% "
        f"(last 24h: ${snapshot.volume_last_24h_usd:,.2f}, prior 24h: ${snapshot.volume_prev_24h_usd:,.2f}). "
        f"Large wallet outflows in last 2h: {snapshot.wallet_outflow_count_2h} transactions. "
        f"Pool address: {snapshot.pool_address}."
    )


def format_for_bull(snapshot: MarketSnapshot) -> str:
    """Format a bull-leaning summary from the same snapshot plus LP-addition context."""
    inflow_count = _wallet_inflow_count_from_snapshot(snapshot)

    lp_count: int | None = None
    lp_total_usd: float | None = None
    lp_error: str | None = None
    try:
        lp_count, lp_total_usd, _ = _recent_large_lp_additions(snapshot.pool_address)
    except Exception as exc:  # noqa: BLE001 - keep formatter resilient
        lp_error = f"{type(exc).__name__}: {exc}"

    inflow_text = (
        str(inflow_count)
        if inflow_count is not None
        else "unavailable (source does not expose swap-level inflows)"
    )

    lp_text = (
        f"{lp_count} large LP additions totaling ${lp_total_usd:,.2f} in last 6h"
        if lp_count is not None and lp_total_usd is not None
        else f"unavailable ({lp_error or 'The Graph query failed'})"
    )

    return (
        f"Token pair: {snapshot.token_pair}. "
        f"Current price: {snapshot.current_price:.6f}. "
        f"24h baseline price: {snapshot.baseline_price_24h:.6f}. "
        f"24h price change: {snapshot.price_change_24h_pct:.2f}% "
        f"(positive supports bullish continuation). "
        f"Volume acceleration: {snapshot.volume_delta_24h_pct:.2f}% "
        f"(last 24h: ${snapshot.volume_last_24h_usd:,.2f}, prior 24h: ${snapshot.volume_prev_24h_usd:,.2f}). "
        f"Large wallet inflows in last 2h: {inflow_text}. "
        f"Recent large LP additions: {lp_text}. "
        f"Pool address: {snapshot.pool_address}."
    )
