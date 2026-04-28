from __future__ import annotations

from dataclasses import asdict
import json
import os
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, ValidationError, conint, field_validator
from sqlalchemy import desc, select
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db.schema import AccuracyTracking, BullRound, JudgeVerdict
from utils.db_manager import (
    get_session,
    init_database,
    insert_judge_verdict,
    upsert_accuracy_tracking,
    upsert_round_comparison_from_judge,
)
from utils.market_data import MarketSnapshot, fetch_snapshot
from utils.db.schema import ArgumentPerformance
from utils.risk_manager import RiskManager
import statistics

# Judge architecture map (must be explicit before implementation):
# 1) Bidirectional messaging role:
#    - Inbound: receives two AXL messages each round (one from Bull, one from Bear).
#    - Outbound: sends verdict payloads to two AXL destinations each round (Bull + Bear).
# 2) Stateful round synchronization:
#    - Maintains a per-round inbox buffer while polling.
#    - Holds first-arriving argument until counterpart arrives or timeout occurs.
# 3) Historical memory for incentives:
#    - Reads prior round verdict winner from SQLite.
#    - Computes realized market direction from stored prior round price vs current snapshot.
#    - Awards one-time accuracy bonus and records audit trail to prevent double counting.
# 4) Persistent auditability:
#    - Writes full verdict artifacts to judge_verdicts.
#    - Writes prediction-outcome checks to accuracy_tracking.
# 5) External side effects per round:
#    - Publishes verdict results to both agents via AXL.
#    - Updates ConvictionTracker onchain and records success/failed status.

JUDGE_SYSTEM_PROMPT = (
    "You are the Judge agent for a Bull-vs-Bear onchain debate. You must score both arguments "
    "consistently and produce calibrated numeric scores. Use ONLY the provided market data and arguments. "
    "Score each side from 0 to 100 as the sum of five criteria worth 0-20 each.\n\n"
    "Criterion 1 - Evidence Quality (0-20):\n"
    "- Full points (20): argument cites at least two specific numerical values from provided market data.\n"
    "- Zero points (0): argument is qualitative only and cites no concrete numbers.\n\n"
    "Criterion 2 - Logical Consistency (0-20):\n"
    "- Full points (20): conclusion follows directly from cited evidence without contradictions.\n"
    "- Zero points (0): argument contradicts itself or conclusion is unsupported by cited evidence.\n\n"
    "Criterion 3 - Metric Accuracy (0-20):\n"
    "- Full points (20): cited values match provided market data exactly or with reasonable rounding.\n"
    "- Zero points (0): values are fabricated, misquoted, or materially misrepresented.\n\n"
    "Criterion 4 - Predictive Value (0-20):\n"
    "- Full points (20): argument makes a specific falsifiable near-term direction prediction.\n"
    "- Zero points (0): directional claim is vague, non-falsifiable, or absent.\n\n"
    "Criterion 5 - Argument Clarity (0-20):\n"
    "- Full points (20): writing is readable and causality chain is explicit.\n"
    "- Zero points (0): prose is confused, circular, or self-referential.\n\n"
    "Accuracy bonus rule: before finalizing round scores, one side may receive a +10 bonus if that side won "
    "the previous round and the realized market movement since the previous round proved that prediction correct "
    "(Bull correct if price moved up, Bear correct if price moved down). Bonus can be awarded only once per prior round."
)

CRITERIA_KEYS = [
    "Evidence Quality",
    "Logical Consistency",
    "Metric Accuracy",
    "Predictive Value",
    "Argument Clarity",
]


class JudgeVerdictOutput(BaseModel):
    winner: str = Field(description='Winning side, exactly "bull" or "bear"')
    roundNumber: int = Field(description="Round number for this verdict")
    bullScore: conint(ge=0, le=100) = Field(description="Bull final score from 0 to 100")
    bearScore: conint(ge=0, le=100) = Field(description="Bear final score from 0 to 100")
    bullCriteriaBreakdown: dict[str, conint(ge=0, le=20)] = Field(
        description="Per-criterion score map for Bull"
    )
    bearCriteriaBreakdown: dict[str, conint(ge=0, le=20)] = Field(
        description="Per-criterion score map for Bear"
    )
    reasoning: str = Field(description="Two to three sentence verdict rationale")
    accuracyBonusApplied: bool = Field(description="Whether this round applied an accuracy bonus")

    @field_validator("winner")
    @classmethod
    def validate_winner(cls, value: str) -> str:
        lowered = value.strip().lower()
        if lowered not in {"bull", "bear"}:
            raise ValueError('winner must be exactly "bull" or "bear"')
        return lowered

    @field_validator("bullCriteriaBreakdown", "bearCriteriaBreakdown")
    @classmethod
    def validate_breakdown(cls, value: dict[str, int]) -> dict[str, int]:
        if set(value.keys()) != set(CRITERIA_KEYS):
            raise ValueError(f"criteria keys must be exactly: {CRITERIA_KEYS}")
        return value

JUDGE_AXL_HTTP_URL = os.getenv("JUDGE_AXL_HTTP_URL", "http://localhost:8003").rstrip("/")
JUDGE_AXL_INBOX_PATH = os.getenv("JUDGE_AXL_INBOX_PATH", "/recv")
AXL_INBOX_URL = f"{JUDGE_AXL_HTTP_URL}{JUDGE_AXL_INBOX_PATH}"
BULL_AXL_PEER_ID = os.getenv(
    "BULL_AXL_PEER_ID",
    "520cda07fce54eb2f43a1a016aea85553e2ef7d0e32bcce91e2a58bd79f876ae",
)
BEAR_AXL_PEER_ID = os.getenv(
    "BEAR_AXL_PEER_ID",
    "5e6b45ce2a4eeb5bf861815f91152c7f8d56178a335fa3db046048b882d48de0",
)
JUDGE_AXL_SEND_URL = f"{JUDGE_AXL_HTTP_URL}/send"

load_dotenv()
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


_init_parser = JsonOutputParser(pydantic_object=JudgeVerdictOutput)
JUDGE_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", JUDGE_SYSTEM_PROMPT),
        (
            "human",
            "Bull argument:\n{bull_argument}\n\n"
            "Bear argument:\n{bear_argument}\n\n"
            "Market data:\n{market_data}\n\n"
            "Return JSON only using this schema:\n{format_instructions}",
        ),
    ]
)

JUDGE_LLM = ChatGroq(model="llama3-70b-8192", temperature=0.1)
JUDGE_PARSER = JsonOutputParser(pydantic_object=JudgeVerdictOutput)
JUDGE_CHAIN: Runnable[dict[str, Any], dict[str, Any]] = JUDGE_PROMPT_TEMPLATE | JUDGE_LLM | JUDGE_PARSER

_fallback_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
JUDGE_FALLBACK_CHAIN: Runnable[dict[str, Any], dict[str, Any]] | None = None
if _fallback_model != "llama3-70b-8192":
    JUDGE_FALLBACK_CHAIN = (
        JUDGE_PROMPT_TEMPLATE
        | ChatGroq(model=_fallback_model, temperature=0.1)
        | JUDGE_PARSER
    )


def _extract_round(message: Mapping[str, Any]) -> int | None:
    payload = message.get("payload")
    if isinstance(payload, Mapping) and payload.get("round") is not None:
        try:
            return int(payload.get("round"))
        except (TypeError, ValueError):
            return None

    if message.get("round") is not None:
        try:
            return int(message.get("round"))
        except (TypeError, ValueError):
            return None

    return None


def _extract_sender(message: Mapping[str, Any]) -> str | None:
    payload = message.get("payload")
    if isinstance(payload, Mapping) and isinstance(payload.get("sender"), str):
        return payload.get("sender", "").strip().lower()

    sender = message.get("sender")
    if isinstance(sender, str):
        return sender.strip().lower()

    return None


def _normalize_message(message: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize raw AXL message shape into {sender, round, argument, payload} when possible."""
    payload = message.get("payload")
    if isinstance(payload, str):
        try:
            decoded = json.loads(payload)
            if isinstance(decoded, dict):
                payload = decoded
        except (json.JSONDecodeError, TypeError, ValueError):
            payload = {"raw": payload}

    if isinstance(payload, Mapping):
        merged = dict(message)
        merged["payload"] = dict(payload)
        if "sender" not in merged and payload.get("sender") is not None:
            merged["sender"] = payload.get("sender")
        if "round" not in merged and payload.get("round") is not None:
            merged["round"] = payload.get("round")
        if "argument" not in merged and payload.get("argument") is not None:
            merged["argument"] = payload.get("argument")
        return merged

    if isinstance(message.get("sender"), str) or message.get("round") is not None:
        return dict(message)

    return {"payload": payload}


def poll_inbox() -> list[dict[str, Any]]:
    """Poll Judge AXL inbox and return a normalized list of inbound messages."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(AXL_INBOX_URL)
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return []

    if isinstance(body, list):
        return [_normalize_message(item) for item in body if isinstance(item, dict)]

    if isinstance(body, dict):
        for key in ("messages", "inbox", "queued", "items", "message"):
            value = body.get(key)
            if isinstance(value, list):
                return [_normalize_message(item) for item in value if isinstance(item, dict)]
            if isinstance(value, dict):
                return [_normalize_message(value)]

        if "sender" in body or "payload" in body or "round" in body:
            return [_normalize_message(body)]

    return []


def wait_for_both_arguments(round_number: int, timeout_seconds: int = 120) -> tuple[dict[str, dict[str, Any] | None], bool]:
    """
    Wait for round-matched Bull and Bear inbox messages.

    Returns ({"bull": <msg|None>, "bear": <msg|None>}, timed_out).
    """
    if DRY_RUN:
        synthetic_bull = {
            "sender": "bull",
            "sender_peer_id": BULL_AXL_PEER_ID,
            "round": round_number,
            "argument": {
                "argument": f"Round {round_number}: dry-run bullish argument generated locally.",
                "confidence": 55,
                "keyMetrics": ["dry_run=true", f"round={round_number}"],
            },
            "message_hash": f"dry-run-bull-{round_number}",
            "signature": f"dry-run-signature-bull-{round_number}",
        }
        synthetic_bear = {
            "sender": "bear",
            "sender_peer_id": BEAR_AXL_PEER_ID,
            "round": round_number,
            "argument": {
                "argument": f"Round {round_number}: dry-run bearish argument generated locally.",
                "confidence": 55,
                "keyMetrics": ["dry_run=true", f"round={round_number}"],
            },
            "message_hash": f"dry-run-bear-{round_number}",
            "signature": f"dry-run-signature-bear-{round_number}",
        }
        return {"bull": synthetic_bull, "bear": synthetic_bear}, False

    started_at = time.monotonic()
    bucket: dict[str, dict[str, Any] | None] = {"bull": None, "bear": None}

    while (time.monotonic() - started_at) < timeout_seconds:
        for message in poll_inbox():
            msg_round = _extract_round(message)
            if msg_round != round_number:
                continue

            sender = _extract_sender(message)
            if sender not in ("bull", "bear"):
                continue

            if bucket[sender] is None:
                bucket[sender] = message

        if bucket["bull"] is not None and bucket["bear"] is not None:
            return bucket, False

        time.sleep(2)

    return bucket, True


def _extract_previous_round_price(previous_bull_round: BullRound) -> float | None:
    # Prefer structured raw market payload, then fall back to key-metric parsing.
    try:
        raw = json.loads(previous_bull_round.raw_market_data)
        if isinstance(raw, Mapping):
            price_source = raw.get("price_source", {})
            if isinstance(price_source, Mapping):
                for key in ("computed_quote_per_base", "current_price", "price"):
                    candidate = price_source.get(key)
                    if candidate is not None:
                        return float(candidate)
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    try:
        metrics = json.loads(previous_bull_round.key_metrics)
        if isinstance(metrics, list):
            for metric in metrics:
                metric_str = str(metric)
                match = re.search(r"current\s+price\s*:\s*([-+]?\d*\.?\d+)", metric_str, flags=re.IGNORECASE)
                if match:
                    return float(match.group(1))
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    return None


def calculate_accuracy_bonus(round_number: int, market_snapshot: MarketSnapshot) -> dict[str, str | int | None]:
    """
    Evaluate prior round prediction correctness and award one-time accuracy bonus.

    Returns: {"recipient": "bull"|"bear"|None, "bonus": int}
    """
    init_database()

    with get_session() as session:
        latest_verdict_stmt = (
            select(JudgeVerdict)
            .where(JudgeVerdict.round_number < round_number)
            .order_by(desc(JudgeVerdict.round_number), desc(JudgeVerdict.timestamp))
            .limit(1)
        )
        latest_verdict = session.scalar(latest_verdict_stmt)
        if latest_verdict is None:
            return {"recipient": None, "bonus": 0}

        evaluated_stmt = select(AccuracyTracking).where(AccuracyTracking.round_number == latest_verdict.round_number)
        existing_eval = session.scalar(evaluated_stmt)
        if existing_eval is not None:
            return {"recipient": None, "bonus": 0}

        previous_bull_stmt = (
            select(BullRound)
            .where(BullRound.round_number == latest_verdict.round_number)
            .order_by(desc(BullRound.timestamp))
            .limit(1)
        )
        previous_bull_round = session.scalar(previous_bull_stmt)
        if previous_bull_round is None:
            return {"recipient": None, "bonus": 0}

        previous_round_price = _extract_previous_round_price(previous_bull_round)
        if previous_round_price is None:
            return {"recipient": None, "bonus": 0}

        actual_direction = "up" if float(market_snapshot.current_price) > float(previous_round_price) else "down"
        predicted_winner = str(latest_verdict.winner).strip().lower()
        prediction_correct = (
            (actual_direction == "up" and predicted_winner == "bull")
            or (actual_direction == "down" and predicted_winner == "bear")
        )

        upsert_accuracy_tracking(
            round_number=int(latest_verdict.round_number),
            predicted_winner=predicted_winner,
            actual_price_direction=actual_direction,
            prediction_correct=prediction_correct,
            bonus_awarded=prediction_correct,
        )

        if prediction_correct:
            return {"recipient": predicted_winner, "bonus": 10}

        return {"recipient": None, "bonus": 0}


def build_judge_outbound_payload(
    *,
    round_number: int,
    bull_score: int,
    bear_score: int,
    winner: str,
    reasoning: str,
    accuracy_bonus: dict[str, str | int | None],
) -> dict[str, Any]:
    """Create a shared verdict payload that can be sent to both Bull and Bear destinations."""
    return {
        "sender": "judge",
        "round": round_number,
        "bullScore": bull_score,
        "bearScore": bear_score,
        "winner": winner,
        "reasoning": reasoning,
        "accuracyBonus": accuracy_bonus,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _market_snapshot_to_text(snapshot: MarketSnapshot) -> str:
    try:
        return json.dumps(asdict(snapshot), default=str)
    except TypeError:
        return snapshot.to_prompt_payload()


def _extract_argument_from_message(message: dict[str, Any] | None, side: str) -> tuple[dict[str, Any], bool]:
    if not message:
        return (
            {
                "argument": f"No {side} argument received before timeout. Neutral placeholder used.",
                "confidence": 50,
                "keyMetrics": ["timeout fallback"],
            },
            True,
        )

    payload = message.get("payload")
    if isinstance(payload, Mapping):
        argument = payload.get("argument")
    else:
        argument = message.get("argument")

    if isinstance(argument, Mapping):
        normalized = {
            "argument": str(argument.get("argument", "")).strip(),
            "confidence": int(argument.get("confidence", 50)),
            "keyMetrics": argument.get("keyMetrics", []),
        }
        return normalized, False

    return (
        {
            "argument": f"Malformed {side} argument payload received. Neutral placeholder used.",
            "confidence": 50,
            "keyMetrics": ["malformed payload fallback"],
        },
        True,
    )


def score_round(
    bull_argument_dict: dict[str, Any],
    bear_argument_dict: dict[str, Any],
    round_number: int,
    market_snapshot: MarketSnapshot,
) -> dict[str, Any]:
    """Score one debate round, apply accuracy bonus, and return normalized verdict dict."""
    accuracy_bonus_result = calculate_accuracy_bonus(round_number, market_snapshot)
    # Add brief historical performance context (averages over last 3 rounds) but instruct the Judge not to bias.
    session_id = os.getenv("DEBATE_SESSION_ID", "default-session")
    def _avg_score_for(side: str) -> float | None:
        with get_session() as session:
            rows = (
                session.query(ArgumentPerformance)
                .filter(ArgumentPerformance.session_id == session_id)
                .filter(ArgumentPerformance.agent == side)
                .order_by(ArgumentPerformance.round_number.desc())
                .limit(3)
                .all()
            )
            scores = [float(r.judge_score_received) for r in rows if r.judge_score_received is not None]
            if not scores:
                return None
            return float(statistics.mean(scores))

    bull_avg = _avg_score_for("bull")
    bear_avg = _avg_score_for("bear")

    context_note = (
        f"Context: Bull's average score over last 3 rounds was {bull_avg if bull_avg is not None else 'N/A'}. "
        f"Bear's average score was {bear_avg if bear_avg is not None else 'N/A'}. "
        "Do not let historical performance bias your scoring of this round's arguments — score only on the quality of evidence presented this round."
    )

    invoke_payload = {
        "bull_argument": json.dumps(bull_argument_dict, default=str),
        "bear_argument": json.dumps(bear_argument_dict, default=str),
        "market_data": f"{context_note}\n\n{_market_snapshot_to_text(market_snapshot)}",
        "format_instructions": _init_parser.get_format_instructions(),
    }

    try:
        try:
            response = JUDGE_CHAIN.invoke(invoke_payload)
        except Exception:
            if JUDGE_FALLBACK_CHAIN is None:
                raise
            response = JUDGE_FALLBACK_CHAIN.invoke(invoke_payload)

        validated = JudgeVerdictOutput.model_validate(response)
        verdict = validated.model_dump()
        verdict["roundNumber"] = round_number

        recipient = str(accuracy_bonus_result.get("recipient") or "").lower()
        bonus_points = int(accuracy_bonus_result.get("bonus") or 0)
        if recipient == "bull" and bonus_points > 0:
            verdict["bullScore"] = min(100, int(verdict["bullScore"]) + bonus_points)
            verdict["accuracyBonusApplied"] = True
        elif recipient == "bear" and bonus_points > 0:
            verdict["bearScore"] = min(100, int(verdict["bearScore"]) + bonus_points)
            verdict["accuracyBonusApplied"] = True
        else:
            verdict["accuracyBonusApplied"] = False

        if int(verdict["bullScore"]) > int(verdict["bearScore"]):
            verdict["winner"] = "bull"
        elif int(verdict["bearScore"]) > int(verdict["bullScore"]):
            verdict["winner"] = "bear"
        else:
            verdict["winner"] = validated.winner

        verdict["accuracyBonusRecipient"] = recipient if recipient in {"bull", "bear"} else None
        verdict["accuracyBonusPoints"] = bonus_points if recipient in {"bull", "bear"} else 0
        return verdict
    except (OutputParserException, ValidationError, ValueError, TypeError, httpx.HTTPError, Exception):
        return {
            "winner": None,
            "roundNumber": round_number,
            "bullScore": 50,
            "bearScore": 50,
            "bullCriteriaBreakdown": {key: 10 for key in CRITERIA_KEYS},
            "bearCriteriaBreakdown": {key: 10 for key in CRITERIA_KEYS},
            "reasoning": "Scoring failed this round — scores held neutral",
            "accuracyBonusApplied": False,
            "accuracyBonusRecipient": None,
            "accuracyBonusPoints": 0,
        }


def _post_verdict_to_destination(verdict_dict: dict[str, Any], destination_peer_id: str, recipient: str, round_number: int) -> bool:
    payload = {
        **verdict_dict,
        "sender": "judge",
        "recipient": recipient,
        "round": round_number,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    try:
        with httpx.Client(timeout=6.0) as client:
            response = client.post(
                JUDGE_AXL_SEND_URL,
                json=payload,
                headers={"X-Destination-Peer-Id": destination_peer_id},
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def _update_conviction_onchain(verdict_dict: dict[str, Any], round_number: int, session_id: str) -> tuple[bool, str]:
    if DRY_RUN:
        from utils.dry_run_adapter import DryRunAdapter

        adapter = DryRunAdapter(session_id=session_id, round_number=round_number)
        result = adapter.simulate_contract_call(
            "ConvictionTracker",
            "updateConviction",
            {"session_id": session_id, "round_number": round_number, "verdict": verdict_dict},
        )
        return bool(result.get("success")), str(result.get("tx_hash") or "simulated-tx-hash")

    rpc_url = os.getenv("ALCHEMY_RPC_URL") or os.getenv("MARKET_DATA_RPC_URL")
    contract_address = os.getenv("CONVICTION_CONTRACT_ADDRESS")
    key_candidates = [
        os.getenv("JUDGE_AGENT_PRIVATE_KEY"),
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

    if not rpc_url or not contract_address or not private_key:
        return False, "failed:missing onchain config"

    abi_path = PROJECT_ROOT / "contracts" / "abi" / "ConvictionTracker.json"
    try:
        with abi_path.open("r", encoding="utf-8") as handle:
            raw_abi = json.load(handle)
    except Exception as exc:  # noqa: BLE001
        return False, f"failed:abi load error ({type(exc).__name__})"

    abi = raw_abi.get("abi", raw_abi) if isinstance(raw_abi, dict) else raw_abi
    if not isinstance(abi, list):
        return False, "failed:invalid abi"

    try:
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not web3.is_connected():
            return False, "failed:rpc unavailable"

        chain_id = int(web3.eth.chain_id)
        if os.getenv("BLOCK_REAL_MONEY_TRANSACTIONS", "1") == "1":
            allowed_raw = os.getenv("TX_ALLOWED_CHAIN_IDS", "1301,11155111,84532,421614")
            allowed_ids = {int(item.strip()) for item in allowed_raw.split(",") if item.strip()}
            if chain_id not in allowed_ids:
                return False, f"failed:safety blocked chain_id={chain_id}"

        account = web3.eth.account.from_key(private_key)
        contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
        nonce = web3.eth.get_transaction_count(account.address)
        tx = contract.functions.updateConviction(
            int(verdict_dict.get("bullScore", 50)),
            int(verdict_dict.get("bearScore", 50)),
            int(round_number),
        ).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": chain_id,
                "gas": int(os.getenv("CONVICTION_UPDATE_GAS_LIMIT", "350000")),
                "gasPrice": int(web3.eth.gas_price),
            }
        )
        signed = web3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        hash_hex = tx_hash.hex()
        if int(receipt.status) == 1:
            return True, hash_hex
        return False, f"failed:tx reverted ({hash_hex})"
    except Exception as exc:  # noqa: BLE001
        return False, f"failed:{type(exc).__name__}"


def publish_verdict(verdict_dict: dict[str, Any], round_number: int, session_id: str) -> dict[str, Any]:
    """Publish verdict to both agents, then attempt ConvictionTracker update onchain."""
    bull_sent = _post_verdict_to_destination(verdict_dict, BULL_AXL_PEER_ID, "bull", round_number)
    bear_sent = _post_verdict_to_destination(verdict_dict, BEAR_AXL_PEER_ID, "bear", round_number)
    onchain_ok, tx_or_status = _update_conviction_onchain(verdict_dict, round_number, session_id)

    return {
        "bull_publish_status": "sent" if bull_sent else "failed",
        "bear_publish_status": "sent" if bear_sent else "failed",
        "conviction_update_status": tx_or_status if onchain_ok else "failed",
        "conviction_tx_hash": tx_or_status if onchain_ok else None,
        "conviction_update_error": None if onchain_ok else tx_or_status,
    }


def run_judge_round(session_id: str, round_number: int, token_pair: str) -> dict[str, Any]:
    """Execute one full Judge cycle: wait, score, publish, persist, and summarize."""
    init_database()
    risk_manager = RiskManager(session_id)

    message_bucket, timed_out = wait_for_both_arguments(round_number)

    for expected_sender in ("bull", "bear"):
        message = message_bucket.get(expected_sender)
        if message is None:
            continue
        validation_decision = risk_manager.validate_axl_message(message, expected_sender, round_number, session_id)
        if validation_decision.action != "PROCEED":
            if not DRY_RUN:
                print(f"[JUDGE] AXL validation warning for {expected_sender}: {validation_decision.reason}")

    bull_argument_dict, bull_fallback_used = _extract_argument_from_message(message_bucket.get("bull"), "bull")
    bear_argument_dict, bear_fallback_used = _extract_argument_from_message(message_bucket.get("bear"), "bear")

    bull_receive_status = "sent" if message_bucket.get("bull") is not None else "missing"
    bear_receive_status = "sent" if message_bucket.get("bear") is not None else "missing"
    if timed_out and (bull_fallback_used or bear_fallback_used):
        missing = []
        if bull_fallback_used:
            missing.append("bull")
        if bear_fallback_used:
            missing.append("bear")
        print(f"[JUDGE] Round {round_number} timed out waiting for: {', '.join(missing)}. Proceeding with neutral fallback.")

    snapshot: MarketSnapshot | None = None
    market_fetch_error: str | None = None
    try:
        snapshot = fetch_snapshot(token_pair)
    except Exception as exc:  # noqa: BLE001
        market_fetch_error = f"{type(exc).__name__}: {exc}"

    if snapshot is None:
        snapshot = MarketSnapshot(
            token_pair=token_pair,
            timestamp=datetime.now(UTC),
            fetch_errors=[market_fetch_error or "unknown fetch failure"],
        )

    verdict = score_round(
        bull_argument_dict=bull_argument_dict,
        bear_argument_dict=bear_argument_dict,
        round_number=round_number,
        market_snapshot=snapshot,
    )

    publish_result = publish_verdict(verdict, round_number, session_id)

    persisted_winner = verdict.get("winner")
    if persisted_winner not in {"bull", "bear"}:
        if int(verdict.get("bullScore", 50)) >= int(verdict.get("bearScore", 50)):
            persisted_winner = "bull"
        else:
            persisted_winner = "bear"

    insert_judge_verdict(
        round_number=round_number,
        bull_score=int(verdict.get("bullScore", 50)),
        bear_score=int(verdict.get("bearScore", 50)),
        winner=str(persisted_winner),
        reasoning=str(verdict.get("reasoning", "")),
        bull_argument_received=json.dumps(bull_argument_dict, default=str),
        bear_argument_received=json.dumps(bear_argument_dict, default=str),
        accuracy_bonus_applied=bool(verdict.get("accuracyBonusApplied", False)),
        accuracy_bonus_recipient=(
            str(verdict.get("accuracyBonusRecipient"))
            if verdict.get("accuracyBonusRecipient") in {"bull", "bear"}
            else None
        ),
        conviction_update_status=str(publish_result.get("conviction_tx_hash") or publish_result.get("conviction_update_status", "failed")),
    )

    upsert_round_comparison_from_judge(
        round_number=round_number,
        bull_confidence=int(bull_argument_dict.get("confidence", 50)),
        bear_confidence=int(bear_argument_dict.get("confidence", 50)),
        bull_axl_status=bull_receive_status,
        bear_axl_status=bear_receive_status,
    )

    bonus_points = int(verdict.get("accuracyBonusPoints", 0))
    bonus_recipient = verdict.get("accuracyBonusRecipient")
    bonus_summary = "None"
    if bonus_recipient in {"bull", "bear"} and bonus_points > 0:
        bonus_summary = f"{str(bonus_recipient).capitalize()} +{bonus_points}"

    tx_summary = str(publish_result.get("conviction_tx_hash") or "failed")
    winner_text = str(verdict.get("winner") or "NONE").upper()
    print(
        f"[JUDGE] Round {round_number} | Bull: {verdict.get('bullScore', 50)} | "
        f"Bear: {verdict.get('bearScore', 50)} | Winner: {winner_text} | "
        f"Accuracy bonus: {bonus_summary} | Tx: {tx_summary}"
    )

    return {
        **verdict,
        "round_number": round_number,
        "token_pair": token_pair,
        "timed_out": timed_out,
        "bull_receive_status": bull_receive_status,
        "bear_receive_status": bear_receive_status,
        "publish_result": publish_result,
        "market_data_error": market_fetch_error,
    }


if __name__ == "__main__":
    load_dotenv()
    round_number = int(os.getenv("JUDGE_TEST_ROUND", "1"))
    token_pair = os.getenv("TOKEN_PAIR", "ETH/USDC")
    result = run_judge_round(session_id=os.getenv("DEBATE_SESSION_ID", "default-session"), round_number=round_number, token_pair=token_pair)
    print(json.dumps(result, indent=2, default=str))
