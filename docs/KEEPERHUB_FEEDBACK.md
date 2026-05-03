# KeeperHub Builder Feedback

This write-up is based on the actual integration paths in `keeper/execution_handler.py`, `uniswap/swap_executor.py`, and `agents/orchestrator.py`.

## UX and UI Friction
- The biggest friction was not the execution layer itself but the split between the dashboard, API docs, MCP docs, and CLI docs. To confirm the integration path, I had to bounce between https://docs.keeperhub.com/api, https://docs.keeperhub.com/ai-tools, and https://docs.keeperhub.com/cli instead of finding one canonical flow.
- The job view would be easier to use if it exposed the same `session_id` / `job_id` fields that the API accepts and returns. Our code writes `session_id` into every job payload and database row, but the UI does not appear to make that correlation obvious.

## Reproducible Bugs
- The submit path was inconsistent across environments: `POST /api/execute/jobs` was not reliably usable from our integration flow, while `/api/jobs` and `/api/executions/{job_id}` were the fallback paths that worked.
- Repro steps:
  1. Set `KEEPERHUB_API_BASE_URL=https://app.keeperhub.com` and a valid `KEEPERHUB_API_KEY`.
  2. Call `submit_job(...)` from `keeper/execution_handler.py` with a normal swap payload.
  3. Observe the first path fail and the fallback path succeed.
- Expected behavior: one documented canonical submit endpoint.
- Actual behavior: multiple possible submit and poll endpoints, with the code needing fallback logic to stay resilient.
- Timestamp note: I did not capture a wall-clock timestamp in the raw logs. The failure trace is present in the repo log files, but those logs do not include timestamped KeeperHub events.

## Documentation Gaps
- The docs do not publish a canonical list of active job endpoints, so we had to infer the working paths by trial and fallback logic.
- The response schema is under-specified. In our runs, job IDs appeared as `jobId`, `job_id`, `executionId`, and `id`, while status appeared as `status` or `state`. That forced defensive parsing in `_extract_job_id()` and `poll_job_status()`.
- Retry history is not clearly documented. We had to check multiple history endpoints such as `/api/executions/{job_id}/history`, `/api/jobs/{job_id}/history`, and `/api/jobs/{job_id}/attempts` to recover retry details.
- Fee and timeout semantics are still ambiguous. The response exposes fees and status, but the docs do not make it clear which timeout is operational, which is chain-level, and which is a client-side default.

## Feature Requests
- A canonical `/api/health` endpoint would let agents check service readiness before submitting jobs.
- A `/api/jobs/{job_id}/cost` endpoint would help budget-aware dApps estimate execution cost before submission.
- A batch submission endpoint, such as `POST /api/jobs/batch`, would reduce latency for multi-round or multi-agent workflows.
- Published rate limit headers, or a `/api/limits` endpoint, would make stress testing and production planning much easier.
- A single documented endpoint for full retry history would remove the need for fallback history probing.
