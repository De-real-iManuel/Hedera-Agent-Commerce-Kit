# Example: Paid MCP Tool — Hedera Agent Launch Report

Adapted from solana-paid-agent-skill `examples/paid-mcp-launch-report.md` for the Hedera ecosystem.

This is a mock-only design: no wallet connection, signing, broadcasting, or live fund handling.

---

## Scenario

A builder exposes an MCP tool:

```
generate_agent_launch_report(query, transaction_id, quote_id)
```

The report is expensive to generate. The server charges 0.5 HBAR per completed report.
The report is produced by the Hedera Agent Kit agent (LangChain + Hedera tools).

---

## Design brief

- Product being sold: one AI-generated Hedera agent launch analysis
- Protected resource/tool/API: MCP tool `generate_agent_launch_report`
- Payment route: seller-side 402 challenge → user pays HBAR externally using their wallet → Mirror Node verifies
- Quote fields: quote_id, resource_hash, price (0.5 HBAR), network (testnet), receiver (0.0.XXXXXX), expires_at, idempotency_key
- Verification source: Hedera Mirror Node REST API (`testnet.mirrornode.hedera.com`)
- Access grant scope: one report for the exact resource_hash and idempotency key
- Usage ledger states: `quoted → verified → granted → consumed`
- Refund/credit states: `expired`, `duplicate`, `verifier_unavailable`
- Safety gates: no custody, no private keys, no auto-signing, testnet only
- Hedera Agent Kit plugins: `core_consensus_plugin` (HCS receipt), `core_account_query_plugin` (balance queries)

---

## Initial MCP response (no payment)

```json
{
  "type": "payment_required",
  "status": 402,
  "quote_id": "3f8a1c2d-...",
  "resource": "mcp.generate_agent_launch_report",
  "resource_hash": "sha256:generate_agent_launch_report:3f8a1c2d-...",
  "price": { "amount": "0.5", "asset": "HBAR", "network": "testnet" },
  "recipient": "0.0.XXXXXX",
  "expires_at": 1700000600,
  "idempotency_key": "idem_generate_agent_launch_report_3f8a1c2d",
  "retry_with": {
    "transaction_id": "<hedera-tx-id>",
    "quote_id": "3f8a1c2d-..."
  },
  "retry_instructions": "1. Send 0.5 HBAR to recipient. 2. Retry with transaction_id and quote_id."
}
```

---

## Retry with proof

```json
{
  "transaction_id": "0.0.12345@1700000300.123456789",
  "quote_id": "3f8a1c2d-..."
}
```

---

## Verification checklist

| Check | Expected |
|---|---|
| Quote binding | quote_id and resource_hash match the original challenge |
| Amount/asset/network | ≥ 0.5 HBAR (≥ 50,000,000 tinybar) on testnet |
| Recipient | Matches `X402_PAYMENT_RECEIVER_ACCOUNT_ID` in `.env` |
| Expiry | Mirror Node confirms tx before `expires_at` |
| Replay | transaction_id not previously bound to a different quote_id |
| Confirmation | Mirror Node returns 200 with matching transfer |
| Access scope | One report only; state → CONSUMED after delivery |

---

## Success response

```json
{
  "status": "succeeded_consumed",
  "tool": "generate_agent_launch_report",
  "result": "<Hedera Agent Kit agent response>",
  "result_ref": "result_3f8a1c2d",
  "receipt": {
    "quote_id": "3f8a1c2d-...",
    "transaction_id": "0.0.12345@1700000300.123456789",
    "consumed_units": 1,
    "access_scope": "single_tool_call",
    "hcs_status": "published",
    "hashscan_url": "https://hashscan.io/testnet/transaction/0.0.12345@1700000300.123456789"
  },
  "powered_by": "Hedera Agent Kit (hedera-agent-kit-py)",
  "note": "Payment verified on Mirror Node. Receipt on HCS. Not re-delivered."
}
```

---

## Blockers before production

- Confirm `hiero_sdk_python` `TopicMessageSubmitTransaction` API matches installed version
- Choose and set one LLM API key in `.env` (OpenAI / Anthropic / Groq)
- Create HCS topic and set `HCS_RECEIPT_TOPIC_ID` in `.env`
- Fund testnet operator account from [Hedera faucet](https://portal.hedera.com/faucet)
- Run `python scripts/validate.py` — all checks must pass
- Run only mock/local tests unless explicitly authorized for testnet live payments
