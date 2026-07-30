"""
examples/mcp/server.py
-----------------------
HACK Hedera Bank Statement MCP Server

A paid MCP server that generates comprehensive Hedera account statements
using the Mirror Node REST API. All tools are pay-per-call via x402.

Tools
-----
  get_account_statement   — Full overview: balance, tokens, recent activity
  get_transaction_history — Paginated HBAR + token transfer history
  get_token_portfolio     — All HTS tokens held (fungible + NFTs)
  get_hcs_activity        — HCS topics submitted to by the account

Every call requires a Hedera micropayment:
  1. Call any tool → receive payment_required (402) with quote_id + receiver
  2. Send HBAR to receiver with the exact memo provided
  3. Call again with transaction_id + quote_id → Mirror Node verified, result delivered

Running
-------
  pip install mcp uvicorn httpx
  python examples/mcp/server.py                    # stdio (Claude Desktop)
  python examples/mcp/server.py --transport sse    # SSE on :9000
  python examples/mcp/server.py --transport http   # Streamable HTTP on :9000 (ChatGPT)

ngrok tunnel:
  ngrok http 9000
  # Then use https://<your-domain>/mcp in ChatGPT
"""

from __future__ import annotations

import argparse
import asyncio
import base64
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
    print("ERROR: mcp>=1.0 required. Run: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

from hack import ServiceContainer, ReceiptModel
from hack.core.exceptions import (
    AlreadyConsumedError, PaymentExpiredError, QuoteNotFoundError, ReplayError,
)

# ── Service container ────────────────────────────────────────────────────────
_container = ServiceContainer.from_settings()
_settings = _container.settings

NETWORK = _settings.hedera_network
MIRROR_BASE = (
    "https://mainnet-public.mirrornode.hedera.com"
    if NETWORK == "mainnet"
    else "https://testnet.mirrornode.hedera.com"
)
HASHSCAN_BASE = f"https://hashscan.io/{NETWORK}"

# ── FastMCP server ───────────────────────────────────────────────────────────
try:
    from mcp.server.transport_security import TransportSecuritySettings
    _transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False  # ngrok handles TLS
    )
except ImportError:
    _transport_security = None

mcp = FastMCP(
    "HACK Hedera Bank Statement",
    instructions=(
        "Generates paid Hedera account statements via Mirror Node. "
        "Each tool costs 0.5 HBAR. Call without payment to get a challenge, "
        "send HBAR with the exact memo, then retry with transaction_id + quote_id."
    ),
    transport_security=_transport_security,
)


# ── Mirror Node helpers ──────────────────────────────────────────────────────

async def _mirror_get(path: str, params: dict | None = None) -> dict:
    """GET from Mirror Node REST API."""
    import httpx
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{MIRROR_BASE}{path}", params=params or {})
        if r.status_code == 404:
            return {"_not_found": True}
        r.raise_for_status()
        return r.json()


def _tinybars_to_hbar(tinybars: int) -> str:
    hbar = tinybars / 100_000_000
    return f"{hbar:,.8f} ℏ"


def _ts_to_human(ts: str) -> str:
    """Convert consensus timestamp '1234567890.000000001' to readable date."""
    try:
        secs = float(ts.split(".")[0])
        import datetime
        return datetime.datetime.utcfromtimestamp(secs).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts


# ── Payment gate ─────────────────────────────────────────────────────────────

async def _gate(tool: str, tx_id: str, quote_id: str) -> tuple[bool, dict]:
    """Return (paid, challenge_or_empty). Handles full x402 lifecycle."""
    if not tx_id or not quote_id:
        quote = _container.lifecycle.create_quote(
            endpoint=f"mcp.{tool}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            receiver=_settings.x402_payment_receiver_account_id,
        )
        suffix = quote.quote_id[-6:]
        memo = f"{_settings.x402_payment_memo}-{suffix}"
        return False, {
            "type": "payment_required",
            "status": 402,
            "tool": tool,
            "quote_id": quote.quote_id,
            "price": {
                "amount": str(quote.amount_hbar),
                "asset": "HBAR",
                "network": NETWORK,
            },
            "receiver": quote.receiver,
            "memo": memo,
            "expires_at": int(quote.expires_at),
            "expires_in_seconds": max(0, int(quote.expires_at - time.time())),
            "instructions": (
                f"Send {quote.amount_hbar} HBAR to {quote.receiver} "
                f"with memo exactly: '{memo}'\n"
                f"Then call this tool again with:\n"
                f"  transaction_id = <your tx id>\n"
                f"  quote_id = {quote.quote_id}"
            ),
        }

    # Verify on Mirror Node (amount + receiver + memo suffix)
    try:
        min_tinybars = int(_settings.x402_payment_amount_hbar * 100_000_000)
        tx_data = await _container.verifier.verify(
            transaction_id=tx_id,
            receiver=_settings.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=NETWORK,
        )
        # Memo binding — prevents reusing old transactions
        expected = quote_id[-6:].lower()
        memo_raw = tx_data.get("memo_base64") or tx_data.get("memo") or ""
        try:
            memo_decoded = base64.b64decode(memo_raw).decode("utf-8", errors="replace").lower()
        except Exception:
            memo_decoded = memo_raw.lower()
        if expected and memo_decoded and expected not in memo_decoded:
            return False, {
                "status": 402, "error": "memo_mismatch",
                "detail": (
                    f"Transaction memo doesn't match this quote. "
                    f"Expected memo to contain '{expected}'. "
                    "Use the exact memo from the payment_required response."
                ),
                "retryable": False,
            }
    except ValueError as e:
        return False, {"status": 402, "error": "payment_not_verified",
                       "detail": str(e), "retryable": True}
    except Exception as e:  # noqa: BLE001
        return False, {"status": 502, "error": "verifier_unavailable",
                       "detail": str(e), "retryable": True}

    # Advance lifecycle
    try:
        _container.lifecycle.advance_to_verified(quote_id, tx_id)
        _container.lifecycle.advance_to_granted(quote_id)
    except (QuoteNotFoundError, PaymentExpiredError, ReplayError, AlreadyConsumedError) as e:
        return False, {"status": 409, "error": type(e).__name__, "detail": str(e)}
    except ValueError as e:
        return False, {"status": 409, "error": "state_error", "detail": str(e)}

    return True, {}


async def _receipt(tool: str, tx_id: str, quote_id: str) -> dict:
    """Consume quote and publish HCS receipt."""
    try:
        _container.lifecycle.advance_to_consumed(quote_id)
    except Exception:  # noqa: BLE001
        pass
    r = ReceiptModel(
        transaction_id=tx_id, caller="mcp-client",
        endpoint=f"mcp.{tool}",
        amount_hbar=_settings.x402_payment_amount_hbar,
        timestamp=int(time.time()),
        hashscan_url=f"{HASHSCAN_BASE}/transaction/{tx_id}",
    )
    pub = await _container.receipt_service.publish_receipt(r)
    try:
        from hack.models.quote import UsageRecord
        _container.metering.record(UsageRecord(
            transaction_id=tx_id, caller="mcp-client",
            endpoint=f"mcp.{tool}",
            amount_hbar=_settings.x402_payment_amount_hbar,
            timestamp=int(time.time()),
        ))
    except Exception:  # noqa: BLE001
        pass
    return {"hcs_status": pub.hcs_status, "hashscan_url": pub.hashscan_url}


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_account_statement(
    account_id: str,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Generate a full Hedera account statement.

    Returns: HBAR balance, USD value estimate, token count, recent
    transactions summary, and account metadata.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _gate("get_account_statement", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    # Fetch account info
    acct = await _mirror_get(f"/api/v1/accounts/{account_id}")
    if acct.get("_not_found"):
        await _receipt("get_account_statement", transaction_id, quote_id)
        return json.dumps({"error": f"Account {account_id} not found on {NETWORK}."})

    bal_tb = acct.get("balance", {}).get("balance", 0)
    bal_hbar = bal_tb / 100_000_000

    # Fetch recent transactions (last 10)
    txs_data = await _mirror_get(
        f"/api/v1/transactions",
        {"account.id": account_id, "limit": 10, "order": "desc"},
    )
    recent_txs = []
    for tx in txs_data.get("transactions", []):
        net = sum(
            t.get("amount", 0) for t in tx.get("transfers", [])
            if t.get("account") == account_id
        )
        recent_txs.append({
            "id": tx.get("transaction_id"),
            "type": tx.get("name"),
            "result": tx.get("result"),
            "time": _ts_to_human(tx.get("consensus_timestamp", "")),
            "net_hbar": _tinybars_to_hbar(net),
            "hashscan": f"{HASHSCAN_BASE}/transaction/{tx.get('transaction_id', '')}",
        })

    # Fetch token balances count
    tokens_data = await _mirror_get(
        f"/api/v1/accounts/{account_id}/tokens", {"limit": 5}
    )
    token_count = len(tokens_data.get("tokens", []))
    token_preview = [
        {"token_id": t.get("token_id"), "balance": t.get("balance")}
        for t in tokens_data.get("tokens", [])[:3]
    ]

    statement = {
        "account_id": acct.get("account"),
        "network": NETWORK,
        "statement_date": _ts_to_human(str(int(time.time())) + ".000000000"),
        "balance": {
            "hbar": round(bal_hbar, 8),
            "tinybars": bal_tb,
            "display": f"{bal_hbar:,.4f} ℏ",
        },
        "tokens_held": token_count,
        "token_preview": token_preview,
        "memo": acct.get("memo", ""),
        "created": _ts_to_human(acct.get("created_timestamp", "")),
        "auto_renew_period_days": round((acct.get("auto_renew_period") or 0) / 86400, 1),
        "recent_transactions": recent_txs,
        "hashscan_account": f"{HASHSCAN_BASE}/account/{account_id}",
        "_paid_via": "x402 · Hedera HBAR · HACK",
    }

    rec = await _receipt("get_account_statement", transaction_id, quote_id)
    return json.dumps({"statement": statement, "receipt": rec}, indent=2)


@mcp.tool()
async def get_transaction_history(
    account_id: str,
    limit: int = 25,
    transaction_type: str = "",
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Fetch full transaction history for a Hedera account.

    Returns paginated list of transactions with type, amount, counterparty,
    timestamp, and HashScan links.
    Optionally filter by type: CRYPTOTRANSFER, TOKENTRANSFER, CONTRACTCALL, etc.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _gate("get_transaction_history", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    params: dict = {"account.id": account_id, "limit": min(limit, 100), "order": "desc"}
    if transaction_type:
        params["transactiontype"] = transaction_type.upper()

    data = await _mirror_get("/api/v1/transactions", params)
    transactions = []
    for tx in data.get("transactions", []):
        # Net amount for this account
        transfers = tx.get("transfers", [])
        net = sum(
            t.get("amount", 0) for t in transfers if t.get("account") == account_id
        )
        # Counterparties
        counterparties = [
            t.get("account") for t in transfers
            if t.get("account") != account_id
            and t.get("account") not in ("0.0.98", "0.0.800")  # exclude fee accounts
            and abs(t.get("amount", 0)) > 0
        ][:3]

        # Token transfers
        token_transfers = [
            {
                "token_id": tt.get("token_id"),
                "amount": tt.get("amount"),
                "account": tt.get("account"),
            }
            for tt in tx.get("token_transfers", [])
            if tt.get("account") == account_id
        ]

        transactions.append({
            "transaction_id": tx.get("transaction_id"),
            "type": tx.get("name"),
            "result": tx.get("result"),
            "time": _ts_to_human(tx.get("consensus_timestamp", "")),
            "net_hbar": _tinybars_to_hbar(net),
            "direction": "IN" if net > 0 else ("OUT" if net < 0 else "NEUTRAL"),
            "counterparties": counterparties,
            "token_transfers": token_transfers,
            "memo": "",
            "hashscan": f"{HASHSCAN_BASE}/transaction/{tx.get('transaction_id', '')}",
        })

    summary = {
        "account_id": account_id,
        "network": NETWORK,
        "transactions_returned": len(transactions),
        "filter_type": transaction_type or "ALL",
        "transactions": transactions,
        "next_page": data.get("links", {}).get("next", ""),
        "_paid_via": "x402 · Hedera HBAR · HACK",
    }

    rec = await _receipt("get_transaction_history", transaction_id, quote_id)
    return json.dumps({"history": summary, "receipt": rec}, indent=2)


@mcp.tool()
async def get_token_portfolio(
    account_id: str,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Get the complete HTS token portfolio for a Hedera account.

    Returns all fungible tokens and NFTs held, with token IDs, balances,
    symbols, and HashScan links for each.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _gate("get_token_portfolio", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    tokens_data = await _mirror_get(
        f"/api/v1/accounts/{account_id}/tokens", {"limit": 100}
    )
    nfts_data = await _mirror_get(
        f"/api/v1/accounts/{account_id}/nfts", {"limit": 50}
    )

    fungible = []
    for t in tokens_data.get("tokens", []):
        tok_info = await _mirror_get(f"/api/v1/tokens/{t.get('token_id')}")
        fungible.append({
            "token_id": t.get("token_id"),
            "balance": t.get("balance"),
            "name": tok_info.get("name", ""),
            "symbol": tok_info.get("symbol", ""),
            "decimals": tok_info.get("decimals", 0),
            "type": tok_info.get("type", "FUNGIBLE_COMMON"),
            "hashscan": f"{HASHSCAN_BASE}/token/{t.get('token_id')}",
        })

    nfts = []
    for n in nfts_data.get("nfts", []):
        raw_meta = n.get("metadata", "")
        try:
            meta_decoded = base64.b64decode(raw_meta).decode("utf-8", errors="replace")
        except Exception:
            meta_decoded = raw_meta
        nfts.append({
            "token_id": n.get("token_id"),
            "serial_number": n.get("serial_number"),
            "metadata_uri": meta_decoded,
            "created": _ts_to_human(n.get("created_timestamp", "")),
            "hashscan": f"{HASHSCAN_BASE}/token/{n.get('token_id')}/{n.get('serial_number')}",
        })

    portfolio = {
        "account_id": account_id,
        "network": NETWORK,
        "fungible_tokens": len(fungible),
        "nfts_held": len(nfts),
        "fungible": fungible,
        "nfts": nfts,
        "hashscan_account": f"{HASHSCAN_BASE}/account/{account_id}",
        "_paid_via": "x402 · Hedera HBAR · HACK",
    }

    rec = await _receipt("get_token_portfolio", transaction_id, quote_id)
    return json.dumps({"portfolio": portfolio, "receipt": rec}, indent=2)


@mcp.tool()
async def get_hcs_activity(
    account_id: str,
    transaction_id: str = "",
    quote_id: str = "",
) -> str:
    """
    Get all HCS (Hedera Consensus Service) activity for an account.

    Shows topics the account has submitted messages to, message counts,
    and recent HCS submissions with their consensus timestamps.
    Costs 0.5 HBAR — provide transaction_id + quote_id after paying.
    """
    paid, challenge = await _gate("get_hcs_activity", transaction_id, quote_id)
    if not paid:
        return json.dumps(challenge, indent=2)

    # Fetch HCS submit transactions for this account
    data = await _mirror_get(
        "/api/v1/transactions",
        {"account.id": account_id, "transactiontype": "CONSENSUSSUBMITMESSAGE",
         "limit": 50, "order": "desc"},
    )

    # Group by topic
    topics: dict[str, dict] = {}
    submissions = []
    for tx in data.get("transactions", []):
        # Extract topic from entity_id
        entity = tx.get("entity_id", "")
        if entity not in topics:
            topics[entity] = {"topic_id": entity, "message_count": 0,
                              "first_seen": tx.get("consensus_timestamp", ""),
                              "last_seen": tx.get("consensus_timestamp", ""),
                              "hashscan": f"{HASHSCAN_BASE}/topic/{entity}"}
        topics[entity]["message_count"] += 1
        topics[entity]["last_seen"] = tx.get("consensus_timestamp", "")

        submissions.append({
            "transaction_id": tx.get("transaction_id"),
            "topic_id": entity,
            "time": _ts_to_human(tx.get("consensus_timestamp", "")),
            "result": tx.get("result"),
            "hashscan": f"{HASHSCAN_BASE}/transaction/{tx.get('transaction_id', '')}",
        })

    # Format topic list with human timestamps
    topic_list = []
    for t in topics.values():
        t["first_seen"] = _ts_to_human(t["first_seen"])
        t["last_seen"] = _ts_to_human(t["last_seen"])
        topic_list.append(t)

    activity = {
        "account_id": account_id,
        "network": NETWORK,
        "unique_topics": len(topic_list),
        "total_hcs_submissions": len(submissions),
        "topics": topic_list,
        "recent_submissions": submissions[:10],
        "_paid_via": "x402 · Hedera HBAR · HACK",
    }

    rec = await _receipt("get_hcs_activity", transaction_id, quote_id)
    return json.dumps({"hcs_activity": activity, "receipt": rec}, indent=2)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="HACK Hedera Bank Statement MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"],
                        default="stdio", help="Transport (default: stdio)")
    parser.add_argument("--port", type=int, default=9000, help="Port (default: 9000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"\nHACK Hedera Bank Statement MCP Server")
    print(f"  Transport : {args.transport}")
    print(f"  Network   : {NETWORK}")
    print(f"  Receiver  : {_settings.x402_payment_receiver_account_id}")
    print(f"  Price     : {_settings.x402_payment_amount_hbar} HBAR/call")
    print(f"  Tools     : get_account_statement, get_transaction_history,")
    print(f"              get_token_portfolio, get_hcs_activity\n")

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        print(f"SSE : http://{args.host}:{args.port}/sse\n")
        import uvicorn
        uvicorn.run(mcp.sse_app(), host=args.host, port=args.port,
                    log_level="info", proxy_headers=True)
    else:
        print(f"HTTP: http://{args.host}:{args.port}/mcp")
        print(f"ChatGPT URL: https://<ngrok-domain>/mcp\n")
        import uvicorn
        uvicorn.run(mcp.streamable_http_app(), host=args.host, port=args.port,
                    log_level="info", proxy_headers=True)


if __name__ == "__main__":
    main()
