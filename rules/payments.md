# Payment Rules

Hard rule: HACK provides seller-side paid-agent infrastructure. It does not process payments, connect wallets, sign, or act as a payment facilitator.

## Required payment state separation

Keep these states explicitly separate:

1. Quote creation (`QUOTED`)
2. User pays externally with their Hedera wallet
3. Payment observation via Hedera Mirror Node REST API
4. Verification: amount, receiver, network, quote binding, expiry, replay check
5. Access grant (`GRANTED`) with bounded TTL (5 min)
6. Usage consumption (`CONSUMED`) — result delivered exactly once
7. Refund / credit / manual review — explicit error states

## Required quote fields

- `quote_id` (UUID)
- `resource_hash` (sha256 of endpoint + quote_id)
- `price.amount` (HBAR)
- `price.asset` = "HBAR"
- `price.network` = "testnet"
- `recipient` (Hedera account ID)
- `expires_at` (Unix timestamp)
- `idempotency_key`

## Required Mirror Node verification checks

- Amount ≥ quoted amount (in tinybar)
- Receiver account matches `X402_PAYMENT_RECEIVER_ACCOUNT_ID`
- Transaction not expired
- Transaction not previously consumed for a different quote
- Mirror Node returned 200 (not 404 / 5xx)

## Error states to handle explicitly

| State | HTTP | Meaning |
|---|---|---|
| `payment_required` | 402 | No proof provided |
| `payment_pending` | 402 | Mirror Node 404 (indexing lag ~3s) |
| `invalid_proof` | 400 | Wrong amount / wrong receiver |
| `expired_quote` | 402 | Quote TTL elapsed |
| `already_consumed` | 409 | Proof reused after result delivered |
| `duplicate_payment` | 409 | Same tx_id on a different quote |
| `verifier_unavailable` | 502 | Mirror Node 5xx / timeout |

## Never claim

- Guaranteed legal compliance
- Guaranteed tax compliance
- Guaranteed payment protocol compliance
- Production readiness without qualified review
