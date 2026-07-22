"""
Hedera Mirror Node verification
--------------------------------
Stateless: fetches a transaction and validates the HBAR transfer.
State tracking (QUOTED → VERIFIED → GRANTED → CONSUMED) lives in payment_state.py.
"""

from __future__ import annotations

import httpx

from backend.config import get_settings

MIRROR_NODE_URLS = {
    "testnet": "https://testnet.mirrornode.hedera.com",
    "mainnet": "https://mainnet-public.mirrornode.hedera.com",
}


def _mirror_url() -> str:
    s = get_settings()
    return MIRROR_NODE_URLS.get(s.hedera_network, MIRROR_NODE_URLS["testnet"])


async def verify_transaction(transaction_id: str) -> dict:
    """
    Fetch and validate the transaction from the Mirror Node.

    Returns the raw transaction dict on success.
    Raises ValueError for payment mismatches or missing transactions.
    Raises httpx.HTTPStatusError for unexpected Mirror Node errors.

    Note: Mirror Node indexing can lag ~3 s behind consensus. The caller
    should surface a retryable 502 to the client on 404, not a hard failure.
    """
    # Normalise: "0.0.12345@1234567890.123456789" → "0.0.12345-1234567890-123456789"
    normalised = transaction_id.replace("@", "-").replace(".", "-", 2)

    url = f"{_mirror_url()}/api/v1/transactions/{normalised}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url)

    if resp.status_code == 404:
        raise ValueError(
            f"Transaction {transaction_id!r} not found on Mirror Node yet. "
            "Mirror Node can lag ~3 s — retry shortly."
        )
    resp.raise_for_status()

    data = resp.json()
    transactions = data.get("transactions", [data])
    if not transactions:
        raise ValueError("Empty transaction list returned from Mirror Node.")

    tx = transactions[0]
    _check_transfer(tx, transaction_id)
    return tx


def _check_transfer(tx: dict, transaction_id: str) -> None:
    """Validate receiver received at least the configured minimum amount."""
    s = get_settings()
    receiver = s.x402_payment_receiver_account_id
    min_tinybars = int(s.x402_payment_amount_hbar * 100_000_000)  # HBAR → tinybar

    transfers = tx.get("transfers", [])
    received = sum(
        t["amount"]
        for t in transfers
        if t.get("account") == receiver and t.get("amount", 0) > 0
    )

    if received < min_tinybars:
        raise ValueError(
            f"Insufficient payment for tx {transaction_id!r}: "
            f"received {received} tinybar, expected ≥ {min_tinybars} "
            f"({s.x402_payment_amount_hbar} HBAR)."
        )
