# Tests

Convexa includes comprehensive unit, integration, and stress tests to validate correctness and performance.

## Test Structure

```
tests/
├── unit/                    Unit tests for individual modules
├── security/                Security-specific test suite
├── integration_test.py      End-to-end debate flow
├── stress_test.py           Performance and load testing
└── fixtures/                Test data and mock configurations
```

## Running Tests

### All Tests

```bash
pytest tests/ -v
```

Runs all test suites and reports pass/fail per test.

### Unit Tests Only

```bash
pytest tests/unit/ -v
```

Tests individual modules in isolation (agents, uniswap, keeper, etc.).

### Integration Tests

```bash
pytest tests/integration_test.py -v
```

Tests complete end-to-end debate flow:
1. Deploy contracts
2. Initialize agents
3. Run full debate cycle
4. Verify settlement

### Security Tests

```bash
pytest tests/security/ -v
```

Tests security properties:
- Reentrancy prevention
- Access control enforcement
- Input validation

### Stress Tests

```bash
pytest tests/stress_test.py -v --timeout=300
```

Tests performance under load:
- Multiple concurrent debates
- Large stake amounts
- High message volume (AXL)
- Long debate durations

## Test Categories

### Unit Tests (Fast)

Test individual functions in isolation:

```bash
# Agent reasoning
pytest tests/unit/test_agent_reasoning.py -v

# Market data fetching
pytest tests/unit/test_market_data.py -v

# Keeper submission
pytest tests/unit/test_keeper_submission.py -v

# Uniswap quote
pytest tests/unit/test_uniswap_quote.py -v
```

**Expected:** All pass within seconds

### Integration Tests (Medium)

Test components working together:

```bash
# Full debate flow
pytest tests/integration_test.py::test_full_debate_flow -v

# Settlement end-to-end
pytest tests/integration_test.py::test_settlement_with_swap -v
```

**Expected:** All pass within 30 seconds

### Security Tests (Medium)

Test for known vulnerabilities:

```bash
# Reentrancy guard
pytest tests/security/test_reentrancy.py -v

# Access control
pytest tests/security/test_access_control.py -v
```

**Expected:** All pass, confirming fixes are in place

### Stress Tests (Slow)

Test performance at scale:

```bash
# 10 concurrent debates
pytest tests/stress_test.py::test_concurrent_debates -v --timeout=300

# Long debate (50 rounds)
pytest tests/stress_test.py::test_long_debate -v --timeout=300

# High message volume
pytest tests/stress_test.py::test_high_message_volume -v --timeout=300
```

**Expected:** Baseline performance within historical range (see [STRESS_TEST_REPORT.md](./STRESS_TEST_REPORT.md))

## Test Coverage

Generate coverage report:

```bash
pytest tests/ --cov=agents --cov=keeper --cov=uniswap --cov-report=html
```

Opens `htmlcov/index.html` with line-by-line coverage.

Target: >80% coverage on critical paths

## Test Configuration

### Fixtures

Reusable test data in `tests/fixtures/`:

```python
# Mock agent response
from tests.fixtures.agent_responses import mock_bull_argument

# Mock market data
from tests.fixtures.market_data import mock_eth_usdc_quote

# Mock contract state
from tests.fixtures.contracts import deployed_escrow
```

### Environment Variables

Tests use `.env.test` (separate from `.env`):

```bash
GROQ_API_KEY=test-key-xxx
ALCHEMY_RPC_URL=http://localhost:8545  # Local fork
KEEPERHUB_API_KEY=test-key-yyy
```

Load in tests:

```python
from tests.conftest import load_test_env
env = load_test_env()
```

## Continuous Integration

Tests run on every push (GitHub Actions):

```yaml
# .github/workflows/test.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Debugging Test Failures

### Verbose Output

```bash
pytest tests/test_file.py::test_name -vv --tb=short
```

Shows detailed assertion errors and stack traces.

### Single Test

```bash
pytest tests/test_file.py::test_name -v
```

Runs one test in isolation.

### Keep State Between Tests

```bash
pytest tests/ -v --no-cleanup
```

Leaves contracts deployed and database intact for inspection.

## Common Test Failures

### Issue: "Insufficient Balance"

**Cause:** Test wallet has no testnet ETH  
**Fix:** Fund test wallet from Unichain Sepolia faucet

```bash
curl -X POST https://faucet.unichain-sepolia.com \
  -d '{"address":"0x...your-test-wallet..."}'
```

### Issue: "AXL Node Timeout"

**Cause:** AXL binary not executable  
**Fix:** Make binary executable

```bash
chmod +x axl-nodes/axl
```

### Issue: "GROQ_API_KEY Missing"

**Cause:** `.env.test` not configured  
**Fix:** Copy and fill in `.env.test`

```bash
cp .env.example .env.test
# Edit .env.test with test keys
```

### Issue: "Hardhat Network Fork Failed"

**Cause:** RPC endpoint unresponsive  
**Fix:** Use different RPC or local fork

```bash
# Local fork
npx hardhat node

# Different RPC
ALCHEMY_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/your_key pytest
```

## Performance Benchmarks

Target performance per test category:

| Test Type | Count | Target Time | Status |
| --- | --- | --- | --- |
| Unit | 50+ | <10s | ✓ Pass |
| Integration | 10+ | <30s | ✓ Pass |
| Security | 15+ | <20s | ✓ Pass |
| Stress (baseline) | 5+ | <5min | ✓ Pass |

See [STRESS_TEST_REPORT.md](./STRESS_TEST_REPORT.md) for detailed performance metrics.

## Adding New Tests

### Template for Unit Test

```python
# tests/unit/test_my_feature.py
import pytest
from my_module import my_function

def test_my_function_happy_path():
    """Test normal operation."""
    result = my_function(input_value)
    assert result == expected_value

def test_my_function_error_case():
    """Test error handling."""
    with pytest.raises(ValueError):
        my_function(invalid_input)
```

### Template for Integration Test

```python
# tests/integration_test.py
@pytest.mark.integration
def test_my_integration():
    """Test component interaction."""
    # Setup
    agent = initialize_agent()
    contract = deploy_contract()
    
    # Action
    result = agent.reason_and_act()
    
    # Assert
    assert contract.verify_action(result)
```

## Test Documentation

See [TEST_RESULTS.md](./TEST_RESULTS.md) for latest run results and [STRESS_TEST_PROTOCOL.md](./STRESS_TEST_PROTOCOL.md) for stress test methodology.
