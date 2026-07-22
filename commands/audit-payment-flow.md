# audit-payment-flow

Audit a seller-side paid Hedera agent, API, or MCP tool flow.

## Inputs to collect

- What is being sold?
- Is it a Hedera agent query, API endpoint, or MCP tool?
- Price (HBAR), receiver account, network (testnet/mainnet)
- Quote expiry and idempotency key strategy
- Payment proof format (Hedera transaction ID)
- Verifier source (Mirror Node REST API)
- Access grant scope (single call, time window, etc.)
- Usage ledger states defined
- Refund/credit/manual-review policy
- Hedera Agent Kit plugins in use
- Any wallet/signing/credential touchpoints

## Audit steps

1. Confirm this is seller-side paid-agent rails. If checkout UX is needed, route to HashPack / Hedera Portal. If buyer-side automation is needed, route to payer-side x402 pattern.
2. Verify quote fields: price, HBAR, receiver, expiry, resource_hash, idempotency_key.
3. Verify Mirror Node checks: amount ≥ quoted, correct receiver, not expired, not replayed.
4. Verify state machine: QUOTED → VERIFIED → GRANTED → CONSUMED all present.
5. Verify bounded access: one resource/job/window, no over-broad grants.
6. Verify HCS receipt publishing via core_consensus_plugin or hiero_sdk_python.
7. Verify Hedera Agent Kit agent is scoped to testnet operator account only.
8. Apply signing/custody hard rules from `rules/`.
9. List missing tests and blockers.

## Output

```md
Verdict: pass / needs changes / blocked
Seller-side positioning: ✅ / ❌
Payment challenge completeness: ✅ / ❌ (missing: ...)
Mirror Node verification gaps: ...
Metering/idempotency gaps: ...
Hedera Agent Kit integration: ✅ / ❌
Signing/custody risks: ...
Required fixes before launch: ...
```
