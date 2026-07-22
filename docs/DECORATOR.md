# `@PaidEndpoint` — Developer Guide

The `PaidEndpoint` decorator is HACK's developer-facing API. It turns any FastAPI route into a pay-per-request endpoint in one line.

---

## Basic usage

```python
from fastapi import FastAPI, Request
from hack import PaidEndpoint

app = FastAPI()

@app.get("/premium")
@PaidEndpoint(price="0.5 HBAR", description="Premium AI insight")
async def premium(request: Request):
    return {"result": "You unlocked premium access."}
```

The decorator intercepts every request to `/premium` and:
1. Returns HTTP 402 with a payment challenge if no valid payment token is present
2. Validates the payment state (GRANTED, not expired, not already consumed)
3. Advances the state to CONSUMED (exactly once)
4. Passes the request to your handler

---

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `price` | `str \| float` | `"0.5 HBAR"` | Payment amount. Accepts `"0.5 HBAR"`, `"0.5"`, or `0.5` |
| `description` | `str` | function name | Human-readable label shown in the 402 challenge body |

---

## What the 402 response looks like

When a client calls a `@PaidEndpoint` without paying:

```json
{
  "error": "Payment Required",
  "description": "Premium AI insight",
  "payment_details": {
    "network": "testnet",
    "receiver": "0.0.XXXXXX",
    "amount_hbar": 0.5,
    "memo": "hack-payment"
  },
  "how_to_pay": [
    "1. POST /api/payment/challenge to get a quote_id",
    "2. Send HBAR to receiver with memo",
    "3. POST /api/payment/verify with {transaction_id, quote_id}",
    "4. Retry this request with headers:",
    "     X-Payment-Token: <transaction_id>",
    "     X-Quote-Id: <quote_id>"
  ],
  "docs": {
    "challenge": "POST /api/payment/challenge",
    "verify":    "POST /api/payment/verify",
    "openapi":   "/docs"
  }
}
```

---

## Required headers for paid requests

```
X-Payment-Token: 0.0.12345@1700000000.000000000
X-Quote-Id:      3f8a1c2d-0000-0000-0000-000000000000
```

Both values come from the `/api/payment/verify` response.

---

## Payment state machine

The decorator enforces the same state machine as the x402 middleware:

```
QUOTED → VERIFIED → GRANTED → CONSUMED
                             ↘ EXPIRED (10-min quote TTL)
                    ↘ EXPIRED (5-min grant TTL)
```

Each payment grants **exactly one request**. Replay attempts return 402 CONSUMED.

---

## Full example with custom logic

```python
from fastapi import FastAPI, Request
from hack import PaidEndpoint
from backend.agent.hedera_agent import run_agent_query

app = FastAPI()

@app.get("/report")
@PaidEndpoint(price="1.0 HBAR", description="AI-generated Hedera report")
async def generate_report(request: Request, q: str = "Hedera network summary"):
    # Payment verified and consumed — run your logic here
    result = await run_agent_query(query=q)
    return {
        "report": result,
        "paid_with": request.headers.get("X-Payment-Token"),
    }
```

---

## Registering multiple endpoints

```python
@app.get("/summary")
@PaidEndpoint(price="0.5 HBAR", description="Quick summary")
async def summary(request: Request): ...

@app.get("/deep-analysis")
@PaidEndpoint(price="2.0 HBAR", description="Deep analysis — 4x compute")
async def deep_analysis(request: Request): ...
```

Each route gets its own price. The quote system handles them independently.

---

## Inspecting registered paid routes

```python
from hack import get_paid_routes
print(get_paid_routes())
# {'/summary': 0.5, '/deep-analysis': 2.0}
```

---

## How it differs from the x402 middleware

| | `@PaidEndpoint` | `X402Middleware` |
|---|---|---|
| Scope | Per-route | Global (PROTECTED_ROUTES set) |
| Price | Per-route | Global from `.env` |
| Use case | Framework users adding new endpoints | Core demo routes |

For the demo flow (`/api/premium-query`), both the middleware and decorator pattern are shown. Use whichever fits your architecture.
