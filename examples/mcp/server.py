"""
examples/mcp/server.py
-----------------------
HACK Hedera MCP Server — pay-per-call tools via x402 + Hedera.

Supports three transports:
  stdio     — for Claude Desktop / Continue / any stdio MCP client
  sse       — legacy SSE transport (Claude Desktop remote, older clients)
  http      — Streamable HTTP transport (ChatGPT, modern MCP clients)

All tools are pay-per-call. Flow:
  1. Call without proof → receives payment_required (402) JSON
  2. Send HBAR to receiver using any Hedera wallet
  3. Call again with (transaction_id, quote_id) → Mirror Node verifies,
     state machine advances, HCS receipt published, result returned

Running:
  pip install mcp uvicorn
  python examples/mcp/server.py                          # stdio
  python examples/mcp/server.py --transport sse          # SSE on :9000
  python examples/mcp/server.py --transport http         # HTTP on :9000 (ChatGPT)

ngrok for public access:
  ngrok http 9000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv
load_dotenv()

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp>=1.0 required. Install with: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

from hack import ServiceContainer, PaymentStatus, ReceiptModel
from hack.core.exceptions import (
    AlreadyConsumedError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
)

# ── Service container ────────────────────────────────────────────────────────
_container = ServiceContainer.from_settings()
_settings = _container.settings

# ── FastMCP server ───────────────────────────────────────────────────────────
# TransportSecuritySettings controls DNS rebinding protection.
# We allow localhost + ngrok wildcard so the server works both locally
# and when exposed via ngrok tunnel.
try:
    from mcp.server.transport_security import TransportSecuritySettings
    _transport_security = TransportSecuritySettings(
        # Disable DNS rebinding protection so ngrok tunnels work.
        # ngrok already provides TLS + host verification at the tunnel level.
        # Re-enable with specific allowed_hosts for production deployments.
        enable_dns_rebinding_protection=False,
    )
except ImportError:
    _transport_security = None

mcp = FastMCP(
    "HACK Hedera MCP Server",
    instructions=(
        "All tools require x402 HBAR micropayment. "
        "Call any tool without payment proof to receive a payment_required (402) response "
        "containing quote_id, receiver, amount, and expiry. "
        f"Send {_settings.x402_payment_amount_hbar} HBAR to the receiver on Hedera "
        f"{_settings.hedera_network}, then retry with transaction_id and quote_id."
    ),
    transport_security=_transport_security,
)


# ── Payment gate helper ──────────────────────────────────────────────────────

async def _payment_gate(
    tool_name: str,
    transaction_id: str,
    quote_id: str,
) -> tuple[bool, dict]:
    """
    Returns (is_paid, result_or_challenge).
    If not paid, result_or_challenge is the 402 challenge dict.
    If paid and verified, returns (True, {}) and the lifecycle is advanced.
    """
    if not transaction_id or not quote_id:
        quote = _container.lifecycle.create_quote(
            endpoint=f"mcp.{tool_name}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            receiver=_settings.x402_payment_receiver_account_id,
        )
        return False, {
            "type": "payment_required",
            "status": 402,
            "tool": tool_name,
            "quote_id": quote.quote_id,
            "price": {
                "amount": str(quote.amount_hbar),
                "asset": "HBAR",
                "network": _settings.hedera_network,
            },
            "receiver": quote.receiver,
            "memo": _settings.x402_payment_memo,
            "expires_at": int(quote.expires_at),
            "expires_in_seconds": max(0, int(quote.expires_at - time.time())),
            "retry_instructions": (
                f"1. Send {quote.amount_hbar} HBAR to {quote.receiver} "
                f"with memo '{_settings.x402_payment_memo}'. "
                f"2. Call this tool again with transaction_id=<tx-id> and quote_id={quote.quote_id}."
            ),
        }

    # Verify on Mirror Node
    try:
        min_tinybars = int(_settings.x402_payment_amount_hbar * 100_000_000)
        await _container.verifier.verify(
            transaction_id=transaction_id,
            receiver=_settings.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=_settings.hedera_network,
        )
    except ValueError as exc:
        return False, {"status": 402, "error": "payment_not_verified", "detail": str(exc), "retryable": True}
    except Exception as exc:  # noqa: BLE001
        return False, {"status": 502, "error": "verifier_unavailable", "detail": str(exc), "retryable": True}

    # Advance lifecycle
    try:
        _container.lifecycle.advance_to_verified(quote_id, transaction_id)
        _container.lifecycle.advance_to_granted(quote_id)
    except (QuoteNotFoundError, PaymentExpiredError, ReplayError, AlreadyConsumedError) as exc:
        return False, {"status": 409, "error": type(exc).__name__, "detail": str(exc)}
    except ValueError as exc:
        return False, {"status": 409, "error": "state_error", "detail": str(exc)}

    return True, {}


async def _publish_receipt(tool_name: str, transaction_id: str, quote_id: str) -> dict:
    """Consume quote and publish HCS receipt."""
    try:
        _container.lifecycle.advance_to_consumed(quote_id)
    except Exception:  # noqa: BLE001
        pass

    receipt = ReceiptModel(
        transaction_id=transaction_id,
        caller="mcp-client",
        endpoint=f"mcp.{tool_name}",
        amount_hbar=_settings.x402_payment_amount_hbar,
        timestamp=int(time.time()),
        hashscan_url=(
            f"https://hashscan.io/{_settings.hedera_network}/transaction/{transaction_id}"
        ),
    )
    published = await _container.receipt_service.publish_receipt(receipt)

    try:
        from hack.models.quote import UsageRecord
        _container.metering.record(UsageRecord(
            transaction_id=transaction_id,
            caller="mcp-client",
            endpoint=f"mcp.{tool_name}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            timestamp=int(time.time()),
        ))
    except Exception:  # noqa: BLE001
        pass

    return {"hcs_status": published.hcs_status, "hashscan_url": published.hashscan_url}


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def analyze_hedera_account(
    account_id: str,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Fetch live account data from the Hedera Mirror Node.
    Returns balance, memo, auto-renew period, and recent transactions.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _payment_gate("analyze_hedera_account", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    import httpx
    network = _settings.hedera_network
    base = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{base}/api/v1/accounts/{account_id}")
        if r.status_code == 404:
            result = {"error": f"Account {account_id} not found on {network}."}
        else:
            r.raise_for_status()
            data = r.json()
            tx_r = await client.get(f"{base}/api/v1/transactions",
                                    params={"account.id": account_id, "limit": 5, "order": "desc"})
            recent = [{"transaction_id": tx.get("transaction_id"), "name": tx.get("name"),
                       "result": tx.get("result")} for tx in tx_r.json().get("transactions", [])] if tx_r.status_code == 200 else []
            bal = data.get("balance", {}).get("balance", 0)
            result = {
                "account_id": data.get("account"), "network": network,
                "balance_hbar": round(bal / 100_000_000, 8), "balance_tinybars": bal,
                "memo": data.get("memo", ""), "recent_transactions": recent,
                "hashscan_url": f"https://hashscan.io/{network}/account/{account_id}",
            }

    receipt = await _publish_receipt("analyze_hedera_account", transaction_id, quote_id)
    return json.dumps({"status": "ok", "result": result, "receipt": receipt}, indent=2)


@mcp.tool()
async def query_hcs_topic(
    topic_id: str,
    limit: int = 10,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Fetch recent messages from a Hedera Consensus Service topic.
    Returns message content, sequence numbers, and timestamps.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _payment_gate("query_hcs_topic", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    import httpx, base64
    network = _settings.hedera_network
    base = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{base}/api/v1/topics/{topic_id}/messages",
                             params={"limit": min(limit, 25), "order": "desc"})
        if r.status_code == 404:
            result = {"error": f"Topic {topic_id} not found."}
        else:
            r.raise_for_status()
            messages = []
            for msg in r.json().get("messages", []):
                raw = msg.get("message", "")
                try:
                    decoded = base64.b64decode(raw).decode("utf-8")
                    content = json.loads(decoded) if decoded.startswith("{") else decoded
                except Exception:
                    content = raw
                messages.append({"sequence_number": msg.get("sequence_number"),
                                  "consensus_timestamp": msg.get("consensus_timestamp"),
                                  "content": content})
            result = {"topic_id": topic_id, "network": network,
                      "message_count": len(messages), "messages": messages,
                      "hashscan_url": f"https://hashscan.io/{network}/topic/{topic_id}"}

    receipt = await _publish_receipt("query_hcs_topic", transaction_id, quote_id)
    return json.dumps({"status": "ok", "result": result, "receipt": receipt}, indent=2)


@mcp.tool()
async def generate_compliance_report(
    payment_transaction_id: str,
    quote_id_to_audit: str,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Run HACK compliance rules against a Hedera payment transaction.
    Returns structured compliance report with pass/fail rules and HCS receipt.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _payment_gate("generate_compliance_report", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    import httpx, uuid as _uuid, time as _time
    from hack.models.quote import Quote, PaymentStatus as PS

    quote = _container.lifecycle.get_quote(quote_id_to_audit)
    if quote is None:
        quote = Quote(
            quote_id=quote_id_to_audit, endpoint="external",
            amount_hbar=_settings.x402_payment_amount_hbar,
            receiver=_settings.x402_payment_receiver_account_id,
            resource_hash=_uuid.uuid4().hex,
            issued_at=_time.time() - 60, expires_at=_time.time() + 540,
            status=PS.GRANTED, transaction_id=payment_transaction_id,
        )

    network = _settings.hedera_network
    base = "https://mainnet-public.mirrornode.hedera.com" if network == "mainnet" else "https://testnet.mirrornode.hedera.com"
    tx_data: dict = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{base}/api/v1/transactions/{payment_transaction_id}")
        if r.status_code == 200:
            tx_data = r.json().get("transactions", [{}])[0]

    check = await _container.compliance_engine.check(
        quote=quote, transaction_id=payment_transaction_id, tx_data=tx_data
    )
    receipt = await _publish_receipt("generate_compliance_report", transaction_id, quote_id)

    return json.dumps({
        "status": "ok",
        "result": {
            "passed": check.passed,
            "transaction_id": check.transaction_id,
            "checked_at": check.checked_at,
            "rules": [{"rule_id": r.rule_id, "name": r.name,
                       "passed": r.passed, "detail": r.detail} for r in check.rules],
        },
        "receipt": receipt,
    }, indent=2)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="HACK Hedera MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"],
                        default="stdio", help="Transport (default: stdio)")
    parser.add_argument("--port", type=int, default=9000, help="Port for sse/http (default: 9000)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"\nHACK Hedera MCP Server")
    print(f"  Transport: {args.transport}")
    print(f"  Network  : {_settings.hedera_network}")
    print(f"  Receiver : {_settings.x402_payment_receiver_account_id}")
    print(f"  Amount   : {_settings.x402_payment_amount_hbar} HBAR/call\n")

    if args.transport == "stdio":
        print("Running on stdio — connect with Claude Desktop or any stdio MCP client", file=sys.stderr)
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        print(f"SSE endpoint  : http://{args.host}:{args.port}/sse")
        print(f"Messages      : http://{args.host}:{args.port}/messages/\n")
        import uvicorn
        uvicorn.run(
            mcp.sse_app(),
            host=args.host,
            port=args.port,
            log_level="info",
            # Allow ngrok and any reverse-proxy host headers
            server_header=False,
            proxy_headers=True,
        )
    else:  # http — Streamable HTTP (ChatGPT, modern clients)
        print(f"HTTP endpoint : http://{args.host}:{args.port}/mcp")
        print(f"ChatGPT URL   : https://<your-ngrok-domain>/mcp\n")
        import uvicorn
        uvicorn.run(
            mcp.streamable_http_app(),
            host=args.host,
            port=args.port,
            log_level="info",
            proxy_headers=True,
        )


if __name__ == "__main__":
    main()
