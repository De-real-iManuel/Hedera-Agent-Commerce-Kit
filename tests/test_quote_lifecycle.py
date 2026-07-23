"""
tests/test_quote_lifecycle.py
------------------------------
Unit tests for QuoteLifecycleService state transitions.

All transitions are exercised: create → verified → granted → consumed,
plus all error paths (expired, replay, already consumed, sweep).
"""

from __future__ import annotations

import time

import pytest

from hack.core.exceptions import (
    AlreadyConsumedError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
)
from hack.core.quote_lifecycle import QuoteLifecycleService
from hack.models.quote import PaymentStatus
from hack.stores.memory import InMemoryQuoteStore


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_lifecycle(quote_ttl: int = 600, grant_ttl: int = 300) -> QuoteLifecycleService:
    return QuoteLifecycleService(
        store=InMemoryQuoteStore(),
        quote_ttl=quote_ttl,
        grant_ttl=grant_ttl,
    )


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_create_quote_returns_quoted_status():
    """create_quote() should return a Quote in QUOTED status."""
    svc = make_lifecycle()
    quote = svc.create_quote(
        endpoint="/api/premium-query",
        amount_hbar=0.5,
        receiver="0.0.12345",
    )
    assert quote.status == PaymentStatus.QUOTED
    assert quote.quote_id
    assert quote.resource_hash
    assert quote.expires_at > quote.issued_at


def test_advance_to_verified_succeeds():
    """A QUOTED quote should advance to VERIFIED with a transaction_id."""
    svc = make_lifecycle()
    quote = svc.create_quote("/api/ep", 0.5, "0.0.1")
    updated = svc.advance_to_verified(quote.quote_id, "0.0.999-1710000000-000000001")
    assert updated.status == PaymentStatus.VERIFIED
    assert updated.transaction_id == "0.0.999-1710000000-000000001"


def test_advance_to_verified_raises_on_expired_quote():
    """advance_to_verified() should raise PaymentExpiredError on an expired quote."""
    svc = make_lifecycle(quote_ttl=1)  # 1-second TTL
    quote = svc.create_quote("/api/ep", 0.5, "0.0.1")
    # Manually expire the quote by backdating expires_at
    quote.expires_at = time.time() - 1
    svc._store.save_quote(quote)

    with pytest.raises(PaymentExpiredError):
        svc.advance_to_verified(quote.quote_id, "0.0.999-1710000000-000000002")


def test_advance_to_verified_raises_replay_on_duplicate_tx():
    """Using the same transaction_id on a second quote should raise ReplayError."""
    svc = make_lifecycle()
    tx_id = "0.0.999-1710000000-000000003"

    quote_a = svc.create_quote("/api/ep", 0.5, "0.0.1")
    svc.advance_to_verified(quote_a.quote_id, tx_id)  # first use — OK

    quote_b = svc.create_quote("/api/ep", 0.5, "0.0.1")
    with pytest.raises(ReplayError):
        svc.advance_to_verified(quote_b.quote_id, tx_id)  # replay — must fail


def test_advance_to_granted_succeeds():
    """A VERIFIED quote should advance to GRANTED with a grant window."""
    svc = make_lifecycle()
    quote = svc.create_quote("/api/ep", 0.5, "0.0.1")
    svc.advance_to_verified(quote.quote_id, "0.0.999-1710000000-000000004")
    granted = svc.advance_to_granted(quote.quote_id)
    assert granted.status == PaymentStatus.GRANTED
    assert granted.grant_expires_at is not None
    assert granted.grant_expires_at > time.time()


def test_advance_to_consumed_succeeds():
    """A GRANTED quote should advance to CONSUMED exactly once."""
    svc = make_lifecycle()
    quote = svc.create_quote("/api/ep", 0.5, "0.0.1")
    svc.advance_to_verified(quote.quote_id, "0.0.999-1710000000-000000005")
    svc.advance_to_granted(quote.quote_id)
    consumed = svc.advance_to_consumed(quote.quote_id)
    assert consumed.status == PaymentStatus.CONSUMED
    assert consumed.consumed_at is not None


def test_advance_to_consumed_raises_on_already_consumed():
    """Consuming a quote a second time should raise AlreadyConsumedError."""
    svc = make_lifecycle()
    quote = svc.create_quote("/api/ep", 0.5, "0.0.1")
    svc.advance_to_verified(quote.quote_id, "0.0.999-1710000000-000000006")
    svc.advance_to_granted(quote.quote_id)
    svc.advance_to_consumed(quote.quote_id)

    with pytest.raises(AlreadyConsumedError):
        svc.advance_to_consumed(quote.quote_id)


def test_advance_to_verified_raises_on_unknown_quote():
    """advance_to_verified() with a non-existent quote_id should raise QuoteNotFoundError."""
    svc = make_lifecycle()
    with pytest.raises(QuoteNotFoundError):
        svc.advance_to_verified("nonexistent-id", "0.0.999-0-0")


def test_sweep_expired_marks_stale_quotes():
    """sweep_expired() should mark all QUOTED quotes past their TTL as EXPIRED."""
    svc = make_lifecycle(quote_ttl=600)
    # Create two quotes and manually expire their TTL
    q1 = svc.create_quote("/a", 0.5, "0.0.1")
    q2 = svc.create_quote("/b", 0.5, "0.0.1")
    q3 = svc.create_quote("/c", 0.5, "0.0.1")  # will remain valid

    q1.expires_at = time.time() - 1
    q2.expires_at = time.time() - 1
    svc._store.save_quote(q1)
    svc._store.save_quote(q2)
    # q3 expires_at is in the future — should NOT be swept

    count = svc.sweep_expired()
    assert count == 2

    assert svc.get_quote(q1.quote_id).status == PaymentStatus.EXPIRED
    assert svc.get_quote(q2.quote_id).status == PaymentStatus.EXPIRED
    assert svc.get_quote(q3.quote_id).status == PaymentStatus.QUOTED
