# Repository Structure

This document describes the role of every top-level directory and file in the Hedera Agent Commerce Kit repository. Read this before exploring the codebase.

---

## Directory Map

```
Hedera-Agent-Commerce-Kit/
│
├── hack/                    Python SDK — the installable toolkit package
├── demo/                    FastAPI application — wiring only, no business logic
├── frontend/                Next.js developer portal and compliance dashboard
├── tests/                   pytest unit and integration tests
├── docs/                    Supplementary documentation (safety, demo script)
├── examples/                Usage examples (MCP paid tool pattern)
├── scripts/                 Developer utilities (install, commit helpers)
├── data/                    Runtime output directory (reports, PDFs, certificates)
├── commands/                Reusable agent command prompts
├── rules/                   Project-specific coding rules and conventions
├── skill/                   Agent skill definitions
├── templates/               Report and certificate templates
│
├── pyproject.toml           Python package definition (hatchling build)
├── .env.example             Backend environment variable template
├── ARCHITECTURE.md          Mermaid system, sequence, state, and component diagrams
├── STRUCTURE.md             This file
└── README.md                Project overview, quick start, and API reference
```

---

## Component Roles

### `hack/` — Python SDK

The core toolkit. This is what developers install and import. It contains zero FastAPI or HTTP routing code — only pure business logic, domain models, and service interfaces.

```
hack/
├── config.py          Pydantic BaseSettings — all environment configuration
├── container.py       ServiceContainer — dependency injection root
├── decorator.py       @PaidEndpoint — one-line route monetization decorator
│
├── models/            Typed Pydantic v2 domain models (Quote, Receipt, UsageRecord)
├── core/              Abstract interfaces, custom exceptions, QuoteLifecycleService
├── stores/            QuoteStore implementations (InMemoryQuoteStore, swappable)
├── verifiers/         PaymentVerifier — Hedera Mirror Node HTTP client
├── receipts/          ReceiptService — HCS publishing and in-memory fallback
├── metering/          MeteringService — per-request usage tracking
├── compliance/        ComplianceEngine, rule set, CertificationService
├── middleware/        X402Middleware for Starlette/FastAPI
├── audit/             ServiceAuditor — automated static + LLM compliance analysis
├── nft/               NftMintingService — HTS soulbound certificate minting
└── reporting/         PDF and SKILL.md report generators
```

**Rule:** The `hack/` package has no knowledge of `demo/` or `frontend/`. It may be used independently in any Python application.

---

### `demo/` — FastAPI Application

The runnable server. Each router file contains only HTTP wiring — request parsing, response shaping, and delegation to `hack/` services via the injected `ServiceContainer`. No business logic lives here.

```
demo/
├── main.py            FastAPI app factory — middleware, CORS, router registration
└── routers/
    ├── health.py      GET /api/health
    ├── payment.py     POST /api/payment/challenge, /verify, GET /status
    ├── premium.py     GET /api/premium-query (x402-gated, Agent Kit powered)
    ├── compliance.py  POST /api/compliance/check, GET /certify
    ├── audit.py       POST /api/audit/submit, /run; GET /report, /certificate
    ├── receipts.py    GET /api/receipt/{txId}
    ├── usage.py       GET /api/usage
    ├── hashscan.py    GET /api/hashscan/{txId}
    └── agent.py       GET /api/agent/query
```

**Start the server:**
```bash
uvicorn demo.main:app --reload
```

---

### `frontend/` — Developer Portal

A Next.js 15 application providing:
- Live API Explorer (x402 payment flow demonstration)
- Compliance certification submission and report viewer
- Certificate gallery with HashScan links
- Interactive Hedera documentation

```
frontend/
├── app/               Next.js App Router pages
├── components/        React components (certification, ui primitives)
├── hooks/             useWalletConnect — Hedera WalletConnect v2 integration
├── lib/               API client (api.ts), type definitions, utilities
└── next.config.mjs    Build configuration
```

**Start the portal:**
```bash
cd frontend && npm run dev
```

---

### `tests/` — Test Suite

pytest unit tests covering all core business logic. Tests run against in-memory implementations only — no network calls required.

```
tests/
├── conftest.py              Shared fixtures (ServiceContainer, mock clients)
├── test_quote_lifecycle.py  6-state payment machine transitions
├── test_mirror_node.py      Mirror Node verifier (mocked HTTP via respx)
├── test_compliance.py       ComplianceEngine rules and CertificationService
└── test_middleware.py       X402Middleware gate and bypass logic
```

**Run tests:**
```bash
python -m pytest tests/ -v
```

---

### `docs/`

Supplementary documentation not suited for the main README.

| File | Contents |
|------|----------|
| `SAFETY.md` | Non-negotiable safety rules — key custody, replay protection, testnet boundaries |
| `DEMO_SCRIPT.md` | Judge walkthrough under 5 minutes |
| `DECORATOR.md` | `@PaidEndpoint` decorator reference |
| `SUBMISSION_CHECKLIST.md` | Pre-submission validation checklist |

---

### `examples/`

Minimal, self-contained usage examples.

| File | Contents |
|------|----------|
| `mcp/paid_tool.py` | Paid MCP tool pattern — how to gate an MCP function behind x402 |
| `paid-mcp-hedera.md` | Prose walkthrough of the MCP integration |

---

### `scripts/`

Developer utilities. Not part of the deployable application.

| File | Purpose |
|------|---------|
| `commit.ps1` | Structured commit helper |

---

### `data/`

Runtime output directory. Created automatically on first audit run. Not committed to version control.

```
data/reports/
├── reports/       JSON audit report files
├── pdfs/          Generated PDF certificates
├── certificates/  Soulbound certificate records
└── skills/        Generated SKILL.md files for agent ingestion
```

---

## What Is Not Here

| Path | Reason |
|------|--------|
| `backend/` | Removed — contained only a local `.venv`, which must not be committed |
| `**/.venv/` | Local Python virtual environments — excluded via `.gitignore` |
| `frontend/.next/` | Next.js build cache — excluded via `.gitignore` |
| `frontend/node_modules/` | npm dependencies — excluded via `.gitignore` |
| `.env` | Live secrets — never committed; use `.env.example` as the template |
