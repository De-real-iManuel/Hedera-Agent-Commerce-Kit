"""
examples/mcp/server.py
-----------------------
A production-quality MCP server with x402 payment gating via HACK.

Every tool in this server is pay-per-call. The payment flow is:

  1. Call any tool without proof  → MCP tool returns a payment_required (402)
     response containing a quote_id, receiver, amount, and expiry.

  2. Client sends HBAR to the receiver account using any Hedera wallet
     (HashPack, Kabila, programmatic transfer via hedera-sdk-python).

  3. Call the same tool again with (transaction_id, quote_id) embedded in
     the arguments → HACK verifies on Mirror Node, advances the state
     machine, publishes an HCS receipt, and returns the real result.

Tools exposed
-------------
  analyze_hedera_account   — fetch live account data from Mirror Node
  query_hcs_topic          — fetch messages from an HCS topic
  generate_compliance_report — run the HACK compliance engine against a tx

Running this server
-------------------
  # Install MCP server library
  pip install mcp

  # Run as stdio MCP server (compatible with Claude Desktop, Continue, etc.)
  python examples/mcp/server.py

  # Or as SSE server for remote agents
  python examples/mcp/server.py --transport sse --port 9000

Connecting to Claude Desktop
-----------------------------
  Add to ~/Library/Application Support/Claude/claude_desktop_config.json:

  {
    "mcpServers": {
      "hack-hedera": {
        "command": "python",
        "args": ["/path/to/examples/mcp/server.py"],
        "env": {
          "HEDERA_OPERATOR_ID": "0.0.XXXXXX",
          "HEDERA_OPERATOR_KEY": "302e...",
          "X402_PAYMENT_RECEIVER_ACCOUNT_ID": "0.0.XXXXXX",
          "HCS_RECEIPT_TOPIC_ID": "0.0.XXXXXX",
          "GROQ_API_KEY": "gsk_..."
        }
      }
    }
  }
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time

# ── Make the project root importable when run from any working directory ──────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.server.sse import SseServerTransport
    from mcp.types import (
        CallToolResult,
        TextContent,
        Tool,
    )
except ImportError:
    print(
        "ERROR: The 'mcp' package is required.\n"
        "Install it with:  pip install mcp\n",
        file=sys.stderr,
    )
    sys.exit(1)

from hack import (
    ServiceContainer,
    PaymentStatus,
    ReceiptModel,
)
from hack.core.exceptions import (
    AlreadyConsumedError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
)

# ── One shared service container for the lifetime of this process ─────────────
_container = ServiceContainer.from_settings()
_settings = _container.settings

# ─── Server definition ────────────────────────────────────────────────────────

server = Server("hack-hedera-mcp")

# ─── Tool schemas ─────────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="analyze_hedera_account",
        description=(
            "Fetch live account data from the Hedera Mirror Node for a given account ID. "
            "Returns balance, memo, auto-renew period, and recent transaction count. "
            "Costs 0.5 HBAR per call — provide transaction_id + quote_id to pay."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Hedera account ID to inspect (e.g. 0.0.123456)",
                },
                "transaction_id": {
                    "type": "string",
                    "description": "Hedera transaction ID proving payment (e.g. 0.0.9075201@1784939817.181941398)",
                },
                "quote_id": {
                    "type": "string",
                    "description": "Quote ID from the payment_required response",
                },
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="query_hcs_topic",
        description=(
            "Fetch the most recent messages from a Hedera Consensus Service topic. "
            "Returns message content, sequence numbers, and consensus timestamps. "
            "Costs 0.5 HBAR per call — provide transaction_id + quote_id to pay."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic_id": {
                    "type": "string",
                    "description": "HCS topic ID to query (e.g. 0.0.9702133)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return (default 10, max 25)",
                    "default": 10,
                },
                "transaction_id": {"type": "string"},
                "quote_id": {"type": "string"},
            },
            "required": ["topic_id"],
        },
    ),
    Tool(
        name="generate_compliance_report",
        description=(
            "Run the HACK compliance engine against a Hedera payment transaction. "
            "Returns a structured compliance report with pass/fail rules and an "
            "immutable HCS receipt anchoring the result. "
            "Costs 0.5 HBAR per call — provide transaction_id + quote_id to pay."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "payment_transaction_id": {
                    "type": "string",
                    "description": "The Hedera transaction ID to audit for compliance",
                },
                "quote_id_to_audit": {
                    "type": "string",
                    "description": "The quote_id associated with the payment to audit",
                },
                "transaction_id": {
                    "type": "string",
                    "description": "Hedera transaction ID proving payment for THIS tool call",
                },
                "quote_id": {
                    "type": "string",
                    "description": "Quote ID from the payment_required response for THIS tool call",
                },
            },
            "required": ["payment_transaction_id", "quote_id_to_audit"],
        },
    ),
]


# ─── Tool listing ─────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


# ─── Tool dispatch ────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Route tool calls through the x402 payment gate."""

    transaction_id = (arguments.get("transaction_id") or "").strip()
    quote_id = (arguments.get("quote_id") or "").strip()

    # ── Step 1: No proof → issue a quote, return 402 ─────────────────────────
    if not transaction_id or not quote_id:
        quote = _container.lifecycle.create_quote(
            endpoint=f"mcp.{name}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            receiver=_settings.x402_payment_receiver_account_id,
        )
        network = _settings.hedera_network
        result = {
            "type": "payment_required",
            "status": 402,
            "tool": name,
            "quote_id": quote.quote_id,
            "resource": f"mcp.{name}",
            "resource_hash": quote.resource_hash,
            "price": {
                "amount": str(quote.amount_hbar),
                "asset": "HBAR",
                "network": network,
            },
            "receiver": quote.receiver,
            "memo": _settings.x402_payment_memo,
            "expires_at": int(quote.expires_at),
            "expires_in_seconds": max(0, int(quote.expires_at - time.time())),
            "retry_instructions": (
                f"1. Send {quote.amount_hbar} HBAR to {quote.receiver} "
                f"with memo '{_settings.x402_payment_memo}' using any Hedera wallet. "
                f"2. Call this tool again with the same arguments plus "
                f"transaction_id=<your-tx-id> and quote_id={quote.quote_id}."
            ),
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # ── Step 2: Verify payment on Mirror Node ─────────────────────────────────
    try:
        min_tinybars = int(_settings.x402_payment_amount_hbar * 100_000_000)
        await _container.verifier.verify(
            transaction_id=transaction_id,
            receiver=_settings.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=_settings.hedera_network,
        )
    except ValueError as exc:
        return [TextContent(type="text", text=json.dumps({
            "status": 402,
            "error": "payment_not_verified",
            "detail": str(exc),
            "hint": "Mirror Node may lag ~3 seconds after consensus. Retry shortly.",
            "retryable": True,
        }, indent=2))]
    except Exception as exc:  # noqa: BLE001
        return [TextContent(type="text", text=json.dumps({
            "status": 502,
            "error": "verifier_unavailable",
            "detail": str(exc),
            "retryable": True,
        }, indent=2))]

    # ── Step 3: Advance the lifecycle state machine ───────────────────────────
    try:
        _container.lifecycle.advance_to_verified(quote_id, transaction_id)
        _container.lifecycle.advance_to_granted(quote_id)
    except (QuoteNotFoundError, PaymentExpiredError, ReplayError) as exc:
        code = 409 if isinstance(exc, (ReplayError, AlreadyConsumedError)) else 402
        return [TextContent(type="text", text=json.dumps({
            "status": code,
            "error": type(exc).__name__,
            "detail": str(exc),
        }, indent=2))]
    except ValueError as exc:
        return [TextContent(type="text", text=json.dumps({
            "status": 409,
            "error": "state_error",
            "detail": str(exc),
        }, indent=2))]

    # ── Step 4: Execute the tool ──────────────────────────────────────────────
    try:
        tool_result = await _dispatch(name, arguments)
    except Exception as exc:  # noqa: BLE001
        # Still consume the quote — the payment was valid, execution failed.
        _safe_consume(quote_id)
        return [TextContent(type="text", text=json.dumps({
            "status": 500,
            "error": "tool_execution_failed",
            "detail": str(exc),
            "note": "Payment was verified and consumed. Quote cannot be reused.",
        }, indent=2))]

    # ── Step 5: Mark consumed + publish HCS receipt ───────────────────────────
    _safe_consume(quote_id)

    receipt = ReceiptModel(
        transaction_id=transaction_id,
        caller="mcp-client",
        endpoint=f"mcp.{name}",
        amount_hbar=_settings.x402_payment_amount_hbar,
        timestamp=int(time.time()),
        hashscan_url=(
            f"https://hashscan.io/{_settings.hedera_network}"
            f"/transaction/{transaction_id}"
        ),
    )
    published = await _container.receipt_service.publish_receipt(receipt)

    _container.metering.record(
        __import__("hack.models.quote", fromlist=["UsageRecord"]).UsageRecord(
            transaction_id=transaction_id,
            caller="mcp-client",
            endpoint=f"mcp.{name}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            timestamp=int(time.time()),
        )
    )

    # ── Step 6: Wrap and return ───────────────────────────────────────────────
    response = {
        "status": "ok",
        "tool": name,
        "result": tool_result,
        "payment": {
            "transaction_id": transaction_id,
            "quote_id": quote_id,
            "amount_hbar": _settings.x402_payment_amount_hbar,
            "consumed": True,
        },
        "receipt": {
            "hcs_status": published.hcs_status,
            "hcs_error": published.hcs_error,
            "hashscan_url": published.hashscan_url,
        },
    }
    return [TextContent(type="text", text=json.dumps(response, indent=2))]


# ─── Tool implementations ─────────────────────────────────────────────────────

async def _dispatch(name: str, args: dict) -> dict:
    """Call the actual tool logic after payment is confirmed."""
    if name == "analyze_hedera_account":
        return await _analyze_hedera_account(args["account_id"])
    if name == "query_hcs_topic":
        return await _query_hcs_topic(
            args["topic_id"],
            limit=min(int(args.get("limit", 10)), 25),
        )
    if name == "generate_compliance_report":
        return await _generate_compliance_report(
            args["payment_transaction_id"],
            args["quote_id_to_audit"],
        )
    raise ValueError(f"Unknown tool: {name}")


async def _analyze_hedera_account(account_id: str) -> dict:
    """Fetch live account data from the Hedera Mirror Node."""
    import httpx

    network = _settings.hedera_network
    base = (
        "https://mainnet-public.mirrornode.hedera.com"
        if network == "mainnet"
        else "https://testnet.mirrornode.hedera.com"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Account info
        r = await client.get(f"{base}/api/v1/accounts/{account_id}")
        if r.status_code == 404:
            return {"error": f"Account {account_id} not found on {network}."}
        r.raise_for_status()
        data = r.json()

        # Recent transactions (lightweight)
        tx_r = await client.get(
            f"{base}/api/v1/transactions",
            params={"account.id": account_id, "limit": 5, "order": "desc"},
        )
        recent_txs = []
        if tx_r.status_code == 200:
            for tx in tx_r.json().get("transactions", []):
                recent_txs.append({
                    "transaction_id": tx.get("transaction_id"),
                    "consensus_timestamp": tx.get("consensus_timestamp"),
                    "name": tx.get("name"),
                    "result": tx.get("result"),
                })

    balance_tinybars = data.get("balance", {}).get("balance", 0)
    return {
        "account_id": data.get("account"),
        "network": network,
        "balance_hbar": round(balance_tinybars / 100_000_000, 8),
        "balance_tinybars": balance_tinybars,
        "memo": data.get("memo", ""),
        "auto_renew_period": data.get("auto_renew_period"),
        "expiry_timestamp": data.get("expiry_timestamp"),
        "key_type": data.get("key", {}).get("_type"),
        "created_timestamp": data.get("created_timestamp"),
        "recent_transactions": recent_txs,
        "hashscan_url": f"https://hashscan.io/{network}/account/{account_id}",
    }


async def _query_hcs_topic(topic_id: str, limit: int = 10) -> dict:
    """Fetch recent messages from an HCS topic via the Mirror Node."""
    import httpx

    network = _settings.hedera_network
    base = (
        "https://mainnet-public.mirrornode.hedera.com"
        if network == "mainnet"
        else "https://testnet.mirrornode.hedera.com"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{base}/api/v1/topics/{topic_id}/messages",
            params={"limit": limit, "order": "desc"},
        )
        if r.status_code == 404:
            return {"error": f"Topic {topic_id} not found on {network}."}
        r.raise_for_status()
        data = r.json()

    messages = []
    for msg in data.get("messages", []):
        # Message content is base64-encoded
        import base64
        raw = msg.get("message", "")
        try:
            decoded = base64.b64decode(raw).decode("utf-8")
            # Try to parse as JSON for structured display
            try:
                content = json.loads(decoded)
            except json.JSONDecodeError:
                content = decoded
        except Exception:  # noqa: BLE001
            content = raw

        messages.append({
            "sequence_number": msg.get("sequence_number"),
            "consensus_timestamp": msg.get("consensus_timestamp"),
            "content": content,
            "payer_account_id": msg.get("payer_account_id"),
        })

    return {
        "topic_id": topic_id,
        "network": network,
        "message_count": len(messages),
        "messages": messages,
        "hashscan_url": f"https://hashscan.io/{network}/topic/{topic_id}",
    }


async def _generate_compliance_report(
    payment_tx_id: str,
    quote_id_to_audit: str,
) -> dict:
    """Run HACK compliance rules against a payment transaction."""
    from hack.models.quote import Quote, PaymentStatus as PS
    import time as _time
    import uuid as _uuid

    # Build a synthetic quote from the transaction to run rules against
    quote = _container.lifecycle.get_quote(quote_id_to_audit)

    if quote is None:
        # Quote not in this process's memory — build a minimal synthetic one
        # so we can still run the on-chain verification rules
        quote = Quote(
            quote_id=quote_id_to_audit,
            endpoint="external",
            amount_hbar=_settings.x402_payment_amount_hbar,
            receiver=_settings.x402_payment_receiver_account_id,
            resource_hash=_uuid.uuid4().hex,
            issued_at=_time.time() - 60,
            expires_at=_time.time() + 540,
            status=PS.GRANTED,
            transaction_id=payment_tx_id,
        )

    # Fetch raw tx data for rule evaluation
    import httpx
    network = _settings.hedera_network
    base = (
        "https://mainnet-public.mirrornode.hedera.com"
        if network == "mainnet"
        else "https://testnet.mirrornode.hedera.com"
    )

    tx_data: dict = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{base}/api/v1/transactions/{payment_tx_id}")
        if r.status_code == 200:
            tx_data = r.json().get("transactions", [{}])[0]

    # Run the compliance engine
    result = await _container.compliance_engine.check(
        quote=quote,
        transaction_id=payment_tx_id,
        tx_data=tx_data,
    )

    # Publish an HCS anchor for this compliance check
    anchor = ReceiptModel(
        transaction_id=payment_tx_id,
        caller="mcp-compliance",
        endpoint="compliance-check",
        amount_hbar=0.0,
        timestamp=int(time.time()),
        hashscan_url=f"https://hashscan.io/{network}/transaction/{payment_tx_id}",
    )
    published = await _container.receipt_service.publish_receipt(anchor)

    return {
        "passed": result.passed,
        "quote_id": result.quote_id,
        "transaction_id": result.transaction_id,
        "checked_at": result.checked_at,
        "rules": [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "passed": r.passed,
                "detail": r.detail,
            }
            for r in result.rules
        ],
        "hcs_anchor": {
            "status": published.hcs_status,
            "hashscan_url": published.hashscan_url,
        },
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _safe_consume(quote_id: str) -> None:
    """Advance to CONSUMED — non-fatal if already consumed or not found."""
    try:
        _container.lifecycle.advance_to_consumed(quote_id)
    except Exception:  # noqa: BLE001
        pass


# ─── Entry point ──────────────────────────────────────────────────────────────

async def _run_stdio() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


async def _run_sse(port: int) -> None:
    """Run the MCP server over SSE using Starlette + uvicorn."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.requests import Request
    from starlette.responses import JSONResponse, Response
    from starlette.routing import Mount, Route

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
            request.scope, request.receive, request._send  # noqa: SLF001
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    async def handle_root(request: Request) -> Response:
        """Health check / info endpoint at root — handles probe POSTs gracefully."""
        return JSONResponse({
            "service": "HACK Hedera MCP Server",
            "version": "1.0.0",
            "transport": "sse",
            "endpoints": {
                "sse": "/sse",
                "messages": "/messages/",
            },
            "tools": ["analyze_hedera_account", "query_hcs_topic", "generate_compliance_report"],
            "payment": {
                "network": _settings.hedera_network,
                "receiver": _settings.x402_payment_receiver_account_id,
                "amount_hbar": _settings.x402_payment_amount_hbar,
            },
            "note": "Connect via /sse endpoint. All tools require x402 HBAR payment.",
        })

    starlette_app = Starlette(
        routes=[
            Route("/",        endpoint=handle_root, methods=["GET", "POST"]),
            Route("/health",  endpoint=handle_root, methods=["GET"]),
            Route("/sse",     endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    config = uvicorn.Config(
        starlette_app, host="0.0.0.0", port=port,
        log_level="info", access_log=True,
    )
    srv = uvicorn.Server(config)
    print(f"\nHACK Hedera MCP Server (SSE)")
    print(f"  Local:    http://localhost:{port}")
    print(f"  SSE:      http://localhost:{port}/sse")
    print(f"  Messages: http://localhost:{port}/messages/")
    print(f"  Health:   http://localhost:{port}/health\n")
    await srv.serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="HACK Hedera MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port for SSE transport (default: 9000)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        asyncio.run(_run_sse(args.port))
    else:
        print("HACK Hedera MCP server running on stdio", file=sys.stderr)
        asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
