# Submission Checklist

Review every item before submitting. Each maps to a judge criterion.

## Core Requirements

- [ ] One-sentence pitch in README hero section
- [ ] All Hedera technologies appear naturally (x402, Mirror Node, HCS, Agent Kit, HBAR)
- [ ] Demo under 5 minutes (see `docs/DEMO_SCRIPT.md`)
- [ ] README readable in under 3 minutes
- [ ] Reproducible on a fresh machine (`./scripts/install.sh` → `start-backend.sh` → `start-frontend.sh`)
- [ ] HashScan links in demo output
- [ ] Testnet only (no mainnet live funds)
- [ ] Public repository

## Technical Correctness

- [ ] HTTP 402 returns a valid payment challenge with quote ID and expiry
- [ ] Mirror Node verification confirms receiver + amount (not just tx existence)
- [ ] HCS receipt published after every successful payment
- [ ] Usage metering records request, caller, endpoint, amount, timestamp
- [ ] Replay protection: CONSUMED payments return 402 on retry
- [ ] Expired quotes return 402 with "request new challenge" guidance
- [ ] Duplicate tx IDs across quotes return 409
- [ ] Mirror Node 404 returns retryable 502, not hard failure

## Safety

- [ ] No private key / seed phrase in any API endpoint or response
- [ ] No auto-signing or custody of user funds
- [ ] No live wallet connections in tests or demos
- [ ] Safety rules documented in `docs/SAFETY.md`
- [ ] `.env` is in `.gitignore`

## Documentation

- [ ] `README.md` — hero, why, architecture, quick start, API reference
- [ ] `ARCHITECTURE.md` — component map and request flow
- [ ] `QUICKSTART.md` — three-command setup
- [ ] `docs/SAFETY.md` — hard rules and failure state table
- [ ] `docs/DEMO_SCRIPT.md` — step-by-step judge walkthrough
- [ ] `templates/` — copyable JSON schemas for challenge, proof, receipt
- [ ] `ROADMAP.md` — MVP done + future work

## Validation

Run before final submission:

```bash
python scripts/validate.py
```

All checks must pass (no FAIL lines).
