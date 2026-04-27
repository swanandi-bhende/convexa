from __future__ import annotations

import os

# Native token placeholder used by the Uniswap trading API for ETH-like native assets.
NATIVE_TOKEN_ADDRESS = "0x0000000000000000000000000000000000000000"

TARGET_CHAIN_ID = int(os.getenv("SWAP_CHAIN_ID", "1301"))

DEFAULT_TOKEN_ADDRESS_BY_CHAIN: dict[int, dict[str, str]] = {
    1301: {
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x31d0220469e10c4E71834a79b1f276d740d3768F",
    }
}

# Universal Router address map for supported target chains.
UNISWAP_UNIVERSAL_ROUTER_BY_CHAIN: dict[int, str] = {
    1: "0x66a9893cc07d91d95644aedd05d03f95e1dba8af",
    1301: "0xf70536b3bcc1bd1a972dc186a2cf84cc6da6be5d",
    11155111: "0x3a9d48ab9751398bbfa63ad67599bb04e4bdf98b",
}

# Symbol-to-address map for the target network. Addresses can be overridden via .env.
TOKEN_ADDRESS_BY_SYMBOL: dict[int, dict[str, str]] = {
    TARGET_CHAIN_ID: {
        "ETH": NATIVE_TOKEN_ADDRESS,
        "WETH": os.getenv(
            "WETH_ADDRESS",
            DEFAULT_TOKEN_ADDRESS_BY_CHAIN.get(TARGET_CHAIN_ID, {}).get("WETH", ""),
        ),
        "USDC": os.getenv(
            "USDC_ADDRESS",
            DEFAULT_TOKEN_ADDRESS_BY_CHAIN.get(TARGET_CHAIN_ID, {}).get("USDC", ""),
        ),
    }
}

TOKEN_DECIMALS_BY_SYMBOL: dict[str, int] = {
    "ETH": 18,
    "WETH": 18,
    "USDC": 6,
}

# Debate-side token symbols, configurable from environment.
BULL_SIDE_TOKEN_SYMBOL = os.getenv("BULL_SIDE_TOKEN_SYMBOL", "USDC").upper()
BEAR_SIDE_TOKEN_SYMBOL = os.getenv("BEAR_SIDE_TOKEN_SYMBOL", "ETH").upper()


def resolve_token_address(token: str, chain_id: int | None = None) -> str:
    """Resolve a token symbol or return the input if it is already an address."""
    candidate = token.strip()
    if candidate.startswith("0x") and len(candidate) == 42:
        return candidate

    chain = chain_id if chain_id is not None else TARGET_CHAIN_ID
    symbol_map = TOKEN_ADDRESS_BY_SYMBOL.get(chain, {})
    resolved = symbol_map.get(candidate.upper(), "")
    if not resolved:
        raise ValueError(f"Unsupported token symbol for chain {chain}: {token}")
    return resolved


def get_universal_router_address(chain_id: int | None = None) -> str:
    """Return Universal Router address for a chain, overridable by env."""
    target_chain = chain_id if chain_id is not None else TARGET_CHAIN_ID
    override = os.getenv("UNISWAP_UNIVERSAL_ROUTER_ADDRESS", "").strip()
    if override:
        return override

    address = UNISWAP_UNIVERSAL_ROUTER_BY_CHAIN.get(target_chain, "")
    if not address:
        raise ValueError(f"No Universal Router address configured for chain {target_chain}")
    return address


def resolve_token_decimals(token: str) -> int:
    """Resolve decimals by symbol with conservative default for unknown symbols."""
    return TOKEN_DECIMALS_BY_SYMBOL.get(token.upper(), 18)
