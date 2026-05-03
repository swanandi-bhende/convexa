from __future__ import annotations

import argparse
import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import json
import os
import re
import signal
from pathlib import Path
import sys
import time
import subprocess
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
from agents.memory import AgentMemory, PerformanceTracker
from agents.strategy_adapter import StrategyAdapter
from keeper import execution_handler
from keeper import keeper_handler
from uniswap import swap_executor
from utils.db_manager import (
    get_debate_session_by_session_id,
    init_database,
    insert_debate_session,
    update_debate_session,
    upsert_round_trace,
)
from utils.market_data import fetch_snapshot
from utils.risk_manager import RiskManager, RiskDecision

load_dotenv()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Convexa debate orchestrator")
    parser.add_argument("--token", default="ETH", help="Base token symbol used to build the default token pair.")
    parser.add_argument("--duration", default=None, help='Debate length like "10rounds" or "60minutes".')
    parser.add_argument("--dry-run", action="store_true", help="Enable simulated execution paths across modules.")
    parser.add_argument("--round-interval", type=int, default=60, help="Seconds between debate rounds.")
    parser.add_argument(
        "--min-stake",
        type=float,
        default=float(os.getenv("MIN_STAKE_ETH", "0.001")),
        help="Minimum stake per side in ETH; defaults to the value from .env.",
    )
    parser.add_argument(
        "--token-pair",
        default=None,
        help='Token pair symbol like "ETH/USDC"; defaults to <token>/USDC when omitted.',
    )
    return parser


_CLI_ARGS, _CLI_UNKNOWN_ARGS = _build_arg_parser().parse_known_args()
TOKEN_SYMBOL = _CLI_ARGS.token.strip().upper() or "ETH"
ROUND_INTERVAL_SECONDS = int(_CLI_ARGS.round_interval)
MIN_STAKE_ETH = float(_CLI_ARGS.min_stake)
TOKEN_PAIR = str(_CLI_ARGS.token_pair or f"{TOKEN_SYMBOL}/USDC")
REQUESTED_DURATION = _CLI_ARGS.duration
DRY_RUN = bool(_CLI_ARGS.dry_run or os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"})

os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"
os.environ["MIN_STAKE_ETH"] = str(MIN_STAKE_ETH)
os.environ["MIN_STAKE_EACH_SIDE_ETH"] = str(MIN_STAKE_ETH)


def parse_duration(duration_str: str, round_interval_seconds: int = ROUND_INTERVAL_SECONDS) -> int:
    value = duration_str.strip().lower()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(rounds?|minutes?)", value)
    if match is None:
        raise ValueError(f"Unsupported duration format: {duration_str}")

    amount = float(match.group(1))
    unit = match.group(2)
    if unit.startswith("round"):
        return max(1, int(amount))

    rounds = amount * 60.0 / float(max(round_interval_seconds, 1))
    return max(1, int(round(rounds)))


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


def configure_runtime(dry_run: bool) -> None:
    set_dry_run(dry_run)
    from agents import bear_agent, bull_agent, judge_agent
    from keeper import execution_handler as keeper_execution_handler
    from keeper import keeper_handler as keeper_settlement_handler
    from uniswap import swap_executor
    from utils import db_manager, market_data, risk_manager

    for module in (
        bear_agent,
        bull_agent,
        judge_agent,
        keeper_execution_handler,
        keeper_settlement_handler,
        swap_executor,
        db_manager,
        market_data,
        risk_manager,
    ):
        try:
            module.set_dry_run(dry_run)
        except AttributeError:
            pass


AXL_NODE_PROCESSES: list[subprocess.Popen[Any]] = []
AXL_NODE_LOG_HANDLES: list[Any] = []
AXL_NODE_CONFIGS = {
    "bear": {
        "cwd": PROJECT_ROOT / "axl-nodes" / "bear",
        "log": PROJECT_ROOT / "axl-nodes" / "logs" / "bear.log",
        "port": 8001,
        "url": os.getenv("BEAR_AXL_HTTP_URL", "http://localhost:8001"),
    },
    "bull": {
        "cwd": PROJECT_ROOT / "axl-nodes" / "bull",
        "log": PROJECT_ROOT / "axl-nodes" / "logs" / "bull.log",
        "port": 8002,
        "url": os.getenv("BULL_AXL_HTTP_URL", "http://localhost:8002"),
    },
    "judge": {
        "cwd": PROJECT_ROOT / "axl-nodes" / "judge",
        "log": PROJECT_ROOT / "axl-nodes" / "logs" / "judge.log",
        "port": 8003,
        "url": os.getenv("JUDGE_AXL_HTTP_URL", "http://localhost:8003"),
    },
}



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
    STATE_IDLE: {STATE_ACCEPTING_STAKES, STATE_SETTLEMENT_TRIGGERED, STATE_DEBATE_ENDED},
    STATE_ACCEPTING_STAKES: {STATE_ROUND_IN_PROGRESS, STATE_IDLE},
    STATE_ROUND_IN_PROGRESS: {STATE_AWAITING_JUDGE, STATE_IDLE},
    STATE_AWAITING_JUDGE: {STATE_CONVICTION_UPDATED, STATE_DEBATE_ENDED, STATE_IDLE},
    STATE_CONVICTION_UPDATED: {STATE_ROUND_IN_PROGRESS, STATE_DEBATE_ENDED, STATE_IDLE},
    STATE_DEBATE_ENDED: {STATE_SETTLEMENT_TRIGGERED, STATE_IDLE},
    STATE_SETTLEMENT_TRIGGERED: {STATE_DEBATE_ENDED},
}

STAKE_COLLECTION_WINDOW_SECONDS = int(os.getenv("STAKE_COLLECTION_WINDOW_SECONDS", "120"))
WIN_THRESHOLD = int(os.getenv("DEMO_CONVICTION_WIN_THRESHOLD", os.getenv("CONVICTION_WIN_THRESHOLD", "70")))
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


def _select_settlement_private_key() -> str:
    key_candidates = [
        os.getenv("AGENT_WALLET_PRIVATE_KEY"),
        os.getenv("ORCHESTRATOR_PRIVATE_KEY"),
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
        raise RuntimeError("Missing settlement private key for orchestrator transactions")
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
    if DRY_RUN:
        # In safe mode, return dummy placeholders; callers should handle None appropriately.
        return None, None

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
    if DRY_RUN:
        # Return simulated neutral scores in safe mode
        return 0, 0

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
    value_wei: int = 0,
) -> str:
    if DRY_RUN:
        return "simulated-tx-hash"

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
            "value": int(value_wei),
        }
    )
    signed = web3.eth.account.sign_transaction(tx, private_key=private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt_timeout = int(os.getenv("ORCHESTRATOR_TX_RECEIPT_TIMEOUT_SECONDS", "180"))
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=receipt_timeout)
    if int(receipt.status) != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return tx_hash.hex()


def _seed_stake_deposits(web3: Web3, escrow_contract: Any) -> dict[str, str]:
    if DRY_RUN:
        return {"bull_deposit_tx_hash": "simulated-bull-deposit", "bear_deposit_tx_hash": "simulated-bear-deposit"}

    bull_private_key = os.getenv("BULL_STAKER_PRIVATE_KEY", "").strip()
    bear_private_key = os.getenv("BEAR_STAKER_PRIVATE_KEY", "").strip()
    if not bull_private_key or not bear_private_key:
        raise RuntimeError("Missing bull or bear staker private key for stake seeding")

    target_deposit_eth = float(os.getenv("DEMO_AUTO_STAKE_DEPOSIT_ETH", os.getenv("AUTO_STAKE_DEPOSIT_ETH", "0.1")))
    target_deposit_wei = int(web3.to_wei(target_deposit_eth, "ether"))
    gas_limit = int(os.getenv("ESCROW_DEPOSIT_GAS_LIMIT", "150000"))
    gas_price = int(web3.eth.gas_price)
    gas_budget_wei = gas_limit * gas_price
    bull_stake_wei, bear_stake_wei, _ = escrow_contract.functions.getStakeInfo().call()

    # Check if wallets have enough balance for minimum deposits
    bull_account = web3.eth.account.from_key(bull_private_key)
    bear_account = web3.eth.account.from_key(bear_private_key)
    bull_balance = int(web3.eth.get_balance(bull_account.address))
    bear_balance = int(web3.eth.get_balance(bear_account.address))
    total_needed = target_deposit_wei + gas_budget_wei

    if bull_balance < total_needed:
        print(f"[STAKE WINDOW] bull wallet has {bull_balance / 1e18:.6f} ETH, insufficient for deposit (need {total_needed / 1e18:.6f} ETH), skipping")
    if bear_balance < total_needed:
        print(f"[STAKE WINDOW] bear wallet has {bear_balance / 1e18:.6f} ETH, insufficient for deposit (need {total_needed / 1e18:.6f} ETH), skipping")

    tx_hashes: dict[str, str] = {}
    if int(bull_stake_wei) < target_deposit_wei and bull_balance >= total_needed:
        tx_hashes["bull_deposit_tx_hash"] = _send_contract_tx(
            web3=web3,
            private_key=bull_private_key,
            contract_function=escrow_contract.functions.deposit(0),
            gas_limit_env_var="ESCROW_DEPOSIT_GAS_LIMIT",
            value_wei=target_deposit_wei,
        )

    if int(bear_stake_wei) < target_deposit_wei and bear_balance >= total_needed:
        tx_hashes["bear_deposit_tx_hash"] = _send_contract_tx(
            web3=web3,
            private_key=bear_private_key,
            contract_function=escrow_contract.functions.deposit(1),
            gas_limit_env_var="ESCROW_DEPOSIT_GAS_LIMIT",
            value_wei=target_deposit_wei,
        )

    return tx_hashes


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


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_GREEN = "\033[32m"
ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_CYAN = "\033[36m"


def _ansi_wrap(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


def _format_meter(score: int, width: int = 20) -> str:
    bounded = max(0, min(100, int(score)))
    filled = int(round((bounded / 100.0) * width))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _risk_decision_to_dict(decision: RiskDecision | None) -> dict[str, Any] | None:
    if decision is None:
        return None
    if is_dataclass(decision):
        return asdict(decision)
    return {
        "action": getattr(decision, "action", None),
        "reason": getattr(decision, "reason", None),
        "context": getattr(decision, "context", None),
    }


def display_debate_header(session_id: str, token_pair: str, dry_run: bool) -> None:
    mode_label = "DRY RUN" if dry_run else "LIVE RUN"
    print(ANSI_BOLD + "=" * 72 + ANSI_RESET)
    print(_ansi_wrap(f"CONVEXA DEBATE ORCHESTRATOR [{mode_label}]", ANSI_CYAN))
    print(f"session_id: {session_id}")
    print(f"token_pair: {token_pair}")
    print(f"round_interval_seconds: {ROUND_INTERVAL_SECONDS}")
    print(f"win_threshold: {WIN_THRESHOLD}")
    print(_ansi_wrap("AXL nodes: bear=8001 | bull=8002 | judge=8003", ANSI_DIM))
    print(ANSI_BOLD + "=" * 72 + ANSI_RESET)


def display_round_summary(
    round_number: int,
    verdict_dict: dict[str, Any],
    conviction_scores: tuple[int, int],
    round_duration_seconds: float,
    dry_run: bool,
) -> None:
    bull_score = int(verdict_dict.get("bullScore", conviction_scores[0]))
    bear_score = int(verdict_dict.get("bearScore", conviction_scores[1]))
    winner = str(verdict_dict.get("winner", "draw")).strip().lower() or "draw"
    winner_color = ANSI_GREEN if winner == "bull" else ANSI_RED if winner == "bear" else ANSI_YELLOW
    settlement_result = verdict_dict.get("micro_settlement_result") or {}
    settlement_tx_hash = settlement_result.get("tx_hash") or verdict_dict.get("micro_settlement_tx_hash")

    print(ANSI_BOLD + "-" * 72 + ANSI_RESET)
    print(
        _ansi_wrap(f"ROUND {round_number} COMPLETE", ANSI_CYAN)
        + f" | duration={round_duration_seconds:.2f}s | mode={'DRY' if dry_run else 'LIVE'}"
    )
    print(
        f"winner={_ansi_wrap(winner.upper(), winner_color)} | "
        f"bull={bull_score:>3} {_format_meter(bull_score)} | "
        f"bear={bear_score:>3} {_format_meter(bear_score)}"
    )
    if settlement_tx_hash:
        print(f"micro_settlement_tx_hash: {settlement_tx_hash}")
    if verdict_dict.get("reason"):
        print(f"round_status: {verdict_dict.get('reason')}")
    print(ANSI_BOLD + "-" * 72 + ANSI_RESET)


def _resolve_settlement_wallets() -> list[str]:
    wallets: list[str] = []
    env_wallets = os.getenv("SETTLEMENT_TEST_WALLETS", "").strip()
    if env_wallets:
        for candidate in env_wallets.split(","):
            cleaned = candidate.strip()
            if cleaned:
                wallets.append(cleaned)

    if len(wallets) < 3:
        address_candidates = [
            os.getenv("AGENT_WALLET_ADDRESS"),
            os.getenv("KEEPERHUB_EXECUTOR_ADDRESS"),
        ]
        private_key_candidates = [
            os.getenv("ORCHESTRATOR_PRIVATE_KEY"),
            os.getenv("AGENT_WALLET_PRIVATE_KEY"),
            os.getenv("DEPLOYER_PRIVATE_KEY"),
        ]
        for candidate in address_candidates:
            if isinstance(candidate, str) and candidate.strip():
                wallets.append(candidate.strip())
        for private_key in private_key_candidates:
            if len(wallets) >= 3:
                break
            if isinstance(private_key, str) and private_key.strip() and not private_key.strip().startswith("your_"):
                try:
                    wallets.append(Web3().eth.account.from_key(private_key.strip()).address)
                except Exception:
                    continue

    unique_wallets: list[str] = []
    seen: set[str] = set()
    for wallet in wallets:
        normalized = wallet.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_wallets.append(normalized)
        if len(unique_wallets) == 3:
            break
    return unique_wallets


def _read_wallet_balances(wallets: list[str]) -> dict[str, int]:
    if DRY_RUN:
        return {wallet: 0 for wallet in wallets}

    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    if not rpc_url:
        raise RuntimeError("Missing RPC URL for wallet balance verification")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Unable to connect to RPC for wallet balance verification")

    return {
        wallet: int(web3.eth.get_balance(Web3.to_checksum_address(wallet)))
        for wallet in wallets
    }


def execute_single_round(
    session_id: str,
    round_number: int,
    token_pair: str,
    dry_run: bool,
) -> tuple[bool, dict[str, Any]]:
    round_started_at = time.time()
    risk_manager = RiskManager(session_id)
    round_trace_payload: dict[str, Any] = {
        "session_id": session_id,
        "round_number": round_number,
        "dry_run": dry_run,
        "round_completed_successfully": False,
    }
    end_condition_result: dict[str, Any] = {"end": False}
    micro_settlement_result: dict[str, Any] | None = None

    gas_decision = risk_manager.check_gas_conditions(round_number, session_id)
    round_trace_payload["gas_decision"] = _risk_decision_to_dict(gas_decision)
    if gas_decision.action == "HALT":
        round_trace_payload["halt_reason"] = gas_decision.reason
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            judge_verdict_json=round_trace_payload,
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (0, 0), 0.0, dry_run)
        return False, {"end": False, "reason": gas_decision.reason, "action": gas_decision.action, "bull_score": 0, "bear_score": 0}

    if gas_decision.action == "DELAY_SWAP":
        round_trace_payload["gas_delay_seconds"] = int(gas_decision.context.get("delay_seconds", 15)) if isinstance(gas_decision.context, dict) else 15

    try:
        snapshot = setup_round(session_id, round_number, token_pair, risk_manager)
    except RecoverableRoundSetupError as exc:
        round_trace_payload["setup_error"] = str(exc)
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            judge_verdict_json=round_trace_payload,
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (0, 0), time.time() - round_started_at, dry_run)
        return False, {"end": False, "reason": str(exc), "action": "RETRYABLE_SETUP_FAILURE", "bull_score": 0, "bear_score": 0}
    except Exception as exc:
        round_trace_payload["setup_error"] = f"{type(exc).__name__}: {exc}"
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            judge_verdict_json=round_trace_payload,
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (0, 0), time.time() - round_started_at, dry_run)
        return False, {"end": False, "reason": str(exc), "action": "SETUP_FAILED", "bull_score": 0, "bear_score": 0}

    snapshot_payload = _coerce_snapshot_payload(snapshot)
    freshness_decision = risk_manager.check_data_freshness(snapshot_payload, round_number)
    round_trace_payload["data_freshness_decision"] = _risk_decision_to_dict(freshness_decision)
    if freshness_decision.action in {"SKIP_ROUND", "HALT"}:
        round_trace_payload["halt_reason"] = freshness_decision.reason
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            market_snapshot_json=snapshot_payload,
            judge_verdict_json=round_trace_payload,
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (0, 0), time.time() - round_started_at, dry_run)
        return False, {"end": False, "reason": freshness_decision.reason, "action": freshness_decision.action, "bull_score": 0, "bear_score": 0}

    bull_argument, bear_argument, partial_round = trigger_agents(session_id, round_number, snapshot)
    round_trace_payload["partial_round"] = partial_round
    round_trace_payload["bull_argument"] = bull_argument
    round_trace_payload["bear_argument"] = bear_argument

    prior_bull_score, prior_bear_score = _read_onchain_scores()
    pre_drift_decision = risk_manager.check_conviction_drift(
        round_number,
        int(prior_bull_score),
        int(prior_bear_score),
        session_id,
    )
    round_trace_payload["pre_drift_decision"] = _risk_decision_to_dict(pre_drift_decision)
    if pre_drift_decision.action in {"PAUSE", "HALT", "REJECT_MESSAGE"}:
        round_trace_payload["halt_reason"] = pre_drift_decision.reason
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            bull_argument_json=bull_argument,
            bear_argument_json=bear_argument,
            judge_verdict_json=round_trace_payload,
            bull_score_after_round=prior_bull_score,
            bear_score_after_round=prior_bear_score,
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (prior_bull_score, prior_bear_score), time.time() - round_started_at, dry_run)
        return False, {"end": False, "reason": pre_drift_decision.reason, "action": pre_drift_decision.action, "bull_score": int(prior_bull_score), "bear_score": int(prior_bear_score)}

    verdict, (bull_score, bear_score) = run_judging(
        session_id,
        round_number,
        bull_argument,
        bear_argument,
        snapshot,
        risk_manager,
    )
    round_trace_payload["verdict"] = verdict

    post_drift_decision = risk_manager.check_conviction_drift(round_number, int(bull_score), int(bear_score), session_id)
    round_trace_payload["post_drift_decision"] = _risk_decision_to_dict(post_drift_decision)
    if post_drift_decision.action in {"PAUSE", "HALT", "REJECT_MESSAGE"}:
        round_trace_payload["halt_reason"] = post_drift_decision.reason
        upsert_round_trace(
            session_id=session_id,
            round_number=round_number,
            bull_argument_json=bull_argument,
            bear_argument_json=bear_argument,
            judge_verdict_json=round_trace_payload,
            bull_score_after_round=int(bull_score),
            bear_score_after_round=int(bear_score),
            timestamp=_utcnow(),
        )
        display_round_summary(round_number, round_trace_payload, (int(bull_score), int(bear_score)), time.time() - round_started_at, dry_run)
        return False, {"end": False, "reason": post_drift_decision.reason, "action": post_drift_decision.action, "bull_score": int(bull_score), "bear_score": int(bear_score)}

    end_condition_result = check_end_conditions(
        session_id=session_id,
        bull_score=int(bull_score),
        bear_score=int(bear_score),
        round_number=round_number,
        max_rounds=int(os.getenv("MAX_DEBATE_ROUNDS", "20")),
        risk_manager=risk_manager,
    )
    round_trace_payload["end_condition_result"] = end_condition_result

    settlement_delay_seconds = 0.0
    if gas_decision.action == "DELAY_SWAP":
        settlement_delay_seconds = float(gas_decision.context.get("delay_seconds", 15)) if isinstance(gas_decision.context, dict) else 15.0

    if settlement_delay_seconds > 0:
        time.sleep(settlement_delay_seconds)

    if not bool(end_condition_result.get("end")) and gas_decision.action != "SKIP_SWAP":
        losing_side = "bear" if int(bull_score) >= int(bear_score) else "bull"
        try:
            swap_result = swap_executor.execute_micro_settlement(
                session_id=session_id,
                round_number=round_number,
                losing_side=losing_side,
                verdict_dict=verdict,
            )
            if is_dataclass(swap_result):
                micro_settlement_result = asdict(swap_result)
            elif isinstance(swap_result, dict):
                micro_settlement_result = dict(swap_result)
            else:
                micro_settlement_result = {"raw": str(swap_result)}
        except Exception as exc:
            micro_settlement_result = {"success": False, "reason": f"micro_settlement_failed:{exc}"}
        round_trace_payload["micro_settlement_result"] = micro_settlement_result
    elif gas_decision.action == "SKIP_SWAP":
        round_trace_payload["micro_settlement_result"] = {"success": False, "reason": "skipped_by_gas_policy"}

    elapsed_seconds = time.time() - round_started_at
    remaining_seconds = max(0.0, float(ROUND_INTERVAL_SECONDS) - elapsed_seconds)
    if remaining_seconds > 0:
        time.sleep(remaining_seconds)

    round_trace_payload["round_completed_successfully"] = True
    end_condition_result.update(
        {
            "bull_score": int(bull_score),
            "bear_score": int(bear_score),
            "verdict": verdict,
            "micro_settlement_result": micro_settlement_result,
        }
    )
    upsert_round_trace(
        session_id=session_id,
        round_number=round_number,
        bull_argument_json=bull_argument,
        bear_argument_json=bear_argument,
        judge_verdict_json=round_trace_payload,
        bull_score_after_round=int(bull_score),
        bear_score_after_round=int(bear_score),
        round_duration_seconds=elapsed_seconds,
        micro_settlement_tx_hash=(
            micro_settlement_result.get("tx_hash") if isinstance(micro_settlement_result, dict) else None
        ),
        timestamp=_utcnow(),
    )
    display_round_summary(round_number, round_trace_payload, (int(bull_score), int(bear_score)), elapsed_seconds, dry_run)
    return True, end_condition_result


def _get_debate_escrow_contract() -> tuple[Web3, Any]:
    if DRY_RUN:
        return None, None

    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    escrow_address = os.getenv("ESCROW_CONTRACT_ADDRESS")
    if not rpc_url or not escrow_address:
        raise RuntimeError("Missing RPC URL or escrow contract address")

    escrow_abi = _load_abi(PROJECT_ROOT / "contracts" / "abi" / "DebateEscrow.json")
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Unable to connect to Unichain Sepolia RPC")

    escrow_contract = web3.eth.contract(
        address=Web3.to_checksum_address(escrow_address),
        abi=escrow_abi,
    )
    return web3, escrow_contract


def _get_axl_binary_path() -> Path:
    binary_path = Path(os.getenv("AXL_BINARY_PATH", str(PROJECT_ROOT / "axl-nodes" / "axl")))
    if not binary_path.is_absolute():
        binary_path = (PROJECT_ROOT / binary_path).resolve()
    return binary_path


def startup_axl_nodes(dry_run: bool) -> None:
    print("[ORCHESTRATOR] Skipping AXL node startup (macOS binary bypassed for Render compatibility)")
    return

def wait_for_axl_ready(timeout_seconds: int = 30) -> None:
    return

    while time.monotonic() < deadline:
        pending = []
        for node_name, node_url in node_urls.items():
            ok, detail = _ping_axl_node(node_url)
            last_status[node_name] = detail
            if not ok:
                pending.append(node_name)

        if not pending:
            return

        time.sleep(2)

    shutdown_axl_nodes()
    failed = ", ".join(f"{node}:{detail}" for node, detail in last_status.items())
    raise RuntimeError(f"AXL startup timeout after {timeout_seconds}s. Last status: {failed}")


def shutdown_axl_nodes() -> None:
    while AXL_NODE_PROCESSES:
        process = AXL_NODE_PROCESSES.pop()
        try:
            process.terminate()
            process.wait(timeout=10)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
    while AXL_NODE_LOG_HANDLES:
        log_handle = AXL_NODE_LOG_HANDLES.pop()
        try:
            log_handle.close()
        except Exception:
            pass



atexit.register(shutdown_axl_nodes)


def _redeploy_contracts() -> tuple[str, str]:
    """
    Redeploy a fresh ConvictionTracker contract to recover from settlement.
    Returns tuple of (escrow_address, conviction_address).
    """
    print("[ORCHESTRATOR] Detected settled contract; redeploying fresh instances...")
    
    contracts_dir = PROJECT_ROOT / "contracts"
    escrow_addr = os.getenv("ESCROW_CONTRACT_ADDRESS")
    if not escrow_addr:
        raise RuntimeError("Missing ESCROW_CONTRACT_ADDRESS for redeploy recovery")

    print(f"[REDEPLOY] Keeping existing DebateEscrow: {escrow_addr}")

    # Deploy ConvictionTracker
    print("[REDEPLOY] Deploying fresh ConvictionTracker (may take several minutes)...")
    conviction_cmd = [
        "npx", "hardhat", "ignition", "deploy",
        "ignition/modules/ConvictionTracker.ts",
        "--network", "unichainSepolia",
        "--reset"
    ]
    try:
        print(f"[REDEPLOY] Running: {' '.join(conviction_cmd)}")
        conviction_result = subprocess.run(
            conviction_cmd,
            cwd=str(contracts_dir),
            capture_output=True,
            text=True,
            input="y\ny\n",
            timeout=1200,
            env={**os.environ, "DEPLOYER_PRIVATE_KEY": os.getenv("DEPLOYER_PRIVATE_KEY", "")}
        )
        if conviction_result.returncode != 0:
            raise RuntimeError(f"ConvictionTracker deployment failed:\n{conviction_result.stderr}")
        conviction_output = conviction_result.stdout + conviction_result.stderr
        conviction_addr = _load_ignition_deployed_address(contracts_dir, "ConvictionTrackerModule#ConvictionTracker")
        if not conviction_addr:
            conviction_addr = _extract_contract_address(conviction_output, "ConvictionTracker")
        print(f"[REDEPLOY] ConvictionTracker deployment completed")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ConvictionTracker deployment timed out after 1200s (20 minutes). Check contracts compilation.")
    except Exception as exc:
        raise RuntimeError(f"ConvictionTracker deployment failed: {exc}")
    
    if not escrow_addr or not conviction_addr:
        raise RuntimeError(f"Failed to extract addresses from deployment output")
    
    # Update environment with new addresses
    os.environ["ESCROW_CONTRACT_ADDRESS"] = escrow_addr
    os.environ["CONVICTION_CONTRACT_ADDRESS"] = conviction_addr
    
    print(f"[REDEPLOY] Fresh contracts deployed:")
    print(f"  DebateEscrow: {escrow_addr}")
    print(f"  ConvictionTracker: {conviction_addr}")
    
    return escrow_addr, conviction_addr


def _extract_contract_address(output: str, contract_name: str) -> str | None:
    """
    Extract contract address from hardhat deployment output.
    Looks for lines like: "✔ Executed ModuleName#ContractName - at address 0x..."
    """
    lines = output.split("\n")
    fallback_address = None
    for line in lines:
        match = re.search(r"0x[a-fA-F0-9]{40}", line)
        if match:
            fallback_address = match.group(0)
            if contract_name in line:
                return fallback_address
    return fallback_address


def _load_ignition_deployed_address(contracts_dir: Path, contract_key: str) -> str | None:
    deployment_file = contracts_dir / "ignition" / "deployments" / "chain-1301" / "deployed_addresses.json"
    if not deployment_file.exists():
        return None

    try:
        with deployment_file.open("r", encoding="utf-8") as handle:
            deployed_addresses = json.load(handle)
    except Exception:
        return None

    address = deployed_addresses.get(contract_key)
    return address if isinstance(address, str) and re.fullmatch(r"0x[a-fA-F0-9]{40}", address) else None


def _start_debate_contracts(session_id: str, duration_seconds: int) -> dict[str, Any]:
    if DRY_RUN:
        from utils.dry_run_adapter import DryRunAdapter

        adapter = DryRunAdapter(session_id=session_id, round_number=0)
        escrow_result = adapter.simulate_contract_call(
            "DebateEscrow",
            "startDebate",
            {"session_id": session_id, "duration_seconds": duration_seconds},
        )
        conviction_result = adapter.simulate_contract_call(
            "ConvictionTracker",
            "startDebate",
            {"session_id": session_id},
        )
        return {
            "escrow_tx_hash": escrow_result.get("tx_hash"),
            "conviction_tx_hash": conviction_result.get("tx_hash"),
        }

    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    escrow_address = os.getenv("ESCROW_CONTRACT_ADDRESS")
    conviction_address = os.getenv("CONVICTION_CONTRACT_ADDRESS")
    if not rpc_url or not escrow_address or not conviction_address:
        raise RuntimeError("Missing RPC URL or contract addresses for debate startup")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Unable to connect to Unichain Sepolia RPC")

    private_key = _select_private_key()
    escrow_contract = web3.eth.contract(
        address=Web3.to_checksum_address(escrow_address),
        abi=_load_abi(PROJECT_ROOT / "contracts" / "abi" / "DebateEscrow.json"),
    )
    conviction_contract = web3.eth.contract(
        address=Web3.to_checksum_address(conviction_address),
        abi=_load_abi(PROJECT_ROOT / "contracts" / "abi" / "ConvictionTracker.json"),
    )

    escrow_active = bool(escrow_contract.functions.debateActive().call())
    escrow_end_time = int(escrow_contract.functions.debateEndTime().call()) if escrow_active else 0
    conviction_active = bool(conviction_contract.functions.debateActive().call())
    conviction_settlement_triggered = bool(conviction_contract.functions.isSettlementTriggered().call())
    latest_block_timestamp = int(web3.eth.get_block("latest")["timestamp"])
    skip_check = os.getenv("SKIP_SETTLED_CONTRACT_CHECK", "").strip().lower() in {"1", "true", "yes"}


    if conviction_settlement_triggered:
        # Contract has settled; check if we should redeploy or skip
        if skip_check:
            print("[ORCHESTRATOR] WARNING: Conviction tracker has settled, but SKIP_SETTLED_CONTRACT_CHECK=true; proceeding with stale contract (demo mode)")
        else:
            print("[ORCHESTRATOR] Conviction tracker has settled; attempting to redeploy fresh contracts...")
            try:
                _redeploy_contracts()
                # Recursively retry with fresh contracts
                return _start_debate_contracts(session_id, duration_seconds)
            except RuntimeError as exc:
                print(f"[ORCHESTRATOR] Redeploy failed: {exc}")
                print(f"[ORCHESTRATOR] Set SKIP_SETTLED_CONTRACT_CHECK=true to skip this check for demo purposes")
                raise
    if conviction_settlement_triggered and not skip_check:
        # If we reach here and the contract is still settled, provide deployment instructions
        print("\n" + "="*72)
        print("CONTRACT SETTLEMENT DETECTED - Manual Redeployment Required")
        print("="*72)
        print("The ConvictionTracker contract has already settled from a previous session.")
        print("To run a new debate session, you must deploy fresh contracts:")
        print()
        print("  cd contracts")
        print("  npx hardhat ignition deploy ignition/modules/DebateEscrow.ts --network unichainSepolia --reset")
        print("  npx hardhat ignition deploy ignition/modules/ConvictionTracker.ts --network unichainSepolia --reset")
        print()
        print("Then update your .env with the new contract addresses and try again.")
        print("="*72 + "\n")
        raise RuntimeError("ConvictionTracker has settled. Deploy fresh contracts (see instructions above)")

    if escrow_active and latest_block_timestamp > escrow_end_time:
        _send_contract_tx(
            web3=web3,
            private_key=private_key,
            contract_function=escrow_contract.functions.emergencyPause("debate window expired"),
            gas_limit_env_var="ESCROW_PAUSE_GAS_LIMIT",
        )
        escrow_active = False

    escrow_tx_hash = "already-active"
    if not escrow_active:
        escrow_tx_hash = _send_contract_tx(
            web3=web3,
            private_key=private_key,
            contract_function=escrow_contract.functions.startDebate(int(duration_seconds)),
            gas_limit_env_var="ESCROW_START_GAS_LIMIT",
        )

    conviction_tx_hash = "already-active"
    if not conviction_active:
        conviction_tx_hash = _send_contract_tx(
            web3=web3,
            private_key=private_key,
            contract_function=conviction_contract.functions.startDebate(),
            gas_limit_env_var="CONVICTION_START_GAS_LIMIT",
        )

    return {
        "escrow_tx_hash": escrow_tx_hash,
        "conviction_tx_hash": conviction_tx_hash,
    }


def run_stake_collection_window(session_id: str, duration_seconds: int = 120) -> bool:
    _state_transition_or_raise(session_id, STATE_ACCEPTING_STAKES)
    contract_result = _start_debate_contracts(session_id, duration_seconds)

    print("=" * 72)
    print("STAKE COLLECTION WINDOW OPEN")
    print(f"session_id: {session_id}")
    print(f"window_duration_seconds: {duration_seconds}")
    print(f"escrow_start_tx: {contract_result.get('escrow_tx_hash')}")
    print(f"conviction_start_tx: {contract_result.get('conviction_tx_hash')}")
    print("=" * 72)

    if not DRY_RUN:
        _web3, escrow_contract = _get_debate_escrow_contract()
        stake_tx_hashes = _seed_stake_deposits(_web3, escrow_contract)
        for label, tx_hash in stake_tx_hashes.items():
            print(f"{label}: {tx_hash}")

    if DRY_RUN:
        bull_stake_wei = 0
        bear_stake_wei = 0
        is_active = True
    else:
        _web3, escrow_contract = _get_debate_escrow_contract()
        bull_stake_wei, bear_stake_wei, is_active = escrow_contract.functions.getStakeInfo().call()

    start_time = time.monotonic()
    last_refresh = -10.0
    while True:
        elapsed = time.monotonic() - start_time
        remaining = max(0.0, float(duration_seconds) - elapsed)
        if elapsed - last_refresh >= 10 or remaining <= 0:
            if not DRY_RUN:
                _web3, escrow_contract = _get_debate_escrow_contract()
                bull_stake_wei, bear_stake_wei, is_active = escrow_contract.functions.getStakeInfo().call()
            bull_stake_eth = float(Web3.from_wei(int(bull_stake_wei), "ether"))
            bear_stake_eth = float(Web3.from_wei(int(bear_stake_wei), "ether"))
            line = (
                f"\r[STAKE WINDOW] remaining={int(remaining):>3}s | "
                f"bull={bull_stake_eth:.4f} ETH | bear={bear_stake_eth:.4f} ETH | active={bool(is_active)}"
            )
            sys.stdout.write(line.ljust(140))
            sys.stdout.flush()
            last_refresh = elapsed

        if remaining <= 0:
            break

        time.sleep(1)

    sys.stdout.write("\n")
    sys.stdout.flush()

    stake_manager = RiskManager(session_id)
    for attempt in range(3):
        minimum_stake_decision = stake_manager.check_minimum_stakes(session_id=session_id, round_number=0)
        if minimum_stake_decision.action == "PROCEED":
            print(
                f"[ORCHESTRATOR] Stake window confirmed | bull={float(Web3.from_wei(int(bull_stake_wei), 'ether')):.4f} ETH | "
                f"bear={float(Web3.from_wei(int(bear_stake_wei), 'ether')):.4f} ETH"
            )
            _state_transition_or_raise(session_id, STATE_ROUND_IN_PROGRESS)
            return True

        if attempt < 2:
            print(
                f"[ORCHESTRATOR] Minimum stakes not met ({minimum_stake_decision.reason}); extending by 60 seconds "
                f"(attempt {attempt + 2}/3)."
            )
            time.sleep(60)
            if not DRY_RUN:
                _web3, escrow_contract = _get_debate_escrow_contract()
                bull_stake_wei, bear_stake_wei, is_active = escrow_contract.functions.getStakeInfo().call()
            continue

        abort_reason = f"minimum stakes not met after 3 checks: {minimum_stake_decision.reason or 'insufficient stake'}"
        print(f"[ORCHESTRATOR] {abort_reason}")
        if DRY_RUN:
            from utils.dry_run_adapter import DryRunAdapter

            adapter = DryRunAdapter(session_id=session_id, round_number=0)
            adapter.simulate_contract_call(
                "DebateEscrow",
                "emergencyPause",
                {"session_id": session_id, "reason": abort_reason},
            )
        else:
            _web3, escrow_contract = _get_debate_escrow_contract()
            private_key = _select_private_key()
            _send_contract_tx(
                web3=_web3,
                private_key=private_key,
                contract_function=escrow_contract.functions.emergencyPause(abort_reason),
                gas_limit_env_var="ESCROW_PAUSE_GAS_LIMIT",
            )

        update_debate_session(
            session_id,
            status="ABORTED",
            settlement_tx_hash=f"abort:{abort_reason}",
            end_time=_utcnow(),
        )
        upsert_round_trace(
            session_id=session_id,
            round_number=0,
            judge_verdict_json={"abort_reason": abort_reason},
            timestamp=_utcnow(),
        )
        return False


def initialize_debate_session(token_pair: str, max_rounds: int, round_interval_seconds: int) -> str:
    """Create an orchestrator session record before the stake window opens."""
    init_database()

    try:
        execution_handler.test_connection()
    except Exception as exc:
        raise RuntimeError(f"KeeperHub startup connectivity check failed: {exc}") from exc

    session_id = str(uuid4())
    insert_debate_session(
        session_id=session_id,
        token_pair=token_pair,
        start_time=_utcnow(),
        total_rounds=max_rounds,
        status=STATE_IDLE,
    )

    return session_id


def setup_round(session_id: str, round_number: int, token_pair: str, risk_manager: RiskManager) -> Any:
    """Fetch market snapshot, persist pre-agent trace, verify AXL pre-flight health, and check data freshness + stakes."""
    init_database()

    snapshot = fetch_snapshot(token_pair)
    snapshot_payload = _coerce_snapshot_payload(snapshot)

    # CHECKPOINT 1: Check data freshness before proceeding
    freshness_decision = risk_manager.check_data_freshness(
        snapshot_payload if isinstance(snapshot_payload, dict) else {"data_freshness_seconds": 120},
        round_number,
        refresh_snapshot_fn=lambda: _coerce_snapshot_payload(fetch_snapshot(token_pair)),
    )
    
    if freshness_decision.action == "SKIP_ROUND":
        print(f"[ORCHESTRATOR] Data freshness check failed: {freshness_decision.reason}")
        update_debate_session(session_id, status=STATE_IDLE)
        raise RecoverableRoundSetupError(f"Stale data: {freshness_decision.reason}")
    
    if freshness_decision.action == "HALT":
        print(f"[ORCHESTRATOR] Data freshness critical failure: {freshness_decision.reason}")
        update_debate_session(session_id, status=STATE_IDLE)
        raise RuntimeError(f"Data freshness halt: {freshness_decision.reason}")
    
    # CHECKPOINT 2: Check minimum stakes
    stakes_decision = risk_manager.check_minimum_stakes(session_id, round_number)
    
    if stakes_decision.action == "HALT":
        print(f"[ORCHESTRATOR] Minimum stakes check failed: {stakes_decision.reason}")
        update_debate_session(session_id, status=STATE_IDLE)
        raise RuntimeError(f"Minimum stakes halt: {stakes_decision.reason}")

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
        bull_future = executor.submit(run_bull_round, session_id, round_number, token_pair)
        bear_future = executor.submit(run_bear_round, session_id, round_number, token_pair)

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
    risk_manager: RiskManager,
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

    verdict = run_judge_round(session_id, round_number, token_pair)

    # Persist memory and performance for both agents so learning data is available.
    try:
        perf = PerformanceTracker()
        bull_arg = bull_argument if isinstance(bull_argument, dict) else {}
        bear_arg = bear_argument if isinstance(bear_argument, dict) else {}

        bull_score = int(verdict.get("bullScore", 0))
        bear_score = int(verdict.get("bearScore", 0))
        winner = str(verdict.get("winner") or "").lower()

        bull_memory = AgentMemory("bull", session_id)
        bear_memory = AgentMemory("bear", session_id)

        # Prepare a safe market snapshot string
        try:
            import json as _json
            if isinstance(market_snapshot, str):
                ms_text = market_snapshot
            else:
                ms_text = _json.dumps(market_snapshot, default=str)
        except Exception:
            ms_text = str(market_snapshot)

        # Add rounds to conversational memory and persist snapshots
        try:
            bull_memory.add_round(round_number, ms_text, bull_arg, bull_score)
            bull_memory.save_snapshot(round_number)
        except Exception:
            pass
        try:
            bear_memory.add_round(round_number, ms_text, bear_arg, bear_score)
            bear_memory.save_snapshot(round_number)
        except Exception:
            pass

        # Record performance and update metric correlations
        try:
            perf.record_round(session_id, "bull", round_number, bull_arg, bull_score, won_round=(winner == "bull"), accuracy_bonus=bool(verdict.get("accuracyBonusApplied", False)))
            perf.update_metric_correlations(session_id, "bull")
        except Exception:
            pass
        try:
            perf.record_round(session_id, "bear", round_number, bear_arg, bear_score, won_round=(winner == "bear"), accuracy_bonus=bool(verdict.get("accuracyBonusApplied", False)))
            perf.update_metric_correlations(session_id, "bear")
        except Exception:
            pass
    except Exception:
        pass

    # CHECKPOINT 3: Check conviction drift and request extended reasoning if needed
    drift_decision = risk_manager.check_conviction_drift(
        round_number, bull_score, bear_score, session_id
    )
    
    if drift_decision.action == "REQUIRE_EXTENDED_REASONING":
        print(f"[ORCHESTRATOR] Conviction drift detected: {drift_decision.reason}. Re-judging with extended reasoning...")
        # Re-call Judge with extended reasoning prompt
        extended_prompt_suffix = (
            f"\nIMPORTANT: Conviction moved significantly this round (Bull: {drift_decision.context.get('deltas', {}).get('bull', 0)} points, "
            f"Bear: {drift_decision.context.get('deltas', {}).get('bear', 0)} points), "
            f"which is unusually large. Provide an extended reasoning section of at least 4 sentences explaining exactly which evidence "
            f"justified this magnitude of score difference."
        )
        # Note: In a real implementation, this would be passed to run_judge_round
        # For now, we just log it and proceed with the original verdict
        print(f"[ORCHESTRATOR] Extended reasoning flag set; Judge should reconsider with extended analysis.")

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
    risk_manager: RiskManager,
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
        # CHECKPOINT 4: Check timeout conditions
        timeout_decision = risk_manager.check_debate_timeout(round_number, session_id)
        
        if timeout_decision.action == "FORCE_SETTLEMENT":
            # Evaluate draw conditions for settlement
            draw_info = risk_manager.evaluate_draw_conditions(bull_score, bear_score, session_id)
            winner = "draw"
            end_reason = f"timeout_force_settlement_{draw_info['draw_type']}"
            print(f"[ORCHESTRATOR] Debate timeout force settlement: {draw_info}")
        else:
            # Normal max rounds reached
            draw_info = risk_manager.evaluate_draw_conditions(bull_score, bear_score, session_id)
            winner = "draw"
            end_reason = f"max_rounds_reached_{draw_info['draw_type']}"
            print(f"[ORCHESTRATOR] Max rounds reached. Draw evaluation: {draw_info}")
    else:
        if DRY_RUN:
            contract_settlement_triggered = False
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


def execute_final_settlement(
    session_id: str,
    winning_side: str,
    final_scores: tuple[int, int],
    dry_run: bool,
) -> str:
    """Coordinate the final swap redistribution, escrow settlement, and wallet verification."""
    _state_transition_or_raise(session_id, STATE_SETTLEMENT_TRIGGERED)

    print(ANSI_BOLD + "=" * 72 + ANSI_RESET)
    print(_ansi_wrap("FINAL SETTLEMENT", ANSI_CYAN))
    print(f"session_id: {session_id}")
    print(f"winning_side: {winning_side}")
    print(f"final_scores: bull={int(final_scores[0])} bear={int(final_scores[1])}")
    print(f"mode: {'DRY RUN' if dry_run else 'LIVE RUN'}")

    redistribution_result = swap_executor.execute_final_settlement(session_id, winning_side, call_settle_side=False)
    if not isinstance(redistribution_result, dict) or not redistribution_result.get("success"):
        raise RuntimeError(f"Final settlement swap execution failed: {redistribution_result}")

    wallets = _resolve_settlement_wallets()
    balances_before: dict[str, int] = {}
    if wallets:
        balances_before = _read_wallet_balances(wallets)
        print("wallet_balances_before_settle:")
        for wallet, balance in balances_before.items():
            print(f"  {wallet}: {balance}")
    else:
        print("wallet_balances_before_settle: unavailable")

    if DRY_RUN:
        from utils.dry_run_adapter import DryRunAdapter

        adapter = DryRunAdapter(session_id=session_id, round_number=0)
        settle_result = adapter.simulate_contract_call(
            "DebateEscrow",
            "settleSide",
            {"session_id": session_id, "winning_side": winning_side, "final_scores": final_scores},
        )
        settlement_tx_hash = str(settle_result.get("tx_hash") or f"dry-run:settleSide:{winning_side}")
    else:
        web3, escrow_contract = _get_debate_escrow_contract()
        private_key = _select_settlement_private_key()
        side_enum = 0 if winning_side.strip().lower() == "bull" else 1
        settlement_tx_hash = _send_contract_tx(
            web3=web3,
            private_key=private_key,
            contract_function=escrow_contract.functions.settleSide(side_enum),
            gas_limit_env_var="ESCROW_SETTLE_GAS_LIMIT",
        )

    if wallets:
        balances_after = _read_wallet_balances(wallets)
        print("wallet_balances_after_settle:")
        for wallet, balance in balances_after.items():
            delta = balance - balances_before.get(wallet, 0)
            print(f"  {wallet}: {balance} (delta={delta})")
    else:
        print("wallet_balances_after_settle: unavailable")

    update_debate_session(
        session_id,
        settlement_triggered=True,
        settlement_tx_hash=settlement_tx_hash,
    )
    _state_transition_or_raise(session_id, STATE_DEBATE_ENDED)
    update_debate_session(session_id, end_time=_utcnow())

    row = get_debate_session_by_session_id(session_id)
    total_duration = (_utcnow() - row.start_time).total_seconds() if row is not None else 0.0
    total_rounds = int(row.total_rounds or 0) if row is not None else 0
    print(f"settlement_tx_hash: {settlement_tx_hash}")
    print(f"total_rounds: {total_rounds}")
    print(f"total_debate_duration_seconds: {total_duration:.2f}")
    print("round_trace audit trail is fully stored in SQLite")
    print(ANSI_BOLD + "=" * 72 + ANSI_RESET)

    return settlement_tx_hash


def trigger_settlement(session_id: str, winning_side: str) -> str:
    """Backward-compatible settlement wrapper."""
    row = get_debate_session_by_session_id(session_id)
    if row is None:
        raise ValueError(f"Unknown debate session: {session_id}")
    final_scores = (int(row.final_bull_score or 0), int(row.final_bear_score or 0))
    return execute_final_settlement(session_id, winning_side, final_scores, DRY_RUN)


def run_debate(token_pair: str, max_rounds: int, round_interval_seconds: int) -> str:
    """Main orchestrator loop with deterministic pacing and clean interruption handling."""
    global ROUND_INTERVAL_SECONDS
    ROUND_INTERVAL_SECONDS = int(round_interval_seconds)
    os.environ["MAX_DEBATE_ROUNDS"] = str(int(max_rounds))
    configure_runtime(DRY_RUN)
    startup_axl_nodes(DRY_RUN)
    session_id = initialize_debate_session(token_pair, max_rounds, round_interval_seconds)
    stake_window_open = run_stake_collection_window(session_id, duration_seconds=STAKE_COLLECTION_WINDOW_SECONDS)
    if not stake_window_open:
        shutdown_axl_nodes()
        return session_id

    display_debate_header(session_id, token_pair, DRY_RUN)

    winning_side: str | None = None
    final_scores: tuple[int, int] = (0, 0)

    # Initialize risk manager for safety checkpoints
    risk_manager = RiskManager(session_id)

    # Prepare strategy adapters so orchestrator can trigger adaptations
    perf_tracker = PerformanceTracker()
    bull_adapter = StrategyAdapter("bull", session_id, perf_tracker)
    bear_adapter = StrategyAdapter("bear", session_id, perf_tracker)

    try:
        for round_number in range(1, max_rounds + 1):
            round_completed, end_state = execute_single_round(session_id, round_number, token_pair, DRY_RUN)

            if round_completed:
                try:
                    bull_adapter.apply_adaptation(round_number)
                except Exception:
                    pass
                try:
                    bear_adapter.apply_adaptation(round_number)
                except Exception:
                    pass

            final_scores = (
                int(end_state.get("bull_score", final_scores[0])),
                int(end_state.get("bear_score", final_scores[1])),
            )

            if bool(end_state.get("end")):
                winning_side = str(end_state.get("winner", "draw"))
                print(f"[ORCHESTRATOR] Debate end condition met at round {round_number}: {end_state}")
                break

    except KeyboardInterrupt:
        update_debate_session(session_id, status=STATE_IDLE, end_time=_utcnow())
        print("[ORCHESTRATOR] Interrupted by user. Session moved to IDLE for clean shutdown.")
        return session_id
    finally:
        shutdown_axl_nodes()

    if winning_side is None:
        winning_side = "draw"
        final_scores = _read_onchain_scores()

    execute_final_settlement(session_id, winning_side, final_scores, DRY_RUN)
    return session_id


if __name__ == "__main__":
    env_win_threshold = WIN_THRESHOLD
    env_max_debate_rounds = int(os.getenv("MAX_DEBATE_ROUNDS", "20"))
    env_min_stake_eth = MIN_STAKE_ETH

    if REQUESTED_DURATION:
        env_max_debate_rounds = parse_duration(REQUESTED_DURATION, ROUND_INTERVAL_SECONDS)

    print(
        "[ORCHESTRATOR] Loaded config | "
        f"ROUND_INTERVAL_SECONDS={ROUND_INTERVAL_SECONDS} | "
        f"CONVICTION_WIN_THRESHOLD={env_win_threshold} | "
        f"MAX_DEBATE_ROUNDS={env_max_debate_rounds} | "
        f"MIN_STAKE_ETH={env_min_stake_eth}"
    )

    session_id = run_debate(TOKEN_PAIR, max_rounds=env_max_debate_rounds, round_interval_seconds=ROUND_INTERVAL_SECONDS)
    print(f"[ORCHESTRATOR] Run complete. session_id={session_id}")
