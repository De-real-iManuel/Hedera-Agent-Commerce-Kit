# HACK Hedera Bank Statement — Paid MCP Server

A production-quality MCP server that generates comprehensive **Hedera account statements** using the Mirror Node REST API. Every tool call is pay-per-use via the x402 payment standard on Hedera.

## What it does

Connect this server to ChatGPT, Claude, or any MCP-compatible agent and ask it to analyze any Hedera account. The agent receives a payment challenge, you pay 0.5 HBAR, and the server returns live on-chain data verified through the Hedera Mirror Node.

## Tools

| Tool | Description |
|------|-------------|
| `get_account_statement` | Full account overview: HBAR balance, token count, recent transactions, account metadata |
| `get_transaction_history` | Paginated HBAR and token transfer history with amounts, counterparties, and HashScan links |
| `get_token_portfolio` | All HTS tokens held — fungible tokens and NFTs with metadata |
| `get_hcs_activity` | HCS topics submitted to by the account, message counts, and recent submissions |

## Payment flow

Every tool call goes through the x402 protocol:

```
1. Call any tool without proof
   → Receive { type: "payment_required", status: 402, quote_id, receiver, memo }

2. Send 0.5 HBAR to `receiver` with the exact `memo` (contains quote_id suffix)
   → Use HashPack, Kabila, or any Hedera wallet

3. Call the tool again with transaction_id + quote_id
   → Mirror Node verifies payment on-chain
   → Result returned + HCS receipt published
```

The memo includes the last 6 characters of the `quote_id` (e.g. `hack-payment-f4a91c`). This binds each payment to a specific quote — replaying an old transaction against a new quote will be rejected.

## Running

```bash
# Install dependencies
pip install mcp uvicorn httpx

# Stdio transport (Claude Desktop, Continue)
python examples/mcp/server.py

# SSE transport (Claude Desktop remote)
python examples/mcp/server.py --transport sse --port 9000

# Streamable HTTP transport (ChatGPT)
python examples/mcp/server.py --transport http --port 9000
```

## Connecting to ChatGPT

1. Start the server: `python examples/mcp/server.py --transport http --port 9000`
2. Expose via ngrok: `ngrok http 9000`
3. In ChatGPT → Settings → Connectors → Add MCP Server
4. URL: `https://<your-ngrok-domain>/mcp`

## Connecting to Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
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
```

## Demo questions for ChatGPT

```
"Generate a full bank statement for Hedera account 0.0.7942957"

"Show me the transaction history for 0.0.9075201 — I want to see 
the last 20 transactions"

"What tokens does account 0.0.7942957 hold? Include NFTs."

"Show me the HCS activity for account 0.0.7942957 — what topics 
has this account submitted messages to?"
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `HEDERA_OPERATOR_ID` | Account that signs HCS receipts |
| `HEDERA_OPERATOR_KEY` | Private key for the operator account |
| `HEDERA_NETWORK` | `testnet` (default) or `mainnet` |
| `X402_PAYMENT_RECEIVER_ACCOUNT_ID` | Account that receives HBAR payments |
| `X402_PAYMENT_AMOUNT_HBAR` | Price per call (default: `0.5`) |
| `HCS_RECEIPT_TOPIC_ID` | HCS topic for immutable payment receipts |
| `GROQ_API_KEY` / `OPENAI_API_KEY` | LLM key (for compliance audit features) |
