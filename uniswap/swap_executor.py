from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from utils.constants import (
    BEAR_SIDE_TOKEN_SYMBOL,
    BULL_SIDE_TOKEN_SYMBOL,
    TARGET_CHAIN_ID,
    get_universal_router_address,
    resolve_token_address,
    resolve_token_decimals,
)
from keeper.execution_handler import (
    FINAL_SETTLEMENT_RETRY_POLICY,
    MICRO_SETTLEMENT_RETRY_POLICY,
    submit_job,
    execute_swap_via_keeperhub,
)
from utils.db.schema import SwapExecution, SwapQuote, SwapWarning
from utils.db_manager import get_session, init_database, upsert_round_trace

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


UNISWAP_API_BASE = os.getenv("UNISWAP_API_BASE", "https://trade-api.gateway.uniswap.org/v1").rstrip("/")
UNISWAP_API_KEY = os.getenv("UNISWAP_API_KEY", "").strip()
MICRO_SETTLEMENT_PERCENT = float(os.getenv("MICRO_SETTLEMENT_PERCENT", "2.0"))
DEFAULT_SLIPPAGE_TOLERANCE = float(os.getenv("DEFAULT_SLIPPAGE_TOLERANCE", "0.5"))
SWAP_DEADLINE_SECONDS = int(os.getenv("SWAP_DEADLINE_SECONDS", "300"))
MAX_GAS_PRICE_GWEI = float(os.getenv("MAX_GAS_PRICE_GWEI", "50"))
AGENT_WALLET_ADDRESS = os.getenv("AGENT_WALLET_ADDRESS", "").strip()
AGENT_WALLET_PRIVATE_KEY = os.getenv("AGENT_WALLET_PRIVATE_KEY", "").strip()
ALCHEMY_RPC_URL = os.getenv("ALCHEMY_RPC_URL", "").strip()
UNISWAP_UNIVERSAL_ROUTER_VERSION = os.getenv("UNISWAP_UNIVERSAL_ROUTER_VERSION", "2.0")
UNISWAP_PERMIT2_DISABLED = _env_bool("UNISWAP_PERMIT2_DISABLED", True)
SWAP_CHAIN_ID = int(os.getenv("SWAP_CHAIN_ID", str(TARGET_CHAIN_ID)))
QUOTE_TIMEOUT_SECONDS = float(os.getenv("QUOTE_TIMEOUT_SECONDS", "10"))
DRY_RUN = _env_bool("DRY_RUN", False)


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"
FINAL_SETTLEMENT_SLIPPAGE_TOLERANCE = float(os.getenv("FINAL_SETTLEMENT_SLIPPAGE_TOLERANCE", "1.0"))
FINAL_SETTLEMENT_SPLIT_THRESHOLD_ETH = float(os.getenv("FINAL_SETTLEMENT_SPLIT_THRESHOLD_ETH", "0.1"))
MICRO_SETTLEMENT_MIN_ETH_EQUIVALENT = float(os.getenv("MICRO_SETTLEMENT_MIN_ETH_EQUIVALENT", "0.001"))

SWAP_EVENT_TOPIC = Web3.keccak(
    text="Swap(address,address,int256,int256,uint160,uint128,int24)"
).hex()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_uniswap_headers: dict[str, str] = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "x-universal-router-version": UNISWAP_UNIVERSAL_ROUTER_VERSION,
}
if UNISWAP_API_KEY:
    _uniswap_headers["x-api-key"] = UNISWAP_API_KEY
if UNISWAP_PERMIT2_DISABLED:
    _uniswap_headers["x-permit2-disabled"] = "true"

uniswap_http_client = httpx.Client(
    base_url=UNISWAP_API_BASE,
    headers=_uniswap_headers,
    timeout=QUOTE_TIMEOUT_SECONDS,
)
web3_client = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))


@dataclass(slots=True)
class QuoteResult:
    success: bool
    reason: str | None
    quote_id: int | None
    session_id: str
    round_number: int
    swap_type: str
    token_in: str
    token_out: str
    token_in_symbol: str
    token_out_symbol: str
    amount_in_wei: str
    quoted_amount_out_wei: str | None
    quoted_price: float | None
    route_description: str | None
    gas_estimate_wei: str | None
    slippage_tolerance_percent: float
    quote_timestamp: datetime
    quote_used: bool
    raw_response: dict[str, Any] | None


@dataclass(slots=True)
class SwapCalldata:
    success: bool
    reason: str | None
    quote_id: int | None
    calldata: str | None
    value_wei: str | None
    gas_limit: str | None
    gas_price_wei: str | None
    deadline_unix: int | None
    raw_response: dict[str, Any] | None


@dataclass(slots=True)
class BroadcastResult:
    success: bool
    reason: str | None
    tx_hash: str | None
    execution_id: int | None
    tx_receipt: dict[str, Any] | None
    status: str


@dataclass(slots=True)
class ExecutionAnalysisResult:
    success: bool
    reason: str | None
    amount_out_actual_wei: str | None
    execution_price: float | None
    slippage_realized_percent: float | None


@dataclass(slots=True)
class SettlementResult:
    success: bool
    reason: str | None
    tx_hash: str | None
    keeperhub_job_id: str | None
    amount_out_actual_wei: str | None


def _normalize_base_url(base_url: str) -> str:
    if "api.uniswap.org/v1" in base_url:
        # Trading API docs and OAS use the gateway endpoint.
        return "https://trade-api.gateway.uniswap.org/v1"
    return base_url


def _extract_decimals_from_quote(quote_result: QuoteResult) -> tuple[int, int]:
    in_decimals = resolve_token_decimals(quote_result.token_in_symbol)
    out_decimals = resolve_token_decimals(quote_result.token_out_symbol)
    payload = quote_result.raw_response or {}
    quote = payload.get("quote") or {}
    route = quote.get("route") or []
    if isinstance(route, list) and route and isinstance(route[0], list) and route[0]:
        first_hop = route[0][0]
        if isinstance(first_hop, dict):
            try:
                in_decimals = int(((first_hop.get("tokenIn") or {}).get("decimals")) or in_decimals)
            except (TypeError, ValueError):
                pass
            try:
                out_decimals = int(((first_hop.get("tokenOut") or {}).get("decimals")) or out_decimals)
            except (TypeError, ValueError):
                pass
    return in_decimals, out_decimals


def _calculate_normalized_price(amount_in_wei: str, amount_out_wei: str | None, in_decimals: int, out_decimals: int) -> float | None:
    if not amount_out_wei:
        return None
    try:
        amount_in = int(amount_in_wei)
        amount_out = int(amount_out_wei)
        if amount_in <= 0:
            return None
        human_in = amount_in / float(10 ** in_decimals)
        human_out = amount_out / float(10 ** out_decimals)
        if human_in <= 0:
            return None
        return human_out / human_in
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _summarize_route(route: Any, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    if not isinstance(route, list) or not route:
        return None

    path_descriptions: list[str] = []
    for path in route:
        if not isinstance(path, list):
            continue
        hops: list[str] = []
        for hop in path:
            if not isinstance(hop, dict):
                continue
            hop_type = hop.get("type", "unknown")
            token_in_symbol = (hop.get("tokenIn") or {}).get("symbol")
            token_out_symbol = (hop.get("tokenOut") or {}).get("symbol")
            hops.append(f"{hop_type}:{token_in_symbol}->{token_out_symbol}")
        if hops:
            path_descriptions.append(" | ".join(hops))

    return "; ".join(path_descriptions) if path_descriptions else None


def _parse_int_like(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return int(text, 0)
        except ValueError:
            return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _insert_quote_row(
    *,
    session_id: str,
    round_number: int,
    swap_type: str,
    token_in: str,
    token_out: str,
    amount_in_wei: str,
    quoted_amount_out_wei: str | None,
    route_description: str | None,
    gas_estimate_wei: str | None,
    quote_timestamp: datetime,
    quote_used: bool,
    quoted_price: float | None,
    slippage_tolerance_percent: float,
) -> int | None:
    try:
        with get_session() as session:
            row = SwapQuote(
                session_id=session_id,
                round_number=round_number,
                swap_type=swap_type,
                token_in=token_in,
                token_out=token_out,
                amount_in_wei=str(amount_in_wei),
                quoted_amount_out_wei=quoted_amount_out_wei,
                quoted_price=quoted_price,
                route_description=route_description,
                gas_estimate_wei=gas_estimate_wei,
                slippage_tolerance_percent=slippage_tolerance_percent,
                quote_timestamp=quote_timestamp,
                quote_used=quote_used,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to insert swap quote row: %s", exc)
        return None


def _mark_quote_used(quote_id: int, used: bool) -> None:
    try:
        with get_session() as session:
            row = session.get(SwapQuote, quote_id)
            if row is None:
                return
            row.quote_used = used
            session.commit()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to update quote_used for quote_id=%s: %s", quote_id, exc)


def _insert_execution_row(
    *,
    session_id: str,
    round_number: int,
    swap_type: str,
    quote_id: int | None,
    tx_hash: str | None,
    token_in: str,
    token_out: str,
    amount_in_actual_wei: str | None,
    status: str,
    gas_price_gwei: float | None,
    error_message: str | None = None,
) -> int | None:
    try:
        with get_session() as session:
            row = SwapExecution(
                session_id=session_id,
                round_number=round_number,
                swap_type=swap_type,
                quote_id=quote_id,
                tx_hash=tx_hash,
                token_in=token_in,
                token_out=token_out,
                amount_in_actual_wei=amount_in_actual_wei,
                amount_out_actual_wei=None,
                execution_price=None,
                slippage_realized_percent=None,
                gas_used_wei=None,
                gas_price_gwei=gas_price_gwei,
                keeperhub_job_id=None,
                status=status,
                confirmed_at=None,
                error_message=error_message,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.id
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to insert swap execution row: %s", exc)
        return None


def _update_execution_row(execution_id: int | None, **fields: Any) -> None:
    if execution_id is None:
        return
    try:
        with get_session() as session:
            row = session.get(SwapExecution, execution_id)
            if row is None:
                return
            for key, value in fields.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            session.commit()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to update swap execution row %s: %s", execution_id, exc)


def _insert_warning(
    *,
    session_id: str,
    round_number: int,
    quote_id: int | None,
    execution_id: int | None,
    warning_type: str,
    message: str,
) -> None:
    try:
        with get_session() as session:
            row = SwapWarning(
                session_id=session_id,
                round_number=round_number,
                warning_type=warning_type,
                message=message,
                quote_id=quote_id,
                execution_id=execution_id,
                created_at=_now_utc_naive(),
            )
            session.add(row)
            session.commit()
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to insert swap warning: %s", exc)


def _failed_quote_result(
    *,
    reason: str,
    session_id: str,
    round_number: int,
    swap_type: str,
    token_in: str,
    token_out: str,
    token_in_symbol: str,
    token_out_symbol: str,
    amount_in_wei: str,
    route_description: str | None,
    slippage_tolerance_percent: float,
    raw_response: dict[str, Any] | None = None,
) -> QuoteResult:
    now = _now_utc_naive()
    quote_id = _insert_quote_row(
        session_id=session_id,
        round_number=round_number,
        swap_type=swap_type,
        token_in=token_in,
        token_out=token_out,
        amount_in_wei=amount_in_wei,
        quoted_amount_out_wei=None,
        route_description=route_description,
        gas_estimate_wei=None,
        quote_timestamp=now,
        quote_used=False,
        quoted_price=None,
        slippage_tolerance_percent=slippage_tolerance_percent,
    )
    return QuoteResult(
        success=False,
        reason=reason,
        quote_id=quote_id,
        session_id=session_id,
        round_number=round_number,
        swap_type=swap_type,
        token_in=token_in,
        token_out=token_out,
        token_in_symbol=token_in_symbol,
        token_out_symbol=token_out_symbol,
        amount_in_wei=amount_in_wei,
        quoted_amount_out_wei=None,
        quoted_price=None,
        route_description=route_description,
        gas_estimate_wei=None,
        slippage_tolerance_percent=slippage_tolerance_percent,
        quote_timestamp=now,
        quote_used=False,
        raw_response=raw_response,
    )


def fetch_quote(
    token_in: str,
    token_out: str,
    amount_in_wei: str,
    swap_type: str,
    session_id: str,
    round_number: int,
    slippage_tolerance: float | None = None,
) -> QuoteResult:
    """Fetch a quote from Uniswap and persist quote metadata to swap_quotes."""
    token_in_symbol = token_in.upper() if not token_in.startswith("0x") else token_in
    token_out_symbol = token_out.upper() if not token_out.startswith("0x") else token_out
    slippage_pct = float(slippage_tolerance if slippage_tolerance is not None else DEFAULT_SLIPPAGE_TOLERANCE)

    if DRY_RUN:
        token_in_address = resolve_token_address(token_in, SWAP_CHAIN_ID)
        token_out_address = resolve_token_address(token_out, SWAP_CHAIN_ID)
        quote_timestamp = _now_utc_naive()
        amount_in_int = int(amount_in_wei)
        quoted_amount_out_wei = str(max(1, int(amount_in_int * 97 // 100)))
        raw_response = {
            "quote": {
                "output": {"amount": quoted_amount_out_wei},
                "route": [],
                "routeString": "dry_run_simulated_route",
                "gasFee": "0",
            }
        }

        in_dec, out_dec = _extract_decimals_from_quote(
            QuoteResult(
                success=True,
                reason=None,
                quote_id=None,
                session_id=session_id,
                round_number=round_number,
                swap_type=swap_type,
                token_in=token_in_address,
                token_out=token_out_address,
                token_in_symbol=token_in_symbol,
                token_out_symbol=token_out_symbol,
                amount_in_wei=str(amount_in_wei),
                quoted_amount_out_wei=quoted_amount_out_wei,
                quoted_price=None,
                route_description="dry_run_simulated_route",
                gas_estimate_wei="0",
                slippage_tolerance_percent=slippage_pct,
                quote_timestamp=quote_timestamp,
                quote_used=False,
                raw_response=raw_response,
            )
        )
        quoted_price = _calculate_normalized_price(
            str(amount_in_wei),
            quoted_amount_out_wei,
            in_dec,
            out_dec,
        )

        quote_id = _insert_quote_row(
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            amount_in_wei=str(amount_in_wei),
            quoted_amount_out_wei=quoted_amount_out_wei,
            route_description="dry_run_simulated_route",
            gas_estimate_wei="0",
            quote_timestamp=quote_timestamp,
            quote_used=False,
            quoted_price=quoted_price,
            slippage_tolerance_percent=slippage_pct,
        )

        return QuoteResult(
            success=True,
            reason=None,
            quote_id=quote_id,
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            quoted_amount_out_wei=quoted_amount_out_wei,
            quoted_price=quoted_price,
            route_description="dry_run_simulated_route",
            gas_estimate_wei="0",
            slippage_tolerance_percent=slippage_pct,
            quote_timestamp=quote_timestamp,
            quote_used=False,
            raw_response=raw_response,
        )

    try:
        token_in_address = resolve_token_address(token_in, SWAP_CHAIN_ID)
        token_out_address = resolve_token_address(token_out, SWAP_CHAIN_ID)
    except ValueError as exc:
        return _failed_quote_result(
            reason="unsupported_token",
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in,
            token_out=token_out,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description=str(exc),
            slippage_tolerance_percent=slippage_pct,
        )

    try:
        gas_price_wei = int(web3_client.eth.gas_price)
    except Exception as exc:  # pragma: no cover
        return _failed_quote_result(
            reason="gas_price_check_failed",
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description=f"gas_price_check_failed: {exc}",
            slippage_tolerance_percent=slippage_pct,
        )

    max_gas_price_wei = Web3.to_wei(MAX_GAS_PRICE_GWEI, "gwei")
    if gas_price_wei > max_gas_price_wei:
        return _failed_quote_result(
            reason="gas_price_too_high",
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description=(
                f"gas_price_too_high current={gas_price_wei} max={int(max_gas_price_wei)}"
            ),
            slippage_tolerance_percent=slippage_pct,
        )

    request_body = {
        "tokenIn": token_in_address,
        "tokenOut": token_out_address,
        "amount": str(amount_in_wei),
        "type": "EXACT_INPUT",
        "tokenInChainId": SWAP_CHAIN_ID,
        "tokenOutChainId": SWAP_CHAIN_ID,
        "swapper": AGENT_WALLET_ADDRESS,
        "slippageTolerance": slippage_pct,
    }

    quote_timestamp = _now_utc_naive()
    client = uniswap_http_client
    if _normalize_base_url(UNISWAP_API_BASE) != UNISWAP_API_BASE:
        client = httpx.Client(
            base_url=_normalize_base_url(UNISWAP_API_BASE),
            headers=_uniswap_headers,
            timeout=QUOTE_TIMEOUT_SECONDS,
        )

    try:
        response = client.post("/quote", json=request_body, timeout=QUOTE_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException:
        return _failed_quote_result(
            reason="quote_timeout",
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description="quote_timeout",
            slippage_tolerance_percent=slippage_pct,
        )
    except httpx.HTTPStatusError as exc:
        err_payload: dict[str, Any]
        try:
            err_payload = exc.response.json()
        except ValueError:
            err_payload = {"detail": exc.response.text}
        if exc.response.status_code == 401:
            reason = "unauthorized_api_key"
        elif exc.response.status_code == 404:
            reason = "no_liquidity"
        else:
            reason = "quote_http_error"
        return _failed_quote_result(
            reason=reason,
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description=f"http_{exc.response.status_code}: {err_payload}",
            slippage_tolerance_percent=slippage_pct,
            raw_response=err_payload,
        )
    except Exception as exc:  # pragma: no cover
        return _failed_quote_result(
            reason="quote_request_failed",
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            route_description=f"quote_request_failed: {exc}",
            slippage_tolerance_percent=slippage_pct,
        )
    finally:
        if client is not uniswap_http_client:
            client.close()

    quote_payload = payload.get("quote") or {}
    quoted_amount_out_wei = ((quote_payload.get("output") or {}).get("amount"))
    route_array = quote_payload.get("route")
    route_description = _summarize_route(route_array, quote_payload.get("routeString"))
    gas_estimate_wei = quote_payload.get("gasFee") or quote_payload.get("gasUseEstimate")

    in_dec, out_dec = _extract_decimals_from_quote(
        QuoteResult(
            success=True,
            reason=None,
            quote_id=None,
            session_id=session_id,
            round_number=round_number,
            swap_type=swap_type,
            token_in=token_in_address,
            token_out=token_out_address,
            token_in_symbol=token_in_symbol,
            token_out_symbol=token_out_symbol,
            amount_in_wei=str(amount_in_wei),
            quoted_amount_out_wei=str(quoted_amount_out_wei) if quoted_amount_out_wei is not None else None,
            quoted_price=None,
            route_description=route_description,
            gas_estimate_wei=str(gas_estimate_wei) if gas_estimate_wei is not None else None,
            slippage_tolerance_percent=slippage_pct,
            quote_timestamp=quote_timestamp,
            quote_used=False,
            raw_response=payload,
        )
    )
    quoted_price = _calculate_normalized_price(
        str(amount_in_wei),
        str(quoted_amount_out_wei) if quoted_amount_out_wei is not None else None,
        in_dec,
        out_dec,
    )

    quote_id = _insert_quote_row(
        session_id=session_id,
        round_number=round_number,
        swap_type=swap_type,
        token_in=token_in_address,
        token_out=token_out_address,
        amount_in_wei=str(amount_in_wei),
        quoted_amount_out_wei=str(quoted_amount_out_wei) if quoted_amount_out_wei is not None else None,
        route_description=route_description,
        gas_estimate_wei=str(gas_estimate_wei) if gas_estimate_wei is not None else None,
        quote_timestamp=quote_timestamp,
        quote_used=False,
        quoted_price=quoted_price,
        slippage_tolerance_percent=slippage_pct,
    )

    return QuoteResult(
        success=True,
        reason=None,
        quote_id=quote_id,
        session_id=session_id,
        round_number=round_number,
        swap_type=swap_type,
        token_in=token_in_address,
        token_out=token_out_address,
        token_in_symbol=token_in_symbol,
        token_out_symbol=token_out_symbol,
        amount_in_wei=str(amount_in_wei),
        quoted_amount_out_wei=str(quoted_amount_out_wei) if quoted_amount_out_wei is not None else None,
        quoted_price=quoted_price,
        route_description=route_description,
        gas_estimate_wei=str(gas_estimate_wei) if gas_estimate_wei is not None else None,
        slippage_tolerance_percent=slippage_pct,
        quote_timestamp=quote_timestamp,
        quote_used=False,
        raw_response=payload,
    )


def build_swap_calldata(quote_result: QuoteResult) -> SwapCalldata:
    """Convert a successful quote result into executable swap calldata via /swap."""
    if not quote_result.success:
        return SwapCalldata(
            success=False,
            reason="quote_not_successful",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=None,
            gas_limit=None,
            gas_price_wei=None,
            deadline_unix=None,
            raw_response=None,
        )

    if not quote_result.raw_response or "quote" not in quote_result.raw_response:
        return SwapCalldata(
            success=False,
            reason="missing_quote_payload",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=None,
            gas_limit=None,
            gas_price_wei=None,
            deadline_unix=None,
            raw_response=quote_result.raw_response,
        )

    if DRY_RUN:
        now = int(time.time())
        deadline_unix = now + SWAP_DEADLINE_SECONDS
        return SwapCalldata(
            success=True,
            reason=None,
            quote_id=quote_result.quote_id,
            calldata=f"0xdeadbeef{quote_result.quote_id or 0:08x}",
            value_wei="0",
            gas_limit="250000",
            gas_price_wei="0",
            deadline_unix=deadline_unix,
            raw_response={"dry_run": True, "quote": quote_result.raw_response.get("quote")},
        )

    now = int(time.time())
    quote_age_seconds = int((_now_utc_naive() - quote_result.quote_timestamp).total_seconds())
    if quote_age_seconds >= max(SWAP_DEADLINE_SECONDS - 30, 1):
        refreshed_quote = fetch_quote(
            token_in=quote_result.token_in_symbol,
            token_out=quote_result.token_out_symbol,
            amount_in_wei=quote_result.amount_in_wei,
            swap_type=quote_result.swap_type,
            session_id=quote_result.session_id,
            round_number=quote_result.round_number,
            slippage_tolerance=quote_result.slippage_tolerance_percent,
        )
        if not refreshed_quote.success:
            return SwapCalldata(
                success=False,
                reason=f"quote_refresh_failed:{refreshed_quote.reason}",
                quote_id=refreshed_quote.quote_id,
                calldata=None,
                value_wei=None,
                gas_limit=None,
                gas_price_wei=None,
                deadline_unix=None,
                raw_response=refreshed_quote.raw_response,
            )
        quote_result = refreshed_quote
        if not quote_result.raw_response or "quote" not in quote_result.raw_response:
            return SwapCalldata(
                success=False,
                reason="missing_quote_payload",
                quote_id=quote_result.quote_id,
                calldata=None,
                value_wei=None,
                gas_limit=None,
                gas_price_wei=None,
                deadline_unix=None,
                raw_response=quote_result.raw_response,
            )

    deadline_unix = now + SWAP_DEADLINE_SECONDS
    swap_request: dict[str, Any] = {
        "quote": quote_result.raw_response["quote"],
        "slippageTolerance": quote_result.slippage_tolerance_percent,
        "deadline": deadline_unix,
        "refreshGasPrice": True,
    }

    permit_data = quote_result.raw_response.get("permitData")
    signature = quote_result.raw_response.get("signature")
    if permit_data is not None and signature:
        swap_request["permitData"] = permit_data
        swap_request["signature"] = signature

    try:
        response = uniswap_http_client.post("/swap", json=swap_request, timeout=QUOTE_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException:
        return SwapCalldata(
            success=False,
            reason="swap_timeout",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=None,
            gas_limit=None,
            gas_price_wei=None,
            deadline_unix=deadline_unix,
            raw_response=None,
        )
    except httpx.HTTPStatusError as exc:
        err_payload: dict[str, Any]
        try:
            err_payload = exc.response.json()
        except ValueError:
            err_payload = {"detail": exc.response.text}
        return SwapCalldata(
            success=False,
            reason=f"swap_http_error_{exc.response.status_code}",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=None,
            gas_limit=None,
            gas_price_wei=None,
            deadline_unix=deadline_unix,
            raw_response=err_payload,
        )
    except Exception as exc:  # pragma: no cover
        return SwapCalldata(
            success=False,
            reason="swap_request_failed",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=None,
            gas_limit=None,
            gas_price_wei=None,
            deadline_unix=deadline_unix,
            raw_response={"detail": str(exc)},
        )

    swap_tx = payload.get("swap") or {}
    calldata = swap_tx.get("data")
    value_wei = swap_tx.get("value")
    gas_limit = swap_tx.get("gasLimit")
    gas_price_wei = swap_tx.get("gasPrice") or swap_tx.get("maxFeePerGas")

    if not calldata:
        return SwapCalldata(
            success=False,
            reason="missing_calldata",
            quote_id=quote_result.quote_id,
            calldata=None,
            value_wei=value_wei,
            gas_limit=gas_limit,
            gas_price_wei=gas_price_wei,
            deadline_unix=deadline_unix,
            raw_response=payload,
        )

    if quote_result.quote_id is not None:
        _mark_quote_used(quote_result.quote_id, True)

    return SwapCalldata(
        success=True,
        reason=None,
        quote_id=quote_result.quote_id,
        calldata=str(calldata),
        value_wei=str(value_wei) if value_wei is not None else "0",
        gas_limit=str(gas_limit) if gas_limit is not None else None,
        gas_price_wei=str(gas_price_wei) if gas_price_wei is not None else None,
        deadline_unix=deadline_unix,
        raw_response=payload,
    )


def broadcast_and_confirm(
    swap_calldata: SwapCalldata,
    session_id: str,
    round_number: int,
    swap_type: str,
) -> BroadcastResult:
    """Sign, broadcast, and confirm swap transaction with pending-first execution logging."""
    if not swap_calldata.success or not swap_calldata.calldata:
        return BroadcastResult(
            success=False,
            reason="invalid_swap_calldata",
            tx_hash=None,
            execution_id=None,
            tx_receipt=None,
            status="failed",
        )

    router_address = get_universal_router_address(SWAP_CHAIN_ID)
    from_address = Web3.to_checksum_address(AGENT_WALLET_ADDRESS)
    gas_price_wei = int(web3_client.eth.gas_price)

    gas_limit_raw = _parse_int_like(swap_calldata.gas_limit, 250000)
    gas_with_buffer = int(gas_limit_raw * 1.1)

    tx_dict = {
        "to": Web3.to_checksum_address(router_address),
        "from": from_address,
        "data": swap_calldata.calldata,
        "value": _parse_int_like(swap_calldata.value_wei, 0),
        "gas": gas_with_buffer,
        "gasPrice": gas_price_wei,
        "nonce": int(web3_client.eth.get_transaction_count(from_address)),
        "chainId": int(web3_client.eth.chain_id),
    }

    execution_id: int | None = None
    if DRY_RUN:
        from utils.dry_run_adapter import DryRunAdapter

        adapter = DryRunAdapter(session_id=session_id, round_number=round_number)
        simulated = adapter.simulate_uniswap_swap(
            {
                "session_id": session_id,
                "round_number": round_number,
                "swap_type": swap_type,
                "quote_result": swap_calldata.raw_response.get("quote", {}) if swap_calldata.raw_response else {},
                "quote_id": swap_calldata.quote_id,
                "amount_in_wei": (swap_calldata.raw_response or {}).get("quote", {}).get("input", {}).get("amount"),
                "quoted_amount_out_wei": (swap_calldata.raw_response or {}).get("quote", {}).get("output", {}).get("amount"),
                "quoted_price": (swap_calldata.raw_response or {}).get("quote", {}).get("quotedPrice"),
                "token_in": (swap_calldata.raw_response or {}).get("quote", {}).get("input", {}).get("token", ""),
                "token_out": (swap_calldata.raw_response or {}).get("quote", {}).get("output", {}).get("token", ""),
                "gas_price_gwei": gas_price_wei / 1e9,
            }
        )
        execution_id = simulated.get("execution_id")
        simulated_hash = str(simulated.get("tx_hash") or Web3.keccak(text=json.dumps(tx_dict, sort_keys=True)).hex())
        print("[DRY_RUN] broadcast_and_confirm would send transaction:")
        print(json.dumps(tx_dict, indent=2, default=str))
        return BroadcastResult(
            success=True,
            reason="dry_run",
            tx_hash=simulated_hash,
            execution_id=execution_id,
            tx_receipt={
                "transactionHash": simulated_hash,
                "status": 1,
                "gasUsed": 0,
                "logs": [],
            },
            status="confirmed",
        )

    try:
        signed_tx = web3_client.eth.account.sign_transaction(tx_dict, private_key=AGENT_WALLET_PRIVATE_KEY)
        raw_tx_hash = web3_client.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = raw_tx_hash.hex()
    except Exception as exc:
        return BroadcastResult(
            success=False,
            reason=f"broadcast_failed: {exc}",
            tx_hash=None,
            execution_id=None,
            tx_receipt=None,
            status="failed",
        )

    execution_id = _insert_execution_row(
        session_id=session_id,
        round_number=round_number,
        swap_type=swap_type,
        quote_id=swap_calldata.quote_id,
        tx_hash=tx_hash_hex,
        token_in=(swap_calldata.raw_response or {}).get("quote", {}).get("input", {}).get("token", ""),
        token_out=(swap_calldata.raw_response or {}).get("quote", {}).get("output", {}).get("token", ""),
        amount_in_actual_wei=(swap_calldata.raw_response or {}).get("quote", {}).get("input", {}).get("amount"),
        status="pending",
        gas_price_gwei=gas_price_wei / 1e9,
        error_message=None,
    )

    deadline = time.time() + 120
    receipt: Any | None = None
    while time.time() < deadline:
        try:
            receipt = web3_client.eth.get_transaction_receipt(tx_hash_hex)
            if receipt:
                break
        except Exception:
            pass
        time.sleep(3)

    if not receipt:
        _update_execution_row(
            execution_id,
            status="pending_timeout",
            error_message="Timed out waiting for receipt after 120 seconds",
        )
        return BroadcastResult(
            success=False,
            reason="pending_timeout",
            tx_hash=tx_hash_hex,
            execution_id=execution_id,
            tx_receipt=None,
            status="pending_timeout",
        )

    receipt_status = int(getattr(receipt, "status", 0) if not isinstance(receipt, dict) else receipt.get("status", 0))
    gas_used = int(getattr(receipt, "gasUsed", 0) if not isinstance(receipt, dict) else receipt.get("gasUsed", 0))
    update_fields = {
        "status": "confirmed" if receipt_status == 1 else "failed",
        "gas_used_wei": str(gas_used),
        "confirmed_at": _now_utc_naive(),
        "error_message": None if receipt_status == 1 else "onchain_revert",
    }
    _update_execution_row(execution_id, **update_fields)

    return BroadcastResult(
        success=receipt_status == 1,
        reason=None if receipt_status == 1 else "onchain_revert",
        tx_hash=tx_hash_hex,
        execution_id=execution_id,
        tx_receipt=dict(receipt),
        status=update_fields["status"],
    )


def _decode_swap_event(log: Any) -> tuple[int, int] | None:
    topics = list(getattr(log, "topics", []) if not isinstance(log, dict) else log.get("topics", []))
    if not topics:
        return None
    topic0 = topics[0].hex() if hasattr(topics[0], "hex") else str(topics[0])
    if topic0.lower() != SWAP_EVENT_TOPIC.lower():
        return None

    data = getattr(log, "data", "") if not isinstance(log, dict) else log.get("data", "")
    data_bytes = bytes.fromhex(data[2:] if isinstance(data, str) and data.startswith("0x") else str(data))
    decoded = web3_client.codec.decode(["int256", "int256", "uint160", "uint128", "int24"], data_bytes)
    amount0 = int(decoded[0])
    amount1 = int(decoded[1])
    return amount0, amount1


def analyze_execution(
    quote_result: QuoteResult,
    tx_receipt: dict[str, Any] | Any,
    session_id: str,
    round_number: int,
) -> ExecutionAnalysisResult:
    """Calculate realized slippage from receipt logs and update swap_executions."""
    if not tx_receipt:
        return ExecutionAnalysisResult(
            success=False,
            reason="missing_receipt",
            amount_out_actual_wei=None,
            execution_price=None,
            slippage_realized_percent=None,
        )

    tx_hash_raw = tx_receipt.get("transactionHash") if isinstance(tx_receipt, dict) else getattr(tx_receipt, "transactionHash", None)
    tx_hash = tx_hash_raw.hex() if hasattr(tx_hash_raw, "hex") else str(tx_hash_raw)

    logs = tx_receipt.get("logs", []) if isinstance(tx_receipt, dict) else getattr(tx_receipt, "logs", [])

    decoded_swap: tuple[int, int] | None = None
    for log in logs:
        decoded_swap = _decode_swap_event(log)
        if decoded_swap:
            break

    if not decoded_swap:
        _update_execution_row(
            _find_execution_id(session_id, round_number, tx_hash),
            error_message="swap_event_not_found_in_receipt_logs",
        )
        return ExecutionAnalysisResult(
            success=False,
            reason="swap_event_not_found",
            amount_out_actual_wei=None,
            execution_price=None,
            slippage_realized_percent=None,
        )

    amount0, amount1 = decoded_swap
    amount_in_actual = abs(amount0)
    amount_out_actual = abs(amount1)

    quote_in_dec, quote_out_dec = _extract_decimals_from_quote(quote_result)
    execution_price = _calculate_normalized_price(
        str(amount_in_actual),
        str(amount_out_actual),
        quote_in_dec,
        quote_out_dec,
    )

    quoted_price = quote_result.quoted_price
    slippage_realized_percent: float | None = None
    if quoted_price is not None and execution_price is not None and quoted_price != 0:
        slippage_realized_percent = ((quoted_price - execution_price) / quoted_price) * 100.0

    execution_id = _find_execution_id(session_id, round_number, tx_hash)
    _update_execution_row(
        execution_id,
        amount_out_actual_wei=str(amount_out_actual),
        execution_price=execution_price,
        slippage_realized_percent=slippage_realized_percent,
    )

    if slippage_realized_percent is not None and abs(slippage_realized_percent) > (DEFAULT_SLIPPAGE_TOLERANCE * 2):
        warning_message = (
            f"Realized slippage anomaly. quote={quoted_price:.8f}, execution={execution_price:.8f}, "
            f"slippage={slippage_realized_percent:.4f}%"
        )
        _insert_warning(
            session_id=session_id,
            round_number=round_number,
            quote_id=quote_result.quote_id,
            execution_id=execution_id,
            warning_type="slippage_exceeds_double_tolerance",
            message=warning_message,
        )
        print("!!! SWAP WARNING !!!")
        print(warning_message)

    return ExecutionAnalysisResult(
        success=True,
        reason=None,
        amount_out_actual_wei=str(amount_out_actual),
        execution_price=execution_price,
        slippage_realized_percent=slippage_realized_percent,
    )


def _find_execution_id(session_id: str, round_number: int, tx_hash: str | None) -> int | None:
    if not tx_hash:
        return None
    try:
        with get_session() as session:
            rows = (
                session.query(SwapExecution)
                .filter(
                    SwapExecution.session_id == session_id,
                    SwapExecution.round_number == round_number,
                    SwapExecution.tx_hash == tx_hash,
                )
                .order_by(SwapExecution.id.desc())
                .limit(1)
                .all()
            )
            return rows[0].id if rows else None
    except Exception:
        return None


def _load_debate_escrow_contract() -> Any:
    if not ALCHEMY_RPC_URL:
        raise RuntimeError("ALCHEMY_RPC_URL is required")
    escrow_address = os.getenv("ESCROW_CONTRACT_ADDRESS", "").strip()
    if not escrow_address:
        raise RuntimeError("ESCROW_CONTRACT_ADDRESS is required")

    abi_path = PROJECT_ROOT / "contracts" / "abi" / "DebateEscrow.json"
    with abi_path.open("r", encoding="utf-8") as f:
        abi = json.load(f)
    return web3_client.eth.contract(address=Web3.to_checksum_address(escrow_address), abi=abi)


def _losing_and_winning_tokens_from_side(losing_side: str) -> tuple[str, str]:
    normalized = losing_side.strip().lower()
    if normalized == "bear":
        return BEAR_SIDE_TOKEN_SYMBOL, BULL_SIDE_TOKEN_SYMBOL
    if normalized == "bull":
        return BULL_SIDE_TOKEN_SYMBOL, BEAR_SIDE_TOKEN_SYMBOL
    raise ValueError(f"Unsupported losing_side: {losing_side}")


def _eth_threshold_to_base_units(token_symbol: str, threshold_eth: float) -> int:
    decimals = resolve_token_decimals(token_symbol)
    return int(threshold_eth * (10 ** decimals))


def execute_micro_settlement(
    session_id: str,
    round_number: int,
    losing_side: str,
    verdict_dict: dict[str, Any],
) -> SettlementResult:
    """Run quote -> calldata -> broadcast -> analyze for one micro-settlement round."""
    del verdict_dict
    init_database()

    try:
        token_in_symbol, token_out_symbol = _losing_and_winning_tokens_from_side(losing_side)
    except ValueError as exc:
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:{exc}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, str(exc), None, None, None)

    try:
        escrow_contract = _load_debate_escrow_contract()
        bull_total, bear_total, _active = escrow_contract.functions.getStakeInfo().call()
    except Exception as exc:
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:stake_info_failed:{exc}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, f"stake_info_failed:{exc}", None, None, None)

    losing_total = int(bear_total if losing_side.strip().lower() == "bear" else bull_total)
    amount_in_wei = int(losing_total * (MICRO_SETTLEMENT_PERCENT / 100.0))
    if amount_in_wei <= 0:
        reason = "micro_amount_is_zero"
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:{reason}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, reason, None, None, None)

    token_in_threshold = _eth_threshold_to_base_units(token_in_symbol, MICRO_SETTLEMENT_MIN_ETH_EQUIVALENT)
    if amount_in_wei < token_in_threshold:
        reason = "below_minimum_threshold"
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:{reason}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, reason, None, None, None)

    quote = fetch_quote(
        token_in=token_in_symbol,
        token_out=token_out_symbol,
        amount_in_wei=str(amount_in_wei),
        swap_type="micro_settlement",
        session_id=session_id,
        round_number=round_number,
    )
    if not quote.success:
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:quote_failed:{quote.reason}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, quote.reason, None, None, None)

    swap_calldata = build_swap_calldata(quote)
    if not swap_calldata.success:
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"skipped:swap_build_failed:{swap_calldata.reason}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, swap_calldata.reason, None, None, None)

    # Route through KeeperHub or fall back to direct submit depending on flag
    USE_KEEPERHUB = os.getenv("USE_KEEPERHUB", "true").strip().lower() in {"1", "true", "yes"}
    if not USE_KEEPERHUB:
        # Build SwapCalldata is identical; call existing broadcast path
        broadcast = broadcast_and_confirm(swap_calldata, session_id, round_number, "micro_settlement")
        analysis = analyze_execution(quote, broadcast.tx_receipt, session_id, round_number)
        return SettlementResult(broadcast.success, broadcast.reason, broadcast.tx_hash, None, analysis.amount_out_actual_wei)

    # Use KeeperHub unified executor
    result = execute_swap_via_keeperhub(session_id, round_number, "micro_settlement", quote)
    if not result.get("success"):
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            micro_settlement_tx_hash=f"failed:keeperhub:{result.get('reason')}",
            timestamp=_now_utc_naive(),
        )
        return SettlementResult(False, result.get("reason"), None, None, None)

    upsert_round_trace(
        session_id=session_id,
        round_number=round_number,
        micro_settlement_tx_hash=f"keeperhub_job:{result.get('job_id')}",
        timestamp=_now_utc_naive(),
    )

    return SettlementResult(True, "confirmed", result.get("tx_hash"), result.get("job_id"), None)


def execute_final_settlement(session_id: str, winning_side: str, call_settle_side: bool = True) -> dict[str, Any]:
    """Run final settlement swaps (optionally split) and call settleSide on DebateEscrow."""
    init_database()
    losing_side = "bear" if winning_side.strip().lower() == "bull" else "bull"
    token_in_symbol, token_out_symbol = _losing_and_winning_tokens_from_side(losing_side)

    escrow_contract = _load_debate_escrow_contract()
    bull_total, bear_total, _active = escrow_contract.functions.getStakeInfo().call()
    total_losing_wei = int(bear_total if losing_side == "bear" else bull_total)

    threshold_units = _eth_threshold_to_base_units(token_in_symbol, FINAL_SETTLEMENT_SPLIT_THRESHOLD_ETH)
    should_split = total_losing_wei > threshold_units
    if DRY_RUN:
        should_split = False

    tranche_amounts: list[int]
    if should_split:
        first = total_losing_wei // 3
        second = total_losing_wei // 3
        third = total_losing_wei - first - second
        tranche_amounts = [first, second, third]
    else:
        tranche_amounts = [total_losing_wei]

    tranche_hashes: list[str] = []
    tranche_job_ids: list[str] = []
    tranche_in: list[int] = []
    tranche_out: list[int] = []
    tranche_gas_used: list[int] = []

    round_number = -1
    for idx, tranche in enumerate(tranche_amounts):
        quote = fetch_quote(
            token_in=token_in_symbol,
            token_out=token_out_symbol,
            amount_in_wei=str(tranche),
            swap_type="final_settlement",
            session_id=session_id,
            round_number=round_number,
            slippage_tolerance=FINAL_SETTLEMENT_SLIPPAGE_TOLERANCE,
        )
        if not quote.success:
            tranche_hashes.append(f"skipped:final_quote_failed_tranche_{idx + 1}:{quote.reason}")
            tranche_job_ids.append(None)
            tranche_in.append(0)
            tranche_out.append(0)
            tranche_gas_used.append(0)
            continue

        swap_calldata = build_swap_calldata(quote)
        if not swap_calldata.success:
            tranche_hashes.append(f"skipped:final_swap_build_failed_tranche_{idx + 1}:{swap_calldata.reason}")
            tranche_job_ids.append(None)
            tranche_in.append(0)
            tranche_out.append(0)
            tranche_gas_used.append(0)
            continue

        # Use unified keeperhub executor when enabled
        USE_KEEPERHUB = os.getenv("USE_KEEPERHUB", "true").strip().lower() in {"1", "true", "yes"}
        if not USE_KEEPERHUB:
            try:
                job_id = submit_job(
                    session_id=session_id,
                    round_number=round_number,
                    job_type="final_settlement",
                    swap_calldata_obj=swap_calldata,
                    retry_policy=FINAL_SETTLEMENT_RETRY_POLICY,
                )
            except Exception as exc:
                tranche_hashes.append(f"skipped:final_keeperhub_submit_failed_tranche_{idx + 1}:{exc}")
                tranche_job_ids.append(None)
                tranche_in.append(0)
                tranche_out.append(0)
                tranche_gas_used.append(0)
                continue

            execution_id = _insert_execution_row(
                session_id=session_id,
                round_number=round_number,
                swap_type="final_settlement",
                quote_id=swap_calldata.quote_id,
                tx_hash=None,
                token_in=quote.token_in,
                token_out=quote.token_out,
                amount_in_actual_wei=quote.amount_in_wei,
                status="pending",
                gas_price_gwei=None,
                error_message="submitted_to_keeperhub",
            )
            _update_execution_row(execution_id, keeperhub_job_id=job_id)

            tranche_hashes.append(f"keeperhub_job:{job_id}")
            tranche_job_ids.append(job_id)
            tranche_in.append(int(tranche))
            tranche_out.append(0)
            tranche_gas_used.append(0)
        else:
            result = execute_swap_via_keeperhub(session_id, round_number, "final_settlement", quote)
            if not result.get("success"):
                tranche_hashes.append(f"skipped:final_keeperhub_failed_tranche_{idx + 1}:{result.get('reason')}")
                tranche_job_ids.append(result.get("job_id"))
                tranche_in.append(0)
                tranche_out.append(0)
                tranche_gas_used.append(0)
                continue

            execution_id = _insert_execution_row(
                session_id=session_id,
                round_number=round_number,
                swap_type="final_settlement",
                quote_id=swap_calldata.quote_id,
                tx_hash=result.get("tx_hash"),
                token_in=quote.token_in,
                token_out=quote.token_out,
                amount_in_actual_wei=quote.amount_in_wei,
                status="confirmed",
                gas_price_gwei=None,
                error_message=None,
            )
            tranche_hashes.append(result.get("tx_hash") or f"keeperhub_job:{result.get('job_id')}")
            tranche_job_ids.append(result.get("job_id"))
            tranche_in.append(int(tranche))
            analysis = result.get("analysis")
            amount_out_actual_wei = None
            if analysis is not None:
                amount_out_actual_wei = getattr(analysis, "amount_out_actual_wei", None)
                if amount_out_actual_wei is None and isinstance(analysis, dict):
                    amount_out_actual_wei = analysis.get("amount_out_actual_wei")
            try:
                tranche_out.append(int(amount_out_actual_wei) if amount_out_actual_wei is not None else 0)
            except (TypeError, ValueError):
                tranche_out.append(0)
            tranche_gas_used.append(0)

        if idx < len(tranche_amounts) - 1:
            if DRY_RUN:
                print("[DRY_RUN] skipping 30-second inter-tranche pause")
            else:
                time.sleep(30)

    settle_tx_hash: str | None = None
    if call_settle_side:
        try:
            side_enum = 0 if winning_side.strip().lower() == "bull" else 1
            tx = escrow_contract.functions.settleSide(side_enum).build_transaction(
                {
                    "from": Web3.to_checksum_address(AGENT_WALLET_ADDRESS),
                    "nonce": int(web3_client.eth.get_transaction_count(Web3.to_checksum_address(AGENT_WALLET_ADDRESS))),
                    "chainId": int(web3_client.eth.chain_id),
                    "gas": int(os.getenv("ESCROW_SETTLE_GAS_LIMIT", "400000")),
                    "gasPrice": int(web3_client.eth.gas_price),
                    "value": 0,
                }
            )

            if DRY_RUN:
                from utils.dry_run_adapter import DryRunAdapter

                adapter = DryRunAdapter(session_id=session_id, round_number=round_number)
                result = adapter.simulate_contract_call(
                    "DebateEscrow",
                    "settleSide",
                    {"session_id": session_id, "round_number": round_number, "winning_side": winning_side, "tx": tx},
                )
                settle_tx_hash = str(result.get("tx_hash") or Web3.keccak(text=json.dumps(tx, sort_keys=True, default=str)).hex())
                print("[DRY_RUN] settleSide transaction prepared")
            else:
                signed = web3_client.eth.account.sign_transaction(tx, private_key=AGENT_WALLET_PRIVATE_KEY)
                sent_hash = web3_client.eth.send_raw_transaction(signed.raw_transaction)
                settle_tx_hash = sent_hash.hex()
        except Exception as exc:  # pragma: no cover
            return {
                "success": False,
                "reason": f"settle_side_failed:{exc}",
                "tx_hashes": tranche_hashes,
            }

    total_in = sum(tranche_in)
    total_out = sum(tranche_out)
    weighted_execution_price = (float(total_out) / float(total_in)) if total_in > 0 else 0.0
    combined_gas_used = sum(tranche_gas_used)

    _insert_execution_row(
        session_id=session_id,
        round_number=-1,
        swap_type="final_settlement",
        quote_id=None,
        tx_hash=settle_tx_hash,
        token_in=resolve_token_address(token_in_symbol, SWAP_CHAIN_ID),
        token_out=resolve_token_address(token_out_symbol, SWAP_CHAIN_ID),
        amount_in_actual_wei=str(total_in),
        status="confirmed",
        gas_price_gwei=None,
        error_message="final_settlement_summary",
    )

    summary = {
        "success": True,
        "settlement_tx_hash": settle_tx_hash,
        "tranche_tx_hashes": tranche_hashes,
        "tranche_job_ids": tranche_job_ids,
        "total_amount_in_wei": str(total_in),
        "total_amount_out_wei": str(total_out),
        "weighted_execution_price": weighted_execution_price,
        "combined_gas_used": combined_gas_used,
    }
    return summary


def _validator_run_once(iteration: int) -> dict[str, Any]:
    session_id = f"validator-{int(time.time())}-{iteration}"
    round_number = iteration

    attempted_amounts = [
        Web3.to_wei(0.001, "ether"),
        Web3.to_wei(0.0001, "ether"),
        Web3.to_wei(0.00005, "ether"),
        Web3.to_wei(0.00001, "ether"),
    ]
    quote: QuoteResult | None = None
    used_amount_wei: int | None = None
    fallback_applied = False
    for retry_index in range(3):
        for index, amount_in_wei in enumerate(attempted_amounts):
            candidate = fetch_quote(
                token_in="ETH",
                token_out="USDC",
                amount_in_wei=str(amount_in_wei),
                swap_type="micro_settlement",
                session_id=session_id,
                round_number=round_number,
            )
            if candidate.success:
                quote = candidate
                used_amount_wei = amount_in_wei
                fallback_applied = index > 0 or retry_index > 0
                break
            if candidate.reason not in {"no_liquidity", "quote_http_error", "quote_timeout", "quote_request_failed"}:
                quote = candidate
                used_amount_wei = amount_in_wei
                break
        if quote is not None:
            break
        if retry_index < 2:
            time.sleep(1)

    if quote is None:
        quote = candidate
        used_amount_wei = attempted_amounts[-1]

    if not quote.success:
        return {
            "ok": False,
            "stage": "quote",
            "reason": quote.reason,
            "session_id": session_id,
            "round_number": round_number,
        }

    calldata = build_swap_calldata(quote)
    if not calldata.success or not calldata.calldata:
        return {
            "ok": False,
            "stage": "swap",
            "reason": calldata.reason,
            "session_id": session_id,
            "round_number": round_number,
        }

    broadcast = broadcast_and_confirm(calldata, session_id, round_number, "micro_settlement")
    analysis = analyze_execution(quote, broadcast.tx_receipt, session_id, round_number)

    with get_session() as session:
        quote_rows = session.query(SwapQuote).filter(SwapQuote.session_id == session_id).count()
        exec_rows = session.query(SwapExecution).filter(SwapExecution.session_id == session_id).count()

    return {
        "ok": True,
        "session_id": session_id,
        "round_number": round_number,
        "quote_id": quote.quote_id,
            "requested_amount_wei": str(attempted_amounts[0]),
            "used_amount_wei": str(used_amount_wei) if used_amount_wei is not None else None,
            "fallback_applied": fallback_applied,
        "tx_hash": broadcast.tx_hash,
        "calldata_non_empty": bool(calldata.calldata and calldata.calldata.startswith("0x")),
        "quote_rows": quote_rows,
        "execution_rows": exec_rows,
        "analysis_success": analysis.success,
        "analysis_reason": analysis.reason,
    }


def close_swap_clients() -> None:
    """Close long-lived clients created by this module."""
    uniswap_http_client.close()


if __name__ == "__main__":
    init_database()
    print(f"[validator] DRY_RUN={DRY_RUN}")

    validator_results: list[dict[str, Any]] = []
    for i in range(1, 4):
        result = _validator_run_once(i)
        validator_results.append(result)
        print(f"[validator][run={i}] {json.dumps(result, default=str)}")

    feedback_path = PROJECT_ROOT / "FEEDBACK.md"
    if not feedback_path.exists():
        feedback_path.write_text(
            "# Uniswap Integration Feedback\n\n"
            "## Run Metadata\n"
            f"- Date: {_now_utc_naive().isoformat()}\n"
            f"- Chain: {SWAP_CHAIN_ID}\n"
            f"- API Base: {UNISWAP_API_BASE}\n"
            f"- DRY_RUN: {DRY_RUN}\n\n"
            "## Validator Runs\n"
            + "\n".join([f"- Run {idx}: {json.dumps(item, default=str)}" for idx, item in enumerate(validator_results, start=1)])
            + "\n\n"
            "## Friction Points\n"
            "- API responses differ by route type, which complicates one-size-fits-all parsing.\n"
            "- For dry-run integration testing, there is no canonical synthetic receipt format from API docs.\n"
            "- Rate limit docs expose 429 behavior but do not clearly publish per-minute limits by free plan in API reference.\n\n"
            "## Documentation Gaps\n"
            "- More explicit examples for /swap when permitData is null vs provided would reduce integration errors.\n"
            "- A dedicated section mapping quote routing variants to expected quote payload shape would help.\n"
            "- Clarification around plan-specific rate-limit numbers in the docs would improve production planning.\n\n"
            "## Requested Features\n"
            "- A documented sandbox mode for swap transaction generation without requiring onchain broadcast.\n"
            "- A lightweight endpoint to validate quote freshness/expiry semantics directly.\n",
            encoding="utf-8",
        )
    else:
        with feedback_path.open("a", encoding="utf-8") as f:
            f.write("\n## Additional Run\n")
            f.write(f"- Date: {_now_utc_naive().isoformat()}\n")
            for idx, item in enumerate(validator_results, start=1):
                f.write(f"- Run {idx}: {json.dumps(item, default=str)}\n")
            if any(item.get("reason") == "unauthorized_api_key" for item in validator_results):
                f.write("- Auth diagnostic: Uniswap API rejected key; set UNISWAP_API_KEY in .env to a valid dashboard key.\n")
