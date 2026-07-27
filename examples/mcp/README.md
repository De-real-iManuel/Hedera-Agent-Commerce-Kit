# HACK Hedera MCP Server

A production-quality MCP server where every tool is pay-per-call using Hedera x402 payments. Built on the `hack` SDK — Mirror Node verification, six-state lifecycle, and HCS immutable receipts included.

---

## Tools

| Tool | What it does | Cost |
|------|-------------|------|
| `analyze_hedera_account` | Fetch live balance, memo, key, and recent transactions for any Hedera account | 0.5 HBAR |
| `query_hcs_topic` | Fetch and decode recent messages from any HCS topic | 0.5 HBAR |
| `generate_compliance_report` | Run HACK compliance rules against a payment transaction; anchors result to HCS | 0.5 HBAR |

---

## Payment Flow

Every tool follows the same three-step pattern:

```
1. Call tool (no payment)
   → Returns payment_required (402) with quote_id, receiver, amount, expiry

2. Send HBAR to receiver using any Hedera wallet
   (HashPack, Kabila, or programmatic transfer)

3. Call same tool again with transaction_id + quote_id
   → Mirror Node verified → HCS receipt published → result returned
```

The server uses the HACK `QuoteLifecycleService` state machine:
`QUOTED → VERIFIED → GRANTED → CONSUMED`

Each payment grants exactly one tool call. Replay is rejected at the transaction ID level.

---

## Setup

**Prerequisites:** Python 3.10+, a configured `.env` at the project root.

```bash
# From the project root
pip install mcp

# Verify your .env has these set:
# HEDERA_OPERATOR_ID, HEDERA_OPERATOR_KEY
# X402_PAYMENT_RECEIVER_ACCOUNT_ID
# HCS_RECEIPT_TOPIC_ID
# GROQ_API_KEY (or OPENAI_API_KEY)
```

---

## Running

### stdio (Claude Desktop, Continue, etc.)

```bash
python examples/mcp/server.py
```

### SSE (remote agents, HTTP clients)

```bash
python examples/mcp/server.py --transport sse --port 9000
# Server available at http://localhost:9000
```

---

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "hack-hedera": {
      "command": "python",
      "args": ["C:/path/to/Hedera-Agent-Commerce-Kit/examples/mcp/server.py"],
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
```

---

## Manual Test (no wallet required)

```bash
python examples/mcp/test_client.py
```

This script:
1. Calls `analyze_hedera_account` without payment — verifies a 402 response
2. Calls `query_hcs_topic` without payment — verifies a 402 response
3. Prints the quote_id and payment instructions for a real test

---

## Pasting Into the HACK Compliance Portal

To audit this MCP server through the HACK portal at `http://localhost:3000/certification`:

1. Open the portal and click **Analyze Service**
2. Set Service Type to **MCP Server**
3. Set Endpoint URL to `http://localhost:9000` (SSE transport) or your deployed URL
4. Paste the contents of `server.py` into the **Source Code** textarea
5. Leave GitHub URL blank
6. Submit and pay — the compliance engine runs static rules against your pasted code

The static rules check for: x402 middleware references, HCS receipt publishing,
Mirror Node verification calls, replay protection, error handling, and hardcoded secrets.

---

## Response Shapes

### Payment required (no proof provided)

```json
{
  "type": "payment_required",
  "status": 402,
  "tool": "analyze_hedera_account",
  "quote_id": "3f8a1c2d-...",
  "resource": "mcp.analyze_hedera_account",
  "resource_hash": "a3f9...",
  "price": { "amount": "0.5", "asset": "HBAR", "network": "testnet" },
  "receiver": "0.0.7972536",
  "memo": "hack-payment",
  "expires_at": 1784949817,
  "expires_in_seconds": 598,
  "retry_instructions": "1. Send 0.5 HBAR to 0.0.7972536 with memo 'hack-payment'. 2. Call this tool again with transaction_id and quote_id."
}
```

### Successful result

```json
{
  "status": "ok",
  "tool": "analyze_hedera_account",
  "result": { ... },
  "payment": {
    "transaction_id": "0.0.9075201@1784939817.181941398",
    "quote_id": "3f8a1c2d-...",
    "amount_hbar": 0.5,
    "consumed": true
  },
  "receipt": {
    "hcs_status": "published",
    "hcs_error": null,
    "hashscan_url": "https://hashscan.io/testnet/transaction/0.0.9075201@1784939817.181941398"
  }
}
```

---

## Adding Your Own Paid Tool

```python
# 1. Add a Tool entry to the TOOLS list
Tool(
    name="my_tool",
    description="...",
    inputSchema={
        "type": "object",
        "properties": {
            "my_param": {"type": "string"},
            "transaction_id": {"type": "string"},  # always required for payment
            "quote_id": {"type": "string"},
        },
        "required": ["my_param"],
    },
),

# 2. Add a branch to _dispatch()
if name == "my_tool":
    return await _my_tool(args["my_param"])

# 3. Implement the function
async def _my_tool(param: str) -> dict:
    return {"result": f"processed {param}"}
```

The payment gate, Mirror Node verification, state machine, HCS receipt, and metering
are all handled by the `call_tool` handler — you only write the business logic.
