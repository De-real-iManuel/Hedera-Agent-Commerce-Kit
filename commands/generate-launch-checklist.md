# generate-launch-checklist

Generate a launch checklist for a seller-side paid Hedera agent/API/MCP tool.

## Positioning

- [ ] The service being sold is clearly described
- [ ] Flow is seller-side paid access, not generic checkout or payer-side x402
- [ ] Wallet UX routes to HashPack / Hedera Portal docs
- [ ] Buyer payment automation routes to payer-side x402 pattern

## Payment challenge

- [ ] `quote_id` (UUID) present
- [ ] `resource_hash` (sha256 of endpoint + quote_id) bound
- [ ] `price.amount`, `price.asset` = HBAR, `price.network` = testnet explicit
- [ ] `recipient` (Hedera account ID) explicit
- [ ] `expires_at` explicit (10 min default)
- [ ] `idempotency_key` present
- [ ] Retry instructions clear

## Mirror Node verification

- [ ] Amount ≥ quoted (in tinybar) checked
- [ ] Receiver account matches config checked
- [ ] Quote binding: transaction_id linked to quote_id
- [ ] Expiry checked before granting access
- [ ] Replay rejected: same tx_id on different quote → 409
- [ ] Mirror Node 404 → retryable 502 (not hard 400)
- [ ] Mirror Node 5xx → retryable 502

## Hedera Agent Kit

- [ ] `hedera-agent-kit` + `hiero-sdk-python` in requirements.txt
- [ ] At least one LLM provider key in `.env.example` instructions
- [ ] `core_consensus_plugin` used for HCS receipt publishing
- [ ] Agent scoped to testnet operator account only
- [ ] Agent mode = AUTONOMOUS on testnet
- [ ] No user private keys handled by agent

## Usage and access

- [ ] Access bounded to one job/resource/window (CONSUMED state)
- [ ] Usage metered: tx_id, caller, endpoint, amount, timestamp
- [ ] Retry returns same result / 409 CONSUMED (no double charge)
- [ ] Expired quote → 402 + "request new challenge"
- [ ] HCS receipt published after every successful payment

## Safety

- [ ] No private keys, seed phrases, or credentials in API responses
- [ ] No auto-signing, no wallet connection, no fund custody
- [ ] Any live-money step requires human approval outside this server
- [ ] `.env` in `.gitignore`
- [ ] Safety rules in `docs/SAFETY.md` and `rules/`

## Tests

- [ ] `python scripts/validate.py` — all checks pass
- [ ] Mock 402 challenge (no payment headers)
- [ ] Mock proof accepted (valid quote_id + tx_id)
- [ ] Mock proof rejected (wrong quote_id → 409)
- [ ] Expired quote returns 402
- [ ] Duplicate proof replay returns 409
- [ ] CONSUMED state returns 402 on second call
- [ ] No wallet/signing/mainnet tests
