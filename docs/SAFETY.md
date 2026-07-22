# Safety Hard Rules

These rules are non-negotiable for Hedera Agent Commerce Kit.
Any feature request that would require violating one of these rules must be marked **BLOCKED** rather than implemented.

## Rules

1. **No private key handling** — Never ask for, store, log, transmit, or infer seed phrases or private keys through API endpoints. The operator key in `.env` is used only for HCS publishing and never echoed.

2. **No auto-signing** — The server never signs transactions on behalf of a user. Payment is always initiated by the user's own wallet.

3. **No custody** — The server never holds or moves user funds. It only observes confirmed on-chain transfers via Mirror Node.

4. **Full transaction transparency** — Never hide transaction instructions, accounts, amounts, fees, or memos from the user.

5. **State separation** — Quote creation, payment observation, Mirror Node verification, access granting, result delivery, and usage metering are discrete steps. Skipping steps is a bug.

6. **Proof binding** — Every payment proof (transaction ID) must be bound to a specific quote ID. Proofs submitted against a different quote are rejected as replays.

7. **Explicit expiry** — Quotes expire after `QUOTE_TTL_SECONDS` (default 10 min). Access grants expire after `GRANT_TTL_SECONDS` (default 5 min). Expired state is surfaced explicitly in API responses.

8. **Single consumption** — A GRANTED quote transitions to CONSUMED on first use. Retrying with the same proof returns a 402, not a free second result.

9. **First-class failure states** — Expired quotes, duplicate transaction IDs, Mirror Node lag, verifier downtime, and failed job delivery are handled explicitly, not silently swallowed.

10. **No live funds in tests** — Use mocks, stubs, or Hedera testnet only. Never run validation flows against mainnet with real HBAR.

11. **No compliance claims** — Do not present tax, legal, or regulatory statements as certainties. Mark them for qualified review.

## Failure state handling

| State | Trigger | Response |
|---|---|---|
| `EXPIRED` | Quote TTL elapsed | 402 + "request new challenge" |
| `DUPLICATE` | Same tx_id on different quote | 409 + detail |
| `CONSUMED` | Proof reused after result delivered | 402 + "each payment grants one request" |
| Mirror Node 404 | Indexing lag | 502 + "retry after ~3s" |
| Mirror Node 5xx | Verifier downtime | 502 + retryable flag |
| Insufficient transfer | Wrong amount / wrong receiver | 400 + tinybar detail |
