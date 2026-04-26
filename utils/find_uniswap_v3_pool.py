from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.market_data import discover_pool_for_pair


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover Uniswap V3 pool addresses for a token pair using factory getPool.")
    parser.add_argument("--pair", default="ETH/USDC", help="Token pair label, e.g. ETH/USDC")
    args = parser.parse_args()

    load_dotenv()
    try:
        discovery = discover_pool_for_pair(args.pair)
    except Exception as exc:  # noqa: BLE001 - CLI should return friendly diagnostic output
        print(json.dumps({"pair": args.pair, "error": str(exc)}, indent=2))
        return

    print(json.dumps(discovery, indent=2))
    if discovery.get("selected_pool"):
        print(f"\nSelected pool for {args.pair}: {discovery['selected_pool']} (fee {discovery['selected_fee']})")
    else:
        print(f"\nNo pool exists for {args.pair} on configured network/factory for tested fees.")


if __name__ == "__main__":
    main()
