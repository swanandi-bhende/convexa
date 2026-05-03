# Features

Convexa combines three key features: prediction market mechanics, agentic reasoning, and reliable onchain execution.

## Agentic Debate

Two AI agents (bull and bear) argue opposite positions over a token pair in multiple rounds:

- **Bull Agent** argues the token will increase in value
- **Bear Agent** argues the token will decrease in value
- **Judge Agent** evaluates both arguments each round and scores conviction

Agents use live market data from Uniswap and reasoned LLM-based arguments to make their cases. Debate persists across multiple rounds with escalating conviction scores.

## Onchain Conviction Tracking

The judge's conviction score is recorded onchain in `ConvictionTracker.sol`:

- **Conviction Range:** -100 (fully bearish) to +100 (fully bullish)
- **Update Frequency:** Once per debate round
- **Immutability:** All verdicts recorded onchain for auditability
- **Settlement Trigger:** Winning verdict (conviction > threshold) triggers payout

Conviction tracking enables transparent, auditable judgment divorced from centralized execution.

## Real Swap Execution

When the debate concludes with a verdict, the winning side executes a **real Uniswap swap**:

- **Bull Wins:** Execute long swap (ETH → USDC if bullish)
- **Bear Wins:** Execute short swap (USDC → ETH if bearish)
- **Route Discovery:** Live Uniswap API quote endpoint finds optimal route
- **Atomic Settlement:** KeeperHub ensures swap + escrow release happen together

The winning conviction is not just narrative—it triggers a real market action with provable execution.

## Peer-to-Peer Agent Communication (AXL)

Bull, bear, and judge agents communicate via **AXL network topology**:

- Three local AXL nodes: bull node, bear node, judge node
- Each round, bull and bear publish arguments to judge node
- Judge publishes verdict back to debate orchestrator
- All communication is cryptographically verified and peer-to-peer (no centralized broker)

AXL routing ensures the debate topology is observable and decentralized.

## Staking and Collateral

Users can stake collateral on either side of a debate:

- **Escrow:** Staked collateral locked in `DebateEscrow.sol` until settlement
- **Winning Side Payout:** Staked amount + proportional share of losing side's stake
- **Losing Side Forfeit:** Stake transferred to winning side
- **Settlement Guarantees:** KeeperHub ensures payouts are reliable and auditable

Staking creates real financial incentive alignment between users and agent predictions.

## Settlement Guarantees

**KeeperHub** manages settlement execution with:

- **Job Queue:** Swap jobs submitted as structured KeeperHub jobs
- **Retry Policy:** Automatic retries if network temporary fails
- **Audit Trail:** Settlement recorded in database with job ID and retry history
- **Executor Address:** KeeperHub executor wallet signs and broadcasts the final swap

Without KeeperHub, settlement would be a fragile direct-broadcast problem. With it, users have execution guarantees and transparent audit logs.

## Core System Architecture

```
Bull Agent ─→ (AXL)  \
                      Judge Agent → Conviction Score → KeeperHub → Uniswap → Settlement
Bear Agent ─→ (AXL) /
                     
↓ (Staking)
Debate Escrow (collateral locked)
```

## Summary

| Feature | Benefit |
| --- | --- |
| Agentic Debate | Transparent reasoning, not opaque predictions |
| Onchain Conviction | Immutable verdict, auditable judge decision |
| Real Swap Execution | Narrative backed by market action |
| Peer-to-Peer Communication | Decentralized debate topology |
| Staking | Real financial incentives |
| Reliable Settlement | KeeperHub guarantees execution |
