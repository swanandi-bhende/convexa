from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _normalize_private_key(raw: str) -> str:
    key = raw.strip()
    return key if key.startswith("0x") else f"0x{key}"


def _load_abi(abi_path: Path) -> list[dict]:
    with abi_path.open("r", encoding="utf-8") as handle:
        parsed = json.load(handle)
    if isinstance(parsed, dict) and "abi" in parsed:
        parsed = parsed["abi"]
    if not isinstance(parsed, list):
        raise RuntimeError(f"Invalid ABI content in {abi_path}")
    return parsed


def _send_tx(*, web3: Web3, private_key: str, to: str, data: str, value_wei: int = 0) -> str:
    account = Account.from_key(_normalize_private_key(private_key))
    nonce = web3.eth.get_transaction_count(account.address)
    gas_price = int(web3.eth.gas_price)

    tx = {
        "from": account.address,
        "to": Web3.to_checksum_address(to),
        "value": int(value_wei),
        "data": data,
        "nonce": nonce,
        "chainId": int(web3.eth.chain_id),
        "gasPrice": gas_price,
    }
    tx["gas"] = int(web3.eth.estimate_gas(tx))

    signed = web3.eth.account.sign_transaction(tx, private_key=_normalize_private_key(private_key))
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    if int(receipt.status) != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return tx_hash.hex()


def main() -> None:
    rpc_url = os.getenv("ALCHEMY_RPC_URL", "").strip()
    escrow_address = os.getenv("ESCROW_CONTRACT_ADDRESS", "").strip()
    deployer_pk = os.getenv("DEPLOYER_PRIVATE_KEY", "").strip()
    bull_pk = os.getenv("BULL_STAKER_PRIVATE_KEY", "").strip()
    bear_pk = os.getenv("BEAR_STAKER_PRIVATE_KEY", "").strip()

    missing = [
        name
        for name, value in {
            "ALCHEMY_RPC_URL": rpc_url,
            "ESCROW_CONTRACT_ADDRESS": escrow_address,
            "DEPLOYER_PRIVATE_KEY": deployer_pk,
            "BULL_STAKER_PRIVATE_KEY": bull_pk,
            "BEAR_STAKER_PRIVATE_KEY": bear_pk,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    if not web3.is_connected():
        raise RuntimeError("Failed to connect to RPC")
    if int(web3.eth.chain_id) != 1301:
        raise RuntimeError(f"Expected chain id 1301, got {web3.eth.chain_id}")

    abi = _load_abi(PROJECT_ROOT / "contracts" / "abi" / "DebateEscrow.json")
    escrow = web3.eth.contract(address=Web3.to_checksum_address(escrow_address), abi=abi)

    start_data = escrow.functions.startDebate(3600).build_transaction({"from": Account.from_key(_normalize_private_key(deployer_pk)).address})["data"]

    start_tx = _send_tx(
        web3=web3,
        private_key=deployer_pk,
        to=escrow_address,
        data=start_data,
        value_wei=0,
    )
    print(f"startDebate_tx_hash={start_tx}")

    # Now that debate is active, build and send deposit transactions
    bull_data = escrow.functions.deposit(0).build_transaction({
        "from": Account.from_key(_normalize_private_key(bull_pk)).address,
        "value": web3.to_wei("0.1", "ether")
    })["data"]
    bull_tx = _send_tx(
        web3=web3,
        private_key=bull_pk,
        to=escrow_address,
        data=bull_data,
        value_wei=web3.to_wei("0.1", "ether"),
    )
    print(f"bull_deposit_tx_hash={bull_tx}")

    bear_data = escrow.functions.deposit(1).build_transaction({
        "from": Account.from_key(_normalize_private_key(bear_pk)).address,
        "value": web3.to_wei("0.1", "ether")
    })["data"]
    bear_tx = _send_tx(
        web3=web3,
        private_key=bear_pk,
        to=escrow_address,
        data=bear_data,
        value_wei=web3.to_wei("0.1", "ether"),
    )
    print(f"bear_deposit_tx_hash={bear_tx}")

    bull_total, bear_total, is_active = escrow.functions.getStakeInfo().call()
    expected = web3.to_wei("0.1", "ether")
    print(f"bull_total_wei={bull_total}")
    print(f"bear_total_wei={bear_total}")
    print(f"debate_active={is_active}")

    if int(bull_total) != int(expected):
        raise RuntimeError(f"Unexpected bull total: expected {expected}, got {bull_total}")
    if int(bear_total) != int(expected):
        raise RuntimeError(f"Unexpected bear total: expected {expected}, got {bear_total}")
    if bool(is_active) is not True:
        raise RuntimeError("Expected debate to be active after seeding")


if __name__ == "__main__":
    main()