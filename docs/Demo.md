# Demo Guide

This guide walks through running a live debate with the Convexa system, demonstrating agent reasoning, onchain conviction scoring, and settlement.

## Prerequisites

1. Setup complete (see [Setup.md](Setup.md))
2. `.env` configured with API keys
3. Testnet wallet funded with ETH (Unichain Sepolia faucet)

## Quick Demo (3 minutes)

```bash
# Terminal 1: Start orchestrator
source venv/bin/activate
python orchestrator.py --token ETH --duration 5rounds --dry-run
```

This runs a complete debate cycle:
1. Spins up 3 local AXL nodes (bull, bear, judge)
2. Bull and bear argue over ETH/USDC
3. Judge scores each round and writes conviction onchain
4. Settlement processes and winners are paid
5. Nodes shut down cleanly

**Expected output:**
- Round numbers incrementing
- Bull/bear argument updates every ~6-12 seconds
- Conviction scores changing
- Final settlement transaction hash

## Full Demo with Onchain Settlement

```bash
python orchestrator.py --token ETH --duration 3rounds
```

**Note:** Requires network access and sufficient wallet balance.

### Demo Flow

| Step | Duration | What Happens |
| --- | --- | --- |
| Setup | 5s | AXL nodes start, agents initialize |
| Round 1 | 30s | Bull and bear exchange arguments |
| Judge Scoring | 10s | Judge evaluates and writes verdict onchain |
| Round 2 | 30s | Debate continues, conviction updates |
| Round 3 | 30s | Final round, judge submits final verdict |
| Settlement | 15s | Winner side executes swap via Uniswap and KeeperHub |
| Payout | 10s | Stakers receive payouts, debate escrow settles |

## Observing the Debate

### Local Logs

Check debate progress:
```bash
tail -f data/logs/debate_*.log
```

### Agent Communication (AXL)

Each agent publishes round arguments via AXL:
- Bull Agent: `agents/bull_agent.py` → `publish_to_judge()`
- Bear Agent: `agents/bear_agent.py` → `publish_to_judge()`
- Judge Agent: `agents/judge_agent.py` → scores and publishes verdict

AXL nodes route messages peer-to-peer between agents.

### Onchain Verification

Watch contract events:
```bash
# Conviction Tracker contract
eth_getLogs(ConvictionTracker, "VerdictRecorded")

# Debate Escrow contract
eth_getLogs(DebateEscrow, "SettlementExecuted")
```

## Demo Scenarios

### Scenario 1: Bull Dominates (ETH Bullish)

The bull agent produces stronger arguments. Conviction score trends positive. Bull side wins and executes a long swap (ETH → USDC).

### Scenario 2: Bear Dominates (ETH Bearish)

The bear agent produces stronger arguments. Conviction trends negative. Bear side wins and executes a short swap (USDC → ETH).

### Scenario 3: Tied Debate

Both agents produce equally strong arguments. Conviction oscillates. Debate may require tiebreaker logic (or settle at neutral payout split).

## Dry-Run vs Live Mode

| Aspect | Dry-Run | Live |
| --- | --- | --- |
| AXL Nodes | Local, in-process | Local, spawned processes |
| Network | None | Requires RPC + KeeperHub |
| Transactions | Simulated | Real onchain execution |
| Settlement | Mock payout | Real swap + escrow release |
| Speed | Fast (debug logs) | Real network latency |

Use dry-run for testing and demos without cost. Use live for validation and proof of execution.

## Monitoring Agent Reasoning

View agent prompts and responses:

```bash
# Bull arguments
cat agents/prompts/bull_system_prompt_v1.txt

# Judge verdict logic
cat agents/prompts/judge_system_prompt_v1.txt

# Raw agent conversation logs
tail -f data/logs/bull_agent.log
tail -f data/logs/bear_agent.log
tail -f data/logs/judge_agent.log
```

## Troubleshooting Demo Issues

**Issue:** Demo hangs or exits early  
→ Check `.env` has all required keys. Run `python orchestrator.py --token ETH --duration 5rounds --dry-run` first.

**Issue:** AXL nodes fail to start  
→ Verify `axl-nodes/axl` is executable: `chmod +x axl-nodes/axl`

**Issue:** Agent communication fails  
→ Check AXL node logs in `axl-nodes/*/logs/` for errors

**Issue:** Settlement transaction fails  
→ Check KeeperHub API key and wallet balance

See [Troubleshooting.md](Troubleshooting.md) for more help.
