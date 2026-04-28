from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4


DRY_RUN = os.getenv("DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "y", "on"}


def set_dry_run(value: bool) -> None:
    global DRY_RUN
    DRY_RUN = bool(value)
    os.environ["DRY_RUN"] = "true" if DRY_RUN else "false"


def _mock_tx_hash(prefix: str) -> str:
    # Keep deterministic shape of tx hashes for downstream integrations and UI previews.
    seed = f"{prefix}-{datetime.now(UTC).isoformat()}-{uuid4()}".encode("utf-8").hex()
    return "0x" + seed[:64].ljust(64, "0")


def execute_settlement(winning_side: str) -> str:
    """KeeperHub settlement interface stub for winner payout path."""
    if DRY_RUN:
        tx_hash = _mock_tx_hash(f"settle-{winning_side}")
        print(f"[DRY_RUN][KEEPER] Settlement simulated for winner={winning_side}. tx={tx_hash}")
        return tx_hash

    tx_hash = _mock_tx_hash(f"settle-{winning_side}")
    print(f"[KEEPER] Settlement would execute here for winner={winning_side}. tx={tx_hash}")
    return tx_hash


def execute_draw_refund(session_id: str) -> str:
    """KeeperHub settlement interface stub for draw refund path."""
    if DRY_RUN:
        tx_hash = _mock_tx_hash(f"draw-refund-{session_id}")
        print(f"[DRY_RUN][KEEPER] Draw refund simulated for session_id={session_id}. tx={tx_hash}")
        return tx_hash

    tx_hash = _mock_tx_hash(f"draw-refund-{session_id}")
    print(f"[KEEPER] Draw refund would execute here for session_id={session_id}. tx={tx_hash}")
    return tx_hash
