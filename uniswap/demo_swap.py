#!/usr/bin/env python3
"""Simple Uniswap demo that uses the project's swap_executor in DRY_RUN mode.

Usage: python3 uniswap/demo_swap.py

This script intentionally uses dry-run paths so it is safe to run during the demo.
"""
from __future__ import annotations

import os
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from uniswap import swap_executor


def main() -> None:
    # Ensure dry-run so we do not broadcast real transactions during demo
    swap_executor.set_dry_run(True)
    try:
        swap_executor.init_database()
    except Exception:
        pass

    # Use addresses from env when available, otherwise token symbols
    token_in = os.getenv("WETH_ADDRESS", "ETH")
    token_out = os.getenv("USDC_ADDRESS", "USDC")

    # Amount: 0.01 ETH in wei
    amount_wei = str(10 ** 16)

    print("Requesting quote (dry-run)...")
    quote = swap_executor.fetch_quote(
        token_in=token_in,
        token_out=token_out,
        amount_in_wei=amount_wei,
        swap_type="micro_settlement",
        session_id="demo-session",
        round_number=0,
    )
    print("Quote result:")
    try:
        print(json.dumps(quote.__dict__, default=str, indent=2))
    except Exception:
        print(quote)

    print("Building swap calldata...")
    calldata = swap_executor.build_swap_calldata(quote)
    try:
        print(json.dumps(calldata.__dict__, default=str, indent=2))
    except Exception:
        print(calldata)

    print("Broadcast (dry-run)...")
    broadcast = swap_executor.broadcast_and_confirm(calldata, "demo-session", 0, "micro_settlement")
    try:
        print(json.dumps(broadcast.__dict__, default=str, indent=2))
    except Exception:
        print(broadcast)


if __name__ == "__main__":
    main()
