from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.bear_agent import run_bear_round
from agents.bull_agent import run_bull_round
from agents.judge_agent import run_judge_round
from keeper import keeper_handler
from utils.db_manager import (
    get_debate_session_by_session_id,
    init_database,
    insert_debate_session,
    update_debate_session,
    upsert_round_trace,
)
from utils.market_data import fetch_snapshot

load_dotenv()


STATE_IDLE = "IDLE"
STATE_ACCEPTING_STAKES = "ACCEPTING_STAKES"
STATE_ROUND_IN_PROGRESS = "ROUND_IN_PROGRESS"
STATE_AWAITING_JUDGE = "AWAITING_JUDGE"
STATE_CONVICTION_UPDATED = "CONVICTION_UPDATED"
STATE_DEBATE_ENDED = "DEBATE_ENDED"
STATE_SETTLEMENT_TRIGGERED = "SETTLEMENT_TRIGGERED"

ALL_STATES = {
    STATE_IDLE,
    STATE_ACCEPTING_STAKES,
    STATE_ROUND_IN_PROGRESS,
    STATE_AWAITING_JUDGE,
    STATE_CONVICTION_UPDATED,
    STATE_DEBATE_ENDED,
    STATE_SETTLEMENT_TRIGGERED,
}

# Deterministic transition map: each orchestrator function drives one of these edges.
STATE_TRANSITIONS: dict[str, set[str]] = {
    STATE_IDLE: {STATE_ACCEPTING_STAKES},
    STATE_ACCEPTING_STAKES: {STATE_ROUND_IN_PROGRESS, STATE_IDLE},
    STATE_ROUND_IN_PROGRESS: {STATE_AWAITING_JUDGE, STATE_IDLE},
    STATE_AWAITING_JUDGE: {STATE_CONVICTION_UPDATED, STATE_DEBATE_ENDED, STATE_IDLE},
    STATE_CONVICTION_UPDATED: {STATE_ROUND_IN_PROGRESS, STATE_DEBATE_ENDED, STATE_IDLE},
    STATE_DEBATE_ENDED: {STATE_SETTLEMENT_TRIGGERED, STATE_IDLE},
    STATE_SETTLEMENT_TRIGGERED: {STATE_DEBATE_ENDED},
}

ROUND_INTERVAL_SECONDS = int(os.getenv("ROUND_INTERVAL_SECONDS", "60"))
WIN_THRESHOLD = int(os.getenv("CONVICTION_WIN_THRESHOLD", "70"))
NEUTRAL_AGENT_ARGUMENT = {
    "argument": "Neutral fallback: agent output unavailable this round; no directional edge inferred.",
    "confidence": 50,
    "keyMetrics": [
        "fallback: true",
        "weighting: reduced",
    ],
}


class RecoverableRoundSetupError(RuntimeError):
    """Raised when setup pre-flight checks fail but retrying is valid."""


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _state_transition_or_raise(session_id: str, next_state: str) -> None:
    if next_state not in ALL_STATES:
        raise ValueError(f"Invalid orchestrator state: {next_state}")

    row = get_debate_session_by_session_id(session_id)
    if row is None:
        raise ValueError(f"Unknown debate session: {session_id}")

    current = str(row.status)
    allowed = STATE_TRANSITIONS.get(current, set())
    if next_state not in allowed and next_state != current:
        raise ValueError(f"Invalid state transition {current} -> {next_state} for session {session_id}")

    update_debate_session(session_id, status=next_state)


def _select_private_key() -> str:
    key_candidates = [
        os.getenv("ORCHESTRATOR_PRIVATE_KEY"),
        os.getenv("AGENT_WALLET_PRIVATE_KEY"),
        os.getenv("DEPLOYER_PRIVATE_KEY"),
    ]
    private_key = next(
        (
            candidate
            for candidate in key_candidates
            if isinstance(candidate, str) and candidate.strip() and not candidate.strip().startswith("your_")
        ),
        None,
    )
    if private_key is None:
        raise RuntimeError("Missing private key for orchestrator transactions")
    return private_key


def _load_abi(abi_path: Path) -> list[dict[str, Any]]:
    with abi_path.open("r", encoding="utf-8") as handle:
        raw_abi = json.load(handle)
    if isinstance(raw_abi, dict):
        maybe_abi = raw_abi.get("abi", raw_abi)
    else:
        maybe_abi = raw_abi
    if not isinstance(maybe_abi, list):
        raise RuntimeError(f"Invalid ABI at {abi_path}")
    return maybe_abi


def _get_web3_and_conviction_contract() -> tuple[Web3, Any]:
    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    conviction_address = os.getenv("CONVICTION_CONTRACT_ADDRESS")
    if not rpc_url or not conviction_address:
        raise RuntimeError("Missing RPC URL or conviction contract address")

    conviction_abi = _load_abi(PROJECT_ROOT / "contracts" / "abi" / "ConvictionTracker.json")
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Unable to connect to Unichain Sepolia RPC")

    conviction_contract = web3.eth.contract(
        address=Web3.to_checksum_address(conviction_address),
        abi=conviction_abi,
    )
    return web3, conviction_contract


def _read_onchain_scores() -> tuple[int, int]:
    _web3, conviction_contract = _get_web3_and_conviction_contract()
    bull_score = int(conviction_contract.functions.currentBullScore().call())
    bear_score = int(conviction_contract.functions.currentBearScore().call())
    return bull_score, bear_score


def _read_contract_declared_winner() -> str | None:
    web3, conviction_contract = _get_web3_and_conviction_contract()
    latest_block = int(web3.eth.block_number)
    from_block = max(0, latest_block - 20000)
    try:
        logs = conviction_contract.events.DebateWinnerDeclared().get_logs(
            from_block=from_block,
            to_block=latest_block,
        )
    except Exception:
        return None

    if not logs:
        return None

    last = logs[-1]
    args = getattr(last, "args", None)
    if args is None and isinstance(last, dict):
        args = last.get("args")
    if not isinstance(args, dict):
        return None

    winning_side = args.get("winningSide")
    if not isinstance(winning_side, str):
        return None
    normalized = winning_side.strip().lower()
    if normalized in {"bull", "bear", "draw"}:
        return normalized
    return None


def _send_contract_tx(
    *,
    web3: Web3,
    private_key: str,
    contract_function: Any,
    gas_limit_env_var: str,
) -> str:
    chain_id = int(web3.eth.chain_id)
    if os.getenv("BLOCK_REAL_MONEY_TRANSACTIONS", "1") == "1":
        allowed_raw = os.getenv("TX_ALLOWED_CHAIN_IDS", "1301,11155111,84532,421614")
        allowed_ids = {int(item.strip()) for item in allowed_raw.split(",") if item.strip()}
        if chain_id not in allowed_ids:
            raise RuntimeError(
                f"Transaction blocked by safety policy on chain_id={chain_id}. "
                "Set TX_ALLOWED_CHAIN_IDS or disable BLOCK_REAL_MONEY_TRANSACTIONS for explicit override."
            )

    account = web3.eth.account.from_key(private_key)
    nonce = web3.eth.get_transaction_count(account.address)
    tx = contract_function.build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "chainId": chain_id,
            "gas": int(os.getenv(gas_limit_env_var, "350000")),
            "gasPrice": int(web3.eth.gas_price),
        }
    )
    signed = web3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt_timeout = int(os.getenv("ORCHESTRATOR_TX_RECEIPT_TIMEOUT_SECONDS", "180"))
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=receipt_timeout)
    if int(receipt.status) != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return tx_hash.hex()


def _coerce_snapshot_payload(snapshot: Any) -> dict[str, Any]:
    if is_dataclass(snapshot):
        return json.loads(json.dumps(asdict(snapshot), default=str))
    if isinstance(snapshot, dict):
        return json.loads(json.dumps(snapshot, default=str))
    return {"raw": str(snapshot)}


def _ping_axl_node(base_url: str) -> tuple[bool, str]:
    base = base_url.rstrip("/")
    if not base:
        return False, "empty URL"

    endpoints = [f"{base}/health", base]
    for endpoint in endpoints:
        try:
            with httpx.Client(timeout=2.0) as client:
                response = client.get(endpoint)
            if response.status_code < 500:
                return True, f"reachable via {endpoint} ({response.status_code})"
        except httpx.HTTPError:
            continue

    return False, f"unreachable: {base}"


def initialize_debate_session(token_pair: str, max_rounds: int, round_interval_seconds: int) -> str:
    """Create an orchestrator session and start both onchain debate contracts."""
    init_database()

    session_id = str(uuid4())
    start_time = _utcnow()

    insert_debate_session(
        session_id=session_id,
        token_pair=token_pair,
        start_time=start_time,
        total_rounds=max_rounds,
        status=STATE_IDLE,
    )

    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    escrow_address = os.getenv("ESCROW_CONTRACT_ADDRESS")
    conviction_address = os.getenv("CONVICTION_CONTRACT_ADDRESS")

    if not rpc_url or not escrow_address or not conviction_address:
        raise RuntimeError("Missing RPC URL or contract addresses for orchestrator session init")

    escrow_abi = _load_abi(PROJECT_ROOT / "contracts" / "abi" / "DebateEscrow.json")
    conviction_abi = _load_abi(PROJECT_ROOT / "contracts" / "abi" / "ConvictionTracker.json")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Unable to connect to Unichain Sepolia RPC")

    private_key = _select_private_key()
    escrow_contract = web3.eth.contract(address=Web3.to_checksum_address(escrow_address), abi=escrow_abi)
    conviction_contract = web3.eth.contract(address=Web3.to_checksum_address(conviction_address), abi=conviction_abi)

    debate_duration_seconds = int(max_rounds) * int(round_interval_seconds) * 2

    allow_active_reuse = os.getenv("ORCHESTRATOR_ALLOW_ACTIVE_DEBATE_REUSE", "1") == "1"

    escrow_tx_hash: str = "not-submitted"
    conviction_tx_hash: str = "not-submitted"
    try:
        escrow_active = bool(escrow_contract.functions.debateActive().call())
    except Exception:
        escrow_active = False

    try:
        conviction_active = bool(conviction_contract.functions.debateActive().call())
    except Exception:
        conviction_active = False

    try:
        if escrow_active and allow_active_reuse:
            escrow_tx_hash = "skipped:escrow already active"
        else:
            try:
                escrow_tx_hash = _send_contract_tx(
                    web3=web3,
                    private_key=private_key,
                    contract_function=escrow_contract.functions.startDebate(int(debate_duration_seconds)),
                    gas_limit_env_var="ESCROW_START_GAS_LIMIT",
                )
            except Exception as exc:  # noqa: BLE001
                if allow_active_reuse:
                    escrow_tx_hash = f"skipped:escrow start failed ({type(exc).__name__})"
                else:
                    raise

        if conviction_active and allow_active_reuse:
            conviction_tx_hash = "skipped:conviction already active"
        else:
            try:
                conviction_tx_hash = _send_contract_tx(
                    web3=web3,
                    private_key=private_key,
                    contract_function=conviction_contract.functions.startDebate(),
                    gas_limit_env_var="CONVICTION_START_GAS_LIMIT",
                )
            except Exception as exc:  # noqa: BLE001
                if allow_active_reuse:
                    conviction_tx_hash = f"skipped:conviction start failed ({type(exc).__name__})"
                else:
                    raise
    except Exception:
        update_debate_session(session_id, status=STATE_IDLE)
        raise

    _state_transition_or_raise(session_id, STATE_ACCEPTING_STAKES)

    try:
        win_threshold = int(conviction_contract.functions.winThreshold().call())
    except Exception:
        win_threshold = int(os.getenv("CONVICTION_WIN_THRESHOLD", "70"))

    countdown_seconds = int(os.getenv("ORCHESTRATOR_FIRST_ROUND_COUNTDOWN_SECONDS", str(round_interval_seconds)))

    print("=" * 72)
    print("CONVEXA ORCHESTRATOR SESSION STARTED")
    print(f"session_id: {session_id}")
    print(f"token_pair: {token_pair}")
    print(f"escrow_contract: {escrow_address}")
    print(f"conviction_contract: {conviction_address}")
    print(f"win_threshold: {win_threshold}")
    print(f"max_rounds: {max_rounds} | round_interval_seconds: {round_interval_seconds}")
    print(f"escrow_start_tx: {escrow_tx_hash}")
    print(f"conviction_start_tx: {conviction_tx_hash}")
    print(f"countdown_to_first_round_seconds: {countdown_seconds}")
    print("=" * 72)

    return session_id


def setup_round(session_id: str, round_number: int, token_pair: str) -> Any:
    """Fetch market snapshot, persist pre-agent trace, and verify AXL pre-flight health."""
    init_database()

    snapshot = fetch_snapshot(token_pair)
    snapshot_payload = _coerce_snapshot_payload(snapshot)

    upsert_round_trace(
        session_id=session_id,
        round_number=round_number,
        market_snapshot_json=snapshot_payload,
        timestamp=_utcnow(),
    )

    node1_url = os.getenv("BEAR_AXL_HTTP_URL", "http://localhost:8001")
    node2_url = os.getenv("BULL_AXL_HTTP_URL", "http://localhost:8002")

    node1_ok, node1_detail = _ping_axl_node(node1_url)
    node2_ok, node2_detail = _ping_axl_node(node2_url)

    if not node1_ok or not node2_ok:
        update_debate_session(session_id, status=STATE_IDLE)
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            judge_verdict_json={
                "setup_error": "axl_node_unreachable",
                "node1": node1_detail,
                "node2": node2_detail,
                "retry_after_seconds": 10,
            },
            timestamp=_utcnow(),
        )
        raise RecoverableRoundSetupError(
            f"AXL health pre-flight failed. node1={node1_detail}; node2={node2_detail}"
        )

    row = get_debate_session_by_session_id(session_id)
    if row is None:
        raise ValueError(f"Unknown debate session: {session_id}")

    current = str(row.status)
    if current == STATE_IDLE:
        update_debate_session(session_id, status=STATE_ROUND_IN_PROGRESS)
    else:
        _state_transition_or_raise(session_id, STATE_ROUND_IN_PROGRESS)

    return snapshot


def trigger_agents(session_id: str, round_number: int, market_snapshot: Any) -> tuple[dict[str, Any], dict[str, Any], bool]:
    """Run Bull and Bear in parallel, with fallback arguments on timeout/failure."""
    init_database()

    token_pair = ""
    if hasattr(market_snapshot, "token_pair"):
        token_pair = str(getattr(market_snapshot, "token_pair"))
    elif isinstance(market_snapshot, dict):
        token_pair = str(market_snapshot.get("token_pair", ""))

    if not token_pair:
        raise ValueError("market_snapshot is missing token_pair")

    timeout_seconds = float(ROUND_INTERVAL_SECONDS) * 0.4
    partial_round = False
    errors: dict[str, str] = {}

    bull_argument = dict(NEUTRAL_AGENT_ARGUMENT)
    bear_argument = dict(NEUTRAL_AGENT_ARGUMENT)

    with ThreadPoolExecutor(max_workers=2) as executor:
        bull_future = executor.submit(run_bull_round, round_number, token_pair)
        bear_future = executor.submit(run_bear_round, round_number, token_pair)

        try:
            bull_result = bull_future.result(timeout=timeout_seconds)
            bull_payload = bull_result.get("argument") if isinstance(bull_result, dict) else None
            if isinstance(bull_payload, dict):
                bull_argument = bull_payload
            else:
                partial_round = True
                errors["bull"] = "invalid_result_payload"
        except TimeoutError:
            partial_round = True
            errors["bull"] = "timeout"
        except Exception as exc:  # noqa: BLE001
            partial_round = True
            errors["bull"] = f"{type(exc).__name__}: {exc}"

        try:
            bear_result = bear_future.result(timeout=timeout_seconds)
            bear_payload = bear_result.get("argument") if isinstance(bear_result, dict) else None
            if isinstance(bear_payload, dict):
                bear_argument = bear_payload
            else:
                partial_round = True
                errors["bear"] = "invalid_result_payload"
        except TimeoutError:
            partial_round = True
            errors["bear"] = "timeout"
        except Exception as exc:  # noqa: BLE001
            partial_round = True
            errors["bear"] = f"{type(exc).__name__}: {exc}"

    upsert_round_trace(
        session_id=session_id,
        round_number=round_number,
        bull_argument_json=bull_argument,
        bear_argument_json=bear_argument,
        judge_verdict_json={
            "partial_round": partial_round,
            "agent_errors": errors,
        },
        timestamp=_utcnow(),
    )

    return bull_argument, bear_argument, partial_round


def run_judging(
    session_id: str,
    round_number: int,
    bull_argument: dict[str, Any],
    bear_argument: dict[str, Any],
    market_snapshot: Any,
) -> tuple[dict[str, Any], tuple[int, int]]:
    """Trigger Judge, persist verdict trace, then return verdict plus chain-sourced scores."""
    _state_transition_or_raise(session_id, STATE_AWAITING_JUDGE)

    token_pair = ""
    if hasattr(market_snapshot, "token_pair"):
        token_pair = str(getattr(market_snapshot, "token_pair"))
    elif isinstance(market_snapshot, dict):
        token_pair = str(market_snapshot.get("token_pair", ""))
    if not token_pair:
        raise ValueError("market_snapshot is missing token_pair")

    verdict = run_judge_round(round_number, token_pair)

    bull_score, bear_score = _read_onchain_scores()

    upsert_round_trace(
        session_id=session_id,
        round_number=round_number,
        bull_argument_json=bull_argument,
        bear_argument_json=bear_argument,
        judge_verdict_json=verdict,
        bull_score_after_round=bull_score,
        bear_score_after_round=bear_score,
        conviction_tx_hash=(
            verdict.get("publish_result", {}).get("conviction_tx_hash")
            if isinstance(verdict.get("publish_result"), dict)
            else None
        ),
        timestamp=_utcnow(),
    )

    _state_transition_or_raise(session_id, STATE_CONVICTION_UPDATED)
    return verdict, (bull_score, bear_score)


def check_end_conditions(
    session_id: str,
    bull_score: int,
    bear_score: int,
    round_number: int,
    max_rounds: int,
) -> dict[str, Any]:
    """Decide whether debate ends based on score threshold, round cap, or chain settlement flag."""
    winner: str | None = None
    end_reason: str | None = None

    if int(bull_score) >= WIN_THRESHOLD:
        winner = "bull"
        end_reason = "bull_reached_threshold"
    elif int(bear_score) >= WIN_THRESHOLD:
        winner = "bear"
        end_reason = "bear_reached_threshold"
    elif int(round_number) >= int(max_rounds):
        winner = "draw"
        end_reason = "max_rounds_reached"
    else:
        _web3, conviction_contract = _get_web3_and_conviction_contract()
        contract_settlement_triggered = bool(conviction_contract.functions.isSettlementTriggered().call())
        if contract_settlement_triggered:
            winner = _read_contract_declared_winner() or "draw"
            end_reason = "contract_settlement_triggered"

    if winner is None:
        return {"end": False}

    update_debate_session(
        session_id,
        status=STATE_DEBATE_ENDED,
        total_rounds=int(round_number),
        winning_side=winner,
        final_bull_score=int(bull_score),
        final_bear_score=int(bear_score),
        end_time=_utcnow(),
    )
    return {
        "end": True,
        "winner": winner,
        "reason": end_reason,
    }


def trigger_settlement(session_id: str, winning_side: str) -> str:
    """Trigger settlement path (winner payout or draw refund) and persist settlement hash."""
    _state_transition_or_raise(session_id, STATE_SETTLEMENT_TRIGGERED)

    if winning_side == "draw":
        settlement_tx_hash = keeper_handler.execute_draw_refund(session_id)
    else:
        settlement_tx_hash = keeper_handler.execute_settlement(winning_side)

    row = get_debate_session_by_session_id(session_id)
    if row is None:
        raise ValueError(f"Unknown debate session: {session_id}")

    total_duration = (_utcnow() - row.start_time).total_seconds()
    final_bull = int(row.final_bull_score or 0)
    final_bear = int(row.final_bear_score or 0)

    update_debate_session(
        session_id,
        settlement_triggered=True,
        settlement_tx_hash=settlement_tx_hash,
    )

    _state_transition_or_raise(session_id, STATE_DEBATE_ENDED)
    update_debate_session(session_id, end_time=_utcnow())

    print("=" * 72)
    print("CONVEXA ORCHESTRATOR SESSION CLOSED")
    print(f"session_id: {session_id}")
    print(f"winner: {winning_side}")
    print(f"final_scores: bull={final_bull} bear={final_bear}")
    print(f"total_rounds: {row.total_rounds}")
    print(f"total_debate_duration_seconds: {total_duration:.2f}")
    print(f"settlement_tx_hash: {settlement_tx_hash}")
    print("round_trace audit trail is fully stored in SQLite")
    print("=" * 72)

    return settlement_tx_hash


def run_debate(token_pair: str, max_rounds: int, round_interval_seconds: int) -> str:
    """Main orchestrator loop with deterministic pacing and clean interruption handling."""
    session_id = initialize_debate_session(token_pair, max_rounds, round_interval_seconds)
    winning_side: str | None = None

    try:
        for round_number in range(1, max_rounds + 1):
            round_start_time = time.time()

            while True:
                try:
                    snapshot = setup_round(session_id, round_number, token_pair)
                    break
                except RecoverableRoundSetupError as exc:
                    print(f"[ORCHESTRATOR] Round {round_number} pre-flight failed: {exc}. Retrying in 10s.")
                    time.sleep(10)

            bull_argument, bear_argument, partial_round = trigger_agents(session_id, round_number, snapshot)
            if partial_round:
                print(f"[ORCHESTRATOR] Round {round_number} running with partial inputs; judge weighting should be lighter.")

            verdict, (bull_score, bear_score) = run_judging(
                session_id,
                round_number,
                bull_argument,
                bear_argument,
                snapshot,
            )

            end_state = check_end_conditions(
                session_id=session_id,
                bull_score=bull_score,
                bear_score=bear_score,
                round_number=round_number,
                max_rounds=max_rounds,
            )

            round_duration = time.time() - round_start_time
            upsert_round_trace(
                session_id=session_id,
                round_number=round_number,
                round_duration_seconds=round_duration,
                judge_verdict_json=verdict,
                bull_score_after_round=int(bull_score),
                bear_score_after_round=int(bear_score),
                timestamp=_utcnow(),
            )

            if bool(end_state.get("end")):
                winning_side = str(end_state.get("winner", "draw"))
                print(f"[ORCHESTRATOR] Debate end condition met at round {round_number}: {end_state}")
                break

            sleep_seconds = max(0.0, float(round_interval_seconds) - round_duration)
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        update_debate_session(session_id, status=STATE_IDLE, end_time=_utcnow())
        print("[ORCHESTRATOR] Interrupted by user. Session moved to IDLE for clean shutdown.")
        return session_id

    if winning_side is None:
        winning_side = "draw"
        bull_score, bear_score = _read_onchain_scores()
        update_debate_session(
            session_id,
            status=STATE_DEBATE_ENDED,
            total_rounds=max_rounds,
            winning_side=winning_side,
            final_bull_score=int(bull_score),
            final_bear_score=int(bear_score),
            end_time=_utcnow(),
        )

    trigger_settlement(session_id, winning_side)
    return session_id


if __name__ == "__main__":
    env_round_interval_seconds = int(os.getenv("ROUND_INTERVAL_SECONDS", "60"))
    env_win_threshold = int(os.getenv("CONVICTION_WIN_THRESHOLD", "70"))
    env_max_debate_rounds = int(os.getenv("MAX_DEBATE_ROUNDS", "20"))
    env_min_stake_eth = float(os.getenv("MIN_STAKE_ETH", "0.001"))

    print(
        "[ORCHESTRATOR] Loaded config | "
        f"ROUND_INTERVAL_SECONDS={env_round_interval_seconds} | "
        f"CONVICTION_WIN_THRESHOLD={env_win_threshold} | "
        f"MAX_DEBATE_ROUNDS={env_max_debate_rounds} | "
        f"MIN_STAKE_ETH={env_min_stake_eth}"
    )

    # Dry-run entrypoint config requested for demo validation.
    session_id = run_debate("ETH/USDC", max_rounds=5, round_interval_seconds=30)
    print(f"[ORCHESTRATOR] Dry run complete. session_id={session_id}")
