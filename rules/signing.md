# Signing Rules

Hard rule: Hedera Agent Commerce Kit must not sign, auto-sign, broadcast, or submit transactions on behalf of users.

## Never do

- Never auto-sign user transactions.
- Never connect user wallets from this repository.
- Never broadcast or submit transactions for user accounts.
- Never request user private keys or seed phrases through any interface.
- Never obscure transaction instructions, accounts, amounts, fees, or authority changes.

## The Hedera Agent Kit operator account

The server uses a single Hedera testnet operator account (configured in `.env`).
This account:
- Signs HCS topic message submissions (receipt publishing)
- Is controlled exclusively by the server operator
- Does NOT act on behalf of any user wallet

## Required human approval for any live-money path

Human/wallet approval is required for:
- Any user-side transaction signing
- New recipient addresses beyond the configured receiver
- Amounts above the quoted HBAR value
- Recurring access or subscription grants
- Refund or manual credit adjustments
- Production mainnet deployment steps

## Transaction preview (for future wallet integration)

Before any external signing step, show:
- Network (testnet / mainnet)
- Asset: HBAR
- Amount in HBAR and tinybar
- Recipient account ID
- Memo field
- Expected account balance delta
- Quote ID and expiry
- Risk notes
