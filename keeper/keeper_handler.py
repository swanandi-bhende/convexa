from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _mock_tx_hash(prefix: str) -> str:
    # Keep deterministic shape of tx hashes for downstream integrations and UI previews.
    seed = f"{prefix}-{datetime.now(UTC).isoformat()}-{uuid4()}".encode("utf-8").hex()
    return "0x" + seed[:64].ljust(64, "0")


def execute_settlement(winning_side: str) -> str:
    """KeeperHub settlement interface stub for winner payout path."""
    tx_hash = _mock_tx_hash(f"settle-{winning_side}")
    print(f"[KEEPER] Settlement would execute here for winner={winning_side}. tx={tx_hash}")
    return tx_hash


def execute_draw_refund(session_id: str) -> str:
    """KeeperHub settlement interface stub for draw refund path."""
    tx_hash = _mock_tx_hash(f"draw-refund-{session_id}")
    print(f"[KEEPER] Draw refund would execute here for session_id={session_id}. tx={tx_hash}")
    return tx_hash
