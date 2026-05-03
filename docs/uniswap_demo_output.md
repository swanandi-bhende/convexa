# Uniswap Demo Output (dry-run)

This file contains the captured dry-run outputs produced by `python3 uniswap/demo_swap.py` for the demo video.

## Quote (dry-run)

{
  "success": true,
  "reason": null,
  "quote_id": 37,
  "session_id": "demo-session",
  "round_number": 0,
  "swap_type": "micro_settlement",
  "token_in": "0x4200000000000000000000000000000000000006",
  "token_out": "0x31d0220469e10c4E71834a79b1f276d740d3768F",
  "amount_in_wei": "10000000000000000",
  "quoted_amount_out_wei": "9700000000000000",
  "quoted_price": 0.97,
  "route_description": "dry_run_simulated_route",
  "gas_estimate_wei": "0",
  "slippage_tolerance_percent": 0.5
}

## Swap Calldata (dry-run)

{
  "success": true,
  "reason": null,
  "quote_id": 37,
  "calldata": "0xdeadbeef00000025",
  "value_wei": "0",
  "gas_limit": "250000",
  "gas_price_wei": "0",
  "deadline_unix": 1777788269
}

## Notes

- The broadcast step attempted to run the dry-run adapter which raised a `DetachedInstanceError` in our environment for some sequences; however the quote and calldata above are valid demo artifacts and safe to include in the demo video.
- For a fully successful dry-run including simulated tx hash, run `python3 uniswap/demo_swap.py` again after pulling latest changes; the script prints the outputs to stdout and they're also saved in `uniswap/demo_output.json` when executed.
