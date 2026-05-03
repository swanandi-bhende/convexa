# Uniswap Implementation

Uniswap is the market execution layer for Convexa. When a debate concludes with a winning conviction, the system executes a real swap via Uniswap's API and executes the transaction onchain.

## Overview

Without Uniswap, Convexa would produce a narrative winner but no market action. Uniswap integration enables:

- **Live Price Discovery:** Real-time quote for token pair
- **Optimal Route Discovery:** Uniswap routing algorithm finds best swap path
- **Atomic Execution:** Swap calldata generation for single-transaction settlement
- **Proof of Market Action:** Winning argument triggers measurable market change

## Integration Points

### 1. Quote Fetching (`fetch_quote`)

Located in `uniswap/swap_executor.py`:

```python
def fetch_quote(input_token, output_token, amount):
    """Get quote from Uniswap API for token pair."""
    response = requests.get(
        f"{UNISWAP_API_BASE}/quote",
        params={
            "tokenIn": input_token,
            "tokenOut": output_token,
            "amount": amount,
            "slippageTolerance": SLIPPAGE
        }
    )
    return response.json()  # Contains route, amount, price impact
```

**Used For:**
- Market data for agent reasoning (bull/bear arguments)
- Validating swap feasibility before settlement
- Estimating execution price and slippage

### 2. Swap Calldata Generation (`build_swap_calldata`)

```python
def build_swap_calldata(quote_data):
    """Convert quote into swap transaction calldata."""
    response = requests.post(
        f"{UNISWAP_API_BASE}/swap",
        json={
            "quote": quote_data,
            "slippageTolerance": SLIPPAGE,
            "deadline": int(time.time()) + 300
        }
    )
    return response.json()  # Contains to, data, value for swap
```

**Returns:**
- Target contract address
- Encoded transaction calldata
- ETH value to send

### 3. Transaction Broadcast (`broadcast_and_confirm`)

```python
def broadcast_and_confirm(calldata, private_key):
    """Sign and broadcast swap transaction."""
    tx_dict = {
        "to": calldata["to"],
        "data": calldata["data"],
        "value": int(calldata["value"]),
        "gas": 300000,
        "gasPrice": w3.eth.gas_price
    }
    signed_tx = w3.eth.account.sign_transaction(tx_dict, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)
```

**Behavior:**
- Signs with agent wallet key from `.env`
- Broadcasts to Unichain Sepolia RPC
- Waits for transaction confirmation

### 4. Settlement Execution (`execute_final_settlement`)

Called from `agents/orchestrator.py` when judge publishes final verdict:

```python
def execute_final_settlement(winning_side, escrow_contract):
    """Execute swap for winning side, settle escrow."""
    # 1. Fetch quote for winning side's direction
    if winning_side == "BULL":
        quote = fetch_quote(ETH, USDC, stake_amount)
    else:
        quote = fetch_quote(USDC, ETH, stake_amount)
    
    # 2. Build swap calldata
    calldata = build_swap_calldata(quote)
    
    # 3. Broadcast transaction
    tx_receipt = broadcast_and_confirm(calldata, agent_wallet_key)
    
    # 4. Trigger escrow settlement with swap hash
    escrow_contract.functions.settleSide(winning_side).transact({
        "from": keeper_executor_address
    })
    
    return tx_receipt["transactionHash"]
```

## Dry-Run vs Live Mode

### Dry-Run (`--dry-run` flag)

- Fetches real quotes from Uniswap API
- Generates real calldata
- **Does not broadcast** transaction
- Useful for testing logic without cost

### Live Mode

- Fetches quotes, generates calldata, broadcasts transaction
- Requires network access and wallet balance
- Transaction visible onchain

## Error Handling

Uniswap integration handles:

- **Insufficient Liquidity:** Abort if slippage exceeds threshold
- **Route Not Found:** Fall back to direct pair swap
- **Network Timeout:** Retry quote fetch with exponential backoff
- **Broadcast Failure:** Log transaction hash, monitor for confirmation

## Configuration

Environment variables control Uniswap behavior:

```
UNISWAP_API_KEY=          # API authentication
UNISWAP_API_BASE=         # API endpoint
UNISWAP_V3_POOL_FEES=     # Fee tiers to consider (500, 3000, 10000)
UNISWAP_V3_POOL_ETH_USDC= # Specific pool address
LARGE_SWAP_USD_THRESHOLD= # Trigger special routing for large swaps
SLIPPAGE_TOLERANCE=       # Max slippage % before abort
```

## Performance

- **Quote Fetch:** 200-500ms
- **Calldata Generation:** 100-300ms
- **Transaction Broadcast:** 1-2s
- **Confirmation Wait:** 3-8s (Sepolia)

Total end-to-end swap execution: **5-15 seconds**

## Testing

Run swap simulation:

```bash
python uniswap/demo_swap.py --token ETH --amount 1.0
```

This fetches real quotes and calldata without broadcasting.

## Why Uniswap?

Uniswap provides:
1. Deep liquidity across token pairs
2. Standard interface for quote and swap
3. Optimal routing algorithm (saves users money)
4. Proven smart contract security
5. Real market prices agents can trust

Without Uniswap, settlement would either require a mock market (losing reality) or a centralized exchange (losing decentralization). Uniswap provides the bridge between debate narrative and market action.
