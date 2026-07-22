# Risk Register — Hedera Agent Commerce Kit

| Risk | Severity | Why it matters | Mitigation |
|---|---:|---|---|
| Operator private key exposed via API response | Critical | Irreversible account compromise | Key loaded from `.env` only; never echoed in any response |
| Agent auto-signs or broadcasts user transactions | Critical | User loses approval control | Agent uses server operator account on testnet only; no user wallet connections |
| Payment proof replay | High | One payment unlocks multiple results | Proof bound to quote_id + resource_hash; tx_id → quote_id map rejects cross-quote reuse |
| Underpayment / wrong receiver | High | Server grants access without correct payment | Mirror Node verifies tinybar amount ≥ quoted and receiver matches config |
| Duplicate payment | Medium | User overcharged or support burden rises | `DUPLICATE` state with manual-review path; idempotent retry returns 409 |
| Mirror Node 404 (indexing lag) | Medium | Payment denied despite valid tx | 404 → retryable 502, not hard 400; client retries after ~3s |
| Mirror Node 5xx (verifier outage) | Medium | Access incorrectly denied or granted | 5xx → retryable 502; no optimistic fulfillment |
| Expired quote | Medium | User paid after TTL | `EXPIRED` state → 402 + "request new challenge" |
| Over-broad access grant | High | One payment unlocks more than priced | CONSUMED state enforced in middleware before handler runs |
| HCS receipt failure | Low | No on-chain audit trail for payment | HCS error captured in receipt dict; does not block payment flow |
| LLM key in `.env` leaked to git | High | API key theft, billing fraud | `.env` in `.gitignore`; `.env.example` uses placeholder values |
| Compliance certainty claims | Medium | Legal/tax statements mislead users | All compliance items marked for qualified review |
| Mainnet deployment without review | High | Real HBAR loss if bugs present | testnet only in MVP; mainnet requires explicit operator decision |
