# Security

Convexa has undergone formal security analysis using industry-standard tools. This document summarizes findings and mitigations.

## Audit Summary

**Date:** May 3, 2026  
**Scope:** DebateEscrow.sol, ConvictionTracker.sol  
**Tools:** Slither v0.11.5, TruffleHog, pip-audit, npm audit  
**Status:** All critical and high-severity issues FIXED

## Key Findings

### Reentrancy Vulnerability (FIXED)

**Issue:** DebateEscrow.settleSide() transferred ETH before updating state, enabling reentrancy attacks.

**Mitigation:** Implemented Checks-Effects-Interactions (CEI) pattern:
1. Check all conditions upfront
2. Update all state variables BEFORE external calls
3. Make external calls last

**Code:**
```solidity
// EFFECTS: Update state first
debateActive = false;
userStakes[staker][Side.BULL] = 0;
userStakes[staker][Side.BEAR] = 0;

// INTERACT: External calls last
(bool sent, ) = payable(staker).call{value: payout}("");
```

**Status:** ✓ Fixed and verified

### Zero-Address Validation (FIXED)

**Issue:** Constructor and setter functions didn't validate address parameters.

**Mitigation:** Added explicit zero-address checks:
```solidity
require(_settlementExecutor != address(0), "Invalid executor");
require(newJudgeAgent != address(0), "Invalid judge");
```

**Status:** ✓ Fixed

### Input Validation on Conviction Scores (FIXED)

**Issue:** Judge could set conviction scores outside valid range (-100 to +100).

**Mitigation:** Added range validation:
```solidity
require(conviction >= -100 && conviction <= 100, "Invalid conviction");
```

**Status:** ✓ Fixed

## Access Control

Both contracts use role-based access control:

| Function | Access Control | Risk |
| --- | --- | --- |
| settleSide() | Only executor | Trusted KeeperHub executor |
| recordVerdict() | Only judge agent | Trusted judge agent address |
| updateJudgeAgent() | Only owner | Trusted deployer |

All critical functions require explicit permissions. Unauthorized calls revert.

## Token Handling

### Ether Safeguards

- Staked ETH locked in contract until settlement
- Settlement transfers happen in CEI pattern
- Re-entrancy guards via state updates before calls

### Approved Tokens

- Only ETH accepted for staking (no ERC20 complexity)
- Uniswap integration uses production-grade token routing

## Contract Verification

Both contracts verified onchain:

- **DebateEscrow:** [Blockscout](https://unichain-sepolia.blockscout.com/address/0x9034105e9C469Be8f8A6ea3115C39F9D8dd45e7b#code)
- **ConvictionTracker:** [Blockscout](https://unichain-sepolia.blockscout.com/address/0x01Dd5eB506d1B760e0EB8962628186be44B152Fe#code)

Source code matches deployed bytecode.

## Dependency Audits

### Python Dependencies

Run audit:
```bash
pip-audit
```

All dependencies pinned to specific versions. No known vulnerabilities in locked set.

### Node Dependencies

Run audit:
```bash
cd contracts && npm audit
```

No high-severity vulnerabilities. Some medium-severity advisories for optional dev dependencies.

## Operational Security

### Private Key Management

- `DEPLOYER_PRIVATE_KEY`: Used only for contract deployment (once)
- `AGENT_WALLET_PRIVATE_KEY`: Used only for settlement transactions (KeeperHub executor)
- Never hardcoded; loaded from `.env`

### API Key Management

- All keys loaded from `.env` at runtime
- `.env` excluded from version control (`.gitignore`)
- Testnet-only keys (no mainnet credentials in repo)

### Credential Scanning

Scan repository for exposed secrets:
```bash
trufflehog filesystem . --debug
```

Result: No credentials found in committed files.

## Testing

### Unit Tests

Test critical security functions:
```bash
cd contracts && npx hardhat test
```

### Integration Tests

Test end-to-end security:
```bash
pytest tests/security/
```

Tests cover:
- Reentrancy prevention
- Access control enforcement
- Input validation
- Token handling

## Known Limitations

1. **Testnet Only:** Contracts deployed on Unichain Sepolia testnet. Not audited for mainnet use.

2. **Agent Trust:** System assumes judge agent (Groq LLM) produces honest verdicts. Judge agent is controlled by system operator.

3. **KeeperHub Trust:** System assumes KeeperHub executor is trusted to broadcast transactions fairly.

4. **Oracle Risk:** Market data from Uniswap API trusted as-is (no price oracle). Large price movements could cause unexpected slippage.

## Security Checklist

✓ Reentrancy protection (CEI pattern)  
✓ Zero-address validation  
✓ Input validation (conviction range)  
✓ Access control (role-based)  
✓ Token handling (only ETH, no ERC20)  
✓ Private key not hardcoded  
✓ No exposed secrets in repo  
✓ Dependencies audited  
✓ Contracts verified onchain  
✓ Tests pass (unit + integration)

## Reporting Security Issues

If you discover a security issue:

1. **Do not** open a public issue on GitHub
2. Email security concerns to the maintainers
3. Provide reproduction steps if possible
4. Allow time for remediation before public disclosure

## References

- [Checks-Effects-Interactions Pattern](https://docs.soliditylang.org/en/latest/security-considerations.html#re-entrancy)
- [Slither Documentation](https://github.com/crytic/slither)
- [OpenZeppelin Security](https://docs.openzeppelin.com/contracts/)
