from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from utils.db.schema import ConvictionHistory
from utils.db_manager import get_session
from utils.risk_manager import RiskDecision


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> int:
    return int(max(lower, min(upper, round(value))))


def _snapshot_value(snapshot: Any, name: str, default: float = 0.0) -> float:
    if snapshot is None:
        return float(default)
    if isinstance(snapshot, dict):
        return float(snapshot.get(name, default) or default)
    return float(getattr(snapshot, name, default) or default)


@dataclass(slots=True)
class MockGroqClient:
    scenario_type: str
    agent: str

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        snapshot = inputs.get("market_snapshot")
        if snapshot is None and isinstance(inputs.get("snapshot"), dict):
            snapshot = inputs.get("snapshot")
        round_number = int(inputs.get("round_number") or 0)
        agent = self.agent.strip().lower()
        scenario = self.scenario_type.strip().lower()

        if agent == "judge":
            return self._judge_response(snapshot, round_number)
        if agent == "bull":
            return self._bull_response(snapshot, scenario, round_number)
        if agent == "bear":
            return self._bear_response(snapshot, scenario, round_number)
        raise ValueError(f"Unsupported mock agent role: {self.agent}")

    def _bull_response(self, snapshot: Any, scenario: str, round_number: int) -> dict[str, Any]:
        price_change = _snapshot_value(snapshot, "price_change_24h_percent")
        volume_delta = _snapshot_value(snapshot, "volume_delta_percent")
        inflows = _snapshot_value(snapshot, "large_inflow_count")
        outflows = _snapshot_value(snapshot, "large_outflow_count")
        lp_net_flow = _snapshot_value(snapshot, "lp_net_flow_usd")
        funding = _snapshot_value(snapshot, "funding_rate_proxy")

        if scenario == "bear":
            confidence = _clamp(35 + (outflows * 2.0) - (price_change * 0.2) - (volume_delta * 0.1))
            argument = (
                f"Residual bid support is fragile. Price change sits at {price_change:.2f}% and volume delta is {volume_delta:.2f}%, "
                f"so this is a low-conviction long case despite {int(inflows)} large inflows."
            )
            key_metrics = [
                f"price_change_24h_percent: {price_change:.2f}%",
                f"volume_delta_percent: {volume_delta:.2f}%",
                f"large_inflow_count: {int(inflows)}",
                f"large_outflow_count: {int(outflows)}",
            ]
            return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}

        if scenario == "choppy":
            confidence = _clamp(47 + (price_change * 1.5) + (volume_delta * 0.5) + (inflows - outflows) * 1.5)
            tone = "slightly constructive" if price_change >= 0 else "cautious"
            argument = (
                f"The tape is {tone}. Price change is {price_change:.2f}% and volume delta is {volume_delta:.2f}%, "
                f"with {int(inflows)} large inflows versus {int(outflows)} outflows."
            )
            if round_number <= 3 and round_number % 2 == 1:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"volume_delta_percent: {volume_delta:.2f}%",
                    f"large_inflow_count: {int(inflows)}",
                ]
            elif round_number <= 3:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"large_outflow_count: {int(outflows)}",
                    f"funding_rate_proxy: {funding:.2f}%",
                    f"lp_net_flow_usd: {lp_net_flow:,.0f}",
                ]
            else:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"volume_delta_percent: {volume_delta:.2f}%",
                    f"lp_net_flow_usd: {lp_net_flow:,.0f}",
                ]
            return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}
        else:
            confidence = _clamp(30 + (price_change * 0.6) + (volume_delta * 0.3) + ((inflows - outflows) * 1.0) + (lp_net_flow / 5000.0) + (funding * 2.0) + (round_number * 1.5))
            argument = (
                f"Whale accumulation is persistent. Price change is {price_change:.2f}%, volume delta is {volume_delta:.2f}%, "
                f"and net LP flow is {lp_net_flow:,.0f} USD with funding proxy {funding:.2f}."
            )

        key_metrics = [
            f"price_change_24h_percent: {price_change:.2f}%",
            f"volume_delta_percent: {volume_delta:.2f}%",
            f"large_inflow_count: {int(inflows)}",
            f"lp_net_flow_usd: {lp_net_flow:,.0f}",
        ]
        return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}

    def _bear_response(self, snapshot: Any, scenario: str, round_number: int) -> dict[str, Any]:
        price_change = _snapshot_value(snapshot, "price_change_24h_percent")
        volume_delta = _snapshot_value(snapshot, "volume_delta_percent")
        inflows = _snapshot_value(snapshot, "large_inflow_count")
        outflows = _snapshot_value(snapshot, "large_outflow_count")
        lp_net_flow = _snapshot_value(snapshot, "lp_net_flow_usd")
        funding = _snapshot_value(snapshot, "funding_rate_proxy")

        if scenario == "bull":
            confidence = _clamp(32 + (outflows * 1.5) - (price_change * 0.15) - (volume_delta * 0.1))
            argument = (
                f"The bullish tape is crowded and vulnerable. Outflows remain limited at {int(outflows)} while price change is {price_change:.2f}%, "
                f"so the downside case is weak and largely reactive."
            )
            key_metrics = [
                f"price_change_24h_percent: {price_change:.2f}%",
                f"volume_delta_percent: {volume_delta:.2f}%",
                f"large_inflow_count: {int(inflows)}",
                f"large_outflow_count: {int(outflows)}",
            ]
            return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}

        if scenario == "choppy":
            confidence = _clamp(48 + (-price_change * 1.5) + (-volume_delta * 0.5) + (outflows - inflows) * 1.5)
            tone = "slightly defensive" if price_change <= 0 else "guarded"
            argument = (
                f"The tape is {tone}. Price change is {price_change:.2f}% and volume delta is {volume_delta:.2f}%, "
                f"with {int(outflows)} outflows against {int(inflows)} inflows."
            )
            if round_number <= 3 and round_number % 2 == 1:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"large_outflow_count: {int(outflows)}",
                    f"funding_rate_proxy: {funding:.2f}%",
                ]
            elif round_number <= 3:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"volume_delta_percent: {volume_delta:.2f}%",
                    f"large_inflow_count: {int(inflows)}",
                    f"lp_net_flow_usd: {lp_net_flow:,.0f}",
                ]
            else:
                key_metrics = [
                    f"price_change_24h_percent: {price_change:.2f}%",
                    f"volume_delta_percent: {volume_delta:.2f}%",
                    f"lp_net_flow_usd: {lp_net_flow:,.0f}",
                ]
            return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}
        else:
            confidence = _clamp(35 + (-price_change * 0.7) + (-volume_delta * 0.4) + (outflows * 1.3) - (inflows * 0.6) + (-lp_net_flow / 7000.0) + (-funding * 2.0))
            argument = (
                f"Outflows are overpowering the bid. Price change is {price_change:.2f}%, volume delta is {volume_delta:.2f}%, "
                f"and LP flow is {lp_net_flow:,.0f} USD with funding proxy {funding:.2f}."
            )

        key_metrics = [
            f"price_change_24h_percent: {price_change:.2f}%",
            f"volume_delta_percent: {volume_delta:.2f}%",
            f"large_outflow_count: {int(outflows)}",
            f"lp_net_flow_usd: {lp_net_flow:,.0f}",
        ]
        return {"argument": argument, "confidence": confidence, "keyMetrics": key_metrics}

    def _judge_response(self, snapshot: Any, round_number: int) -> dict[str, Any]:
        price_change = _snapshot_value(snapshot, "price_change_24h_percent")
        volume_delta = _snapshot_value(snapshot, "volume_delta_percent")
        inflows = _snapshot_value(snapshot, "large_inflow_count")
        outflows = _snapshot_value(snapshot, "large_outflow_count")
        lp_net_flow = _snapshot_value(snapshot, "lp_net_flow_usd")
        funding = _snapshot_value(snapshot, "funding_rate_proxy")

        scenario = self.scenario_type.strip().lower()
        if scenario == "bear":
            if round_number >= 7:
                bear_score = 72
            else:
                bear_score = min(68, 50 + (round_number * 2))
            bull_score = max(0, bear_score - 16)
            winner = "bear"
            reasoning = (
                f"The bearish side dominates because outflows and negative flow signals overwhelm the bid. "
                f"Price change is {price_change:.2f}% and LP net flow is {lp_net_flow:,.0f} USD."
            )
        elif scenario == "choppy":
            bull_score = _clamp(48 + (price_change * 1.5) + (volume_delta * 0.6) + ((inflows - outflows) * 1.2) + (funding * 1.0))
            bear_score = _clamp(48 - (price_change * 1.5) - (volume_delta * 0.6) + ((outflows - inflows) * 1.2) - (funding * 1.0))
            winner = "bull" if bull_score >= bear_score else "bear"
            reasoning = (
                f"This is a mixed tape with alternating directional evidence. Price change is {price_change:.2f}% and volume delta is {volume_delta:.2f}%.")
        else:
            if round_number >= 7:
                bull_score = 72
            else:
                bull_score = min(68, 50 + (round_number * 2))
            bear_score = max(0, bull_score - 16)
            winner = "bull"
            reasoning = (
                f"Whale accumulation and rising liquidity support the bullish case. Price change is {price_change:.2f}% and "
                f"volume delta is {volume_delta:.2f}%, while net LP flow is {lp_net_flow:,.0f} USD."
            )

        bull_breakdown = {
            "Evidence Quality": 18,
            "Logical Consistency": 18,
            "Metric Accuracy": 19,
            "Predictive Value": 16,
            "Argument Clarity": 17,
        }
        bear_breakdown = {
            "Evidence Quality": 18,
            "Logical Consistency": 18,
            "Metric Accuracy": 19,
            "Predictive Value": 16,
            "Argument Clarity": 17,
        }

        return {
            "winner": winner,
            "roundNumber": 0,
            "bullScore": bull_score,
            "bearScore": bear_score,
            "bullCriteriaBreakdown": bull_breakdown,
            "bearCriteriaBreakdown": bear_breakdown,
            "reasoning": reasoning,
            "accuracyBonusApplied": False,
        }


@dataclass(slots=True)
class MockAlchemyRPC:
    snapshot: Any | None = None

    def slot0_value(self, snapshot: Any | None = None) -> tuple[int, int, int, int, int, int, bool]:
        source = snapshot if snapshot is not None else self.snapshot
        current_price = _snapshot_value(source, "current_price", 1800.0)
        sqrt_price_x96 = int((current_price ** 0.5) * (2**96))
        return (sqrt_price_x96, 0, 0, 0, 0, 0, True)

    class _Functions:
        def __init__(self, outer: "MockAlchemyRPC") -> None:
            self._outer = outer

        def slot0(self) -> Any:
            class _Call:
                def __init__(self, outer: "MockAlchemyRPC") -> None:
                    self._outer = outer

                def call(self, *args: Any, **kwargs: Any) -> tuple[int, int, int, int, int, int, bool]:
                    return self._outer.slot0_value()

            return _Call(self._outer)

        def token0(self) -> Any:
            class _Call:
                def call(self) -> str:
                    return "0x0000000000000000000000000000000000000001"

            return _Call()

        def token1(self) -> Any:
            class _Call:
                def call(self) -> str:
                    return "0x0000000000000000000000000000000000000002"

            return _Call()

    class _Contract:
        def __init__(self, outer: "MockAlchemyRPC") -> None:
            self.functions = MockAlchemyRPC._Functions(outer)

    class _Eth:
        def __init__(self, outer: "MockAlchemyRPC") -> None:
            self._outer = outer

        def contract(self, *args: Any, **kwargs: Any) -> Any:
            return MockAlchemyRPC._Contract(self._outer)

    @property
    def eth(self) -> Any:
        return self._Eth(self)


@dataclass(slots=True)
class MockGraphQL:
    snapshot: Any

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        del query, variables
        inflows = int(_snapshot_value(self.snapshot, "large_inflow_count", 0))
        outflows = int(_snapshot_value(self.snapshot, "large_outflow_count", 0))
        additions = float(_snapshot_value(self.snapshot, "recent_lp_additions_usd", 0.0))
        removals = float(_snapshot_value(self.snapshot, "recent_lp_removals_usd", 0.0))
        pool_tvl = float(_snapshot_value(self.snapshot, "pool_tvl_usd", 0.0))
        now_ts = int(datetime.now(UTC).timestamp())

        swaps = []
        for idx in range(inflows):
            swaps.append({"timestamp": now_ts - idx * 120, "amountUSD": "5000", "amount0": "1.0", "origin": f"0xinflow{idx:02d}"})
        for idx in range(outflows):
            swaps.append({"timestamp": now_ts - idx * 180, "amountUSD": "4500", "amount0": "-1.0", "origin": f"0xoutflow{idx:02d}"})

        return {
            "swaps": swaps,
            "pool": {
                "id": "0xmockpool",
                "totalValueLockedUSD": f"{pool_tvl:.2f}",
                "totalValueLockedToken0": "1200.0",
                "totalValueLockedToken1": "2200000.0",
            },
            "mints": [{"amountUSD": f"{additions:.2f}", "timestamp": now_ts - 300}],
            "burns": [{"amountUSD": f"{removals:.2f}", "timestamp": now_ts - 240}],
            "poolDayDatas": [
                {"date": now_ts - 86400, "volumeUSD": "1200000.0"},
                {"date": now_ts - 3600, "volumeUSD": "1800000.0"},
            ],
        }


@dataclass(slots=True)
class MockKeeperHubClient:
    gas_spike_mode: bool = False
    attempts: int = 0

    def submit_job(self, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.attempts += 1
        if self.gas_spike_mode and self.attempts <= 2:
            return {"success": False, "error": "gas_too_high", "attempt": self.attempts, "job_type": job_type, "payload": payload}
        return {
            "success": True,
            "job_id": f"mock-job-{self.attempts:03d}",
            "status": "confirmed",
            "job_type": job_type,
            "payload": payload,
        }

    def confirm_job(self, job_id: str) -> dict[str, Any]:
        return {"success": True, "job_id": job_id, "status": "confirmed"}


@dataclass(slots=True)
class MockAXLNode:
    failure_mode: bool = False
    failure_after_messages: int = 0
    messages_seen: int = 0
    inbox: list[dict[str, Any]] = field(default_factory=list)

    def send(self, message: dict[str, Any]) -> dict[str, Any]:
        self.messages_seen += 1
        if self.failure_mode and self.messages_seen > self.failure_after_messages:
            raise TimeoutError("Mock AXL node stopped responding")
        self.inbox.append(dict(message))
        return {"success": True, "delivered": True}

    def receive(self) -> list[dict[str, Any]]:
        if self.failure_mode and self.messages_seen > self.failure_after_messages:
            raise TimeoutError("Mock AXL node stopped responding")
        return list(self.inbox)

    def healthcheck(self) -> bool:
        return not (self.failure_mode and self.messages_seen > self.failure_after_messages)


@dataclass(slots=True)
class MockDebateRuntime:
    scenario_type: str
    snapshots: list[Any]
    bull_failure_after_messages: int | None = None
    keeperhub_gas_spike_mode: bool = False
    bull_client: MockGroqClient = field(init=False)
    bear_client: MockGroqClient = field(init=False)
    judge_client: MockGroqClient = field(init=False)
    alchemy_client: MockAlchemyRPC = field(init=False)
    graphql_client: MockGraphQL = field(init=False)
    keeperhub_client: MockKeeperHubClient = field(init=False)
    bull_node: MockAXLNode = field(init=False)
    bear_node: MockAXLNode = field(init=False)
    current_snapshot: Any | None = None
    snapshot_index: int = 0
    current_scores: tuple[int, int] = (0, 0)
    message_buffer: dict[tuple[str, int], dict[str, Any]] = field(default_factory=dict)
    session_id: str | None = None

    def __post_init__(self) -> None:
        self.bull_client = MockGroqClient(self.scenario_type, "bull")
        self.bear_client = MockGroqClient(self.scenario_type, "bear")
        self.judge_client = MockGroqClient(self.scenario_type, "judge")
        self.alchemy_client = MockAlchemyRPC(self.snapshots[0] if self.snapshots else None)
        self.graphql_client = MockGraphQL(self.snapshots[0] if self.snapshots else None)
        self.keeperhub_client = MockKeeperHubClient(gas_spike_mode=self.keeperhub_gas_spike_mode)
        self.bull_node = MockAXLNode(
            failure_mode=self.bull_failure_after_messages is not None,
            failure_after_messages=int(self.bull_failure_after_messages or 0),
        )
        self.bear_node = MockAXLNode()

    def next_snapshot(self, token_pair: str) -> Any:
        del token_pair
        if self.snapshot_index >= len(self.snapshots):
            if self.current_snapshot is None:
                raise RuntimeError("No snapshots configured for mock runtime")
            return self.current_snapshot
        snapshot = self.snapshots[self.snapshot_index]
        self.snapshot_index += 1
        self.current_snapshot = snapshot
        self.alchemy_client.snapshot = snapshot
        self.graphql_client.snapshot = snapshot
        return snapshot

    def snapshot_for_round(self, token_pair: str) -> Any:
        del token_pair
        if self.current_snapshot is None:
            return self.next_snapshot(token_pair)
        return self.current_snapshot

    def store_message(self, side: str, round_number: int, argument: dict[str, Any]) -> bool:
        node = self.bull_node if side == "bull" else self.bear_node
        if side == "bull" and self.bull_failure_after_messages is not None and round_number > self.bull_failure_after_messages:
            return False
        delivered = True
        try:
            node.send(argument)
        except TimeoutError:
            delivered = False

        if not delivered:
            return False

        payload = {
            "sender": side,
            "round": round_number,
            "argument": dict(argument),
            "sender_peer_id": f"mock-{side}-peer-id",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        payload["message_hash"] = sha256(f"{side}:{round_number}:{payload['timestamp']}".encode("utf-8")).hexdigest()
        payload["signature"] = f"mock-signature:{side}:{round_number}"
        self.message_buffer[(side, round_number)] = {"sender": side, "round": round_number, "payload": payload}
        return True

    def wait_for_both_arguments(self, round_number: int, timeout_seconds: int = 120) -> tuple[dict[str, dict[str, Any] | None], bool]:
        del timeout_seconds
        bucket = {
            "bull": self.message_buffer.get(("bull", round_number)),
            "bear": self.message_buffer.get(("bear", round_number)),
        }
        return bucket, False

    def bull_argument(self, snapshot: Any, round_number: int, memory: Any | None = None, weights: dict | None = None) -> dict[str, Any]:
        del memory, weights
        return self.bull_client.invoke({"market_snapshot": snapshot, "round_number": round_number})

    def bear_argument(self, snapshot: Any, round_number: int, memory: Any | None = None, weights: dict | None = None) -> dict[str, Any]:
        del memory, weights
        return self.bear_client.invoke({"market_snapshot": snapshot, "round_number": round_number})

    def judge_verdict(self, bull_argument: dict[str, Any], bear_argument: dict[str, Any], round_number: int, market_snapshot: Any) -> dict[str, Any]:
        verdict = self.judge_client.invoke(
            {
                "bull_argument": bull_argument,
                "bear_argument": bear_argument,
                "market_snapshot": market_snapshot,
                "round_number": round_number,
            }
        )
        verdict["roundNumber"] = round_number
        verdict["accuracyBonusApplied"] = False
        return verdict

    def update_conviction_onchain(self, verdict_dict: dict[str, Any], round_number: int, session_id: str) -> tuple[bool, str]:
        bull_score = int(verdict_dict.get("bullScore", 0))
        bear_score = int(verdict_dict.get("bearScore", 0))
        previous_bull, previous_bear = self.current_scores
        self.current_scores = (bull_score, bear_score)

        with get_session() as session:
            session.add(
                ConvictionHistory(
                    session_id=session_id,
                    round_number=round_number,
                    bull_score=bull_score,
                    bear_score=bear_score,
                    delta_from_previous_bull=(bull_score - previous_bull) if round_number > 1 else None,
                    delta_from_previous_bear=(bear_score - previous_bear) if round_number > 1 else None,
                    drift_flagged=False,
                    timestamp=datetime.now(UTC),
                )
            )
            session.commit()

        return True, f"0xmockconviction{round_number:02d}"

    def current_round_trace_summary(self) -> dict[str, Any]:
        return {
            "snapshot_index": self.snapshot_index,
            "current_scores": self.current_scores,
            "messages": len(self.message_buffer),
        }


class MockRiskManager:
    def __init__(self, session_id: str, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self.session_id = session_id

    def check_data_freshness(self, market_snapshot: dict[str, Any], round_number: int, max_retries: int = 4) -> RiskDecision:
        del market_snapshot, round_number, max_retries
        return RiskDecision(action="PROCEED", reason="mock_freshness_ok")

    def check_minimum_stakes(self, session_id: str | None = None, round_number: int = 0) -> RiskDecision:
        del session_id, round_number
        return RiskDecision(action="PROCEED", reason="mock_stakes_ok")

    def check_conviction_drift(self, round_number: int, new_bull_score: int, new_bear_score: int, session_id: str | None = None) -> RiskDecision:
        del round_number, new_bull_score, new_bear_score, session_id
        return RiskDecision(action="PROCEED", reason="mock_drift_ok")

    def validate_axl_message(self, message: dict[str, Any], expected_sender: str, round_number: int, session_id: str | None = None) -> RiskDecision:
        del message, expected_sender, round_number, session_id
        return RiskDecision(action="PROCEED", reason="mock_axl_ok")

    def check_debate_timeout(self, round_number: int, session_id: str | None = None) -> RiskDecision:
        del round_number, session_id
        return RiskDecision(action="PROCEED", reason="mock_timeout_ok")

    def evaluate_draw_conditions(self, bull_score: int, bear_score: int, session_id: str | None = None) -> dict[str, Any]:
        del bull_score, bear_score, session_id
        return {"draw_type": "marginal_winner"}

    def __getattr__(self, name: str) -> Any:
        if name.startswith("check_") or name.startswith("validate_"):
            def _default(*args: Any, **kwargs: Any) -> RiskDecision:
                del args, kwargs
                return RiskDecision(action="PROCEED", reason=f"mock_{name}")

            return _default
        raise AttributeError(name)
