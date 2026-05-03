from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid5, NAMESPACE_URL

import httpx
from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, ValidationError, conint

try:
    from langchain.output_parsers import RetryOutputParser
except Exception:  # noqa: BLE001
    RetryOutputParser = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_system_prompt() -> str:
    prompt_path = PROJECT_ROOT / "agents" / "prompts" / "bull_system_prompt_v1.txt"
    raw = prompt_path.read_text(encoding="utf-8")
    # Allow metadata/comment header in prompt file while keeping runtime prompt clean.
    lines = raw.splitlines()
    body_start = 0
    for idx, line in enumerate(lines):
        if line.strip().startswith("PROMPT_START"):
            body_start = idx + 1
            break
    return "\n".join(lines[body_start:]).strip().replace("{", "{{").replace("}", "}}")


SYSTEM_PROMPT = _load_system_prompt()

from utils.db_manager import init_database, insert_bull_round, upsert_round_comparison_from_bull
from utils.market_data import MarketSnapshot, fetch_snapshot, format_for_bull
from agents.memory import AgentMemory, PerformanceTracker
from agents.strategy_adapter import StrategyAdapter


class BullAgentOutput(BaseModel):
    argument: str = Field(description="A 2-3 sentence bullish thesis grounded in market metrics")
    confidence: conint(ge=0, le=100) = Field(description="Confidence score from 0 to 100")
    keyMetrics: list[str] = Field(min_length=2, max_length=4, description="2-4 key metric strings")


load_dotenv()
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"

# Bull agent communicates exclusively with the Judge node via AXL. Direct Bull-Bear communication is architecturally prohibited.
ALLOWED_DESTINATIONS = [os.getenv("JUDGE_AXL_PEER_ID", "")]
_init_parser = JsonOutputParser(pydantic_object=BullAgentOutput)

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "Market data for this round:\n{market_data}\n\n"
            "Return JSON only. Follow this schema exactly:\n{format_instructions}",
        ),
    ]
)

LLM = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.3,
)

PARSER = JsonOutputParser(pydantic_object=BullAgentOutput)
BULL_CHAIN: Runnable[dict[str, Any], dict[str, Any]] = PROMPT_TEMPLATE | LLM | PARSER
RETRY_PARSER = (
    RetryOutputParser.from_llm(parser=PARSER, llm=LLM) if RetryOutputParser is not None else None
)

JSON_REPAIR_LLM = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.0,
)
JSON_REPAIR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You repair malformed JSON. Return only valid JSON and preserve the schema exactly.",
        ),
        (
            "human",
            "Original prompt:\n{original_prompt}\n\nMalformed output:\n{raw_output}\n\n"
            "Format instructions:\n{format_instructions}",
        ),
    ]
)

LAST_GENERATION_STATUS: dict[str, Any] = {
    "status": "idle",
    "parse_valid": False,
    "repaired": False,
    "reason": "",
}


DEFAULT_FALLBACK_ARGUMENT = {
    "argument": "Market signals are temporarily unavailable, so the bullish case is weak for this round. Upside remains possible but unconfirmed due to missing data.",
    "confidence": 25,
    "keyMetrics": [
        "data availability: partial",
        "confidence policy fallback: 25",
    ],
}

_PREVIOUS_BULL_ARGUMENT: dict[str, Any] | None = None


def _set_generation_status(*, status: str, parse_valid: bool, repaired: bool, reason: str = "") -> None:
    global LAST_GENERATION_STATUS
    LAST_GENERATION_STATUS = {
        "status": status,
        "parse_valid": bool(parse_valid),
        "repaired": bool(repaired),
        "reason": reason,
    }


def _repair_json_output(raw_content: str, prompt_value: Any) -> str:
    repair_prompt = JSON_REPAIR_PROMPT.format_prompt(
        original_prompt=getattr(prompt_value, "to_string", lambda: str(prompt_value))(),
        raw_output=raw_content,
        format_instructions=_init_parser.get_format_instructions(),
    )
    repaired_output = JSON_REPAIR_LLM.invoke(repair_prompt)
    return getattr(repaired_output, "content", str(repaired_output))


def _is_specific_metric(metric: str) -> bool:
    return any(char.isdigit() for char in metric)


def _default_key_metrics(snapshot: MarketSnapshot) -> list[str]:
    return [
        f"large inflow count: {snapshot.large_inflow_count}",
        f"net wallet flow count: {snapshot.net_wallet_flow_count}",
        f"recent lp additions usd: {snapshot.recent_lp_additions_usd:.2f}",
        f"lp net flow usd: {snapshot.lp_net_flow_usd:.2f}",
    ]


def _calibrate_confidence(snapshot: MarketSnapshot, llm_confidence: int) -> int:
    # Deterministic confidence calibration keeps scoring tied to bullish signal alignment.
    score = 25
    price_change = snapshot.price_change_24h_percent
    volume_delta = snapshot.volume_delta_percent
    outflows = snapshot.large_outflow_count

    if price_change >= 3:
        score += 25
    elif price_change >= 1:
        score += 15
    elif price_change <= -1:
        score -= 10

    if volume_delta >= 20:
        score += 25
    elif volume_delta >= 5:
        score += 15
    elif volume_delta <= -10:
        score -= 10

    if outflows >= 10:
        score -= 20
    elif outflows >= 3:
        score -= 10
    else:
        score += 5

    if snapshot.current_price <= 0:
        score = min(score, 35)

    combined = int(round((score + llm_confidence) / 2))
    return max(0, min(100, combined))


def _post_process_argument(payload: dict[str, Any], snapshot: MarketSnapshot) -> dict[str, Any]:
    argument = str(payload.get("argument", "")).strip()
    if not _is_specific_metric(argument):
        argument = (
            f"{argument} "
            f"Observed values: 24h price change {snapshot.price_change_24h_percent:.2f}%, "
            f"volume delta {snapshot.volume_delta_percent:.2f}%, "
            f"outflows {snapshot.large_outflow_count}."
        ).strip()

    metrics = payload.get("keyMetrics", [])
    if not isinstance(metrics, list):
        metrics = []

    specific_metrics = [str(item) for item in metrics if _is_specific_metric(str(item))]

    deduped_metrics: list[str] = []
    seen_metrics: set[str] = set()
    for item in specific_metrics:
        key = item.strip().lower()
        if key in seen_metrics:
            continue
        seen_metrics.add(key)
        deduped_metrics.append(item)

    for item in _default_key_metrics(snapshot):
        if len(deduped_metrics) >= 4:
            break
        key = item.strip().lower()
        if key in seen_metrics:
            continue
        seen_metrics.add(key)
        deduped_metrics.append(item)

    llm_confidence = int(payload.get("confidence", 0))
    calibrated_confidence = _calibrate_confidence(snapshot, llm_confidence)

    return {
        "argument": argument,
        "confidence": calibrated_confidence,
        "keyMetrics": deduped_metrics[:4],
    }


def sanitize_argument(raw_dict: dict[str, Any]) -> dict[str, Any]:
    argument = str(raw_dict.get("argument", "")).strip()
    if len(argument) > 500:
        argument = argument[:500]

    confidence_value = raw_dict.get("confidence", 50)
    try:
        confidence = int(confidence_value)
    except (TypeError, ValueError):
        confidence = 50
    confidence = max(0, min(100, confidence))

    metrics = raw_dict.get("keyMetrics", [])
    if not isinstance(metrics, list):
        metrics = [str(metrics)] if metrics is not None else []
    normalized_metrics = [str(item) for item in metrics if str(item).strip()]

    return {
        "argument": argument,
        "confidence": confidence,
        "keyMetrics": normalized_metrics,
    }


def _fallback_using_previous_round(round_number: int, reason: str) -> dict[str, Any]:
    if _PREVIOUS_BULL_ARGUMENT is not None:
        reused = sanitize_argument(dict(_PREVIOUS_BULL_ARGUMENT))
        reused["confidence"] = max(0, int(reused.get("confidence", 50)) - 20)
        reused["argument"] = (
            f"Round {round_number}: reusing prior bullish argument because JSON generation failed "
            f"({reason}). {reused.get('argument', '')}"
        ).strip()
        if len(reused["argument"]) > 500:
            reused["argument"] = reused["argument"][:500]
        if not reused.get("keyMetrics"):
            reused["keyMetrics"] = ["fallback: previous-round reuse"]
        return reused

    fallback = dict(DEFAULT_FALLBACK_ARGUMENT)
    fallback["argument"] = (
        f"Round {round_number}: unable to generate bullish JSON output ({reason}), "
        "using conservative fallback."
    )
    return sanitize_argument(fallback)


def _is_strongly_negative_for_bull(snapshot: MarketSnapshot) -> bool:
    price_strongly_down = snapshot.price_change_24h_percent <= -5.0
    outflows_dominant = snapshot.large_outflow_count >= 10
    volume_sharply_declining = snapshot.volume_delta_percent <= -20.0
    return price_strongly_down and outflows_dominant and volume_sharply_declining


def _apply_bull_confidence_cap(argument_dict: dict[str, Any], snapshot: MarketSnapshot) -> dict[str, Any]:
    if not _is_strongly_negative_for_bull(snapshot):
        return argument_dict

    capped = dict(argument_dict)
    capped["confidence"] = min(int(capped.get("confidence", 0)), 45)
    return capped


def generate_bull_argument(market_snapshot: MarketSnapshot, round_number: int, memory: AgentMemory | None = None, weights: dict | None = None) -> dict[str, Any]:
    """Generate a validated bullish argument for one round with robust fallback behavior."""
    global _PREVIOUS_BULL_ARGUMENT

    if DRY_RUN:
        fallback = dict(DEFAULT_FALLBACK_ARGUMENT)
        fallback["argument"] = (
            f"Round {round_number}: dry-run bullish thesis derived from local market snapshot. "
            f"Price change {market_snapshot.price_change_24h_percent:.2f}% and volume delta {market_snapshot.volume_delta_percent:.2f}% were reviewed."
        )
        fallback["confidence"] = 55 if market_snapshot.price_change_24h_percent <= 0 else 45
        processed = _post_process_argument(sanitize_argument(fallback), market_snapshot)
        processed = sanitize_argument(processed)
        _PREVIOUS_BULL_ARGUMENT = dict(processed)
        _set_generation_status(status="dry_run", parse_valid=True, repaired=False, reason="dry_run")
        return _apply_bull_confidence_cap(processed, market_snapshot)

    market_summary = format_for_bull(market_snapshot, weights=weights)

    # Inject recent memory context if available
    if memory is not None:
        try:
            mem_block = memory.memory.load_memory_variables({}).get("debate_history", "")
            if mem_block:
                market_summary = f"Recent debate history:\n{mem_block}\n\n{market_summary}"
        except Exception:
            pass

    try:
        invoke_payload = {
            "market_data": market_summary,
            "format_instructions": _init_parser.get_format_instructions(),
        }
        prompt_value = PROMPT_TEMPLATE.format_prompt(**invoke_payload)
        raw_output = LLM.invoke(prompt_value)
        raw_content = getattr(raw_output, "content", str(raw_output))

        repaired = False
        try:
            parsed = PARSER.parse(raw_content)
        except OutputParserException:
            repaired = True
            repaired_content = _repair_json_output(raw_content, prompt_value)
            parsed = PARSER.parse(repaired_content)

        sanitized = sanitize_argument(parsed if isinstance(parsed, dict) else {})
        validated = BullAgentOutput.model_validate(sanitized)
        processed = _post_process_argument(validated.model_dump(), market_snapshot)
        processed = sanitize_argument(processed)
        _PREVIOUS_BULL_ARGUMENT = dict(processed)
        _set_generation_status(status="repaired" if repaired else "ok", parse_valid=True, repaired=repaired, reason="")
        return _apply_bull_confidence_cap(processed, market_snapshot)
    except httpx.HTTPError as exc:
        fallback = _fallback_using_previous_round(round_number, f"network:{type(exc).__name__}")
        processed = _post_process_argument(fallback, market_snapshot)
        processed = sanitize_argument(processed)
        _set_generation_status(status="fallback", parse_valid=False, repaired=False, reason=type(exc).__name__)
        return _apply_bull_confidence_cap(processed, market_snapshot)
    except (OutputParserException, ValidationError, ValueError, TypeError) as exc:
        fallback = _fallback_using_previous_round(round_number, f"parser:{type(exc).__name__}")
        processed = _post_process_argument(fallback, market_snapshot)
        processed = sanitize_argument(processed)
        _set_generation_status(status="fallback", parse_valid=False, repaired=False, reason=type(exc).__name__)
        return _apply_bull_confidence_cap(processed, market_snapshot)
    except Exception as exc:  # noqa: BLE001 - non-network/runtime fallback
        fallback = _fallback_using_previous_round(round_number, f"runtime:{type(exc).__name__}")
        processed = _post_process_argument(fallback, market_snapshot)
        processed = sanitize_argument(processed)
        _set_generation_status(status="fallback", parse_valid=False, repaired=False, reason=type(exc).__name__)
        return _apply_bull_confidence_cap(processed, market_snapshot)


def publish_to_judge(argument_dict: dict[str, Any], round_number: int) -> bool:
    """Publish Bull round output to Judge via local AXL HTTP endpoint."""
    payload = {
        "sender": "bull",
        "sender_peer_id": os.getenv("BULL_AXL_PEER_ID", ""),
        "round": round_number,
        "argument": argument_dict,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    payload["message_hash"] = str(uuid5(NAMESPACE_URL, json.dumps(payload, sort_keys=True, default=str)))
    payload["signature"] = f"bull-signature:{payload['message_hash']}"

    if DRY_RUN:
        print(f"[DRY_RUN] Bull publish_to_judge round={round_number}")
        return True

    judge_peer_id = os.getenv("JUDGE_AXL_PEER_ID")
    if not judge_peer_id:
        return False

    assert len(ALLOWED_DESTINATIONS) == 1 and judge_peer_id == ALLOWED_DESTINATIONS[0], (
        "Invalid destination: Bull is only permitted to send to the Judge node"
    )

    axl_base_url = os.getenv("BULL_AXL_HTTP_URL", "http://localhost:8002").rstrip("/")
    axl_send_url = f"{axl_base_url}/send"

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                axl_send_url,
                json=payload,
                headers={"X-Destination-Peer-Id": judge_peer_id},
            )
            response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False


def run_bull_round(session_id: str, round_number: int, token_pair: str) -> dict[str, Any]:
    """Execute one complete Bull round: fetch, reason, publish, log, and summarize."""
    init_database()

    performance_tracker = PerformanceTracker()
    strategy_adapter = StrategyAdapter("bull", session_id, performance_tracker)
    memory = AgentMemory("bull", session_id)

    # Possibly adapt strategy weights
    try:
        strategy_adapter.apply_adaptation(round_number)
    except Exception:
        pass

    weights = strategy_adapter.get_current_weights()

    snapshot: MarketSnapshot | None = None
    market_fetch_error: str | None = None
    try:
        snapshot = fetch_snapshot(token_pair)
    except Exception as exc:  # noqa: BLE001 - keep round alive even when data provider fails
        market_fetch_error = f"{type(exc).__name__}: {exc}"

    if snapshot is None:
        # Minimal snapshot fallback to keep round execution non-fatal.
        snapshot = MarketSnapshot(
            token_pair=token_pair,
            timestamp=datetime.now(UTC),
            fetch_errors=[market_fetch_error or "unknown fetch failure"],
        )

    argument_dict = generate_bull_argument(snapshot, round_number, memory=memory, weights=weights)
    axl_sent = publish_to_judge(argument_dict, round_number)
    axl_status = "sent" if axl_sent else "failed"

    key_metrics = argument_dict.get("keyMetrics", [])
    if not isinstance(key_metrics, list):
        key_metrics = []

    snapshot_payload = json.loads(json.dumps(asdict(snapshot), default=str))

    insert_bull_round(
        round_number=round_number,
        token_pair=token_pair,
        argument=str(argument_dict.get("argument", "")),
        confidence=int(argument_dict.get("confidence", 0)),
        key_metrics=[str(item) for item in key_metrics],
        raw_market_data=snapshot_payload,
        axl_delivery_status=axl_status,
    )

    upsert_round_comparison_from_bull(
        round_number=round_number,
        bull_confidence=int(argument_dict.get("confidence", 0)),
        bull_axl_status=axl_status,
    )

    # If a judge score was provided via environment or orchestrator callback, record it
    judge_score_env = os.getenv("LATEST_JUDGE_SCORE_BULL")
    try:
        judge_score = int(judge_score_env) if judge_score_env is not None else None
    except Exception:
        judge_score = None

    if judge_score is not None:
        try:
            memory.add_round(round_number, market_summary if 'market_summary' in locals() else format_for_bull(snapshot, weights=weights), argument_dict, judge_score)
        except Exception:
            pass
        try:
            performance_tracker.record_round(session_id, "bull", round_number, argument_dict, judge_score, won_round=(int(argument_dict.get("confidence",0))>50), accuracy_bonus=False)
            performance_tracker.update_metric_correlations(session_id, "bull", round_number)
        except Exception:
            pass

    argument_preview = str(argument_dict.get("argument", ""))[:90]
    print(
        f"[BULL] Round {round_number} | "
        f"Confidence: {argument_dict.get('confidence', 0)} | "
        f"AXL: {axl_status} | "
        f"Argument: {argument_preview}"
    )

    return {
        "round_number": round_number,
        "token_pair": token_pair,
        "argument": argument_dict,
        "axl_delivery_success": axl_sent,
        "market_data_error": market_fetch_error,
    }


if __name__ == "__main__":
    load_dotenv()
    result = run_bull_round(session_id=os.getenv("DEBATE_SESSION_ID", "default-session"), round_number=1, token_pair="ETH/USDC")
    print(json.dumps(result["argument"], indent=2))
    print(f"AXL delivery success: {result['axl_delivery_success']}")
