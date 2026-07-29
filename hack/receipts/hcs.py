"""
hack/receipts/hcs.py
---------------------
HCSReceiptService — a ReceiptService that publishes payment receipts to a
Hedera Consensus Service (HCS) topic using the hiero-sdk-python SDK.

The SDK client is synchronous, so the publish step is offloaded to a thread
pool via asyncio.get_event_loop().run_in_executor to avoid blocking the
event loop.

Failures during HCS publishing are non-fatal: the receipt is cached locally
and returned with hcs_status="failed" and hcs_error set.  The payment flow
is never blocked by an HCS issue.

Receipts are indexed locally by transaction_id for instant retrieval.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from ..core.interfaces import ReceiptService
from ..models.quote import ReceiptModel


def _build_hedera_client(operator_id: str, operator_key: str, network: str):
    """
    Construct a Hiero SDK client.  Returns None if the SDK is not installed
    or credentials are invalid.
    """
    try:
        from hiero_sdk_python import (  # type: ignore
            AccountId,
            Client,
            Network,
            PrivateKey,
        )

        account_id = AccountId.from_string(operator_id)
        private_key = PrivateKey.from_string(operator_key)
        net_str = "testnet" if network == "testnet" else "mainnet"
        client = Client(Network(network=net_str))
        client.set_operator(account_id, private_key)
        return client
    except Exception:
        return None


def _submit_to_hcs_sync(
    client,
    topic_id_str: str,
    message: str,
) -> int:
    """Blocking call — returns the topic sequence number. Run in an executor."""
    from hiero_sdk_python import TopicId, TopicMessageSubmitTransaction  # type: ignore

    topic_id = TopicId.from_string(topic_id_str)
    receipt = TopicMessageSubmitTransaction(
        topic_id=topic_id,
        message=message.encode("utf-8"),
    ).execute(client)

    # The receipt contains the sequence number assigned to this message.
    seq = getattr(receipt, "topic_sequence_number", None) or getattr(receipt, "topicSequenceNumber", None)
    return int(seq) if seq is not None else 0


class HCSReceiptService(ReceiptService):
    """
    Publishes receipts to a Hedera HCS topic and caches them locally.

    Args:
        topic_id:     HCS topic ID (e.g. "0.0.12345").
        operator_id:  Hedera account ID of the signing operator.
        operator_key: Ed25519 private key (DER or hex encoded).
        network:      "testnet" (default) or "mainnet".
    """

    def __init__(
        self,
        topic_id: str,
        operator_id: str,
        operator_key: str,
        network: str = "testnet",
    ) -> None:
        self._topic_id = topic_id
        self._operator_id = operator_id
        self._operator_key = operator_key
        self._network = network
        self._cache: dict[str, ReceiptModel] = {}

    async def publish_receipt(self, receipt: ReceiptModel) -> ReceiptModel:
        """
        Cache the receipt and publish it to HCS in a thread pool executor.
        Returns the (possibly updated) receipt; never raises.
        """
        try:
            loop = asyncio.get_event_loop()
            client = await loop.run_in_executor(
                None,
                _build_hedera_client,
                self._operator_id,
                self._operator_key,
                self._network,
            )
            if client is None:
                raise RuntimeError(
                    "Hedera client could not be initialised. "
                    "Check HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY."
                )

            message = json.dumps(receipt.model_dump())
            seq = await loop.run_in_executor(
                None,
                _submit_to_hcs_sync,
                client,
                self._topic_id,
                message,
            )
            receipt.hcs_status = "published"
            receipt.hcs_error = None
            if seq:
                receipt.hcs_sequence_number = seq
        except Exception as exc:  # noqa: BLE001
            receipt.hcs_status = "failed"
            receipt.hcs_error = str(exc)

        self._cache[receipt.transaction_id] = receipt
        return receipt

    def get_receipt(self, tx_id: str) -> Optional[ReceiptModel]:
        """Return the cached receipt for the given transaction ID, or None."""
        return self._cache.get(tx_id)
