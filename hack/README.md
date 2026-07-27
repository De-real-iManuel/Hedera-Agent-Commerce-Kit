# hack — Python SDK

The core toolkit for Hedera Agent Commerce Kit. This package contains all business logic, domain models, service interfaces, and concrete implementations. It has no dependency on the demo server or the frontend — it may be imported in any Python application or future `pip install hack-hedera` distribution.

---

## What This Package Provides

```python
from hack import PaidEndpoint          # One-line endpoint monetization
from hack import X402Middleware        # Starlette/FastAPI payment gate
from hack import ServiceContainer      # Dependency injection root
from hack import QuoteLifecycleService # Six-state payment machine
from hack import ComplianceEngine      # Rule-based compliance evaluation
from hack import CertificationService  # Soulbound NFT certificate issuance
```

All imports above are stable public API. Internal module paths may change — always import from `hack` directly.

---

## Package Layout

```
hack/
│
├── config.py          Pydantic BaseSettings — all environment configuration
├── container.py       ServiceContainer — lazy-initializing DI root
├── decorator.py       @PaidEndpoint — route monetization decorator
├── py.typed           PEP 561 marker — typed distribution
│
├── models/            Pydantic v2 domain models
│   ├── quote.py       Quote, PaymentStatus, ChallengeResponse, VerifyResponse
│   ├── compliance.py  ComplianceRule, ComplianceCheckResult, CertificationReport
│   └── audit.py       ServiceAuditRequest, ServiceAuditReport, SoulboundCertificate
│
├── core/              Pure business logic — no I/O
│   ├── interfaces.py      Abstract base classes: QuoteStore, PaymentVerifier,
│   │                      ReceiptService, MeteringService
│   ├── exceptions.py      Typed exception hierarchy (HACKError subclasses)
│   └── quote_lifecycle.py QuoteLifecycleService — authoritative state machine
│
├── stores/            QuoteStore implementations
│   └── memory.py      InMemoryQuoteStore — in-process, swap for Redis/DB
│
├── verifiers/         PaymentVerifier implementations
│   └── mirror_node.py MirrorNodeVerifier — Hedera Mirror Node REST client
│
├── receipts/          ReceiptService implementations
│   ├── hcs.py         HCSReceiptService — publishes to Hedera Consensus Service
│   └── memory.py      InMemoryReceiptService — fallback when HCS is not configured
│
├── metering/          MeteringService implementations
│   └── service.py     InMemoryMeteringService — per-request usage tracking
│
├── compliance/        Compliance evaluation
│   ├── engine.py      ComplianceEngine — rule runner and aggregator
│   ├── rules.py       Built-in rule set (receiver match, amount, expiry, replay)
│   └── certifier.py   CertificationService — issues reports and triggers NFT minting
│
├── middleware/        Starlette/FastAPI integration
│   └── x402.py        X402Middleware — enforces GRANTED state before route handlers
│
├── audit/             Developer service compliance analysis
│   ├── service_auditor.py  ServiceAuditor — orchestrates static + LLM analysis
│   ├── probes.py           Live endpoint probing and response analysis
│   ├── static_rules.py     Static rule evaluation against probe results
│   ├── llm.py              LLM-assisted finding generation and remediation
│   ├── github.py           GitHub repository analysis (optional, requires token)
│   └── store.py            ReportStore — filesystem persistence for reports
│
├── nft/               Hedera Token Service integration
│   └── service.py     NftMintingService — creates and mints soulbound certificates
│
└── reporting/         Output generation
    ├── pdf.py         PdfReporter — generates compliance certificate PDFs
    └── skill_md.py    SkillMdGenerator — generates SKILL.md for agent ingestion
```

---

## Core Concepts

### Payment Lifecycle

Every x402 payment moves through a six-state machine enforced by `QuoteLifecycleService`:

```
QUOTED → VERIFIED → GRANTED → CONSUMED
           ↓            ↓
        EXPIRED       EXPIRED
           ↓
       DUPLICATE  (replay rejected)
```

- **QUOTED** — challenge issued, client has not yet paid
- **VERIFIED** — Mirror Node confirms the on-chain transfer
- **GRANTED** — access window opened (default 5 minutes)
- **CONSUMED** — response delivered; the quote is permanently closed
- **EXPIRED** — TTL elapsed before the required state was reached
- **DUPLICATE** — the same transaction ID was submitted for a different quote

Each transition is validated independently. An attempt to advance from an invalid state raises a typed exception from `hack.core.exceptions`.

### Service Container

`ServiceContainer` wires all concrete implementations together using lazy property initialization. Every service is built once and cached:

```python
from hack import ServiceContainer

container = ServiceContainer.from_settings()

# Access services
container.lifecycle        # QuoteLifecycleService
container.verifier         # MirrorNodeVerifier
container.receipt_service  # HCSReceiptService or InMemoryReceiptService
container.compliance_engine
container.certifier
container.service_auditor
```

### Abstract Interfaces

The four core services are defined as abstract base classes in `hack.core.interfaces`. Swap any implementation without touching business logic:

| Interface | Default Implementation | Swap For |
|-----------|----------------------|----------|
| `QuoteStore` | `InMemoryQuoteStore` | Redis, SQLite, Supabase |
| `PaymentVerifier` | `MirrorNodeVerifier` | Mock verifier for testing |
| `ReceiptService` | `HCSReceiptService` | `InMemoryReceiptService` (dev) |
| `MeteringService` | `InMemoryMeteringService` | InfluxDB, Prometheus |

---

## Usage Examples

### Gate a single FastAPI route

```python
from fastapi import FastAPI, Request
from hack import PaidEndpoint

app = FastAPI()

@app.get("/data")
@PaidEndpoint(price="0.5 HBAR", description="On-chain verified data access")
async def get_data(request: Request):
    return {"result": "access granted"}
```

The decorator handles: challenge issuance, Mirror Node verification, lifecycle management, HCS receipt publishing, and usage metering.

### Gate all routes with middleware

```python
from fastapi import FastAPI
from hack import ServiceContainer, X402Middleware

app = FastAPI()
container = ServiceContainer.from_settings()

app.add_middleware(
    X402Middleware,
    lifecycle=container.lifecycle,
    protected_routes={"/api/premium", "/api/data"},
)
```

### Run a compliance check programmatically

```python
from hack import ServiceContainer

container = ServiceContainer.from_settings()

result = await container.compliance_engine.check(
    quote=quote,
    transaction_id=tx_id,
    tx_data=verified_transfer,
)

print(result.passed)   # True / False
print(result.rules)    # List[ComplianceRule] with per-rule pass/fail
```

### Submit a service for full compliance audit

```python
from hack.audit.service_auditor import ServiceAuditor
from hack.models.audit import ServiceAuditRequest

auditor = container.service_auditor

report = await auditor.audit(ServiceAuditRequest(
    service_name="my-mcp-server",
    service_type="mcp",
    endpoint_url="https://my-service.example.com",
    repo_url="https://github.com/org/repo",  # optional
))

print(report.overall_score)   # 0–100
print(report.passed)          # True / False
```

---

## Configuration

All settings are loaded from environment variables (or a `.env` file at the project root) via Pydantic BaseSettings. See `.env.example` for a complete reference.

Key settings:

| Variable | Type | Description |
|----------|------|-------------|
| `HEDERA_OPERATOR_ID` | `str` | Account ID for HCS message signing |
| `HEDERA_OPERATOR_KEY` | `str` | Private key — never logged or echoed |
| `HEDERA_NETWORK` | `str` | `testnet` (default) or `mainnet` |
| `X402_PAYMENT_RECEIVER_ACCOUNT_ID` | `str` | HBAR payment destination |
| `X402_PAYMENT_AMOUNT_HBAR` | `float` | Amount per request (default `0.5`) |
| `HCS_RECEIPT_TOPIC_ID` | `str` | HCS topic for payment receipts |
| `QUOTE_TTL_SECONDS` | `int` | Quote validity window (default `600`) |
| `GRANT_TTL_SECONDS` | `int` | Access grant window (default `300`) |

---

## Testing

The `hack/` package is fully testable with no network access required. All tests use in-memory store and verifier implementations.

```bash
python -m pytest tests/ -v
```

Test coverage:

- `test_quote_lifecycle.py` — all state transitions, expiry, and replay rejection
- `test_mirror_node.py` — Mirror Node verifier with HTTP mocked via respx
- `test_compliance.py` — ComplianceEngine rule evaluation and CertificationService
- `test_middleware.py` — X402Middleware request gating and bypass

---

## Packaging

The `hack` package is defined in `pyproject.toml` at the repository root using hatchling. A future `pip install hack-hedera` release will make this toolkit available as a standalone dependency.

```toml
[tool.hatch.build.targets.wheel]
packages = ["hack"]
```
