from __future__ import annotations

import json
import time
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from utils.db.schema import KeeperHubJob as KeeperHubJobModel, SwapExecution as SwapExecutionModel, SwapQuote as SwapQuoteModel
from utils.db_manager import get_session, update_debate_session, upsert_round_trace


class DryRunAdapter:
    def __init__(self, session_id: str | None = None, round_number: int | None = None, token_pair: str | None = None) -> None:
        self.session_id = session_id or "dry-run-session"
        self.round_number = int(round_number or 0)
        self.token_pair = token_pair or "ETH/USDC"

    def _fake_hash(self, namespace: str, payload: Any) -> str:
        seed = f"{namespace}:{self.session_id}:{self.round_number}:{json.dumps(payload, default=str, sort_keys=True)}:{uuid4()}"
        return "0x" + seed.encode("utf-8").hex()[:64].ljust(64, "0")

    def _now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _mapping(self, value: Any) -> dict[str, Any]:
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return dict(value)
        return {"raw": str(value)}

    def simulate_contract_call(self, contract_name: str, function_name: str, args: Any) -> dict[str, Any]:
        payload = self._mapping(args)
        tx_hash = self._fake_hash(f"{contract_name}.{function_name}", payload)
        block_number = 1_000_000 + self.round_number

        print(f"[DRY_RUN] {contract_name}.{function_name} args={json.dumps(payload, default=str, sort_keys=True)}")

        if contract_name == "DebateEscrow" and function_name == "startDebate":
            update_debate_session(
                self.session_id,
                status="ACCEPTING_STAKES",
            )
        elif contract_name == "ConvictionTracker" and function_name == "updateConviction":
            upsert_round_trace(
                session_id=self.session_id,
                round_number=self.round_number,
                judge_verdict_json=payload.get("verdict"),
                conviction_tx_hash=tx_hash,
                timestamp=self._now(),
            )
        elif contract_name == "DebateEscrow" and function_name == "settleSide":
            winning_side = str(payload.get("winning_side") or payload.get("winner") or payload.get("side") or "unknown")
            update_debate_session(
                self.session_id,
                status="DEBATE_ENDED",
                winning_side=winning_side,
                settlement_tx_hash=tx_hash,
                end_time=self._now(),
            )
            print(f"[DRY_RUN] settleSide winning_side={winning_side}")
        elif contract_name == "DebateEscrow" and function_name == "emergencyPause":
            reason = str(payload.get("reason") or "dry-run emergency pause")
            update_debate_session(
                self.session_id,
                status="ABORTED",
                settlement_tx_hash=f"abort:{reason}",
                end_time=self._now(),
            )

        return {
            "success": True,
            "tx_hash": tx_hash,
            "receipt": {
                "transactionHash": tx_hash,
                "status": 1,
                "blockNumber": block_number,
                "gasUsed": 210000 + (self.round_number * 1000),
                "logs": [],
            },
            "block_number": block_number,
        }

    def simulate_keeperhub_job(self, job_params: Any) -> dict[str, Any]:
        payload = self._mapping(job_params)
        job_id = str(payload.get("job_id") or payload.get("jobId") or f"dry-job-{uuid4().hex[:12]}")
        tx_hash = self._fake_hash("keeperhub", payload)

        with get_session() as session:
            row = KeeperHubJobModel(
                session_id=str(payload.get("session_id") or self.session_id),
                round_number=int(payload.get("round_number") or self.round_number),
                job_id=job_id,
                job_type=str(payload.get("job_type") or "micro_settlement"),
                swap_quote_id=payload.get("swap_quote_id"),
                submitted_at=self._now(),
                max_gas_price_gwei=float(payload.get("max_gas_price_gwei") or payload.get("maxGasPrice") or 0.0),
                deadline_timestamp=int(payload.get("deadline_timestamp") or payload.get("deadline") or 0),
                retry_policy_json=json.dumps(payload.get("retry_policy") or payload.get("retryPolicy") or {}, default=str),
                current_status="submitted",
                last_polled_at=self._now(),
                confirmed_at=None,
                tx_hash=tx_hash,
                actual_gas_price_gwei=None,
                keeperhub_fee_wei=None,
                error_message=None,
            )
            session.add(row)
            session.commit()

        time.sleep(2)

        with get_session() as session:
            row = session.query(KeeperHubJobModel).filter(KeeperHubJobModel.job_id == job_id).one_or_none()
            if row is not None:
                row.current_status = "confirmed"
                row.last_polled_at = self._now()
                row.confirmed_at = self._now()
                row.tx_hash = tx_hash
                row.actual_gas_price_gwei = float(payload.get("actual_gas_price_gwei") or 1.0)
                session.commit()

        return {"job_id": job_id, "tx_hash": tx_hash, "status": "confirmed"}

    def simulate_uniswap_swap(self, quote_params: Any) -> dict[str, Any]:
        payload = self._mapping(quote_params)
        quote_result = payload.get("quote_result") or payload.get("quoteResult") or payload.get("quote") or {}
        if is_dataclass(quote_result):
            quote_result = asdict(quote_result)
        elif not isinstance(quote_result, dict):
            quote_result = {}

        quote_id = quote_result.get("quote_id") or quote_result.get("quoteId") or payload.get("quote_id") or payload.get("quoteId")
        quoted_price = quote_result.get("quoted_price") or quote_result.get("quotedPrice")
        tx_hash = self._fake_hash("uniswap-swap", payload)
        token_in_value = str(payload.get("token_in") or payload.get("tokenIn") or quote_result.get("token_in") or quote_result.get("tokenIn") or "ETH")
        token_out_value = str(payload.get("token_out") or payload.get("tokenOut") or quote_result.get("token_out") or quote_result.get("tokenOut") or "USDC")
        amount_in_value = str(payload.get("amount_in_wei") or payload.get("amountInWei") or quote_result.get("amount_in_wei") or quote_result.get("amountInWei") or "0")
        quoted_amount_out_value = str(payload.get("quoted_amount_out_wei") or quote_result.get("quoted_amount_out_wei") or quote_result.get("quotedAmountOutWei") or "0")
        route_description = str(payload.get("route_description") or quote_result.get("route_description") or quote_result.get("routeDescription") or "dry-run route")
        gas_estimate_value = str(payload.get("gas_estimate_wei") or quote_result.get("gas_estimate_wei") or quote_result.get("gasEstimateWei") or "210000")
        slippage_value = float(payload.get("slippage_tolerance_percent") or payload.get("slippageTolerancePercent") or quote_result.get("slippage_tolerance_percent") or quote_result.get("slippageTolerancePercent") or 0.5)

        with get_session() as session:
            quote_row = None
            if quote_id is not None:
                quote_row = session.query(SwapQuoteModel).filter(SwapQuoteModel.id == int(quote_id)).one_or_none()
            if quote_row is None:
                quote_row = SwapQuoteModel(
                    session_id=str(payload.get("session_id") or self.session_id),
                    round_number=int(payload.get("round_number") or self.round_number),
                    swap_type=str(payload.get("swap_type") or payload.get("swapType") or "micro_settlement"),
                    token_in=token_in_value,
                    token_out=token_out_value,
                    amount_in_wei=amount_in_value,
                    quoted_amount_out_wei=quoted_amount_out_value,
                    quoted_price=float(quoted_price) if quoted_price is not None else None,
                    route_description=route_description,
                    gas_estimate_wei=gas_estimate_value,
                    slippage_tolerance_percent=slippage_value,
                    quote_timestamp=self._now(),
                    quote_used=True,
                )
                session.add(quote_row)
                session.commit()
                session.refresh(quote_row)
            else:
                quote_row.quote_used = True
                if quote_row.quoted_amount_out_wei is None:
                    quote_row.quoted_amount_out_wei = quoted_amount_out_value
                if quote_row.quoted_price is None and quoted_price is not None:
                    quote_row.quoted_price = float(quoted_price)
                if quote_row.route_description is None:
                    quote_row.route_description = route_description
                if quote_row.gas_estimate_wei is None:
                    quote_row.gas_estimate_wei = gas_estimate_value
                if quote_row.slippage_tolerance_percent is None:
                    quote_row.slippage_tolerance_percent = slippage_value
                session.commit()
                session.refresh(quote_row)

            execution_row = SwapExecutionModel(
                session_id=str(payload.get("session_id") or self.session_id),
                round_number=int(payload.get("round_number") or self.round_number),
                swap_type=str(payload.get("swap_type") or payload.get("swapType") or "micro_settlement"),
                quote_id=int(quote_id) if quote_id is not None else quote_row.id,
                tx_hash=tx_hash,
                token_in=str(quote_row.token_in),
                token_out=str(quote_row.token_out),
                amount_in_actual_wei=str(quote_row.amount_in_wei),
                amount_out_actual_wei=str(payload.get("amount_out_actual_wei") or payload.get("amountOutActualWei") or quote_row.quoted_amount_out_wei or "0"),
                execution_price=float(quoted_price) if quoted_price is not None else None,
                slippage_realized_percent=0.0,
                gas_used_wei=str(payload.get("gas_used_wei") or payload.get("gasUsedWei") or "0"),
                gas_price_gwei=float(payload.get("gas_price_gwei") or payload.get("gasPriceGwei") or 0.0),
                keeperhub_job_id=None,
                status="confirmed",
                confirmed_at=self._now(),
                error_message="dry_run_simulated_confirmation",
            )
            session.add(execution_row)
            session.commit()
            session.refresh(execution_row)

        return {
            "success": True,
            "tx_hash": tx_hash,
            "quote_id": quote_row.id,
            "execution_id": execution_row.id,
            "tx_receipt": {
                "transactionHash": tx_hash,
                "status": 1,
                "gasUsed": 0,
                "logs": [],
            },
        }
