# Convexa

Convexa is an onchain debate market where two AI agents argue opposite positions on a token, back their conviction with real staked liquidity, and trigger automated Uniswap swaps while KeeperHub ensures reliable settlement and AXL keeps the debate peer-to-peer.

Prediction markets can price belief but hide reasoning. AI agents can reason but usually operate without real counterparties or dispute resolution. Convexa fuses both: bull and bear agents argue over live market data via AXL, the judge records conviction scores onchain, and the winning side executes a real swap with atomic settlement.

## Quick Start

**Prerequisites:** Node 18+, Python 3.10+, AXL binary at `axl-nodes/axl`

```bash
git clone <repo-url> convexa && cd convexa
./setup.sh
python orchestrator.py --token ETH --duration 5rounds --dry-run
```

## Documentation

- **[Setup.md](docs/Setup.md)** – Environment setup, dependencies, wallet configuration, contract deployment
- **[Demo.md](docs/Demo.md)** – Interactive walkthrough and demo scenarios
- **[Features.md](docs/Features.md)** – Core system capabilities and mechanics
- **[Uniswap_Implementation.md](docs/Uniswap_Implementation.md)** – Swap execution, quote handling, settlement integration
- **[KeeperHub_Implementation.md](docs/KeeperHub_Implementation.md)** – Job queue orchestration, retry policy, execution guarantees
- **[AXL_Implementation.md](docs/AXL_Implementation.md)** – Peer-to-peer messaging, node topology, debate routing
- **[Security.md](docs/Security.md)** – Audit findings, contract analysis, risk mitigation
- **[Tests.md](docs/Tests.md)** – Test suite, scenarios, performance benchmarks
- **[Troubleshooting.md](docs/Troubleshooting.md)** – Common issues and solutions

## Deployed Contracts

| Contract | Address | Network | Explorer |
| --- | --- | --- | --- |
| DebateEscrow | `0x9034105e9C469Be8f8A6ea3115C39F9D8dd45e7b` | Unichain Sepolia | [View](https://unichain-sepolia.blockscout.com/address/0x9034105e9C469Be8f8A6ea3115C39F9D8dd45e7b#code) |
| ConvictionTracker | `0x01Dd5eB506d1B760e0EB8962628186be44B152Fe` | Unichain Sepolia | [View](https://unichain-sepolia.blockscout.com/address/0x01Dd5eB506d1B760e0EB8962628186be44B152Fe#code) |

## Project Structure

```
convexa/
├── agents/            Agent logic, judge, memory, orchestrator
├── axl-nodes/         AXL binary, node configs, local infrastructure
├── contracts/         Solidity contracts, Hardhat project, ABIs
├── frontend/          Next.js UI for demonstration
├── keeper/            KeeperHub integration, job submission, polling
├── scripts/           Utility scripts and simulations
├── tests/             Integration, unit, stress, security tests
├── uniswap/           Quote, swap execution, settlement logic
└── utils/             Shared constants, database, market data, risk
```

## License

GPL-3.0 – See LICENSE for details.
