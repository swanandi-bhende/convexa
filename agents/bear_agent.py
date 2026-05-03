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
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, conint

try:
    from langchain.output_parsers import RetryOutputParser
except Exception:  # noqa: BLE001
    RetryOutputParser = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.db_manager import init_database, insert_bear_round
from utils.market_data import MarketSnapshot, fetch_snapshot, format_for_bear
from agents.memory import AgentMemory, PerformanceTracker
from agents.strategy_adapter import StrategyAdapter


def _load_system_prompt() -> str:
    prompt_path = PROJECT_ROOT / "agents" / "prompts" / "bear_system_prompt_v1.txt"
    raw = prompt_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    body_start = 0
    for idx, line in enumerate(lines):
        if line.strip().startswith("PROMPT_START"):
            body_start = idx + 1
            break
    return "\n".join(lines[body_start:]).strip()


SYSTEM_PROMPT = _load_system_prompt()


class BearAgentOutput(BaseModel):
    argument: str = Field(description="A 2-3 sentence bearish thesis grounded in market metrics")
    confidence: conint(ge=0, le=100) = Field(description="Confidence score from 0 to 100")
    keyMetrics: list[str] = Field(min_length=2, max_length=4, description="2-4 key metric strings")


load_dotenv()
DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"

# Bear agent communicates exclusively with the Judge node via AXL. Direct Bull-Bear communication is architecturally prohibited.
ALLOWED_DESTINATIONS = [os.getenv("JUDGE_AXL_PEER_ID", "")]
_init_parser = JsonOutputParser(pydantic_object=BearAgentOutput)

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

PARSER = JsonOutputParser(pydantic_object=BearAgentOutput)
BEAR_CHAIN: Runnable[dict[str, Any], dict[str, Any]] = PROMPT_TEMPLATE | LLM | PARSER
RETRY_PARSER = (
    RetryOutputParser.from_llm(parser=PARSER, llm=LLM) if RetryOutputParser is not None else None
)


DEFAULT_FALLBACK_ARGUMENT = {
    "argument": "Market signals are temporarily unavailable, so the bearish case is weak for this round. Risk remains elevated due to missing confirmatory data.",
    "confidence": 25,
    "keyMetrics": [
        "data availability: partial",
        "confidence policy fallback: 25",
    ],
}

_PREVIOUS_BEAR_ARGUMENT: dict[str, Any] | None = None


def _is_specific_metric(metric: str) -> bool:
    return any(char.isdigit() for char in metric)


def _default_key_metrics(snapshot: MarketSnapshot) -> list[str]:
    return [
        f"large outflow count: {snapshot.large_outflow_count}",
        f"recent lp removals usd: {snapshot.recent_lp_removals_usd:.2f}",
        f"funding rate proxy: {snapshot.funding_rate_proxy:.2f}%",
        f"volume delta percent: {snapshot.volume_delta_percent:.2f}%",
    ]


def _calibrate_confidence(snapshot: MarketSnapshot, llm_confidence: int) -> int:
    # Deterministic confidence calibration avoids flat scores once real market data varies.
    score = 25
    price_change = snapshot.price_change_24h_percent
    volume_delta = snapshot.volume_delta_percent
    outflows = snapshot.large_outflow_count

    if price_change <= -3:
        score += 25
    elif price_change <= -1:
        score += 15
    elif price_change >= 1:
        score -= 10

    if volume_delta <= -20:
        score += 25
    elif volume_delta <= -5:
        score += 15
    elif volume_delta >= 10:
        score -= 10

    if outflows >= 10:
        score += 20
    elif outflows >= 3:
        score += 10

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
    if _PREVIOUS_BEAR_ARGUMENT is not None:
        reused = sanitize_argument(dict(_PREVIOUS_BEAR_ARGUMENT))
        reused["confidence"] = max(0, int(reused.get("confidence", 50)) - 20)
        reused["argument"] = (
            f"Round {round_number}: reusing prior bearish argument because JSON generation failed "
            f"({reason}). {reused.get('argument', '')}"
        ).strip()
        if len(reused["argument"]) > 500:
            reused["argument"] = reused["argument"][:500]
        if not reused.get("keyMetrics"):
            reused["keyMetrics"] = ["fallback: previous-round reuse"]
        return reused

    fallback = dict(DEFAULT_FALLBACK_ARGUMENT)
    fallback["argument"] = (
        f"Round {round_number}: unable to generate bearish JSON output ({reason}), "
        "using conservative fallback."
    )
    return sanitize_argument(fallback)


def generate_bear_argument(market_snapshot: MarketSnapshot, round_number: int, memory: AgentMemory | None = None, weights: dict | None = None) -> dict[str, Any]:
    """Generate a validated bearish argument for one round with robust fallback behavior."""
    global _PREVIOUS_BEAR_ARGUMENT

    if DRY_RUN:
        fallback = dict(DEFAULT_FALLBACK_ARGUMENT)
        fallback["argument"] = (
            f"Round {round_number}: dry-run bearish thesis derived from local market snapshot. "
            f"Price change {market_snapshot.price_change_24h_percent:.2f}% and large outflows {market_snapshot.large_outflow_count} were reviewed."
        )
        fallback["confidence"] = 58 if market_snapshot.price_change_24h_percent >= 0 else 46
        processed = _post_process_argument(sanitize_argument(fallback), market_snapshot)
        processed = sanitize_argument(processed)
        _PREVIOUS_BEAR_ARGUMENT = dict(processed)
        return processed

    market_summary = format_for_bear(market_snapshot, weights=weights)

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

        if RETRY_PARSER is not None:
            parsed = RETRY_PARSER.parse_with_prompt(raw_content, prompt_value)
        else:
            parsed = PARSER.parse(raw_content)

        sanitized = sanitize_argument(parsed if isinstance(parsed, dict) else {})
        validated = BearAgentOutput.model_validate(sanitized)
        processed = _post_process_argument(validated.model_dump(), market_snapshot)
        processed = sanitize_argument(processed)
        _PREVIOUS_BEAR_ARGUMENT = dict(processed)
        return processed
    except Exception as exc:  # noqa: BLE001 - includes Groq transport/model errors and parser failures
        fallback = _fallback_using_previous_round(round_number, type(exc).__name__)
        processed = _post_process_argument(fallback, market_snapshot)
        return sanitize_argument(processed)


def publish_to_judge(argument_dict: dict[str, Any], round_number: int) -> bool:
    """Publish Bear round output to Judge via local AXL HTTP endpoint."""
    payload = {
        "sender": "bear",
        "sender_peer_id": os.getenv("BEAR_AXL_PEER_ID", ""),
        "round": round_number,
        "argument": argument_dict,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    payload["message_hash"] = str(uuid5(NAMESPACE_URL, json.dumps(payload, sort_keys=True, default=str)))
    payload["signature"] = f"bear-signature:{payload['message_hash']}"

    if DRY_RUN:
        print(f"[DRY_RUN] Bear publish_to_judge round={round_number}")
        return True

    judge_peer_id = os.getenv("JUDGE_AXL_PEER_ID")
    if not judge_peer_id:
        return False

    assert len(ALLOWED_DESTINATIONS) == 1 and judge_peer_id == ALLOWED_DESTINATIONS[0], (
        "Invalid destination: Bear is only permitted to send to the Judge node"
    )

    axl_base_url = os.getenv("BEAR_AXL_HTTP_URL", "http://localhost:8001").rstrip("/")
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


def run_bear_round(session_id: str, round_number: int, token_pair: str) -> dict[str, Any]:
    """Execute one complete Bear round: fetch, reason, publish, log, and summarize."""
    init_database()

    performance_tracker = PerformanceTracker()
    strategy_adapter = StrategyAdapter("bear", session_id, performance_tracker)
    memory = AgentMemory("bear", session_id)

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

    argument_dict = generate_bear_argument(snapshot, round_number, memory=memory, weights=weights)
    axl_sent = publish_to_judge(argument_dict, round_number)
    axl_status = "sent" if axl_sent else "failed"

    key_metrics = argument_dict.get("keyMetrics", [])
    if not isinstance(key_metrics, list):
        key_metrics = []

    snapshot_payload = json.loads(json.dumps(asdict(snapshot), default=str))

    insert_bear_round(
        round_number=round_number,
        token_pair=token_pair,
        argument=str(argument_dict.get("argument", "")),
        confidence=int(argument_dict.get("confidence", 0)),
        key_metrics=[str(item) for item in key_metrics],
        raw_market_data=snapshot_payload,
        axl_delivery_status=axl_status,
    )

    argument_preview = str(argument_dict.get("argument", ""))[:90]
    print(
        f"[BEAR] Round {round_number} | "
        f"Confidence: {argument_dict.get('confidence', 0)} | "
        f"AXL: {axl_status} | "
        f"Argument: {argument_preview}"
    )

    # If a judge score was provided via environment or orchestrator callback, record it
    judge_score_env = os.getenv("LATEST_JUDGE_SCORE_BEAR")
    try:
        judge_score = int(judge_score_env) if judge_score_env is not None else None
    except Exception:
        judge_score = None

    if judge_score is not None:
        try:
            memory.add_round(round_number, market_summary if 'market_summary' in locals() else format_for_bear(snapshot, weights=weights), argument_dict, judge_score)
        except Exception:
            pass
        try:
            performance_tracker.record_round(session_id, "bear", round_number, argument_dict, judge_score, won_round=(int(argument_dict.get("confidence",0))>50), accuracy_bonus=False)
            performance_tracker.update_metric_correlations(session_id, "bear", round_number)
        except Exception:
            pass

    return {
        "round_number": round_number,
        "token_pair": token_pair,
        "argument": argument_dict,
        "axl_delivery_success": axl_sent,
        "market_data_error": market_fetch_error,
    }


if __name__ == "__main__":
    load_dotenv()
    result = run_bear_round(session_id=os.getenv("DEBATE_SESSION_ID", "default-session"), round_number=1, token_pair="ETH/USDC")
    print(json.dumps(result["argument"], indent=2))
    print(f"AXL delivery success: {result['axl_delivery_success']}")
