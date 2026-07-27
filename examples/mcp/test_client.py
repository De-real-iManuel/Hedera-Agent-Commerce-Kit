"""
examples/mcp/test_client.py
----------------------------
Manual smoke test for the HACK MCP server — no wallet required.

Tests the 402 challenge flow for every tool by calling them without
a transaction_id, then prints the payment instructions so you can
complete a real payment if desired.

Run:
    python examples/mcp/test_client.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv
load_dotenv()

# Import the server's tool dispatch directly — no subprocess needed for testing
from examples.mcp.server import _container, _settings, call_tool  # type: ignore


SEPARATOR = "─" * 60


async def test_payment_required(tool_name: str, args: dict) -> dict:
    """Call a tool without payment — expect a 402 response."""
    print(f"\n{SEPARATOR}")
    print(f"Tool: {tool_name}")
    print(f"Args (no payment): {json.dumps({k: v for k, v in args.items()}, indent=2)}")

    results = await call_tool(tool_name, args)
    text = results[0].text
    parsed = json.loads(text)

    assert parsed.get("status") == 402, (
        f"Expected 402 payment_required, got {parsed.get('status')}"
    )
    assert "quote_id" in parsed, "Expected quote_id in response"
    assert "receiver" in parsed, "Expected receiver in response"

    print(f"\n✓ Received payment_required (402)")
    print(f"  quote_id  : {parsed['quote_id']}")
    print(f"  receiver  : {parsed['receiver']}")
    print(f"  amount    : {parsed['price']['amount']} {parsed['price']['asset']}")
    print(f"  expires_in: {parsed.get('expires_in_seconds')}s")
    print(f"\n  To complete a real payment:")
    print(f"  {parsed['retry_instructions']}")
    return parsed


async def test_with_payment(tool_name: str, args: dict, transaction_id: str, quote_id: str) -> None:
    """Call a tool with a real payment proof."""
    full_args = {**args, "transaction_id": transaction_id, "quote_id": quote_id}
    print(f"\n{SEPARATOR}")
    print(f"Tool: {tool_name} (with payment proof)")

    results = await call_tool(tool_name, full_args)
    text = results[0].text
    parsed = json.loads(text)

    print(f"\n  status : {parsed.get('status')}")
    print(f"  receipt: {json.dumps(parsed.get('receipt', {}), indent=4)}")
    print(f"  result : {json.dumps(parsed.get('result', {}), indent=4)}")


async def main() -> None:
    print("HACK Hedera MCP Server — Smoke Test")
    print(f"Network  : {_settings.hedera_network}")
    print(f"Receiver : {_settings.x402_payment_receiver_account_id}")
    print(f"Amount   : {_settings.x402_payment_amount_hbar} HBAR per call")

    # ── Test 1: analyze_hedera_account ────────────────────────────────────────
    challenge1 = await test_payment_required(
        "analyze_hedera_account",
        {"account_id": _settings.x402_payment_receiver_account_id},
    )

    # ── Test 2: query_hcs_topic ───────────────────────────────────────────────
    if _settings.hcs_receipt_topic_id:
        challenge2 = await test_payment_required(
            "query_hcs_topic",
            {"topic_id": _settings.hcs_receipt_topic_id, "limit": 5},
        )
    else:
        print(f"\n{SEPARATOR}")
        print("Skipping query_hcs_topic — HCS_RECEIPT_TOPIC_ID not set in .env")

    # ── Test 3: generate_compliance_report ────────────────────────────────────
    challenge3 = await test_payment_required(
        "generate_compliance_report",
        {
            "payment_transaction_id": "0.0.9075201@1784939817.181941398",
            "quote_id_to_audit": "example-quote-id",
        },
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEPARATOR}")
    print("✓ All tools correctly returned 402 payment_required")
    print("\nTo test with a real payment:")
    print(f"  1. Send {_settings.x402_payment_amount_hbar} HBAR to"
          f" {_settings.x402_payment_receiver_account_id}"
          f" with memo '{_settings.x402_payment_memo}'")
    print(f"  2. Run: python examples/mcp/test_client.py --paid"
          f" --tx 0.0.XXXXX@TIMESTAMP"
          f" --quote {challenge1['quote_id']}")
    print(f"\n  Or paste server.py into the HACK portal at"
          f" http://localhost:3000/certification")
    print(f"  to run an automated compliance audit.\n")


if __name__ == "__main__":
    # Optional: run a real paid test if --paid flag is given
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--paid", action="store_true")
    parser.add_argument("--tx", default="")
    parser.add_argument("--quote", default="")
    args = parser.parse_args()

    if args.paid:
        if not args.tx or not args.quote:
            print("--paid requires --tx <transaction_id> and --quote <quote_id>")
            sys.exit(1)

        async def run_paid() -> None:
            await test_with_payment(
                "analyze_hedera_account",
                {"account_id": _settings.x402_payment_receiver_account_id},
                args.tx,
                args.quote,
            )
        asyncio.run(run_paid())
    else:
        asyncio.run(main())
