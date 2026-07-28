# Hedera Agent Commerce Kit — Roadmap

This document outlines the long-term vision for HACK. The current submission is **Phase 1** — a complete, production-ready foundation. Each subsequent phase builds on it without requiring architectural rewrites.

---

## Phase 1 — Current Submission ✅

> **Scope:** A composable toolkit for developers who want to add pay-per-request monetization to any API, MCP server, or AI agent on Hedera.

### Core Infrastructure
- [x] `@PaidEndpoint` decorator — one-line monetization for any FastAPI route
- [x] x402 payment flow — standard HTTP 402 challenge / verify / grant lifecycle
- [x] HBAR payments via Hedera Token Service
- [x] Hedera Mirror Node verification — on-chain payment confirmation
- [x] HCS immutable receipts — every payment anchored to a Hedera Consensus Service topic

### Compliance & Certification
- [x] Compliance audit engine — automated rule evaluation per payment
- [x] AI-powered service certification — LLM-driven analysis of x402 compliance posture
- [x] Soulbound NFT certificates — non-transferable proof of certification minted on HTS

### Developer Experience
- [x] WalletConnect integration — browser wallet support via HIP-820
- [x] Enterprise-grade Next.js frontend with certification UI
- [x] API Explorer — live interactive documentation with real payment flows
- [x] Docker support — single-container backend deployment
- [x] MCP server support — paid tool example for AI agent use cases
- [x] Full documentation, `.env.example`, and deployment guides

---

## Phase 2 — Developer Platform

> **Goal:** Turn HACK into the standard infrastructure layer for developers building and distributing monetized AI services on Hedera.

### Developer Portal
- [ ] Self-service registration — publish an API or MCP server to the HACK registry
- [ ] Service dashboard — view payment volume, active sessions, and endpoint performance
- [ ] API key management — issue scoped access tokens for downstream consumers
- [ ] Usage analytics — per-endpoint revenue, request counts, and latency histograms
- [ ] Version management — publish, deprecate, and sunset service versions

### Distribution & Integration
- [ ] SDK distribution — `hack-client` (Python/TypeScript) and `hack-server` packages on npm/PyPI
- [ ] MCP publishing — one-command publish of a paid MCP server to the HACK registry
- [ ] Webhook notifications — real-time payment events delivered to developer endpoints
- [ ] OpenAPI spec export — auto-generate x402-annotated specs from registered services

### Collaboration
- [ ] Team workspaces — shared service management across organizations
- [ ] Role-based access — owner, admin, read-only roles per workspace
- [ ] Enterprise dashboards — aggregate billing and usage across a portfolio of services
- [ ] Audit logs — immutable record of all configuration changes and key actions

---

## Phase 3 — Agent Marketplace

> **Goal:** An open, on-chain marketplace where AI agents autonomously discover, evaluate, purchase, and call services — without human intervention.

### Service Discovery
- [ ] Public registry — searchable index of all published APIs, MCP servers, and agents
- [ ] Discovery API — machine-readable endpoint for agents to query capabilities and pricing
- [ ] Capability categories — structured taxonomy (data, compute, inference, storage, etc.)
- [ ] Full-text and semantic search — agents find services by natural language description

### Trust & Reputation
- [ ] Trust scores — composite on-chain reputation derived from payment history and audits
- [ ] Reputation system — verifiable track record of uptime, latency, and compliance grades
- [ ] Service verification — HACK-certified badge for services that pass the compliance engine
- [ ] Community ratings — developer and agent feedback anchored to HCS for tamper resistance

### Autonomous Agent Workflows
- [ ] Agent-native pricing — services declare pricing in a machine-readable format
- [ ] Autonomous payment — agents read a 402 challenge, pay via HBAR, and continue — zero human steps
- [ ] Receipt verification — agents confirm payment on Mirror Node before consuming a response
- [ ] Workflow continuity — agents chain multiple paid service calls within a single task context

### Enterprise Search
- [ ] Filtered discovery — search by price ceiling, certification grade, network (testnet/mainnet)
- [ ] SLA declarations — services publish uptime commitments queryable by agents and operators

---

## Phase 4 — Enterprise Infrastructure

> **Goal:** Production-grade deployment options for organizations running internal AI service networks at scale.

### Multi-Tenancy & Deployment
- [ ] Multi-tenant deployments — isolated environments per organization on shared infrastructure
- [ ] Private registries — internal service catalogs not exposed to the public marketplace
- [ ] On-premises support — HACK stack deployable in air-gapped or regulated environments

### Compliance & Governance
- [ ] Compliance reports — exportable audit trails for regulatory and internal review
- [ ] Policy engines — configurable rules enforcing payment thresholds, allowed services, and geo restrictions
- [ ] SLA monitoring — automated alerting when services breach declared availability targets

### Operations
- [ ] Billing dashboards — consolidated HBAR spend and revenue across an organization
- [ ] Monitoring integrations — Prometheus/Grafana-compatible metrics for all HACK services
- [ ] Organization management — hierarchical account structures with delegated administration

---

## Design Principles

These principles apply across all phases and are non-negotiable as the platform grows:

- **On-chain first** — every payment, receipt, and certificate is verifiable on Hedera without trusting HACK infrastructure
- **Composable** — each component (middleware, verifier, compliance engine, NFT minter) is independently usable
- **Agent-native** — the primary consumer of this platform is an autonomous AI agent, not a human
- **Open by default** — the core toolkit remains open source; revenue comes from managed services and enterprise tiers
