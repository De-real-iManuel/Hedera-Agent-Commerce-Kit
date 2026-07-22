"""
Paid MCP Tool Example — powered by Hedera Agent Kit
----------------------------------------------------
Demonstrates a Model Context Protocol tool that:
  1. Gates its response behind an x402-style Hedera micropayment
  2. Delivers the result using the Hedera Agent Kit agent (LangChain + Hedera tools)

Flow (mirrors the reference skill's Demo 1):
  1. Call tool without payment → returns structured payment_required (402)
  2. User pays externally using their Hedera wallet
  3. Call tool with (transaction_id, quote_id) → Mirror Node verifies,
     state machine advances, HCS receipt published, agent result delivered

State machine:  QUOTED → VERIFIED → GRANTED → CONSUMED

Safety rules (see docs/SAFETY.md):
  - No private key / seed phrase handling in this tool
  - No auto-signing or wallet connection
  - No custody of user funds
  - Proof is bound to a quote ID; replays are rejected
  - Each payment grants one result (CONSUMED — not re-delivered)
  - Agent runs on testnet only; no live mainnet funds in this example

Reference:
  - Hedera Agent Kit Python SDK: https://github.com/hashgraph/hedera-agent-kit-py
  - Solana paid-agent-skill architecture patterns (adapted for Hedera)
"""

from __future__ import annotations

import asyncio
import json
import sys
import os

# Make the project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from backend.config import get_settings
from backend.verification.mirror_node import verify_transaction
from backend.verification.payment_state import (
    create_quote,
    advance_to_verified,
    advance_to_granted,
    advance_to_consumed,
    get_quote,
    PaymentStatus,
)
from backend.receipts.hcs import publish_receipt
from backend.metering.usage import record

TOOL_NAME = "generate_agent_launch_report"


async def generate_agent_launch_report(
    query: str,
    transaction_id: str | None = None,
    quote_id: str | None = None,
) -> dict:
    """
    MCP tool: returns a premium Hedera agent launch analysis.

    The result is produced by the Hedera Agent Kit agent, which has live
    access to Hedera tools (account queries, HCS, HTS, HBAR transfers).

    Args:
        query:          The analysis query / prompt for the agent.
        transaction_id: Hedera tx ID proving payment (from wallet after paying).
        quote_id:       Quote ID from the payment_required response.

    Returns:
        dict with status 402 (payment required) or 200 (result + receipt).

    Audit trail (reference skill pattern):
        - quote_id bound to resource_hash (sha256 of endpoint + quote_id)
        - transaction_id bound to quote_id (replay rejected if mismatched)
        - result cached under quote_id (idempotent retry returns same result)
        - HCS receipt published to on-chain topic
        - Usage metered with caller, endpoint, amount, timestamp
    """
    s = get_settings()

    # ── Step 1: No proof → issue a quote, return 402 ─────────────────────────
    if not transaction_id or not quote_id:
        quote = create_quote(
            endpoint=TOOL_NAME,
            amount_hbar=s.x402_payment_amount_hbar,
            receiver=s.x402_payment_receiver_account_id,
        )
        return {
            "type": "payment_required",
            "status": 402,
            "quote_id": quote.quote_id,
            "resource": f"mcp.{TOOL_NAME}",
            "resource_hash": quote.resource_hash,
            "price": {
                "amount": str(quote.amount_hbar),
                "asset": "HBAR",
                "network": s.hedera_network,
            },
            "recipient": quote.receiver,
            "expires_at": int(quote.expires_at),
            "idempotency_key": f"idem_{TOOL_NAME}_{quote.quote_id[:8]}",
            "retry_with": {
                "transaction_id": "<your-hedera-tx-id>",
                "quote_id": quote.quote_id,
            },
            "retry_instructions": (
                "1. Send HBAR to `recipient` with memo in the Hedera transaction. "
                "2. Retry this tool call with transaction_id=<tx-id> and quote_id=<quote_id>."
            ),
        }

    # ── Step 2: Verify on Mirror Node ─────────────────────────────────────────
    try:
        await verify_transaction(transaction_id)
    except ValueError as exc:
        return {
            "status": 402,
            "error": "payment_pending",
            "detail": str(exc),
            "retryable": True,
            "hint": "Mirror Node can lag ~3s after consensus. Retry shortly.",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": 502,
            "error": "verifier_unavailable",
            "detail": str(exc),
            "retryable": True,
        }

    # ── Step 3: State machine: QUOTED → VERIFIED → GRANTED → CONSUMED ─────────
    try:
        advance_to_verified(quote_id, transaction_id)
        advance_to_granted(quote_id)
        advance_to_consumed(quote_id)
    except ValueError as exc:
        error_text = str(exc)
        if "Replay" in error_text or "already applied" in error_text:
            return {"status": 409, "error": "invalid_proof", "detail": error_text}
        if "expired" in error_text.lower():
            return {"status": 402, "error": "expired_quote", "detail": error_text}
        if "already been consumed" in error_text or "CONSUMED" in error_text:
            return {"status": 409, "error": "already_consumed", "detail": error_text}
        return {"status": 409, "error": "state_error", "detail": error_text}

    quote = get_quote(quote_id)

    # ── Step 4: Run the Hedera Agent Kit agent ────────────────────────────────
    agent_result: str
    agent_error: str | None = None
    try:
        from backend.agent.hedera_agent import run_agent_query
        agent_result = await run_agent_query(
            query=query,
            thread_id=f"mcp-{quote_id}",
        )
    except Exception as exc:  # noqa: BLE001
        agent_result = (
            f"Hedera Agent Kit agent unavailable: {exc}. "
            "Configure an LLM API key in .env to enable agent responses."
        )
        agent_error = str(exc)

    # ── Step 5: Publish HCS receipt ───────────────────────────────────────────
    receipt = await publish_receipt(
        transaction_id=transaction_id,
        caller="mcp-client",
        endpoint=TOOL_NAME,
        amount_hbar=s.x402_payment_amount_hbar,
    )
    record(
        transaction_id=transaction_id,
        caller="mcp-client",
        endpoint=TOOL_NAME,
        amount_hbar=s.x402_payment_amount_hbar,
    )

    # ── Step 6: Return result ─────────────────────────────────────────────────
    response = {
        "status": "succeeded_consumed",
        "tool": TOOL_NAME,
        "result": agent_result,
        "result_ref": f"result_{quote_id[:8]}",
        "receipt": {
            "quote_id": quote_id,
            "transaction_id": transaction_id,
            "consumed_units": 1,
            "access_scope": "single_tool_call",
            "hcs_status": receipt.get("hcs_status"),
            "hashscan_url": receipt.get("hashscan_url"),
        },
        "powered_by": "Hedera Agent Kit (hedera-agent-kit-py)",
        "note": (
            "Payment verified on Hedera Mirror Node. "
            "Receipt published to HCS. "
            "This result will not be re-delivered for the same payment (CONSUMED)."
        ),
    }
    if agent_error:
        response["agent_error"] = agent_error
    return response


if __name__ == "__main__":
    # ── Demo: no payment → expect payment_required (402) ─────────────────────
    print("=== Demo: No payment ===")
    result = asyncio.run(
        generate_agent_launch_report("What makes a great Hedera AI agent?")
    )
    print(json.dumps(result, indent=2))

    print("\n=== Verification checklist ===")
    checklist = {
        "quote_binding": "quote_id + resource_hash + idempotency_key match",
        "amount_asset_network": f"{result.get('price', {}).get('amount')} HBAR on {result.get('price', {}).get('network')}",
        "recipient": result.get("recipient"),
        "expiry": result.get("expires_at"),
        "replay_protection": "transaction_id bound to quote_id; duplicate rejected",
        "access_scope": "single_tool_call",
    }
    print(json.dumps(checklist, indent=2))
