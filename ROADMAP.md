# Hedera Agent Commerce Kit — Roadmap

HACK is being built in four phases. The current submission is **Phase 1** — a complete, production-ready foundation that every subsequent phase builds on.

The long-term vision: a **verifiable registry** where developers publish monetized MCP servers and APIs, and AI agents like Claude discover, pay for, and call them autonomously — with every transaction, receipt, and trust signal anchored on Hedera.

---

## Phase 1 — Developer Toolkit ✅ Current Submission

> Build the primitives. Make it trivial to monetize any API or MCP server on Hedera.

The core insight: AI agents need to transact with services the way HTTP requests work — lightweight, stateless, and standardized. x402 is that standard. HACK is the implementation.

**What's built:**

- `@PaidEndpoint` — one decorator monetizes any FastAPI route
- x402 payment lifecycle — challenge, verify, grant, consume, expire
- HBAR payments with Hedera Mirror Node verification (no third-party oracle)
- HCS immutable receipts — every payment anchored to a Consensus Service topic
- Compliance audit engine — static and LLM-assisted rule evaluation
- AI-powered service certification — structured findings across payment, security, and architecture
- Soulbound NFT certificates — on-chain proof of compliance audit completion
- WalletConnect v2 — browser wallet support via HIP-820
- Enterprise Next.js frontend — certification UI, API explorer, certificate gallery
- Docker support — single-container deployment
- MCP server support — paid tool integration pattern
- Full documentation, environment templates, and deployment guides

**On-chain proof:**
Every component has been exercised on Hedera testnet. Real transactions, real HCS messages, real NFTs — not simulated.

---

## Phase 2 — Developer Platform

> Make HACK the standard infrastructure for publishing monetized AI services.

Phase 1 gives developers the tools. Phase 2 gives them the platform to distribute what they build — with the registry itself anchored on-chain so the history is tamper-proof and verifiable by anyone.

**Service Registry**
- Self-service publishing — developers register MCP servers and APIs against the HACK registry
- HCS-anchored registration events — every listing, update, and deprecation is an on-chain record
- Compliance-gated listing — services must pass the audit engine before receiving a verified badge
- Version management — publish, deprecate, and sunset service versions with on-chain history

**Developer Experience**
- Developer dashboard — payment volume, active sessions, endpoint performance
- Usage analytics — per-endpoint revenue, request counts, and latency histograms
- Webhook notifications — real-time payment lifecycle events
- SDK distribution — `hack-client` and `hack-server` packages on npm and PyPI

**Trust Infrastructure**
- On-chain compliance scores — audit results published to HCS, not stored in a mutable database
- Verified badge — services that pass the compliance engine get a certification that's independently verifiable
- Audit history — every compliance run is anchored on-chain; scores can't be retroactively altered

---

## Phase 3 — Agent-Accessible Registry

> The registry becomes the infrastructure layer for the agent economy.

This is where the vision becomes a platform. Phase 3 is not about building agents — it is about building the registry that agents like Claude, GPT, and custom LangChain agents plug into. One integration with the HACK registry gives any agent access to the full ecosystem of verified, monetized services.

**Discovery**
- Public registry API — machine-readable index of all listed services, capabilities, and pricing
- Discovery MCP server — a single MCP connection gives any agent access to the entire registry
- Structured capability taxonomy — services declare what they do in a standardized schema agents can query
- Semantic search — natural language service discovery across the registry

**Agent Integration**
- Native x402 support — agents read a 402 challenge, pay with HBAR, and continue without human steps
- Session-based spending — users authorize a spending limit once; agents operate within it autonomously
- Receipt verification — agents confirm payment on Mirror Node before consuming a response
- Workflow continuity — agents chain multiple paid service calls within a single task context

**Trust and Reputation**
- On-chain trust scores — composite reputation derived from compliance grades, payment history, and uptime
- Community ratings — developer and agent feedback anchored to HCS
- Service verification — HACK-certified badge visible in agent tool selection
- Transparent history — every trust signal is derivable from public HCS data; the registry can't manipulate scores

**For Developers**
- Network effects — listing a service in the HACK registry makes it accessible to every agent that connects to the discovery MCP server
- Monetization from day one — services earn HBAR for every agent call, settled on-chain with no intermediary

---

## Phase 4 — Enterprise Infrastructure

> Production-grade deployment for organizations running internal agent service networks at scale.

**Deployment**
- Multi-tenant environments — isolated namespaces per organization on shared infrastructure
- Private registries — internal service catalogs not exposed to the public marketplace
- On-chain auditability preserved in private deployments via dedicated HCS topics

**Governance**
- Policy engines — configurable rules for payment thresholds, allowed service categories, and geographic restrictions
- Compliance reports — exportable audit trails for regulatory and internal review, all derivable from on-chain data
- Audit logs — immutable record of configuration changes and administrative actions

**Operations**
- Billing dashboards — consolidated HBAR spend and revenue across an organization
- SLA monitoring — automated alerting when services breach declared availability targets
- Organization management — hierarchical account structures with delegated administration

---

## Why This Belongs on Hedera

Every phase of this roadmap is deeper because it runs on Hedera, not despite it.

**The registry history can't be rewritten.** Registration events, compliance updates, and service deprecations are published to HCS. Anyone can replay the topic and verify the current state independently. A centralized registry can silently alter trust scores. HACK cannot.

**Payment disputes don't exist.** Every transaction is on the Mirror Node. There is no "our records show" — there is only the chain. This removes an entire category of enterprise objection.

**Trust is structural, not reputational.** A verified badge in HACK is backed by an on-chain certificate, an HCS-anchored audit report, and a compliance history. It is not a star rating on a platform the operator controls.

**Hedera's fixed fees make agent economics predictable.** Agents need to know what a Hedera operation costs before they execute it. No gas estimation, no fee spikes. This is a prerequisite for autonomous agent workflows that chain multiple paid calls.

---

## Design Principles

These are fixed across all phases:

- **On-chain first** — payments, receipts, compliance results, and registry events are verifiable on Hedera without trusting HACK infrastructure
- **Registry as product, payment as mechanism** — the registry is what developers and agents use; x402 + HBAR is how it enforces trust and generates revenue
- **Agent-native by design** — the primary consumer of this platform is an autonomous AI agent, not a human developer clicking through a UI
- **Open core** — the toolkit that powers Phase 1 remains open source; the platform and managed registry are the business
