#!/usr/bin/env python3
"""
Create an HCS topic for HACK receipt logging.

Usage (from project root, with venv active):
    python scripts/create_topic.py

Requires HEDERA_OPERATOR_ID and HEDERA_OPERATOR_KEY in .env.
Prints the new topic ID — paste it into HCS_RECEIPT_TOPIC_ID in your .env.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main() -> None:
    operator_id  = os.environ.get("HEDERA_OPERATOR_ID", "")
    operator_key = os.environ.get("HEDERA_OPERATOR_KEY", "")
    network      = os.environ.get("HEDERA_NETWORK", "testnet")

    if not operator_id or "XXXX" in operator_id:
        print("ERROR: Set HEDERA_OPERATOR_ID in your .env file first.")
        sys.exit(1)
    if not operator_key or "..." in operator_key:
        print("ERROR: Set HEDERA_OPERATOR_KEY in your .env file first.")
        sys.exit(1)

    try:
        from hiero_sdk_python import (  # type: ignore
            Client, Network, AccountId, PrivateKey,
            TopicCreateTransaction,
        )
    except ImportError:
        print("ERROR: hiero_sdk_python not installed. Run ./scripts/install.sh first.")
        sys.exit(1)

    print(f"Connecting to Hedera {network}...")
    client = Client(Network(network=network))
    client.set_operator(
        AccountId.from_string(operator_id),
        PrivateKey.from_string(operator_key),
    )

    print("Creating HCS topic for HACK receipts...")
    receipt = TopicCreateTransaction().execute(client)
    topic_id = str(receipt.topicId)

    print()
    print(f"  ✅  Topic created: {topic_id}")
    print()
    print("Add this to your .env:")
    print(f"  HCS_RECEIPT_TOPIC_ID={topic_id}")
    print()
    print(f"View on HashScan: https://hashscan.io/{network}/topic/{topic_id}")


if __name__ == "__main__":
    main()
