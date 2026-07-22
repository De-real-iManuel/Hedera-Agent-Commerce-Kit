"""
HCS Receipt Logger — powered by Hedera Agent Kit
-------------------------------------------------
After every verified payment, publishes a JSON receipt to an HCS topic using
the Hedera Agent Kit's core_consensus_plugin (TopicMessageSubmitTransaction).

Provides a local in-memory cache so receipts can be fetched instantly without
re-querying the Mirror Node.

Safety:
  - Operator credentials are loaded from environment only; never logged.
  - HCS errors are captured and attached to the receipt dict but do NOT block
    the payment flow (the payment is already verified before this runs).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from backend.config import get_settings

# Local receipt cache: transaction_id → receipt dict
_receipts: Dict[str, Dict[str, Any]] = {}


def _build_hedera_client():
    """
    Build a Hiero/Hedera SDK client using hedera-agent-kit's hiero_sdk_python.
    Returns the client or None if credentials are missing.
    """
    try:
        from hiero_sdk_python import Client, Network, AccountId, PrivateKey  # type: ignore

        s = get_settings()
        account_id = AccountId.from_string(s.hedera_operator_id)
        private_key = PrivateKey.from_string(s.hedera_operator_key)

        network = "testnet" if s.hedera_network == "testnet" else "mainnet"
        client = Client(Network(network=network))
        client.set_operator(account_id, private_key)
        return client
    except Exception:
        return None


def _submit_to_hcs(client, topic_id_str: str, message: str) -> None:
    """Submit a message to an HCS topic via the Hedera Agent Kit SDK."""
    from hiero_sdk_python import TopicId, TopicMessageSubmitTransaction  # type: ignore

    topic_id = TopicId.from_string(topic_id_str)
    TopicMessageSubmitTransaction(
        topic_id=topic_id,
        message=message.encode("utf-8"),
    ).execute(client)


async def publish_receipt(
    transaction_id: str,
    caller: str,
    endpoint: str,
    amount_hbar: float,
) -> Dict[str, Any]:
    """
    Build a receipt, cache it, and publish it to the configured HCS topic.

    Returns the receipt dict (with `hcs_error` key if publishing failed).
    The caller's payment flow is never blocked by an HCS failure.
    """
    s = get_settings()
    receipt: Dict[str, Any] = {
        "transaction_id": transaction_id,
        "caller": caller,
        "endpoint": endpoint,
        "amount_hbar": amount_hbar,
        "timestamp": int(time.time()),
        "hashscan_url": (
            f"https://hashscan.io/{s.hedera_network}/transaction/{transaction_id}"
        ),
    }

    try:
        client = _build_hedera_client()
        if client is None:
            raise RuntimeError(
                "Hedera client could not be initialised. "
                "Check HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY in .env."
            )
        _submit_to_hcs(client, s.hcs_receipt_topic_id, json.dumps(receipt))
        receipt["hcs_status"] = "published"
    except Exception as exc:  # noqa: BLE001
        # HCS publish failure is non-fatal — log the error in the receipt
        receipt["hcs_status"] = "failed"
        receipt["hcs_error"] = str(exc)

    _receipts[transaction_id] = receipt
    return receipt


def get_receipt(transaction_id: str) -> Optional[Dict[str, Any]]:
    return _receipts.get(transaction_id)
