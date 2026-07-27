# demo — FastAPI Application

The runnable server for Hedera Agent Commerce Kit. This directory contains only HTTP wiring — request parsing, response shaping, error handling, and delegation to the `hack/` SDK via the injected `ServiceContainer`. No business logic lives here.

---

## Responsibility Boundary

| Concern | Lives In |
|---------|----------|
| HTTP routing and request parsing | `demo/` |
| Response shaping and status codes | `demo/` |
| Payment state machine | `hack/core/quote_lifecycle.py` |
| Mirror Node verification | `hack/verifiers/mirror_node.py` |
| HCS receipt publishing | `hack/receipts/hcs.py` |
| Compliance rule evaluation | `hack/compliance/engine.py` |
| Service auditing | `hack/audit/service_auditor.py` |
| NFT certificate minting | `hack/nft/service.py` |

If you find business logic in a router file, it belongs in `hack/` instead.

---

## Directory Layout

```
demo/
├── main.py            FastAPI app factory
│                      Registers middleware, CORS, and all routers.
│                      Builds the ServiceContainer on startup.
│
└── routers/
    ├── health.py      GET  /api/health
    ├── payment.py     POST /api/payment/challenge
    │                  POST /api/payment/verify
    │                  GET  /api/payment/status/{quote_id}
    ├── premium.py     GET  /api/premium-query  (x402-gated)
    ├── audit.py       POST /api/audit/submit
    │                  POST /api/audit/run/{quote_id}
    │                  GET  /api/audit/report/{report_id}
    │                  GET  /api/audit/report/{report_id}/pdf
    │                  GET  /api/audit/report/{report_id}/skill.md
    │                  GET  /api/audit/certificate/{certificate_id}
    │                  GET  /api/audit/certificates
    ├── compliance.py  POST /api/compliance/check
    │                  GET  /api/compliance/certify/{quote_id}
    ├── receipts.py    GET  /api/receipt/{txId}
    ├── usage.py       GET  /api/usage
    ├── hashscan.py    GET  /api/hashscan/{txId}
    └── agent.py       GET  /api/agent/query
```

---

## Running the Server

**Prerequisites:** Python 3.10+, a configured `.env` file at the project root.

```bash
# From the project root — activate your virtual environment first
uvicorn demo.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts with:
- Hot reload enabled (`--reload`) — file changes restart the server automatically
- CORS configured to allow all `localhost` origins — the Next.js dev server connects without additional setup
- `X402Middleware` protecting `/api/premium-query`
- `ServiceContainer` initialized and attached to `app.state.container`

Interactive API documentation is available at:
- **Swagger UI** — `http://localhost:8000/docs`
- **ReDoc** — `http://localhost:8000/redoc`

---

## Payment Flow — How the Routers Interact

A complete compliance audit involves three sequential requests:

```
1. POST /api/audit/submit
   → Creates a payment quote via ServiceContainer.lifecycle
   → Returns {quote_id, amount_hbar, receiver, memo, expires_at}

2. POST /api/payment/verify
   → Confirms the HBAR transfer on Hedera Mirror Node
   → Advances quote: QUOTED → VERIFIED → GRANTED
   → Publishes an HCS receipt

3. POST /api/audit/run/{quote_id}?transaction_id=...
   → Confirms the quote is in GRANTED state
   → Runs the ServiceAuditor compliance pipeline
   → Mints a soulbound NFT certificate if the service passes
   → Returns {report, certificate}
```

The `audit.py` router checks the current quote state before calling `advance_to_verified()`. If `POST /api/payment/verify` has already advanced the quote to `GRANTED`, the state machine calls are skipped — only the Mirror Node verification is re-run as a confirmation step.

---

## Service Access Pattern

Every router receives services through `request.app.state.container`:

```python
@router.post("/submit")
async def submit_audit(body: ServiceAuditRequest, request: Request):
    container = request.app.state.container
    lifecycle = container.lifecycle
    settings  = container.settings
    # ...
```

This pattern ensures:
- Services are never imported directly from `hack/` in router files
- The container handles all initialization, caching, and configuration
- Tests can substitute a test container without modifying router code

---

## In-Memory Submission Store

The audit router keeps an in-memory dict (`_AUDIT_SUBMISSIONS`) mapping `quote_id` to the original `ServiceAuditRequest`. This is intentional — audit submissions are ephemeral. A process restart clears in-flight submissions, but completed reports and certificates are persisted to `data/reports/` by the `ReportStore`.

For production deployments with multiple workers, replace this dict with a shared cache (Redis, database).

---

## Environment Variables

The demo server reads all configuration from the root `.env` file via `hack.config.Settings`. See `.env.example` for a complete reference.

Minimum required variables to start the server:

```env
HEDERA_OPERATOR_ID=0.0.XXXXXX
HEDERA_OPERATOR_KEY=302e...
X402_PAYMENT_RECEIVER_ACCOUNT_ID=0.0.XXXXXX
HCS_RECEIPT_TOPIC_ID=0.0.XXXXXX
GROQ_API_KEY=gsk_...          # or OPENAI_API_KEY / ANTHROPIC_API_KEY
```

If `HCS_RECEIPT_TOPIC_ID` or operator credentials are absent, the server starts with an in-memory receipt service. Payment verification and audit analysis still work — HCS publishing is degraded to in-memory logging.
