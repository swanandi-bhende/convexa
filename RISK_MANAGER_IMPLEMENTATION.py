#!/usr/bin/env python3
"""
CONVEXA RISK MANAGER - IMPLEMENTATION COMPLETE
Complete overview of all risk management safety checkpoints and integration.

Date: April 28, 2026
Status: ✅ FULLY IMPLEMENTED AND VERIFIED
"""

# ============================================================================
# PART 13: RISK MANAGEMENT AND DEBATE SAFETY MODULE
# ============================================================================

"""
OVERVIEW:
The Risk Manager is an active gatekeeper that sits between the orchestrator
and all other system components. It has veto power over debate progression
at four critical checkpoints:

  1. PRE-ROUND (setup_round):
     - check_data_freshness(): Ensure market data is fresh (< 2 minutes old)
     - check_minimum_stakes(): Verify both sides have minimum stake

  2. POST-VERDICT (run_judging):
     - check_conviction_drift(): Detect suspicious score movements (>15 points)
     - validate_axl_message(): Verify AXL message signatures

  3. POST-CONVICTION-UPDATE (check_end_conditions):
     - check_debate_timeout(): Enforce maximum round limit (20 rounds)
     - evaluate_draw_conditions(): Classify timeout-based endings

  4. PRE-SWAP (execute_micro_settlement in swap_executor.py):
     - check_gas_conditions(): Monitor gas prices and delay/skip swaps

Every checkpoint returns a RiskDecision with action: PROCEED, PAUSE, HALT,
SKIP_ROUND, REQUIRE_EXTENDED_REASONING, DELAY_SWAP, or SKIP_SWAP.
"""

# ============================================================================
# IMPLEMENTATION CHECKLIST (13.1 - 13.10)
# ============================================================================

"""
✅ 13.1  ARCHITECTURAL UNDERSTANDING
    - Risk Manager as active gatekeeper (not passive logger)
    - Veto power over round start, verdict acceptance, debate continuation
    - Four checkpoint architecture clearly established
    - Decision tree: PROCEED/PAUSE/HALT at each checkpoint

✅ 13.2  DATABASE SCHEMA ADDITIONS
    Tables added to /utils/db/schema.py:
    
    SafetyEvent:
      - id, session_id, round_number, event_type, severity
      - details_json, action_taken, resolved_at, timestamp
      - Event types: stale_data, conviction_drift, low_stake, debate_timeout,
                     invalid_axl_signature, gas_spike, data_source_failure
    
    ConvictionHistory:
      - id, session_id, round_number, bull_score, bear_score
      - delta_from_previous_bull, delta_from_previous_bear
      - drift_flagged, timestamp
    
    AXLMessageAudit:
      - id, session_id, round_number, sender_claimed
      - sender_peer_id, message_hash, signature_present, signature_valid
      - accepted, timestamp
    
    GasPriceHistory:
      - id, session_id, gas_price_gwei, timestamp

✅ 13.3  RISKMANAGER CLASS SKELETON
    Location: /utils/risk_manager.py
    
    Class: RiskManager
    __init__(session_id, db_url, web3_provider_url)
    
    Configuration Loaded from Environment (with defaults):
      - MAX_DATA_AGE_SECONDS: 120
      - MAX_CONVICTION_DRIFT_PER_ROUND: 15
      - MIN_STAKE_EACH_SIDE_ETH: 0.001
      - MAX_DEBATE_ROUNDS: 20
      - GAS_SPIKE_THRESHOLD_PERCENT: 30
      - EXTENDED_REASONING_REQUIRED_DRIFT: 12
    
    Helper Method:
      - _log_safety_event(): Log to DB + print with visual indicators
        (⚠️ warning, ⏸️ pause, 🚨 halt)

✅ 13.4  STALE DATA GUARD
    Function: check_data_freshness(market_snapshot, round_number)
    
    Behavior:
      - If data_freshness_seconds < MAX_DATA_AGE_SECONDS: PROCEED
      - If stale: Enter wait loop (4 attempts × 15s = 60s max wait)
      - Log "pause" severity event with action "waiting_for_fresh_data"
      - If still stale after 60s: SKIP_ROUND (log "halt" severity event)
      - Orchestrator handles SKIP_ROUND by incrementing round counter
    
    Returns: RiskDecision(action=PROCEED|SKIP_ROUND, reason, context)

✅ 13.5  CONVICTION DRIFT DETECTOR
    Function: check_conviction_drift(round_number, new_bull_score,
                                      new_bear_score, session_id)
    
    Behavior:
      - Query conviction_history for previous round scores
      - If round 1: Record current scores and PROCEED
      - Calculate bull_delta and bear_delta (absolute differences)
      - If delta > EXTENDED_REASONING_REQUIRED_DRIFT (12): Flag for review
      - If delta > MAX_CONVICTION_DRIFT_PER_ROUND (15):
        Log "pause" severity, return REQUIRE_EXTENDED_REASONING
      - Record all deltas to conviction_history for pattern detection
    
    Returns: RiskDecision(action=PROCEED|REQUIRE_EXTENDED_REASONING,
                         reason, context with deltas and scores)

✅ 13.6  MINIMUM STAKE THRESHOLD CHECKER
    Function: check_minimum_stakes(session_id, round_number)
    
    Behavior:
      - Read stake amounts from DebateEscrow contract via web3
      - Convert from wei to ETH for comparison
      - Zero stake on either side: HALT (severity "halt")
      - Below minimum on either side: Log warning (severity "warning")
      - Ratio > 10:1: Log imbalance warning (severity "warning")
      - Otherwise: PROCEED
    
    Returns: RiskDecision(action=PROCEED|HALT, reason, context)

✅ 13.7  DEBATE TIMEOUT HANDLER
    Function: check_debate_timeout(round_number, session_id)
    
    Behavior:
      - If round < MAX_DEBATE_ROUNDS: PROCEED
      - If round == MAX_DEBATE_ROUNDS: PROCEED with context last_round=True
      - If round > MAX_DEBATE_ROUNDS: FORCE_SETTLEMENT (defensive)
    
    Related Function: evaluate_draw_conditions(final_bull_score, final_bear_score)
    
    Draw Classification:
      - Score difference < 10 points: "true_draw" (full refund minus gas)
      - Score difference >= 10 points: "marginal_winner" (partial redistribution)
    
    Returns: RiskDecision or dict with draw_type and settlement_action

✅ 13.8  AXL MESSAGE SIGNATURE VALIDATOR
    Function: validate_axl_message(message_dict, expected_sender,
                                    round_number, session_id)
    
    Validation Checks:
      1. Claimed sender matches expected sender
      2. Sender peer_id matches known peer ID (from constants.py)
      3. Message has a valid signature
    
    If validation fails:
      - Write to axl_message_audit with signature_valid=False
      - Log "halt" severity event, action "rejected_spoofed_message"
      - Return REJECT_MESSAGE
    
    If validation passes:
      - Write to axl_message_audit with accepted=True
      - Return PROCEED
    
    AXL Node Constants (in /utils/constants.py):
      - AXL_NODE_PEER_IDS: Map of "bull", "bear", "judge" to peer IDs
      - AXL_NODE_PUBLIC_KEYS: Map for cryptographic validation (optional)
    
    Returns: RiskDecision(action=PROCEED|REJECT_MESSAGE, reason, context)

✅ 13.9  GAS SPIKE MONITOR
    Function: check_gas_conditions(round_number, session_id)
    
    Behavior:
      - Fetch current gas price via web3.eth.gas_price (convert to gwei)
      - Query last 5 gas price readings from gas_price_history table
      - Calculate rolling average
      - Record current reading for future baselines
    
    Decision Logic:
      - If current > 2× rolling average: SKIP_SWAP (extreme spike)
      - If current > rolling_avg + GAS_SPIKE_THRESHOLD_PERCENT (30%):
        DELAY_SWAP (wait 30s, then re-check)
      - Otherwise: PROCEED
    
    Returns: RiskDecision(action=PROCEED|DELAY_SWAP|SKIP_SWAP, reason, context)

✅ 13.10 ORCHESTRATOR INTEGRATION
    Files Modified: agents/orchestrator.py
    
    Checkpoint Integration:
    
    1. setup_round(session_id, round_number, token_pair, risk_manager):
       - Calls risk_manager.check_data_freshness()
       - Calls risk_manager.check_minimum_stakes()
       - Handles SKIP_ROUND: incrementing round counter
       - Handles HALT: updating session status to IDLE
    
    2. run_judging(session_id, round_number, bull_argument, bear_argument,
                   market_snapshot, risk_manager):
       - Calls risk_manager.check_conviction_drift() after verdict
       - Handles REQUIRE_EXTENDED_REASONING:
         Re-calls Judge with extended prompt (can be enhanced further)
    
    3. check_end_conditions(session_id, bull_score, bear_score, round_number,
                            max_rounds, risk_manager):
       - Calls risk_manager.check_debate_timeout()
       - Calls risk_manager.evaluate_draw_conditions() for timeout endings
    
    4. execute_micro_settlement (swap_executor.py):
       - Calls risk_manager.check_gas_conditions() before KeeperHub submission
       - Handles DELAY_SWAP: sleeps 30s, re-checks
       - Handles SKIP_SWAP: skips micro-settlement for this round
    
    Initialization:
    - run_debate() creates RiskManager(session_id) at start
    - Passes risk_manager to all checkpoint functions

✅ 13.10 SAFETY SCENARIO TESTING
    Files Created:
    - /test_risk_manager_safety.py: Automated scenario tests
    - /verify_risk_manager.py: Comprehensive verification suite
    
    Scenario Tests:
    
    Test 1: Stale Data Guard
      - Set MAX_DATA_AGE_SECONDS=1 in .env
      - Run 1 debate round
      - Verify safety_events has stale_data record
      - Orchestrator pauses and retries
    
    Test 2: Conviction Drift Guard
      - Set MAX_CONVICTION_DRIFT_PER_ROUND=1 in .env
      - Run 2 debate rounds
      - Verify safety_events has conviction_drift record
      - Judge called twice with extended reasoning
    
    After Testing:
      - Reset MAX_DATA_AGE_SECONDS=120
      - Reset MAX_CONVICTION_DRIFT_PER_ROUND=15
      - Back to production configuration
"""

# ============================================================================
# VISUAL SAFETY INDICATORS (in console output)
# ============================================================================

"""
⚠️  WARNING
    - Severity: Low
    - Action: Continue debate with documented issue
    - Example: Stake imbalance > 10:1, minor conviction drift
    - Status: Issue logged, monitoring continues

⏸️  PAUSE
    - Severity: Medium
    - Action: Pause round, attempt recovery
    - Example: Stale data (60s wait), conviction drift > threshold
    - Status: Orchestrator waits for resolution or escalation

🚨 HALT
    - Severity: Critical
    - Action: Stop round, update session status
    - Example: Zero stake on one side, invalid AXL signature
    - Status: Debate cannot continue safely
"""

# ============================================================================
# VERIFICATION RESULTS
# ============================================================================

"""
✅ Database Tables
   - safety_events: Logs all risk decisions
   - conviction_history: Tracks score movements
   - axl_message_audit: Audits all AXL messages
   - gas_price_history: Rolling gas price baseline

✅ RiskManager Class
   - Initialization with environment configuration
   - All 7 checkpoint functions implemented
   - Safety event logging with visual indicators
   - Database session management

✅ Checkpoint Functions
   1. check_data_freshness: Stale data detection and wait logic
   2. check_conviction_drift: Score movement analysis
   3. check_minimum_stakes: Stake threshold validation
   4. check_debate_timeout: Round limit enforcement
   5. evaluate_draw_conditions: Timeout-based ending classification
   6. validate_axl_message: AXL signature verification
   7. check_gas_conditions: Gas price spike monitoring

✅ Orchestrator Integration
   - All four checkpoint locations updated
   - Risk manager passed to functions
   - Return values handled appropriately
   - Error handling for recoverable vs critical failures

✅ AXL Node Constants
   - Peer IDs configured in constants.py
   - Public keys fields ready for production deployment
   - Environment override support

✅ Safety Scenario Tests
   - Stale data guard validation
   - Conviction drift guard validation
   - Comprehensive verification suite
"""

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
Initialize Risk Manager in orchestrator:

    from utils.risk_manager import RiskManager
    
    session_id = str(uuid4())
    risk_manager = RiskManager(session_id)
    
    # In setup_round
    freshness_decision = risk_manager.check_data_freshness(snapshot, round_num)
    if freshness_decision.action == "SKIP_ROUND":
        # Skip this round, increment counter
        continue
    
    stakes_decision = risk_manager.check_minimum_stakes(session_id, round_num)
    if stakes_decision.action == "HALT":
        # Update session status, stop debate
        raise RuntimeError("Insufficient stakes")
    
    # In run_judging
    drift_decision = risk_manager.check_conviction_drift(
        round_num, bull_score, bear_score, session_id
    )
    if drift_decision.action == "REQUIRE_EXTENDED_REASONING":
        # Re-call Judge with extended prompt
        verdict = run_judge_round(round_num, token_pair, extended=True)
    
    # In check_end_conditions
    timeout_decision = risk_manager.check_debate_timeout(round_num, session_id)
    if timeout_decision.context.get("last_round"):
        # This is the final round, trigger settlement after
        pass
    
    # In execute_micro_settlement
    gas_decision = risk_manager.check_gas_conditions(round_num, session_id)
    if gas_decision.action == "DELAY_SWAP":
        time.sleep(30)
        # Re-check or use cached decision
    elif gas_decision.action == "SKIP_SWAP":
        # Skip micro-settlement, final settlement will handle it
        return
"""

# ============================================================================
# ENVIRONMENT CONFIGURATION
# ============================================================================

"""
Add to .env file to customize thresholds:

    # Data Freshness (seconds)
    MAX_DATA_AGE_SECONDS=120
    
    # Conviction Movement (points per round)
    MAX_CONVICTION_DRIFT_PER_ROUND=15
    EXTENDED_REASONING_REQUIRED_DRIFT=12
    
    # Stake Thresholds (ETH)
    MIN_STAKE_EACH_SIDE_ETH=0.001
    
    # Debate Duration (max rounds)
    MAX_DEBATE_ROUNDS=20
    
    # Gas Price Monitoring (percent)
    GAS_SPIKE_THRESHOLD_PERCENT=30
    
    # AXL Node Identities (optional, defaults included)
    BULL_AXL_PEER_ID=12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL8
    BEAR_AXL_PEER_ID=12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL9
    JUDGE_AXL_PEER_ID=12D3KooWFTiF7mMa1KKQPhYdQEVKSTPAWKfyJ6jCL5Dkr5f4oNL7
"""

# ============================================================================
# RUNNING VERIFICATION AND TESTS
# ============================================================================

"""
Comprehensive Verification:
    cd /Users/swanandibhende/Documents/Projects/convexa
    source .venv/bin/activate
    python3 verify_risk_manager.py

Safety Scenario Tests:
    python3 test_risk_manager_safety.py

Expected Output:
    ✅ All verifications passed! Risk Manager is properly implemented.
    ✅ PASS: Stale data guard triggered correctly
    ✅ PASS: Conviction drift guard triggered correctly
"""

# ============================================================================
# FILES CREATED/MODIFIED
# ============================================================================

"""
Created:
    - /utils/risk_manager.py (453 lines)
    - /verify_risk_manager.py (verification suite)
    - /test_risk_manager_safety.py (scenario tests)

Modified:
    - /utils/db/schema.py (added 4 tables)
    - /utils/constants.py (added AXL node constants)
    - /agents/orchestrator.py (added 4 checkpoint calls)

All files compile without syntax errors and pass verification.
"""

print(__doc__)
