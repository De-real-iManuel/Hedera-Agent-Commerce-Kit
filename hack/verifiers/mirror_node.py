"""
hack/verifiers/mirror_node.py
------------------------------
MirrorNodeVerifier — a PaymentVerifier that queries the Hedera Mirror Node
REST API to confirm an HBAR transfer.

Transaction ID normalisation:
  "0.0.12345@1234567890.123456789"
    → replace "@" with "-"
    → replace first two "." with "-"
    → "0-0-12345-1234567890-123456789"

This follows the Mirror Node URL format required by the v1 API.

Error mapping:
  404 → ValueError with "Mirror Node lag ~3s" hint (caller should retry)
  5xx → VerifierUnavailableError (retryable)
  insufficient amount → InsufficientPaymentError
"""

from __future__ import annotations

import httpx

from ..core.exceptions import InsufficientPaymentError, VerifierUnavailableError
from ..core.interfaces import PaymentVerifier

_MIRROR_NODE_URLS: dict[str, str] = {
    "testnet": "https://testnet.mirrornode.hedera.com",
    "mainnet": "https://mainnet-public.mirrornode.hedera.com",
    "previewnet": "https://previewnet.mirrornode.hedera.com",
}


def _normalise_tx_id(transaction_id: str) -> str:
    """
    Convert a Hedera transaction ID to the format expected by Mirror Node.

    Handles both "@"-delimited and already-normalised IDs.

    Examples:
      "0.0.1234@1710000000.000000001"  → "0.0.1234-1710000000-000000001"
      "0.0.1234.1710000000.000000001"  → "0.0.1234-1710000000-000000001"

    The Mirror Node expects: <shard>.<realm>.<num>-<seconds>-<nanos>
    Only the account portion (shard.realm.num) keeps its dots; the "@" or
    dot separating the account from the timestamp becomes "-" and the dot
    within the timestamp nanosecond part also becomes "-".
    """
    if "@" in transaction_id:
        # Format: "0.0.1234@1710000000.000000001"
        # Split on "@" → account part keeps dots, timestamp part loses its dot
        account, timestamp = transaction_id.split("@", 1)
        normalised_timestamp = timestamp.replace(".", "-")
        return f"{account}-{normalised_timestamp}"
    else:
        # Format: "0.0.1234.1710000000.000000001" (all dots)
        # Replace the 3rd and 4th dots with dashes; keep first two dots.
        parts = transaction_id.split(".")
        if len(parts) >= 5:
            # shard.realm.num.seconds.nanos → shard.realm.num-seconds-nanos
            return f"{parts[0]}.{parts[1]}.{parts[2]}-{parts[3]}-{parts[4]}"
        # Already in correct format (e.g. "0.0.1234-1710000000-000000001")
        return transaction_id


class MirrorNodeVerifier(PaymentVerifier):
    """
    Verifies HBAR payments by querying the Hedera Mirror Node REST API.

    Args:
        base_url: Mirror Node base URL.  Defaults to testnet.
                  Pass "" or None to auto-select from the ``network`` argument.
        timeout:  HTTP request timeout in seconds (default 15).
    """

    def __init__(
        self,
        base_url: str = "https://testnet.mirrornode.hedera.com",
        timeout: int = 15,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else ""
        self._timeout = timeout

    async def verify(
        self,
        transaction_id: str,
        receiver: str,
        min_tinybars: int,
        network: str = "testnet",
    ) -> dict:
        """
        Fetch and validate a transaction from the Mirror Node.

        Returns the raw transaction dict on success.

        Raises:
            ValueError: transaction not found (Mirror Node may still be indexing).
            VerifierUnavailableError: Mirror Node returned 5xx.
            InsufficientPaymentError: amount received < min_tinybars.
        """
        base = self._base_url or _MIRROR_NODE_URLS.get(network, _MIRROR_NODE_URLS["testnet"])
        normalised = _normalise_tx_id(transaction_id)
        url = f"{base}/api/v1/transactions/{normalised}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(url)
            except httpx.RequestError as exc:
                raise VerifierUnavailableError(
                    f"Mirror Node unreachable: {exc}"
                ) from exc

        if resp.status_code == 404:
            raise ValueError(
                f"Transaction {transaction_id!r} not found on Mirror Node. "
                "Mirror Node lag ~3s — retry shortly."
            )

        if resp.status_code >= 500:
            raise VerifierUnavailableError(
                f"Mirror Node returned {resp.status_code}. "
                "This is retryable — try again in a few seconds."
            )

        resp.raise_for_status()

        data = resp.json()
        transactions: list[dict] = data.get("transactions", [data])
        if not transactions:
            raise ValueError("Empty transaction list returned from Mirror Node.")

        tx = transactions[0]
        self._check_transfer(tx, transaction_id, receiver, min_tinybars)
        return tx

    # ─── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _check_transfer(
        tx: dict,
        transaction_id: str,
        receiver: str,
        min_tinybars: int,
    ) -> None:
        """Validate that the receiver received at least min_tinybars."""
        transfers: list[dict] = tx.get("transfers", [])
        received = sum(
            t.get("amount", 0)
            for t in transfers
            if t.get("account") == receiver and t.get("amount", 0) > 0
        )
        if received < min_tinybars:
            raise InsufficientPaymentError(
                f"Insufficient payment for tx {transaction_id!r}: "
                f"received {received} tinybar, expected ≥ {min_tinybars}."
            )
