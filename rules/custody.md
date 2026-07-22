# Custody Rules

Hard rule: Hedera Agent Commerce Kit must not custody user funds.

## Never do

- Never ask for seed phrases, private keys, or mnemonics through any API endpoint.
- Never store or transmit signing material.
- Never design a flow where this server controls user funds.
- Never imply the Hedera Agent Kit agent can approve spending on behalf of the user.
- Never hide who receives funds or what access is granted.

## Required design boundary

Seller-side paid-agent rails must separate:

1. Quote creation (server issues challenge)
2. External user payment (user's own wallet sends HBAR)
3. Payment observation (Mirror Node REST API)
4. Verification/confirmation (amount + receiver + expiry checks)
5. Access granting (state → GRANTED with bounded TTL)
6. Usage consumption (state → CONSUMED, result delivered once)
7. Refund/credit/manual review (separate path, never automatic)

## Allowed

- Document non-custodial architecture.
- Route to official Hedera wallet docs (HashPack, Hedera Portal).
- Require human approval and qualified compliance review for any live-money path.
- Use the Hedera Agent Kit's own operator account for HCS publishing only.
