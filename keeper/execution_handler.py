from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from web3 import Web3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from utils.constants import TARGET_CHAIN_ID, get_universal_router_address
from utils.db.schema import KeeperHubJob as KeeperHubJobModel
from utils.db.schema import KeeperHubRetry as KeeperHubRetryModel
from utils.db_manager import get_session
from dataclasses import dataclass
from typing import Optional

KEEPERHUB_API_KEY = os.getenv("KEEPERHUB_API_KEY", "").strip()
KEEPERHUB_MCP_URL = os.getenv("KEEPERHUB_MCP_URL", "https://app.keeperhub.com/mcp").strip()
KEEPERHUB_API_BASE_URL = os.getenv("KEEPERHUB_API_BASE_URL", "https://app.keeperhub.com").strip().rstrip("/")
KEEPERHUB_EXECUTOR_ADDRESS = os.getenv("KEEPERHUB_EXECUTOR_ADDRESS", "").strip()
KEEPERHUB_JOB_SUBMIT_PATH = os.getenv("KEEPERHUB_JOB_SUBMIT_PATH", "/api/execute/jobs").strip()
KEEPERHUB_NETWORK = os.getenv("KEEPERHUB_NETWORK", "unichain-sepolia").strip()
SWAP_CHAIN_ID = int(os.getenv("SWAP_CHAIN_ID", str(TARGET_CHAIN_ID)))
ALCHEMY_RPC_URL = os.getenv("ALCHEMY_RPC_URL", "").strip()


def _now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_auth_headers(api_key: str) -> dict[str, str]:
    # KeeperHub docs show Bearer auth for general API and X-API-Key for direct execution.
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-API-Key": api_key,
    }
    return headers


def _create_http_client() -> httpx.Client:
    if not KEEPERHUB_API_KEY:
        raise RuntimeError("Missing KEEPERHUB_API_KEY")
    return httpx.Client(
        base_url=KEEPERHUB_API_BASE_URL,
        headers=_build_auth_headers(KEEPERHUB_API_KEY),
        timeout=float(os.getenv("KEEPERHUB_HTTP_TIMEOUT_SECONDS", "15")),
    )


@dataclass(slots=True)
class RetryPolicy:
    maxRetries: int
    retryOnGasSpike: bool
    retryOnRevert: bool
    backoffSeconds: int
    maxGasPriceGwei: float


@dataclass(slots=True)
class KeeperHubJob:
    calldata: str
    to: str
    value: str
    maxGasPrice: float
    deadline: int
    retryPolicy: RetryPolicy
    privateRouting: bool = False


MICRO_SETTLEMENT_RETRY_POLICY = RetryPolicy(
    maxRetries=3,
    retryOnGasSpike=True,
    retryOnRevert=True,
    backoffSeconds=15,
    maxGasPriceGwei=float(os.getenv("KEEPERHUB_MICRO_MAX_RETRY_GAS_GWEI", "90")),
)

FINAL_SETTLEMENT_RETRY_POLICY = RetryPolicy(
    maxRetries=5,
    retryOnGasSpike=True,
    retryOnRevert=True,
    backoffSeconds=30,
    maxGasPriceGwei=float(os.getenv("KEEPERHUB_FINAL_MAX_RETRY_GAS_GWEI", "120")),
)


def _extract_response_data(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload:
        return payload.get("data")
    return payload


def _extract_job_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("jobId", "job_id", "executionId", "execution_id", "id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _insert_keeperhub_job_row(
    *,
    session_id: str,
    round_number: int,
    job_id: str,
    job_type: str,
    swap_quote_id: int | None,
    submitted_at: datetime,
    max_gas_price_gwei: float,
    deadline_timestamp: int,
    retry_policy: RetryPolicy,
    current_status: str,
    tx_hash: str | None,
    actual_gas_price_gwei: float | None,
    keeperhub_fee_wei: str | None,
    error_message: str | None,
) -> None:
    with get_session() as session:
        row = KeeperHubJobModel(
            session_id=session_id,
            round_number=round_number,
            job_id=job_id,
            job_type=job_type,
            swap_quote_id=swap_quote_id,
            submitted_at=submitted_at,
            max_gas_price_gwei=max_gas_price_gwei,
            deadline_timestamp=deadline_timestamp,
            retry_policy_json=json.dumps(asdict(retry_policy), default=str),
            current_status=current_status,
            last_polled_at=None,
            confirmed_at=None,
            tx_hash=tx_hash,
            actual_gas_price_gwei=actual_gas_price_gwei,
            keeperhub_fee_wei=keeperhub_fee_wei,
            error_message=error_message,
        )
        session.add(row)
        session.commit()


def _insert_retry_rows(job_id: str, retries: Any) -> None:
    if not isinstance(retries, list):
        return

    with get_session() as session:
        for idx, entry in enumerate(retries, start=1):
            if not isinstance(entry, dict):
                continue
            reason = str(entry.get("reason") or "unknown")
            outcome = entry.get("outcome")
            timestamp_raw = entry.get("timestamp")
            retry_timestamp = _now_utc_naive()
            if isinstance(timestamp_raw, str):
                try:
                    retry_timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    pass

            row = KeeperHubRetryModel(
                job_id=job_id,
                retry_attempt_number=int(entry.get("attempt") or idx),
                retry_reason=reason,
                retry_timestamp=retry_timestamp,
                retry_outcome=str(outcome) if outcome is not None else None,
            )
            session.merge(row)

        session.commit()


@dataclass(slots=True)
class JobResult:
    success: bool
    job_id: str
    status: str | None
    tx_hash: str | None
    actual_gas_price_gwei: float | None
    confirmed_at: datetime | None
    raw_response: Any | None


def _map_keeper_status_to_local(status: str | None) -> str:
    if not status:
        return "submitted"
    s = str(status).strip().lower()
    if s in {"confirmed", "executed", "success", "succeeded"}:
        return "confirmed"
    if s in {"failed", "error", "reverted", "cancelled", "cancelled_by_user"}:
        return "failed"
    # transitional states
    return "pending"


def monitor_retries(job_id: str, response_data: Any, last_seen_retry_count: int) -> int:
    """Detect new retries and persist them to keeperhub_retries.

    Returns the updated retry count.
    """
    if not isinstance(response_data, dict):
        return last_seen_retry_count

    # Check common fields
    retry_count = None
    for k in ("retryCount", "retriesCount", "attempts", "retry_count"):
        if k in response_data:
            try:
                retry_count = int(response_data.get(k) or 0)
            except Exception:
                retry_count = None
            break

    # Also consider explicit retries list
    retries_list = response_data.get("retries") if isinstance(response_data.get("retries"), list) else None
    if retry_count is None and retries_list is not None:
        retry_count = len(retries_list)

    if retry_count is None:
        return last_seen_retry_count

    if retry_count <= last_seen_retry_count:
        return last_seen_retry_count

    # We have new retries to record
    new_retries = []
    try:
        # Prefer to fetch detailed history if available
        client = _create_http_client()
        history_paths = [f"/api/executions/{job_id}/history", f"/api/jobs/{job_id}/history", f"/api/jobs/{job_id}/attempts"]
        details = None
        for p in history_paths:
            try:
                resp = client.get(p)
                if resp.status_code < 300:
                    details = resp.json()
                    break
            except Exception:
                continue
        if details is None and retries_list is not None:
            details = {"retries": retries_list}
    except Exception:
        details = {"retries": retries_list} if retries_list is not None else None

    if details and isinstance(details, dict) and isinstance(details.get("retries"), list):
        new_retries = details.get("retries")
    elif retries_list is not None:
        new_retries = retries_list

    # Persist any new retry records beyond last_seen_retry_count
    if new_retries:
        for idx, entry in enumerate(new_retries, start=1):
            if idx <= last_seen_retry_count:
                continue
            reason = str(entry.get("reason") or entry.get("error") or "unknown") if isinstance(entry, dict) else str(entry)
            timestamp_raw = entry.get("timestamp") if isinstance(entry, dict) else None
            retry_timestamp = _now_utc_naive()
            if isinstance(timestamp_raw, str):
                try:
                    retry_timestamp = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            row = KeeperHubRetryModel(
                job_id=job_id,
                retry_attempt_number=idx,
                retry_reason=reason,
                retry_timestamp=retry_timestamp,
                retry_outcome=str(entry.get("outcome")) if isinstance(entry, dict) and entry.get("outcome") is not None else None,
            )
            with get_session() as session:
                session.merge(row)
                session.commit()

            print(f"[KEEPERHUB] Job {job_id} retry attempt {idx}/{retry_count} — reason: {reason} — waiting {MICRO_SETTLEMENT_RETRY_POLICY.backoffSeconds if MICRO_SETTLEMENT_RETRY_POLICY.backoffSeconds else 15}s before next attempt")

    return retry_count


def poll_job_status(job_id: str, timeout_seconds: int = 300) -> JobResult:
    """Poll KeeperHub for job status until terminal state or timeout.

    Updates `keeperhub_jobs` on each poll with `current_status` and `last_polled_at`.
    """
    if not job_id:
        raise ValueError("job_id is required")

    start = datetime.now().timestamp()
    deadline = start + float(timeout_seconds)
    last_retry_count = 0
    client = _create_http_client()
    attempted_paths = [f"/api/executions/{job_id}", f"/api/jobs/{job_id}", f"/api/executions/{job_id}/status"]

    last_status = None
    while datetime.now().timestamp() < deadline:
        response_data = None
        used_path = None
        for path in attempted_paths:
            try:
                resp = client.get(path)
            except Exception as exc:
                continue
            if resp.status_code == 404:
                continue
            try:
                response_data = resp.json()
            except Exception:
                response_data = {"raw": resp.text}
            used_path = path
            break

        # If no path succeeded, sleep and retry
        if response_data is None:
            time.sleep(5)
            continue

        data = _extract_response_data(response_data)
        # Flatten if wrapper
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            data = data["data"]

        status_field = None
        if isinstance(data, dict):
            status_field = data.get("status") or data.get("state")

        local_status = _map_keeper_status_to_local(status_field)

        # Update DB row
        with get_session() as session:
            row = session.query(KeeperHubJobModel).filter(KeeperHubJobModel.job_id == job_id).one_or_none()
            if row:
                row.current_status = local_status
                row.last_polled_at = _now_utc_naive()
                session.commit()

        # Monitor retries
        try:
            last_retry_count = monitor_retries(job_id, data or {}, last_retry_count)
        except Exception:
            pass

        # Terminal success
        if local_status == "confirmed":
            tx_hash = None
            gas_price = None
            confirmed_at = _now_utc_naive()
            if isinstance(data, dict):
                tx_hash = data.get("transactionHash") or data.get("txHash") or data.get("tx_hash")
                gas_price = data.get("gasPriceGwei") or data.get("gasPrice") or data.get("gas_price_gwei")
            # Persist final values
            with get_session() as session:
                row = session.query(KeeperHubJobModel).filter(KeeperHubJobModel.job_id == job_id).one_or_none()
                if row:
                    row.current_status = "confirmed"
                    row.tx_hash = str(tx_hash) if tx_hash is not None else row.tx_hash
                    try:
                        row.actual_gas_price_gwei = float(gas_price) if gas_price is not None else row.actual_gas_price_gwei
                    except Exception:
                        pass
                    row.confirmed_at = confirmed_at
                    row.last_polled_at = _now_utc_naive()
                    session.commit()

            return JobResult(True, job_id, "confirmed", tx_hash if tx_hash else None, float(gas_price) if gas_price is not None else None, confirmed_at, data)

        # Terminal failure
        if local_status == "failed":
            error_message = None
            if isinstance(data, dict):
                error_message = data.get("error") or data.get("message") or str(data)
            with get_session() as session:
                row = session.query(KeeperHubJobModel).filter(KeeperHubJobModel.job_id == job_id).one_or_none()
                if row:
                    row.current_status = "failed"
                    row.error_message = str(error_message) if error_message is not None else row.error_message
                    row.last_polled_at = _now_utc_naive()
                    session.commit()
            return JobResult(False, job_id, "failed", None, None, None, data)

        # Not terminal — adapt sleep based on age
        elapsed = datetime.now().timestamp() - start
        if elapsed < 60:
            time.sleep(5)
        else:
            time.sleep(15)

    # Timeout
    with get_session() as session:
        row = session.query(KeeperHubJobModel).filter(KeeperHubJobModel.job_id == job_id).one_or_none()
        if row:
            row.current_status = "pending_timeout"
            row.last_polled_at = _now_utc_naive()
            session.commit()

    return JobResult(False, job_id, "pending_timeout", None, None, None, None)


def execute_swap_via_keeperhub(session_id: str, round_number: int, job_type: str, swap_quote_result: Any):
    """Unified entry point: build calldata, submit job, poll status, analyze execution, and update swap_executions.

    Returns an execution result dict containing job_id, tx_hash, confirmed, retry_count, and analysis.
    """
    # local import to avoid circular dependencies
    from uniswap.swap_executor import build_swap_calldata, analyze_execution, _insert_execution_row, _update_execution_row

    # choose retry policy
    retry_policy = MICRO_SETTLEMENT_RETRY_POLICY if job_type == "micro_settlement" else FINAL_SETTLEMENT_RETRY_POLICY

    swap_calldata = build_swap_calldata(swap_quote_result)
    if not swap_calldata.success:
        return {
            "success": False,
            "reason": f"swap_build_failed:{swap_calldata.reason}",
        }

    try:
        job_id = submit_job(
            session_id=session_id,
            round_number=round_number,
            job_type=job_type,
            swap_calldata_obj=swap_calldata,
            retry_policy=retry_policy,
        )
    except Exception as exc:
        return {"success": False, "reason": f"keeperhub_submit_failed:{exc}"}

    execution_id = _insert_execution_row(
        session_id=session_id,
        round_number=round_number,
        swap_type=job_type,
        quote_id=swap_calldata.quote_id,
        tx_hash=None,
        token_in=swap_quote_result.token_in,
        token_out=swap_quote_result.token_out,
        amount_in_actual_wei=swap_quote_result.amount_in_wei,
        status="pending",
        gas_price_gwei=None,
        error_message="submitted_to_keeperhub",
    )
    _update_execution_row(execution_id, keeperhub_job_id=job_id)

    # Poll status and monitor retries within the same loop
    job_result = poll_job_status(job_id)

    if not job_result.success:
        _update_execution_row(execution_id, status="failed", error_message=f"keeperhub_terminal:{job_result.status}")
        return {
            "success": False,
            "job_id": job_id,
            "status": job_result.status,
            "tx_hash": job_result.tx_hash,
            "retry_count": None,
            "analysis": None,
        }

    # success — fetch tx receipt via web3
    tx_hash = job_result.tx_hash
    tx_receipt = None
    try:
        from web3 import Web3

        web3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))
        if web3.is_connected() and tx_hash:
            try:
                tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
            except Exception:
                tx_receipt = {"transactionHash": tx_hash}
    except Exception:
        tx_receipt = {"transactionHash": tx_hash}

    # Update execution row with tx_hash and confirmed
    _update_execution_row(execution_id, status="confirmed", tx_hash=tx_hash, confirmed_at=_now_utc_naive())

    # Run analysis
    analysis = analyze_execution(swap_quote_result, tx_receipt, session_id, round_number)

    return {
        "success": True,
        "job_id": job_id,
        "tx_hash": tx_hash,
        "status": "confirmed",
        "retry_count": None,
        "analysis": analysis,
    }


def test_connection() -> dict[str, Any]:
    """Verify KeeperHub reachability and credentials before debate startup."""
    # Allow skipping KeeperHub connectivity checks during dry-runs or when explicitly disabled.
    use_keeperhub = os.getenv("USE_KEEPERHUB", "true").strip().lower() in {"1", "true", "yes"}
    dry_run = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes"}
    if not use_keeperhub or dry_run:
        print("[KEEPERHUB] Skipping connection test (dry-run or USE_KEEPERHUB disabled)")
        return {"skipped": True}

    if not KEEPERHUB_API_KEY:
        raise RuntimeError("KEEPERHUB_API_KEY is missing")
    if not KEEPERHUB_EXECUTOR_ADDRESS:
        raise RuntimeError("KEEPERHUB_EXECUTOR_ADDRESS is missing")

    endpoints_to_try = [
        "/api/chains",
        "/api/workflows?limit=1",
        "/api/executions?limit=1",
    ]

    info: dict[str, Any] = {
        "executor_address": KEEPERHUB_EXECUTOR_ADDRESS,
        "mcp_url": KEEPERHUB_MCP_URL,
        "api_base_url": KEEPERHUB_API_BASE_URL,
    }

    errors: list[str] = []
    with _create_http_client() as client:
        successful_path: str | None = None
        for path in endpoints_to_try:
            try:
                response = client.get(path)
            except Exception as exc:  # pragma: no cover
                errors.append(f"{path}: request_failed:{exc}")
                continue

            if response.status_code == 401:
                raise RuntimeError("KeeperHub credentials rejected (401 Unauthorized)")
            if response.status_code == 403:
                raise RuntimeError("KeeperHub API key lacks required scope (403 Forbidden)")
            if response.status_code == 404:
                errors.append(f"{path}: not_found")
                continue
            if response.status_code >= 500:
                errors.append(f"{path}: server_error_{response.status_code}")
                continue

            if response.status_code < 300:
                successful_path = path
                payload = response.json()
                info["account_probe_endpoint"] = path
                info["account_probe_payload"] = _extract_response_data(payload)
                break

            errors.append(f"{path}: unexpected_status_{response.status_code}")

        billing_payload = None
        for billing_path in ("/api/billing/status", "/api/analytics"):
            try:
                billing_resp = client.get(billing_path)
                if billing_resp.status_code < 300:
                    billing_payload = _extract_response_data(billing_resp.json())
                    info["billing_endpoint"] = billing_path
                    info["billing"] = billing_payload
                    break
            except Exception:  # pragma: no cover
                continue

        if successful_path is None:
            raise RuntimeError(
                "KeeperHub is unreachable or key scope is incompatible for required endpoints. "
                f"Attempts: {errors}"
            )

    print("[KEEPERHUB] Connection verified")
    print(f"[KEEPERHUB] Executor wallet: {KEEPERHUB_EXECUTOR_ADDRESS}")
    if billing_payload is not None:
        print(f"[KEEPERHUB] Billing/Credits: {json.dumps(billing_payload, default=str)}")

    return info


def submit_job(
    session_id: str,
    round_number: int,
    job_type: str,
    swap_calldata_obj: Any,
    retry_policy: RetryPolicy,
) -> str:
    """Submit a KeeperHub execution job and persist initial job metadata."""
    if swap_calldata_obj is None or not getattr(swap_calldata_obj, "calldata", None):
        raise ValueError("swap_calldata_obj must contain calldata")

    if not ALCHEMY_RPC_URL:
        raise RuntimeError("ALCHEMY_RPC_URL is required for gas-aware job submission")

    # Safe simulation mode: when DRY_RUN is enabled or explicit simulate flag set,
    # insert a local keeperhub_jobs row and return a fake job id without calling the network.
    simulate_flag = os.getenv("KEEPERHUB_SIMULATE_SUBMIT", "").strip().lower() in {"1", "true", "yes"}
    dry_run = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes"}
    if simulate_flag or dry_run:
        fake_job_id = f"sim-job-{int(time.time())}"
        _insert_keeperhub_job_row(
            session_id=session_id,
            round_number=round_number,
            job_id=fake_job_id,
            job_type=job_type,
            swap_quote_id=getattr(swap_calldata_obj, "quote_id", None),
            submitted_at=_now_utc_naive(),
            max_gas_price_gwei=float(retry_policy.maxGasPriceGwei if hasattr(retry_policy, 'maxGasPriceGwei') else getattr(retry_policy, 'maxGasPriceGwei', 0) or 0),
            deadline_timestamp=int(getattr(swap_calldata_obj, "deadline_unix", 0) or 0),
            retry_policy=retry_policy,
            current_status="submitted",
            tx_hash=None,
            actual_gas_price_gwei=None,
            keeperhub_fee_wei=None,
            error_message=None,
        )
        return fake_job_id

    web3_client = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))
    if not web3_client.is_connected():
        raise RuntimeError("Unable to connect to RPC while preparing KeeperHub job")

    gas_price_wei = int(web3_client.eth.gas_price)
    gas_price_gwei = float(gas_price_wei) / 1e9
    max_gas_price_gwei = round(gas_price_gwei * 1.3, 6)

    deadline = getattr(swap_calldata_obj, "deadline_unix", None)
    if deadline is None:
        raise ValueError("swap_calldata_obj.deadline_unix is required")

    to_address = get_universal_router_address(SWAP_CHAIN_ID)
    job = KeeperHubJob(
        calldata=str(getattr(swap_calldata_obj, "calldata")),
        to=Web3.to_checksum_address(to_address),
        value=str(getattr(swap_calldata_obj, "value_wei", "0") or "0"),
        maxGasPrice=max_gas_price_gwei,
        deadline=int(deadline),
        retryPolicy=retry_policy,
        privateRouting=(job_type == "final_settlement"),
    )

    submit_payload = {
        "network": KEEPERHUB_NETWORK,
        "chainId": str(SWAP_CHAIN_ID),
        "calldata": job.calldata,
        "to": job.to,
        "value": job.value,
        "maxGasPrice": job.maxGasPrice,
        "deadline": job.deadline,
        "retryPolicy": asdict(job.retryPolicy),
        "privateRouting": job.privateRouting,
    }

    with _create_http_client() as client:
        submit_paths = [
            KEEPERHUB_JOB_SUBMIT_PATH,
            "/api/jobs",
            "/api/execute/transaction",
            "/api/execute/jobs",
        ]

        response = None
        used_path = None
        for submit_path in submit_paths:
            try:
                attempt = client.post(submit_path, json=submit_payload)
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(f"KeeperHub job submission request failed: {exc}") from exc

            if attempt.status_code == 404:
                continue

            response = attempt
            used_path = submit_path
            break

        if response is None:
            raise RuntimeError("KeeperHub job submission endpoint not found (all tried paths returned 404)")

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"error": response.text}
            raise RuntimeError(
                f"KeeperHub submit failed status={response.status_code} path={used_path} payload={error_payload}"
            )

        payload = response.json()

    response_data = _extract_response_data(payload)
    if not isinstance(response_data, dict):
        response_data = payload if isinstance(payload, dict) else {"raw": payload}

    job_id = _extract_job_id(response_data)
    if not job_id:
        raise RuntimeError(f"KeeperHub response missing job ID: {payload}")

    current_status = str(response_data.get("status") or "submitted")
    tx_hash = response_data.get("transactionHash") or response_data.get("txHash")
    actual_gas_price_gwei = response_data.get("gasPriceGwei")
    keeperhub_fee_wei = response_data.get("keeperhubFeeWei") or response_data.get("feeWei")

    _insert_keeperhub_job_row(
        session_id=session_id,
        round_number=round_number,
        job_id=job_id,
        job_type=job_type,
        swap_quote_id=getattr(swap_calldata_obj, "quote_id", None),
        submitted_at=_now_utc_naive(),
        max_gas_price_gwei=max_gas_price_gwei,
        deadline_timestamp=int(deadline),
        retry_policy=retry_policy,
        current_status=current_status,
        tx_hash=str(tx_hash) if tx_hash else None,
        actual_gas_price_gwei=float(actual_gas_price_gwei) if actual_gas_price_gwei is not None else None,
        keeperhub_fee_wei=str(keeperhub_fee_wei) if keeperhub_fee_wei is not None else None,
        error_message=None,
    )

    _insert_retry_rows(job_id, response_data.get("retries"))
    return job_id
