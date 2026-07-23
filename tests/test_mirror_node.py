"""
tests/test_mirror_node.py
--------------------------
Unit tests for MirrorNodeVerifier using respx to mock HTTP responses.

Tests cover:
  - Successful 200 response with valid transfer
  - 404 raises ValueError with Mirror Node lag hint
  - Insufficient amount raises InsufficientPaymentError
  - Mismatched receiver raises InsufficientPaymentError (no credit to receiver)
  - 5xx raises VerifierUnavailableError
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from hack.core.exceptions import InsufficientPaymentError, VerifierUnavailableError
from hack.verifiers.mirror_node import MirrorNodeVerifier

TESTNET_BASE = "https://testnet.mirrornode.hedera.com"
RECEIVER = "0.0.12345"
TX_ID = "0.0.999999@1710000000.000000001"
# Mirror Node format: account keeps dots, "@" and nanosecond dot become "-"
NORMALISED_TX_ID = "0.0.999999-1710000000-000000001"
TX_URL = f"{TESTNET_BASE}/api/v1/transactions/{NORMALISED_TX_ID}"

# 50 HBAR in tinybars
AMOUNT_50_HBAR = 50_000_000


def _valid_tx_response(receiver: str = RECEIVER, amount: int = AMOUNT_50_HBAR) -> dict:
    return {
        "transactions": [
            {
                "transaction_id": NORMALISED_TX_ID,
                "result": "SUCCESS",
                "transfers": [
                    {"account": receiver, "amount": amount},
                    {"account": "0.0.3", "amount": -amount},
                ],
            }
        ]
    }


@pytest.mark.asyncio
async def test_verify_success():
    """A valid 200 response with sufficient transfer should return the tx dict."""
    verifier = MirrorNodeVerifier(base_url=TESTNET_BASE)

    with respx.mock(base_url=TESTNET_BASE) as mock:
        mock.get(f"/api/v1/transactions/{NORMALISED_TX_ID}").mock(
            return_value=Response(200, json=_valid_tx_response())
        )
        result = await verifier.verify(
            transaction_id=TX_ID,
            receiver=RECEIVER,
            min_tinybars=AMOUNT_50_HBAR,
            network="testnet",
        )

    assert result["result"] == "SUCCESS"
    assert result["transfers"][0]["account"] == RECEIVER


@pytest.mark.asyncio
async def test_verify_404_raises_value_error():
    """A 404 response should raise ValueError with a Mirror Node lag hint."""
    verifier = MirrorNodeVerifier(base_url=TESTNET_BASE)

    with respx.mock(base_url=TESTNET_BASE) as mock:
        mock.get(f"/api/v1/transactions/{NORMALISED_TX_ID}").mock(
            return_value=Response(404, json={"message": "Not found"})
        )
        with pytest.raises(ValueError, match="lag ~3s"):
            await verifier.verify(
                transaction_id=TX_ID,
                receiver=RECEIVER,
                min_tinybars=AMOUNT_50_HBAR,
                network="testnet",
            )


@pytest.mark.asyncio
async def test_verify_insufficient_amount_raises():
    """Transfer below min_tinybars should raise InsufficientPaymentError."""
    verifier = MirrorNodeVerifier(base_url=TESTNET_BASE)
    small_amount = 1_000  # 0.00001 HBAR — well below 0.5 HBAR required

    with respx.mock(base_url=TESTNET_BASE) as mock:
        mock.get(f"/api/v1/transactions/{NORMALISED_TX_ID}").mock(
            return_value=Response(200, json=_valid_tx_response(amount=small_amount))
        )
        with pytest.raises(InsufficientPaymentError):
            await verifier.verify(
                transaction_id=TX_ID,
                receiver=RECEIVER,
                min_tinybars=AMOUNT_50_HBAR,
                network="testnet",
            )


@pytest.mark.asyncio
async def test_verify_wrong_receiver_raises():
    """Transfer to a different account should raise InsufficientPaymentError."""
    verifier = MirrorNodeVerifier(base_url=TESTNET_BASE)
    wrong_receiver = "0.0.99999"

    with respx.mock(base_url=TESTNET_BASE) as mock:
        mock.get(f"/api/v1/transactions/{NORMALISED_TX_ID}").mock(
            return_value=Response(
                200,
                json=_valid_tx_response(receiver=wrong_receiver),
            )
        )
        with pytest.raises(InsufficientPaymentError):
            await verifier.verify(
                transaction_id=TX_ID,
                receiver=RECEIVER,  # expects our receiver, not wrong_receiver
                min_tinybars=AMOUNT_50_HBAR,
                network="testnet",
            )


@pytest.mark.asyncio
async def test_verify_5xx_raises_verifier_unavailable():
    """A 500 response from the Mirror Node should raise VerifierUnavailableError."""
    verifier = MirrorNodeVerifier(base_url=TESTNET_BASE)

    with respx.mock(base_url=TESTNET_BASE) as mock:
        mock.get(f"/api/v1/transactions/{NORMALISED_TX_ID}").mock(
            return_value=Response(503, json={"message": "Service Unavailable"})
        )
        with pytest.raises(VerifierUnavailableError):
            await verifier.verify(
                transaction_id=TX_ID,
                receiver=RECEIVER,
                min_tinybars=AMOUNT_50_HBAR,
                network="testnet",
            )
