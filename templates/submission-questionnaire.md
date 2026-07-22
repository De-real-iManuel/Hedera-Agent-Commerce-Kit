# Submission Questionnaire — Hedera Agent Commerce Kit

## What did you build?

**Hedera Agent Commerce Kit (HACK)** — seller-side paid-agent infrastructure for Hedera AI agents, APIs, and MCP tools.

It lets any FastAPI endpoint, MCP tool, or AI agent become a pay-per-request service using:
- Hedera x402-style HTTP 402 challenges
- HBAR micropayments on Hedera testnet
- Hedera Mirror Node payment verification
- HCS immutable receipt logging (via Hedera Agent Kit `core_consensus_plugin`)
- The Hedera Agent Kit Python SDK for LangChain-powered agent responses
- A 6-state payment machine (QUOTED → VERIFIED → GRANTED → CONSUMED) with replay protection and expiry

## Why does this belong in the Hedera ecosystem?

Hedera AI Studio already has the Agent Kit for building agents. HACK connects the Agent Kit to a payment layer:

- Builders expose paid APIs and MCP tools — HACK handles the commerce side
- Every successful payment triggers an HCS receipt via `core_consensus_plugin`
- The premium endpoint returns a real Hedera Agent Kit agent response (account queries, HCS, HTS tools)
- Fills the gap between "how do I build a Hedera agent" and "how does my agent charge for its work"

## What Hedera technologies appear naturally?

| Technology | Where used |
|---|---|
| **Hedera Agent Kit** | `backend/agent/hedera_agent.py` — agent with Hedera tools |
| **HCS** | `backend/receipts/hcs.py` — immutable payment receipts |
| **Mirror Node** | `backend/verification/mirror_node.py` — on-chain payment proof |
| **HBAR** | x402 payment currency |
| **HashScan** | `/api/hashscan/{txId}` — explorer links in every receipt |
| **Hedera testnet** | All demo flows; no mainnet live funds |

## What is the demo flow?

See `docs/DEMO_SCRIPT.md`. Under 5 minutes:
`curl` → 402 challenge → wallet pays HBAR → Mirror Node verifies → Hedera Agent Kit agent responds → HCS receipt → HashScan link

## Safety boundaries

- No user private keys handled anywhere
- No auto-signing, no fund custody
- Agent uses server operator account on testnet only
- `.env` in `.gitignore`
- All safety rules in `docs/SAFETY.md` and `rules/`

## Proof of quality

- `python scripts/validate.py` — 55+ automated checks, all passing
- 6-state payment machine with replay protection and bounded access windows
- Full reference architecture in `ARCHITECTURE.md`
- Skill documentation in `skill/` (mirrors solana-paid-agent-skill structure)
- Risk register in `templates/risk-register.md`
- Audit command in `commands/audit-payment-flow.md`
- Launch checklist in `commands/generate-launch-checklist.md`
