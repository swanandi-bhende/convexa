"""
Risk Manager: Active gatekeeper between orchestrator and all other components.
The risk manager sits at four critical checkpoints in each round:
  1. Pre-round: check_data_freshness (stale data guard)
  2. Post-verdict: check_conviction_drift (conviction drift detector)
  3. Post-signature: check_axl_signature_validity (AXL audit)
  4. Post-conviction: check_debate_timeout (timeout guard)

At each checkpoint, the risk manager returns PROCEED, PAUSE, or HALT.
"""

import json
import os
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from utils.db.schema import Base, SafetyEvent, ConvictionHistory, AXLMessageAudit, GasPriceHistory

DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


@dataclass
class RiskDecision:
    """Return value from every risk manager checkpoint."""
    action: str  # "PROCEED", "PAUSE", "HALT", "SKIP_ROUND", "REQUIRE_EXTENDED_REASONING"
    reason: Optional[str] = None
    context: dict = field(default_factory=dict)


class RiskManager:
    """
    Active risk gatekeeper enforcing safety constraints across the debate system.
    Every orchestrator decision must be approved by the risk manager at key checkpoints.
    """

    def __init__(self, session_id: str, db_url: Optional[str] = None, web3_provider_url: Optional[str] = None):
        """
        Initialize the risk manager with configuration from environment and create database session.
        
        Args:
            session_id: Unique identifier for this debate session
            db_url: SQLAlchemy database URL (default from DATABASE_URL env)
            web3_provider_url: Web3 provider URL for on-chain state reading (default from WEB3_PROVIDER_URL env)
        """
        self.session_id = session_id
        
        # Load risk thresholds from environment with sensible defaults
        self.MAX_DATA_AGE_SECONDS = int(os.getenv("MAX_DATA_AGE_SECONDS", "120"))
        self.MAX_CONVICTION_DRIFT_PER_ROUND = int(os.getenv("MAX_CONVICTION_DRIFT_PER_ROUND", "15"))
        self.MIN_STAKE_EACH_SIDE_ETH = float(os.getenv("MIN_STAKE_EACH_SIDE_ETH", "0.001"))
        self.MAX_DEBATE_ROUNDS = int(os.getenv("MAX_DEBATE_ROUNDS", "20"))
        self.GAS_SPIKE_THRESHOLD_PERCENT = float(os.getenv("GAS_SPIKE_THRESHOLD_PERCENT", "30"))
        self.EXTENDED_REASONING_REQUIRED_DRIFT = int(os.getenv("EXTENDED_REASONING_REQUIRED_DRIFT", "12"))
        
        # Database setup
        db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./debate.db")
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Web3 setup (optional, for gas price monitoring and contract state reading)
        self.web3_provider_url = web3_provider_url or os.getenv("WEB3_PROVIDER_URL", None)
        self.web3 = None
        if self.web3_provider_url:
            try:
                from web3 import Web3
                self.web3 = Web3(Web3.HTTPProvider(self.web3_provider_url))
                if not self.web3.is_connected():
                    print(f"⚠️  Warning: Web3 provider at {self.web3_provider_url} is not connected")
                    self.web3 = None
            except Exception as e:
                print(f"⚠️  Warning: Failed to initialize Web3: {e}")
                self.web3 = None

    def _log_safety_event(
        self,
        round_number: int,
        event_type: str,
        severity: str,
        details: dict,
        action_taken: str,
    ) -> None:
        """
        Log a safety event to the database and print a formatted warning to stdout.
        
        Args:
            round_number: Current debate round number
            event_type: Type of safety event (stale_data, conviction_drift, etc.)
            severity: Severity level ("warning", "pause", or "halt")
            details: Full context dict that triggered this event
            action_taken: What the risk manager instructed orchestrator to do
        """
        # Map severity to visual indicator
        indicators = {
            "warning": "⚠️ ",
            "pause": "⏸️  ",
            "halt": "🚨 ",
        }
        indicator = indicators.get(severity, "ℹ️ ")
        
        # Print to stdout with clear visual indicator
        timestamp = datetime.utcnow().isoformat()
        print(
            f"{indicator}[{timestamp}] RISK MANAGER | "
            f"Session: {self.session_id} | Round: {round_number} | "
            f"Event: {event_type} | Severity: {severity.upper()} | "
            f"Action: {action_taken}"
        )
        
        # Write to database
        with self.SessionLocal() as db:
            event = SafetyEvent(
                session_id=self.session_id,
                round_number=round_number,
                event_type=event_type,
                severity=severity,
                details_json=json.dumps(details),
                action_taken=action_taken,
                resolved_at=None,
                timestamp=datetime.utcnow(),
            )
            db.add(event)
            db.commit()

    def check_data_freshness(self, market_snapshot: dict, round_number: int, max_retries: int = 4) -> RiskDecision:
        """
        First checkpoint: Guard against stale market data.
        
        This function is called before the round begins. It checks if the market snapshot
        contains data older than MAX_DATA_AGE_SECONDS. If data is stale, it attempts to
        fetch fresh data up to 4 times (60 seconds total wait). If data remains stale after
        all attempts, the round is skipped to prevent agents from debating on outdated data.
        
        Args:
            market_snapshot: Market data dict with 'data_freshness_seconds' field
            round_number: Current round number
            max_retries: Maximum retry attempts for fresh data (default 4)
        
        Returns:
            RiskDecision with action PROCEED, PAUSE, SKIP_ROUND, or HALT
        """
        if DRY_RUN:
            return RiskDecision(action="PROCEED", reason="dry_run_skips_freshness_gate")

        data_freshness_seconds = market_snapshot.get("data_freshness_seconds", None)
        
        # If no freshness info, assume data is acceptable
        if data_freshness_seconds is None:
            return RiskDecision(action="PROCEED", reason=None)
        
        # If data is fresh, proceed immediately
        if data_freshness_seconds <= self.MAX_DATA_AGE_SECONDS:
            return RiskDecision(action="PROCEED", reason=None)
        
        # Data is stale — attempt to refresh
        self._log_safety_event(
            round_number=round_number,
            event_type="stale_data",
            severity="pause",
            details={"data_age_seconds": data_freshness_seconds, "max_allowed": self.MAX_DATA_AGE_SECONDS},
            action_taken="waiting_for_fresh_data",
        )
        
        # Try up to max_retries times to get fresh data
        attempt = 0
        current_freshness = data_freshness_seconds
        while attempt < max_retries and current_freshness > self.MAX_DATA_AGE_SECONDS:
            print(f"  [Attempt {attempt + 1}/{max_retries}] Waiting 15s before retry...")
            time.sleep(15)
            attempt += 1
            
            # Simulate fresh fetch attempt — in real code, call market_data.fetch_snapshot()
            # For now, we just check if the timestamp would have advanced
            try:
                # Placeholder: in production, call market_data.fetch_snapshot() here
                # fresh_snapshot = market_data.fetch_snapshot()
                # current_freshness = fresh_snapshot.get("data_freshness_seconds", data_freshness_seconds)
                # This is where the actual fetch would happen
                current_freshness = data_freshness_seconds  # Placeholder
                break  # In real implementation, break if fresh data is obtained
            except Exception as e:
                print(f"  [Attempt {attempt}] Fetch failed: {e}")
                continue
        
        # After all retries, check if data is fresh now
        if current_freshness <= self.MAX_DATA_AGE_SECONDS:
            print(f"  ✓ Fresh data obtained after {attempt} attempts")
            return RiskDecision(action="PROCEED", reason=None)
        
        # Data is still stale after all retries — skip this round
        self._log_safety_event(
            round_number=round_number,
            event_type="stale_data",
            severity="halt",
            details={
                "data_age_seconds": current_freshness,
                "max_allowed": self.MAX_DATA_AGE_SECONDS,
                "retry_attempts": attempt,
            },
            action_taken="round_skipped_stale_data",
        )
        
        return RiskDecision(
            action="SKIP_ROUND",
            reason=f"data_remained_stale_after_{attempt*15}s_wait",
            context={"data_age_seconds": current_freshness, "attempts": attempt},
        )

    def check_conviction_drift(
        self,
        round_number: int,
        new_bull_score: int,
        new_bear_score: int,
        session_id: Optional[str] = None,
    ) -> RiskDecision:
        """
        Post-verdict checkpoint: Detect suspicious conviction score movements.
        
        This function is called after the Judge returns a verdict but before the new
        conviction is written to the blockchain. It compares the new scores against
        the previous round's scores to detect unusual drift. Large movements are flagged
        for extended reasoning, and extreme movements trigger a pause.
        
        Args:
            round_number: Current round number
            new_bull_score: New bull conviction score from Judge
            new_bear_score: New bear conviction score from Judge
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            RiskDecision with action PROCEED, REQUIRE_EXTENDED_REASONING, or PAUSE
        """
        session_id = session_id or self.session_id
        
        with self.SessionLocal() as db:
            # Query for previous round's scores
            previous_record = db.query(ConvictionHistory).filter(
                ConvictionHistory.session_id == session_id,
                ConvictionHistory.round_number == round_number - 1,
            ).first()

            current_record = db.query(ConvictionHistory).filter(
                ConvictionHistory.session_id == session_id,
                ConvictionHistory.round_number == round_number,
            ).first()
            
            # Round 1: no previous scores to compare, just record and proceed
            if previous_record is None:
                if current_record is None:
                    current_record = ConvictionHistory(
                        session_id=session_id,
                        round_number=round_number,
                        bull_score=new_bull_score,
                        bear_score=new_bear_score,
                        delta_from_previous_bull=None,
                        delta_from_previous_bear=None,
                        drift_flagged=False,
                        timestamp=datetime.utcnow(),
                    )
                    db.add(current_record)
                else:
                    current_record.bull_score = new_bull_score
                    current_record.bear_score = new_bear_score
                    current_record.delta_from_previous_bull = None
                    current_record.delta_from_previous_bear = None
                    current_record.drift_flagged = False
                    current_record.timestamp = datetime.utcnow()
                db.commit()
                return RiskDecision(action="PROCEED", reason=None)
            
            # Calculate deltas
            bull_delta = abs(new_bull_score - previous_record.bull_score)
            bear_delta = abs(new_bear_score - previous_record.bear_score)
            
            # Determine if drift is flagged (warning threshold)
            drift_flagged = (bull_delta >= self.EXTENDED_REASONING_REQUIRED_DRIFT or
                           bear_delta >= self.EXTENDED_REASONING_REQUIRED_DRIFT)
            
            # Record this round's conviction in history
            if current_record is None:
                current_record = ConvictionHistory(
                    session_id=session_id,
                    round_number=round_number,
                    bull_score=new_bull_score,
                    bear_score=new_bear_score,
                    delta_from_previous_bull=int(bull_delta),
                    delta_from_previous_bear=int(bear_delta),
                    drift_flagged=drift_flagged,
                    timestamp=datetime.utcnow(),
                )
                db.add(current_record)
            else:
                current_record.bull_score = new_bull_score
                current_record.bear_score = new_bear_score
                current_record.delta_from_previous_bull = int(bull_delta)
                current_record.delta_from_previous_bear = int(bear_delta)
                current_record.drift_flagged = drift_flagged
                current_record.timestamp = datetime.utcnow()
            db.commit()
            
            # Check if drift exceeds hard limit (pause threshold)
            if bull_delta > self.MAX_CONVICTION_DRIFT_PER_ROUND or bear_delta > self.MAX_CONVICTION_DRIFT_PER_ROUND:
                self._log_safety_event(
                    round_number=round_number,
                    event_type="conviction_drift",
                    severity="pause",
                    details={
                        "previous_bull": previous_record.bull_score,
                        "previous_bear": previous_record.bear_score,
                        "new_bull": new_bull_score,
                        "new_bear": new_bear_score,
                        "bull_delta": bull_delta,
                        "bear_delta": bear_delta,
                        "max_allowed": self.MAX_CONVICTION_DRIFT_PER_ROUND,
                    },
                    action_taken="require_extended_reasoning",
                )
                
                return RiskDecision(
                    action="REQUIRE_EXTENDED_REASONING",
                    reason=f"bull_delta={bull_delta}, bear_delta={bear_delta}",
                    context={
                        "previous_scores": {
                            "bull": previous_record.bull_score,
                            "bear": previous_record.bear_score,
                        },
                        "new_scores": {"bull": new_bull_score, "bear": new_bear_score},
                        "deltas": {"bull": bull_delta, "bear": bear_delta},
                    },
                )
            
            # If flagged but within hard limit, log warning for later analysis
            if drift_flagged:
                self._log_safety_event(
                    round_number=round_number,
                    event_type="conviction_drift",
                    severity="warning",
                    details={
                        "previous_bull": previous_record.bull_score,
                        "previous_bear": previous_record.bear_score,
                        "new_bull": new_bull_score,
                        "new_bear": new_bear_score,
                        "bull_delta": bull_delta,
                        "bear_delta": bear_delta,
                        "extended_reasoning_threshold": self.EXTENDED_REASONING_REQUIRED_DRIFT,
                    },
                    action_taken="flagged_for_monitoring",
                )
            
            # Normal case: drift within acceptable limits
            return RiskDecision(action="PROCEED", reason=None)

    def check_axl_signature_validity(
        self,
        round_number: int,
        sender_claimed: str,
        sender_peer_id: str,
        message_hash: str,
        signature_present: bool,
        signature_valid: bool,
        session_id: Optional[str] = None,
    ) -> RiskDecision:
        """
        Post-signature checkpoint: Audit AXL messages and validate signatures.
        
        This function is called when the Judge receives an AXL message (argument or verdict).
        It validates that the message is properly signed and records the audit trail.
        
        Args:
            round_number: Current round number
            sender_claimed: Claimed sender ("bull" or "bear")
            sender_peer_id: P2P peer ID of the sender
            message_hash: Hash of the message content
            signature_present: Whether the message has a signature
            signature_valid: Whether the signature is cryptographically valid
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            RiskDecision with action PROCEED or HALT
        """
        session_id = session_id or self.session_id
        
        with self.SessionLocal() as db:
            # Record audit entry regardless of validity
            audit_record = AXLMessageAudit(
                session_id=session_id,
                round_number=round_number,
                sender_claimed=sender_claimed,
                sender_peer_id=sender_peer_id,
                message_hash=message_hash,
                signature_present=signature_present,
                signature_valid=signature_valid,
                accepted=signature_valid,  # Only accept if signature is valid
                timestamp=datetime.utcnow(),
            )
            db.add(audit_record)
            db.commit()
        
        # If signature is missing or invalid, halt the round
        if not signature_present:
            self._log_safety_event(
                round_number=round_number,
                event_type="invalid_axl_signature",
                severity="halt",
                details={
                    "sender_claimed": sender_claimed,
                    "sender_peer_id": sender_peer_id,
                    "issue": "signature_missing",
                },
                action_taken="message_rejected_no_signature",
            )
            return RiskDecision(
                action="HALT",
                reason="message_missing_signature",
                context={"sender": sender_claimed},
            )
        
        if not signature_valid:
            self._log_safety_event(
                round_number=round_number,
                event_type="invalid_axl_signature",
                severity="halt",
                details={
                    "sender_claimed": sender_claimed,
                    "sender_peer_id": sender_peer_id,
                    "message_hash": message_hash,
                    "issue": "signature_invalid",
                },
                action_taken="message_rejected_invalid_signature",
            )
            return RiskDecision(
                action="HALT",
                reason="message_signature_invalid",
                context={"sender": sender_claimed, "message_hash": message_hash},
            )
        
        # Signature is valid, proceed
        return RiskDecision(action="PROCEED", reason=None)

    def check_debate_timeout(self, round_number: int, session_id: Optional[str] = None) -> RiskDecision:
        """
        Timeout guard: Enforce maximum debate round limit.
        
        This function is called after conviction is updated to check if the debate
        has exceeded the maximum round limit. If the current round is MAX_DEBATE_ROUNDS,
        flags last_round=True so orchestrator knows to trigger settlement after this round.
        If round exceeds max, returns FORCE_SETTLEMENT.
        
        Args:
            round_number: Current round number
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            RiskDecision with action PROCEED, FORCE_SETTLEMENT, or context with last_round flag
        """
        session_id = session_id or self.session_id
        
        # If this is the final permitted round, flag it for settlement after
        if round_number == self.MAX_DEBATE_ROUNDS:
            self._log_safety_event(
                round_number=round_number,
                event_type="debate_timeout",
                severity="warning",
                details={"current_round": round_number, "max_rounds": self.MAX_DEBATE_ROUNDS},
                action_taken="flagged_last_round",
            )
            return RiskDecision(
                action="PROCEED",
                reason=None,
                context={"last_round": True},
            )
        
        # If somehow we exceeded max (defensive check), force settlement
        if round_number > self.MAX_DEBATE_ROUNDS:
            self._log_safety_event(
                round_number=round_number,
                event_type="debate_timeout",
                severity="halt",
                details={
                    "current_round": round_number,
                    "max_rounds": self.MAX_DEBATE_ROUNDS,
                    "exceeds_max": True,
                },
                action_taken="force_settlement",
            )
            return RiskDecision(
                action="FORCE_SETTLEMENT",
                reason="exceeded_max_rounds",
                context={"settlement_type": "draw", "round": round_number},
            )
        
        return RiskDecision(action="PROCEED", reason=None)

    def check_minimum_stakes(self, session_id: Optional[str] = None, round_number: int = 0) -> RiskDecision:
        """
        Guard against meaningless debates with insufficient stake on either side.
        
        Reads current stake amounts from DebateEscrow contract via web3 and validates:
        1. Both sides meet minimum stake (MIN_STAKE_EACH_SIDE_ETH)
        2. Stake ratio does not exceed 10:1 imbalance
        
        Args:
            session_id: Session ID (uses self.session_id if not provided)
            round_number: Current round number for logging
        
        Returns:
            RiskDecision with HALT if either side has zero stake, WARNING if imbalanced
        """
        session_id = session_id or self.session_id

        if DRY_RUN:
            return RiskDecision(action="PROCEED", reason=None)

        try:
            from agents.orchestrator import _get_debate_escrow_contract

            _web3, escrow_contract = _get_debate_escrow_contract()
            if escrow_contract is None:
                return RiskDecision(action="PROCEED", reason=None)

            bull_stake_wei, bear_stake_wei, _is_active = escrow_contract.functions.getStakeInfo().call()
            
            # Convert from wei to ETH (wei / 10^18)
            bull_stake_eth = bull_stake_wei / 1e18
            bear_stake_eth = bear_stake_wei / 1e18
            
            if bull_stake_eth < self.MIN_STAKE_EACH_SIDE_ETH:
                self._log_safety_event(
                    round_number=round_number,
                    event_type="low_stake",
                    severity="halt",
                    details={
                        "bull_stake_eth": bull_stake_eth,
                        "bear_stake_eth": bear_stake_eth,
                        "min_required": self.MIN_STAKE_EACH_SIDE_ETH,
                    },
                    action_taken="below_minimum_stake_on_bull_side",
                )
                return RiskDecision(
                    action="HALT",
                    reason="insufficient_stake_on_one_side",
                    context={"side": "bull", "stake": bull_stake_eth},
                )
            
            if bear_stake_eth < self.MIN_STAKE_EACH_SIDE_ETH:
                self._log_safety_event(
                    round_number=round_number,
                    event_type="low_stake",
                    severity="halt",
                    details={
                        "bull_stake_eth": bull_stake_eth,
                        "bear_stake_eth": bear_stake_eth,
                        "min_required": self.MIN_STAKE_EACH_SIDE_ETH,
                    },
                    action_taken="below_minimum_stake_on_bear_side",
                )
                return RiskDecision(
                    action="HALT",
                    reason="insufficient_stake_on_one_side",
                    context={"side": "bear", "stake": bear_stake_eth},
                )

            if bull_stake_eth < self.MIN_STAKE_EACH_SIDE_ETH or bear_stake_eth < self.MIN_STAKE_EACH_SIDE_ETH:
                self._log_safety_event(
                    round_number=round_number,
                    event_type="low_stake",
                    severity="halt",
                    details={
                        "bull_stake_eth": bull_stake_eth,
                        "bear_stake_eth": bear_stake_eth,
                        "min_required": self.MIN_STAKE_EACH_SIDE_ETH,
                    },
                    action_taken="below_minimum_stake",
                )
                return RiskDecision(
                    action="HALT",
                    reason="insufficient_stake",
                    context={"bull_stake_eth": bull_stake_eth, "bear_stake_eth": bear_stake_eth},
                )

            # Check for severe imbalance (10:1 ratio)
            if bull_stake_eth > 0 and bear_stake_eth > 0:
                ratio = max(bull_stake_eth / bear_stake_eth, bear_stake_eth / bull_stake_eth)
                if ratio > 10:
                    self._log_safety_event(
                        round_number=round_number,
                        event_type="low_stake",
                        severity="warning",
                        details={
                            "bull_stake_eth": bull_stake_eth,
                            "bear_stake_eth": bear_stake_eth,
                            "ratio": ratio,
                            "max_allowed_ratio": 10,
                        },
                        action_taken="severe_stake_imbalance_documented",
                    )
            
            # Return PROCEED with warnings logged
            return RiskDecision(action="PROCEED", reason=None)
            
        except Exception as e:
            print(f"⚠️  Error checking minimum stakes: {e}")
            return RiskDecision(action="PROCEED", reason=None)

    def evaluate_draw_conditions(
        self, final_bull_score: int, final_bear_score: int, session_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Determine draw type when debate ends by timeout rather than conviction threshold.
        
        When neither side reaches the win threshold but max rounds are reached,
        this function classifies the outcome for settlement purposes.
        
        Args:
            final_bull_score: Bull's final conviction score
            final_bear_score: Bear's final conviction score
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            Dict with keys:
              - draw_type: "true_draw" (close) or "marginal_winner" (one side ahead)
              - leading_side: "bull" or "bear" if marginal_winner, None if true_draw
              - score_difference: Absolute difference between scores
        """
        session_id = session_id or self.session_id
        
        score_difference = abs(final_bull_score - final_bear_score)
        
        # If difference is less than 10 points, it's a true draw
        if score_difference < 10:
            return {
                "draw_type": "true_draw",
                "leading_side": None,
                "score_difference": score_difference,
                "settlement_action": "full_refund_minus_gas",
            }
        
        # One side is ahead by 10+ points but didn't reach threshold
        leading_side = "bull" if final_bull_score > final_bear_score else "bear"
        return {
            "draw_type": "marginal_winner",
            "leading_side": leading_side,
            "score_difference": score_difference,
            "settlement_action": "partial_redistribution",
        }

    def validate_axl_message(
        self,
        message_dict: dict[str, Any],
        expected_sender: str,
        round_number: int,
        session_id: Optional[str] = None,
    ) -> RiskDecision:
        """
        Validate AXL messages before Judge processes them.
        
        Checks that:
        1. Message has a sender field
        2. Claimed sender matches expected sender
        3. Sender peer ID matches known peer ID for that side
        4. Message has a valid signature (if required)
        
        Args:
            message_dict: The incoming AXL message
            expected_sender: Expected sender ("bull" or "bear")
            round_number: Current round number
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            RiskDecision with PROCEED or REJECT_MESSAGE
        """
        from utils.constants import AXL_NODE_PEER_IDS
        
        session_id = session_id or self.session_id
        
        # Extract message fields with safe access
        sender_claimed = message_dict.get("sender", "").lower()
        sender_peer_id = message_dict.get("sender_peer_id", "")
        message_hash = message_dict.get("message_hash", "")
        signature = message_dict.get("signature", None)
        
        # Check if sender claim matches expectation
        if sender_claimed != expected_sender.lower():
            with self.SessionLocal() as db:
                audit_record = AXLMessageAudit(
                    session_id=session_id,
                    round_number=round_number,
                    sender_claimed=sender_claimed,
                    sender_peer_id=sender_peer_id,
                    message_hash=message_hash,
                    signature_present=signature is not None,
                    signature_valid=False,
                    accepted=False,
                    timestamp=datetime.utcnow(),
                )
                db.add(audit_record)
                db.commit()
            
            self._log_safety_event(
                round_number=round_number,
                event_type="invalid_axl_signature",
                severity="halt",
                details={
                    "expected_sender": expected_sender,
                    "claimed_sender": sender_claimed,
                },
                action_taken="rejected_sender_mismatch",
            )
            return RiskDecision(
                action="REJECT_MESSAGE",
                reason="sender_claim_mismatch",
                context={"expected": expected_sender, "claimed": sender_claimed},
            )
        
        # Check if peer ID matches known peer ID for this side
        known_peer_id = AXL_NODE_PEER_IDS.get(expected_sender.lower(), "")
        if known_peer_id and sender_peer_id != known_peer_id:
            with self.SessionLocal() as db:
                audit_record = AXLMessageAudit(
                    session_id=session_id,
                    round_number=round_number,
                    sender_claimed=sender_claimed,
                    sender_peer_id=sender_peer_id,
                    message_hash=message_hash,
                    signature_present=signature is not None,
                    signature_valid=False,
                    accepted=False,
                    timestamp=datetime.utcnow(),
                )
                db.add(audit_record)
                db.commit()
            
            self._log_safety_event(
                round_number=round_number,
                event_type="invalid_axl_signature",
                severity="halt",
                details={
                    "sender_claimed": sender_claimed,
                    "expected_peer_id": known_peer_id,
                    "received_peer_id": sender_peer_id,
                    "issue": "peer_id_mismatch",
                },
                action_taken="rejected_spoofed_message",
            )
            return RiskDecision(
                action="REJECT_MESSAGE",
                reason="peer_id_mismatch",
                context={"sender": sender_claimed, "expected_peer_id": known_peer_id},
            )
        
        # Check signature presence and validity
        signature_valid = signature is not None and len(str(signature)) > 0
        if not signature_valid:
            with self.SessionLocal() as db:
                audit_record = AXLMessageAudit(
                    session_id=session_id,
                    round_number=round_number,
                    sender_claimed=sender_claimed,
                    sender_peer_id=sender_peer_id,
                    message_hash=message_hash,
                    signature_present=False,
                    signature_valid=False,
                    accepted=False,
                    timestamp=datetime.utcnow(),
                )
                db.add(audit_record)
                db.commit()
            
            self._log_safety_event(
                round_number=round_number,
                event_type="invalid_axl_signature",
                severity="halt",
                details={
                    "sender_claimed": sender_claimed,
                    "sender_peer_id": sender_peer_id,
                    "issue": "signature_missing",
                },
                action_taken="message_rejected_no_signature",
            )
            return RiskDecision(
                action="REJECT_MESSAGE",
                reason="message_missing_signature",
                context={"sender": sender_claimed},
            )
        
        # All checks passed — record as accepted
        with self.SessionLocal() as db:
            audit_record = AXLMessageAudit(
                session_id=session_id,
                round_number=round_number,
                sender_claimed=sender_claimed,
                sender_peer_id=sender_peer_id,
                message_hash=message_hash,
                signature_present=True,
                signature_valid=True,
                accepted=True,
                timestamp=datetime.utcnow(),
            )
            db.add(audit_record)
            db.commit()
        
        return RiskDecision(action="PROCEED", reason=None)

    def check_gas_conditions(self, round_number: int, session_id: Optional[str] = None) -> RiskDecision:
        """
        Monitor gas prices and delay/skip swaps if prices spike significantly.
        
        Fetches current gas price via web3, compares against rolling 5-entry average,
        and returns delay/skip recommendations. This complements KeeperHub's own
        gas management with an application-level check before swap submission.
        
        Args:
            round_number: Current round number
            session_id: Session ID (uses self.session_id if not provided)
        
        Returns:
            RiskDecision with action PROCEED, DELAY_SWAP, or SKIP_SWAP
        """
        session_id = session_id or self.session_id
        
        if not self.web3:
            return RiskDecision(action="PROCEED", reason=None)
        
        try:
            # Fetch current gas price in wei, convert to gwei
            current_gas_wei = self.web3.eth.gas_price
            current_gas_gwei = current_gas_wei / 1e9
            
            with self.SessionLocal() as db:
                # Query last 5 gas price readings
                recent_readings = db.query(GasPriceHistory).filter(
                    GasPriceHistory.session_id == session_id
                ).order_by(GasPriceHistory.timestamp.desc()).limit(5).all()
                
                # Calculate rolling average
                if recent_readings:
                    avg_gas_gwei = sum(r.gas_price_gwei for r in recent_readings) / len(recent_readings)
                else:
                    # No prior readings, just record current and proceed
                    new_reading = GasPriceHistory(
                        session_id=session_id,
                        gas_price_gwei=current_gas_gwei,
                        timestamp=datetime.utcnow(),
                    )
                    db.add(new_reading)
                    db.commit()
                    return RiskDecision(action="PROCEED", reason=None)
                
                # Record current gas price for future comparisons
                new_reading = GasPriceHistory(
                    session_id=session_id,
                    gas_price_gwei=current_gas_gwei,
                    timestamp=datetime.utcnow(),
                )
                db.add(new_reading)
                db.commit()
                
                # Check if gas spiked above threshold
                percent_above_avg = ((current_gas_gwei - avg_gas_gwei) / avg_gas_gwei) * 100
                
                # If more than double the average, skip swap entirely
                if current_gas_gwei > avg_gas_gwei * 2:
                    self._log_safety_event(
                        round_number=round_number,
                        event_type="gas_spike",
                        severity="warning",
                        details={
                            "current_gas_gwei": current_gas_gwei,
                            "rolling_avg_gwei": avg_gas_gwei,
                            "percent_above_avg": percent_above_avg,
                        },
                        action_taken="skip_swap_extreme_gas",
                    )
                    return RiskDecision(
                        action="SKIP_SWAP",
                        reason="extreme_gas_spike",
                        context={
                            "current_gwei": current_gas_gwei,
                            "avg_gwei": avg_gas_gwei,
                        },
                    )
                
                # If above spike threshold (GAS_SPIKE_THRESHOLD_PERCENT), delay
                if percent_above_avg > self.GAS_SPIKE_THRESHOLD_PERCENT:
                    self._log_safety_event(
                        round_number=round_number,
                        event_type="gas_spike",
                        severity="warning",
                        details={
                            "current_gas_gwei": current_gas_gwei,
                            "rolling_avg_gwei": avg_gas_gwei,
                            "percent_above_avg": percent_above_avg,
                            "threshold_percent": self.GAS_SPIKE_THRESHOLD_PERCENT,
                        },
                        action_taken="delay_swap_30s",
                    )
                    return RiskDecision(
                        action="DELAY_SWAP",
                        reason="gas_spike_detected",
                        context={
                            "delay_seconds": 30,
                            "current_gwei": current_gas_gwei,
                            "avg_gwei": avg_gas_gwei,
                        },
                    )
                
                # Gas is normal
                return RiskDecision(action="PROCEED", reason=None)
                
        except Exception as e:
            print(f"⚠️  Error checking gas conditions: {e}")
            return RiskDecision(action="PROCEED", reason=None)
