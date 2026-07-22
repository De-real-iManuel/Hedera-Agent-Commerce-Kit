---
name: hedera-agent-commerce-kit
description: Seller-side paid-agent rails for Hedera AI agents, APIs, and MCP tools. x402-style 402 flows, Hedera Agent Kit integration, Mirror Node verification, HCS receipts, usage metering, access control, and signing safety.
version: 0.1.0
license: MIT
---

# Hedera Agent Commerce Kit — Skill

Use this skill when designing or reviewing a Hedera-aware agent, API, or MCP tool that needs to charge for access safely.

This is **seller-side**: it helps the service provider expose paid access using Hedera x402, HBAR, Mirror Node, and HCS.
It does not implement wallet checkout, custody, auto-signing, or payer-side purchasing agents.

---

## Routing table

| User asks for | Load | Goal |
|---|---|---|
| Overall architecture for a paid Hedera agent/API/MCP tool | `paid-agent-architecture.md` | Choose payment boundary, state machine, access model, and non-custodial responsibilities |
| Paid MCP, paid API, HTTP 402, x402 seller flow, payment-required responses | `seller-side-x402.md` | Design seller-side 402 challenge, Mirror Node verification, retry, replay protection, and access grant |
| Usage credits, per-call billing, metering, refunds, duplicate requests | `usage-metering.md` | Design ledger, idempotency keys, job states, credit consumption, and failure/refund behavior |
| Wallet safety, transaction approval, custody, signing UX, risk review | `safety-and-signing.md` | Enforce no-custody/no-auto-signing rules and human-readable transaction risk gates |
| Hedera Agent Kit setup, plugins, LangChain tools, agent configuration | `hedera-agent-kit-integration.md` | Wire the official Hedera Agent Kit Python SDK into the payment-gated endpoint |
| Devnet/local testing, simulation, mock payment flows, validation script | `testing-and-simulation.md` | Test without live funds or real wallet signing |

---

## Route away from this skill

- Checkout UI, Hedera wallet UX, QR payments: use official Hedera SDK or HashPack wallet docs.
- Buyer/payer agent paying someone else: use the payer-side x402 pattern.
- Private balance transfers: use Hedera Token Service confidential transfers.
- Receipt NFTs: use Hedera Token Service + Metadata standard.

---

## Always apply rules

- `rules/custody.md`
- `rules/signing.md`
- `rules/payments.md`

---

## Safety hard rules

1. Never ask for, store, log, transmit, or infer seed phrases/private keys.
2. Never auto-sign transactions or imply the agent can approve wallet actions for the user.
3. Never hide transaction instructions, accounts, token amounts, fees, or authority changes.
4. Never custody user funds or design flows that require custody.
5. Never run live wallet connections, signing, or mainnet transactions in tests.
6. Separate quote creation, user approval, payment observation, Mirror Node confirmation, access granting, usage consumption, and refund/credit handling.
7. Bind payment proofs to a quote ID and resource hash; reject replayed or mismatched proofs.
8. Use explicit expiry for quotes (10 min) and bounded access windows for grants (5 min).
9. Treat duplicate payments, expired quotes, failed jobs, and Mirror Node downtime as first-class states.
10. Do not present legal, tax, payment, or compliance claims as certainty.

---

## Output templates

### 1. Paid MCP / API design brief

```md
## Seller-side paid-agent design (Hedera)
- Product being sold:
- Protected resource/tool/API:
- Payment route: user wallet → HBAR transfer → Mirror Node verify
- Quote fields: quote_id, price (HBAR), network, receiver, expiry, resource_hash, idempotency_key
- Verification source: Hedera Mirror Node REST API
- Access grant scope:
- Usage ledger states: quoted → verified → granted → consumed
- Refund/credit/manual-review states: expired, duplicate, verifier_unavailable
- Safety gates: no custody, no private keys, no auto-signing, testnet only
- Hedera Agent Kit plugins used:
- Blockers / upstream docs to verify:
```

### 2. 402 challenge shape (Hedera)

```json
{
  "type": "payment_required",
  "quote_id": "uuid",
  "resource": "mcp.tool_name or /api/path",
  "resource_hash": "sha256:endpoint:quote_id",
  "price": { "amount": "0.5", "asset": "HBAR", "network": "testnet" },
  "recipient": "0.0.XXXXXX",
  "expires_at": 1700000600,
  "idempotency_key": "idem_...",
  "retry_with": { "transaction_id": "<hedera-tx-id>", "quote_id": "uuid" }
}
```

### 3. Launch readiness verdict

```md
Verdict: pass / needs changes / blocked
Seller-side fit:
Payment challenge completeness:
Mirror Node verification gaps:
Metering and idempotency gaps:
Access-grant boundaries:
Hedera Agent Kit integration:
Signing/custody risks:
Required fixes before launch:
```
