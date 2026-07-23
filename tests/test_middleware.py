"""
tests/test_middleware.py
-------------------------
Integration tests for X402Middleware using Starlette's TestClient.

Tests cover:
  - 402 returned when payment headers are absent
  - 200 returned when quote is in GRANTED state and headers are correct
  - 402 returned when the quote has been consumed (double-spend prevention)
  - 402 returned when the quote has expired
"""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hack.core.quote_lifecycle import QuoteLifecycleService
from hack.middleware.x402 import X402Middleware
from hack.models.quote import PaymentStatus
from hack.stores.memory import InMemoryQuoteStore


# ─── App factory ─────────────────────────────────────────────────────────────

def make_app(lifecycle: QuoteLifecycleService) -> FastAPI:
    """Create a minimal FastAPI app with X402Middleware protecting /premium."""
    app = FastAPI()
    app.add_middleware(
        X402Middleware,
        lifecycle=lifecycle,
        protected_routes={"/premium"},
    )

    @app.get("/premium")
    async def premium():
        return {"result": "paid access granted"}

    @app.get("/free")
    async def free():
        return {"result": "free access"}

    return app


def make_lifecycle_with_granted_quote(
    quote_ttl: int = 600,
    grant_ttl: int = 300,
) -> tuple[QuoteLifecycleService, str, str]:
    """
    Build a lifecycle service, create a quote, and advance it to GRANTED.
    Returns (lifecycle, quote_id, transaction_id).
    """
    store = InMemoryQuoteStore()
    lifecycle = QuoteLifecycleService(store=store, quote_ttl=quote_ttl, grant_ttl=grant_ttl)

    quote = lifecycle.create_quote("/premium", 0.5, "0.0.12345")
    tx_id = "0.0.999-1710000000-000000099"

    lifecycle.advance_to_verified(quote.quote_id, tx_id)
    lifecycle.advance_to_granted(quote.quote_id)

    return lifecycle, quote.quote_id, tx_id


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_middleware_returns_402_without_headers():
    """Accessing a protected route without payment headers returns 402."""
    store = InMemoryQuoteStore()
    lifecycle = QuoteLifecycleService(store=store)
    app = make_app(lifecycle)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/premium")
    assert response.status_code == 402
    body = response.json()
    assert body["error"] == "Payment Required"
    assert "how_to_pay" in body


def test_middleware_passes_with_granted_quote():
    """A GRANTED quote with correct headers should allow the request through."""
    lifecycle, quote_id, tx_id = make_lifecycle_with_granted_quote()
    app = make_app(lifecycle)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/premium",
        headers={"X-Payment-Token": tx_id, "X-Quote-Id": quote_id},
    )
    assert response.status_code == 200
    assert response.json()["result"] == "paid access granted"


def test_middleware_returns_402_on_consumed_quote():
    """After the first successful request, the quote is CONSUMED and a second fails."""
    lifecycle, quote_id, tx_id = make_lifecycle_with_granted_quote()
    app = make_app(lifecycle)
    client = TestClient(app, raise_server_exceptions=False)

    headers = {"X-Payment-Token": tx_id, "X-Quote-Id": quote_id}

    # First request — succeeds and consumes the quote
    r1 = client.get("/premium", headers=headers)
    assert r1.status_code == 200

    # Second request — the quote is now CONSUMED
    r2 = client.get("/premium", headers=headers)
    assert r2.status_code == 402
    assert "consumed" in r2.json().get("detail", "").lower()


def test_middleware_returns_402_on_expired_quote():
    """An expired quote (grant window elapsed) should return 402."""
    store = InMemoryQuoteStore()
    # Grant TTL of 0 seconds — the grant is immediately expired
    lifecycle = QuoteLifecycleService(store=store, quote_ttl=600, grant_ttl=0)

    quote = lifecycle.create_quote("/premium", 0.5, "0.0.12345")
    tx_id = "0.0.999-1710000000-000000098"
    lifecycle.advance_to_verified(quote.quote_id, tx_id)
    lifecycle.advance_to_granted(quote.quote_id)

    # Manually push the grant_expires_at into the past
    q = store.get_quote(quote.quote_id)
    q.grant_expires_at = time.time() - 10
    store.save_quote(q)

    app = make_app(lifecycle)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/premium",
        headers={"X-Payment-Token": tx_id, "X-Quote-Id": quote.quote_id},
    )
    assert response.status_code == 402


def test_free_route_passes_without_headers():
    """Non-protected routes should pass through the middleware untouched."""
    store = InMemoryQuoteStore()
    lifecycle = QuoteLifecycleService(store=store)
    app = make_app(lifecycle)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/free")
    assert response.status_code == 200
    assert response.json()["result"] == "free access"
