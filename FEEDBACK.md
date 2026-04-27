# Uniswap Integration Feedback

## Run Metadata
- Date: 2026-04-27T03:04:16.905992
- Chain: 1301
- API Base: https://trade-api.gateway.uniswap.org/v1
- DRY_RUN: True

## Validator Runs
- Run 1: {"ok": false, "stage": "quote", "reason": "unsupported_token", "session_id": "validator-1777259056-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "unsupported_token", "session_id": "validator-1777259056-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "unsupported_token", "session_id": "validator-1777259056-3", "round_number": 3}

## Friction Points
- API responses differ by route type, which complicates one-size-fits-all parsing.
- For dry-run integration testing, there is no canonical synthetic receipt format from API docs.
- Rate limit docs expose 429 behavior but do not clearly publish per-minute limits by free plan in API reference.

## Documentation Gaps
- More explicit examples for /swap when permitData is null vs provided would reduce integration errors.
- A dedicated section mapping quote routing variants to expected quote payload shape would help.
- Clarification around plan-specific rate-limit numbers in the docs would improve production planning.

## Requested Features
- A documented sandbox mode for swap transaction generation without requiring onchain broadcast.
- A lightweight endpoint to validate quote freshness/expiry semantics directly.

## Additional Run
- Date: 2026-04-27T03:04:37.116212
- Run 1: {"ok": false, "stage": "quote", "reason": "quote_http_error", "session_id": "validator-1777259075-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "quote_http_error", "session_id": "validator-1777259075-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "quote_http_error", "session_id": "validator-1777259076-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T11:18:55.297427
- Run 1: {"ok": false, "stage": "quote", "reason": "unauthorized_api_key", "session_id": "validator-1777288733-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "unauthorized_api_key", "session_id": "validator-1777288734-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "unauthorized_api_key", "session_id": "validator-1777288734-3", "round_number": 3}
- Auth diagnostic: Uniswap API rejected key; set UNISWAP_API_KEY in .env to a valid dashboard key.

## Additional Run
- Date: 2026-04-27T11:57:22.654128
- Run 1: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291039-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291041-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291041-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:00:52.182209
- Run 1: {"ok": false, "stage": "swap", "reason": "quote_near_expiry_refresh_required", "session_id": "validator-1777291249-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291250-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291251-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:02:32.000992
- Run 1: {"ok": false, "stage": "swap", "reason": "quote_refresh_failed:no_liquidity", "session_id": "validator-1777291348-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291350-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291351-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:06:20.419435
- Run 1: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291577-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291579-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291579-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:09:05.024880
- Run 1: {"ok": true, "session_id": "validator-1777291737-1", "round_number": 1, "quote_id": 41, "requested_amount_wei": "1000000000000000", "used_amount_wei": "1000000000000000", "fallback_applied": false, "tx_hash": "a85b38c4d0c7a99cc6495fefddc27a2b7d6666aadd8ff63e6e766f69414a3a96", "calldata_non_empty": true, "quote_rows": 1, "execution_rows": 1, "analysis_success": false, "analysis_reason": "swap_event_not_found"}
- Run 2: {"ok": true, "session_id": "validator-1777291740-2", "round_number": 2, "quote_id": 43, "requested_amount_wei": "1000000000000000", "used_amount_wei": "100000000000000", "fallback_applied": true, "tx_hash": "401452177ed3367470dcc87b002cbc192da7a9ba3e2f99b89ba4df116457f40e", "calldata_non_empty": true, "quote_rows": 2, "execution_rows": 1, "analysis_success": false, "analysis_reason": "swap_event_not_found"}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291743-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:09:46.816565
- Run 1: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291778-1", "round_number": 1}
- Run 2: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291781-2", "round_number": 2}
- Run 3: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291784-3", "round_number": 3}

## Additional Run
- Date: 2026-04-27T12:10:55.151839
- Run 1: {"ok": true, "session_id": "validator-1777291844-1", "round_number": 1, "quote_id": 65, "requested_amount_wei": "1000000000000000", "used_amount_wei": "1000000000000000", "fallback_applied": false, "tx_hash": "788ec446c74304785fff6b5450932a989660521e55861762b457ff275157406a", "calldata_non_empty": true, "quote_rows": 1, "execution_rows": 1, "analysis_success": false, "analysis_reason": "swap_event_not_found"}
- Run 2: {"ok": true, "session_id": "validator-1777291848-2", "round_number": 2, "quote_id": 67, "requested_amount_wei": "1000000000000000", "used_amount_wei": "100000000000000", "fallback_applied": true, "tx_hash": "261a7919e2d3b12910b4f5d089b12a4f06575026dc897ac589efa3779a4ab57a", "calldata_non_empty": true, "quote_rows": 2, "execution_rows": 1, "analysis_success": false, "analysis_reason": "swap_event_not_found"}
- Run 3: {"ok": true, "session_id": "validator-1777291851-3", "round_number": 3, "quote_id": 70, "requested_amount_wei": "1000000000000000", "used_amount_wei": "50000000000000", "fallback_applied": true, "tx_hash": "a9749c9b79e8a146525c75d7502abda22f0f033435caa8702f0b8c0edf510cfa", "calldata_non_empty": true, "quote_rows": 3, "execution_rows": 1, "analysis_success": false, "analysis_reason": "swap_event_not_found"}
