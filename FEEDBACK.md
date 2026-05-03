# Uniswap Integration Feedback

## Run Metadata
- Date: 2026-04-27T03:04:16.905992
- Chain: 1301
- API Base: https://trade-api.gateway.uniswap.org/v1
- DRY_RUN: True

## What Worked Well
- The quote payload exposes `quote.route`, `quote.routeString`, and `quote.output.amount`, which made it easy to render routing information in the frontend and still fall back cleanly when the route was empty in dry-run or liquidity-starved cases.
- The integration code could keep one flow for quote, calldata, and broadcast: `fetch_quote()` in `uniswap/swap_executor.py` returns a stable `QuoteResult`, `build_swap_calldata()` turns that into a `SwapCalldata`, and `broadcast_and_confirm()` reuses the same quote object for the final execution step.
- When `permitData` is absent, the swap path still works because the request builder only attaches `permitData` and `signature` when both are present. That kept the demo path simple and avoided special-case branches in the UI.
- The `swap.data`, `swap.value`, `swap.gasLimit`, and `swap.gasPrice` fields were enough to show the user exactly what would be broadcast before sending anything onchain.

## Bugs and Unexpected Behaviors
- On 2026-04-27T11:18:55.297427, using an invalid dashboard key produced `unauthorized_api_key` during quote generation.
  - Repro: call `fetch_quote()` with `tokenIn=0x4200000000000000000000000000000000000006`, `tokenOut=0x31d0220469e10c4E71834a79b1f276d740d3768F`, `amount=1000000000000000`, `type=EXACT_INPUT`, `tokenInChainId=1301`, `tokenOutChainId=1301`, and a bad `UNISWAP_API_KEY`.
  - Unexpected response: the validator surfaced a hard authorization failure instead of a softer quota or environment diagnostic.
  - Impact: the app cannot infer whether the issue is a bad key, a plan restriction, or a temporary platform outage.

- On 2026-04-27T12:00:52.182209, a quote that was still usable locally became too old by the time `build_swap_calldata()` retried it and returned `quote_near_expiry_refresh_required`.
  - Repro: request a small exact-input quote, wait until it is near the refresh threshold, then call the calldata builder.
  - Unexpected response: the code had to refresh the quote, and if the refresh hit `no_liquidity`, the entire path failed even though the earlier quote was valid enough to preview.
  - Impact: quote freshness is operationally important but not obvious to a user in the UI.

- Several test runs returned `no_liquidity` for the same low-value ETH/USDC path on Unichain Sepolia even when the request parameters were valid.
  - Repro: repeat the exact quote call above with a valid key and the same 1e15 wei size.
  - Unexpected response: the API often failed at quote time rather than returning a degraded route suggestion or a clearer liquidity explanation.

## Documentation Gaps
- The public docs at https://developers.uniswap.org/ and https://github.com/Uniswap/uniswap-ai do not show enough concrete examples of `route` shapes for the cases we hit in practice: empty route arrays, nested route arrays, and fallback responses.
- The docs do not clearly contrast `/quote` responses with and without `permitData`, which made the swap request builder more defensive than it should have been.
- Plan limits and rate-limit behavior are not published clearly enough for automated builds. The difference between a bad API key, a throttled key, and a genuine liquidity failure is not obvious from the docs alone.
- There is no clear sandbox example that shows a full quote -> calldata -> dry-run broadcast loop without onchain submission.

## DX Friction Points
- The API base had to be normalized to `https://trade-api.gateway.uniswap.org/v1`, while the environment also exposed `https://api.uniswap.org/v1`. That ambiguity slowed initial wiring because the two forms were not interchangeable in practice.
- Error handling had to branch on HTTP failures, missing route data, missing calldata, and quote expiry, which made the integration code larger than expected for a simple swap flow.
- The frontend could not rely on a single response shape for all quote scenarios, so the parsing layer had to special-case `route`, `routeString`, `permitData`, and the `swap` object separately.

## Feature Requests
- A documented sandbox endpoint that returns full `swap` calldata and a synthetic receipt would make frontends much easier to build and test.
- A quote validation endpoint, such as `POST /quote/validate`, would help us check freshness before constructing calldata.
- A compact response schema that always includes an explicit `reason` field for failures like low liquidity, key rejection, and quote expiry would make agent workflows easier to debug.

## Reference Payload
```json
{
  "tokenIn": "0x4200000000000000000000000000000000000006",
  "tokenOut": "0x31d0220469e10c4E71834a79b1f276d740d3768F",
  "amount": "1000000000000000",
  "type": "EXACT_INPUT",
  "tokenInChainId": 1301,
  "tokenOutChainId": 1301,
  "swapper": "0xd182af8155f1D4E2A05A4aA811A2056d1b961960",
  "slippageTolerance": 0.5
}
```
## Additional Run

- Date: 2026-04-27T12:06:20.419435

- Run 1: {"ok": false, "stage": "quote", "reason": "no_liquidity", "session_id": "validator-1777291577-1", "round_number": 1}
