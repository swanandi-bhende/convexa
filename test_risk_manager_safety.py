#!/usr/bin/env python3
"""
Safety scenario tests for the Risk Manager.
Tests stale data guard and conviction drift detector with deliberate threshold violations.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from utils.db.schema import Base, SafetyEvent
from utils.db_manager import init_database
from agents.orchestrator import run_debate


def load_env_file():
    """Load and display current .env settings."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print(f"❌ Missing .env file at {env_file}")
        return None
    
    env_vars = dotenv_values(str(env_file))
    print(f"\n📋 Current .env Risk Manager thresholds:")
    print(f"   MAX_DATA_AGE_SECONDS: {env_vars.get('MAX_DATA_AGE_SECONDS', '120 (default)')}")
    print(f"   MAX_CONVICTION_DRIFT_PER_ROUND: {env_vars.get('MAX_CONVICTION_DRIFT_PER_ROUND', '15 (default)')}")
    print(f"   EXTENDED_REASONING_REQUIRED_DRIFT: {env_vars.get('EXTENDED_REASONING_REQUIRED_DRIFT', '12 (default)')}")
    return str(env_file)


def set_env_threshold(env_file: str, key: str, value: str):
    """Update a single threshold in the .env file."""
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Find and update the line if it exists, or add it if not
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    
    if not found:
        lines.append(f"{key}={value}\n")
    
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    # Reload environment
    load_dotenv(env_file, override=True)
    print(f"✓ Set {key}={value}")


def check_safety_events(event_type: str, min_count: int = 1) -> int:
    """Query safety_events table and return count of events matching type."""
    try:
        db_url = os.getenv("DATABASE_URL", "sqlite:///./debate.db")
        engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db:
            stmt = select(SafetyEvent).where(SafetyEvent.event_type == event_type)
            events = db.execute(stmt).scalars().all()
            
            print(f"\n📊 Safety Events - {event_type}: {len(events)} record(s)")
            for event in events:
                print(f"   Round {event.round_number}: {event.severity.upper()} - {event.action_taken}")
            
            return len(events)
    except Exception as e:
        print(f"⚠️  Error querying safety_events: {e}")
        return 0


def test_stale_data_guard():
    """Test 1: Force stale data detection with MAX_DATA_AGE_SECONDS=1."""
    print("\n" + "=" * 72)
    print("TEST 1: STALE DATA GUARD")
    print("=" * 72)
    
    env_file = load_env_file()
    if not env_file:
        return False
    
    print("\n🔧 Configuring for stale data test...")
    set_env_threshold(env_file, "MAX_DATA_AGE_SECONDS", "1")
    set_env_threshold(env_file, "ORCHESTRATOR_SAFE_MODE", "1")  # Avoid real transactions
    
    print("\n▶️  Running 1 debate round to trigger stale data detection...")
    try:
        # Run with very short debate to just test one round
        session_id = run_debate("ETH/USDC", max_rounds=1, round_interval_seconds=5)
        print(f"✓ Debate session {session_id} completed")
    except Exception as e:
        print(f"⚠️  Debate run encountered exception (expected): {type(e).__name__}")
    
    # Check if stale_data events were recorded
    time.sleep(1)
    stale_count = check_safety_events("stale_data")
    
    if stale_count > 0:
        print("✅ PASS: Stale data guard triggered correctly")
        return True
    else:
        print("❌ FAIL: No stale data events recorded")
        return False


def test_conviction_drift_guard():
    """Test 2: Force conviction drift detection with MAX_CONVICTION_DRIFT_PER_ROUND=1."""
    print("\n" + "=" * 72)
    print("TEST 2: CONVICTION DRIFT GUARD")
    print("=" * 72)
    
    env_file = load_env_file()
    if not env_file:
        return False
    
    print("\n🔧 Configuring for conviction drift test...")
    set_env_threshold(env_file, "MAX_DATA_AGE_SECONDS", "120")  # Reset to normal
    set_env_threshold(env_file, "MAX_CONVICTION_DRIFT_PER_ROUND", "1")  # Very low threshold
    set_env_threshold(env_file, "ORCHESTRATOR_SAFE_MODE", "1")  # Avoid real transactions
    
    print("\n▶️  Running 2 debate rounds to trigger drift detection...")
    try:
        session_id = run_debate("ETH/USDC", max_rounds=2, round_interval_seconds=5)
        print(f"✓ Debate session {session_id} completed")
    except Exception as e:
        print(f"⚠️  Debate run encountered exception (expected): {type(e).__name__}")
    
    # Check if conviction_drift events were recorded
    time.sleep(1)
    drift_count = check_safety_events("conviction_drift")
    
    if drift_count > 0:
        print("✅ PASS: Conviction drift guard triggered correctly")
        return True
    else:
        print("❌ FAIL: No conviction drift events recorded")
        return False


def reset_env_defaults():
    """Reset .env thresholds to production defaults."""
    print("\n" + "=" * 72)
    print("RESETTING ENVIRONMENT TO PRODUCTION DEFAULTS")
    print("=" * 72)
    
    env_file = load_env_file()
    if not env_file:
        return
    
    print("\n🔧 Resetting thresholds...")
    set_env_threshold(env_file, "MAX_DATA_AGE_SECONDS", "120")
    set_env_threshold(env_file, "MAX_CONVICTION_DRIFT_PER_ROUND", "15")
    set_env_threshold(env_file, "EXTENDED_REASONING_REQUIRED_DRIFT", "12")
    set_env_threshold(env_file, "ORCHESTRATOR_SAFE_MODE", "0")
    
    print("✓ Environment reset to production values")


def main():
    """Run all safety scenario tests."""
    print("\n" + "=" * 72)
    print("CONVEXA RISK MANAGER SAFETY SCENARIO TESTS")
    print("=" * 72)
    
    load_dotenv()
    init_database()
    
    results = {}
    
    # Test 1: Stale Data Guard
    results["stale_data"] = test_stale_data_guard()
    
    # Test 2: Conviction Drift Guard
    results["conviction_drift"] = test_conviction_drift_guard()
    
    # Reset environment
    reset_env_defaults()
    
    # Summary
    print("\n" + "=" * 72)
    print("TEST SUMMARY")
    print("=" * 72)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:30s} {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All safety scenario tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
