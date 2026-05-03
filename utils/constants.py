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


# Metric sentiment polarity map: defines which side each metric naturally supports
# This prevents metric overlap by explicitly assigning sentiment direction to each metric
METRIC_SENTIMENT_MAP: dict[str, str] = {
    # Directional metrics: both agents can cite but must interpret in their favor
    "price_change_24h_percent": "directional",
    "price_change_2h_percent": "directional",
    "volume_delta_percent": "directional",
    "funding_rate_proxy": "directional",
    "lp_net_flow_usd": "directional",
    
    # Bullish-primary metrics: belong primarily to Bull's argument
    "large_inflow_count": "bullish_primary",
    "recent_lp_additions_usd": "bullish_primary",
    "net_wallet_flow_count": "bullish_primary",
    
    # Bearish-primary metrics: belong primarily to Bear's argument
    "large_outflow_count": "bearish_primary",
    "recent_lp_removals_usd": "bearish_primary",
}

# AXL Node Identities: peer IDs and public keys for message validation
# These are loaded from environment with fallback defaults for testing/demo
AXL_NODE_PEER_IDS: dict[str, str] = {
    "bull": os.getenv(
        "BULL_AXL_PEER_ID",
        "12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL8"  # Demo default
    ),
    "bear": os.getenv(
        "BEAR_AXL_PEER_ID",
        "12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL9"  # Demo default
    ),
    "judge": os.getenv(
        "JUDGE_AXL_PEER_ID",
        "12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL7"  # Demo default
    ),
}

# AXL Node Public Keys: used for cryptographic signature validation
# In production, these should be loaded from a secure configuration or service
AXL_NODE_PUBLIC_KEYS: dict[str, str] = {
    "bull": os.getenv(
        "BULL_AXL_PUBLIC_KEY",
        ""  # Should be set in production
    ),
    "bear": os.getenv(
        "BEAR_AXL_PUBLIC_KEY",
        ""  # Should be set in production
    ),
    "judge": os.getenv(
        "JUDGE_AXL_PUBLIC_KEY",
        ""  # Should be set in production
    ),
}
