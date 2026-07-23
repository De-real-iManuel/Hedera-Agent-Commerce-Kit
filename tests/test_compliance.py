"""
tests/test_compliance.py
-------------------------
Unit tests for the compliance engine, individual rules, and the
CertificationService.
"""

from __future__ import annotations

import time

import pytest

from hack.compliance.certifier import CertificationService
from hack.compliance.engine import ComplianceEngine
from hack.compliance.rules import (
    check_amount,
    check_quote_expiry,
    check_receiver_match,
    check_replay_protection,
    DEFAULT_RULES,
)
from hack.models.quote import PaymentStatus, Quote
from hack.receipts.memory import InMemoryReceiptService


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_quote(
    status: PaymentStatus = PaymentStatus.VERIFIED,
    expires_offset: float = 600.0,
    receiver: str = "0.0.12345",
    amount_hbar: float = 0.5,
) -> Quote:
    now = time.time()
    return Quote(
        quote_id="test-quote-id",
        endpoint="/api/premium-query",
        amount_hbar=amount_hbar,
        receiver=receiver,
        resource_hash="abc123",
        issued_at=now,
        expires_at=now + expires_offset,
        status=status,
        transaction_id="0.0.999-1710000000-000000001",
    )


def make_tx_data(
    receiver: str = "0.0.12345",
    amount: int = 50_000_000,
) -> dict:
    return {
        "result": "SUCCESS",
        "transfers": [
            {"account": receiver, "amount": amount},
            {"account": "0.0.3", "amount": -amount},
        ],
    }


# ─── Individual rule tests ────────────────────────────────────────────────────

def test_expiry_rule_passes_valid_quote():
    quote = make_quote(expires_offset=600.0)
    rule = check_quote_expiry(quote, {})
    assert rule.passed is True


def test_expiry_rule_fails_expired_quote():
    quote = make_quote(expires_offset=-1.0, status=PaymentStatus.EXPIRED)
    rule = check_quote_expiry(quote, {})
    assert rule.passed is False


def test_replay_rule_passes_verified_quote():
    quote = make_quote(status=PaymentStatus.VERIFIED)
    rule = check_replay_protection(quote, {})
    assert rule.passed is True


def test_replay_rule_fails_consumed_quote():
    quote = make_quote(status=PaymentStatus.CONSUMED)
    rule = check_replay_protection(quote, {})
    assert rule.passed is False
    assert "consumed" in rule.detail.lower()


def test_amount_rule_passes_sufficient_payment():
    quote = make_quote(amount_hbar=0.5)
    tx = make_tx_data(amount=50_000_000)  # exactly 0.5 HBAR
    rule = check_amount(quote, tx)
    assert rule.passed is True


def test_amount_rule_fails_underpayment():
    quote = make_quote(amount_hbar=0.5)
    tx = make_tx_data(amount=1_000)  # far below 0.5 HBAR
    rule = check_amount(quote, tx)
    assert rule.passed is False
    assert "Insufficient" in rule.detail


def test_receiver_rule_passes_correct_receiver():
    quote = make_quote(receiver="0.0.12345")
    tx = make_tx_data(receiver="0.0.12345")
    rule = check_receiver_match(quote, tx)
    assert rule.passed is True


def test_receiver_rule_fails_wrong_receiver():
    quote = make_quote(receiver="0.0.12345")
    tx = make_tx_data(receiver="0.0.99999")
    rule = check_receiver_match(quote, tx)
    assert rule.passed is False


# ─── Engine integration tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_rules_pass_with_valid_data():
    """All default rules should pass for a valid, unexpired, paid quote."""
    engine = ComplianceEngine(rules=list(DEFAULT_RULES))
    quote = make_quote(status=PaymentStatus.VERIFIED, expires_offset=600.0)
    tx_data = make_tx_data()
    result = await engine.check(quote, "0.0.999-1710000000-000000001", tx_data)

    assert result.passed is True
    assert all(r.passed for r in result.rules)
    assert result.quote_id == "test-quote-id"


@pytest.mark.asyncio
async def test_compliance_check_fails_underpayment():
    """An underpayment should cause the amount rule to fail and overall to fail."""
    engine = ComplianceEngine(rules=[check_amount])
    quote = make_quote(amount_hbar=0.5)
    tx_data = make_tx_data(amount=100)  # tiny amount
    result = await engine.check(quote, "0.0.999-0-0", tx_data)

    assert result.passed is False
    assert result.rules[0].rule_id == "amount"
    assert result.rules[0].passed is False


# ─── Certifier tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_certifier_returns_passed_report():
    """CertificationService should issue a report with passed=True for valid data."""
    receipt_svc = InMemoryReceiptService()
    engine = ComplianceEngine(rules=list(DEFAULT_RULES))
    certifier = CertificationService(
        engine=engine,
        receipt_service=receipt_svc,
        network="testnet",
    )

    quote = make_quote(status=PaymentStatus.VERIFIED, expires_offset=600.0)
    tx_data = make_tx_data()
    tx_id = "0.0.999-1710000000-000000001"

    report = await certifier.certify(quote, tx_id, tx_data)

    assert report.passed is True
    assert report.quote_id == "test-quote-id"
    assert report.transaction_id == tx_id
    assert "hashscan.io" in report.hashscan_url
    assert report.report_id  # non-empty UUID


@pytest.mark.asyncio
async def test_certifier_returns_failed_report_for_expired():
    """CertificationService should issue a failed report for an expired quote."""
    receipt_svc = InMemoryReceiptService()
    engine = ComplianceEngine(rules=[check_quote_expiry])
    certifier = CertificationService(engine=engine, receipt_service=receipt_svc)

    quote = make_quote(status=PaymentStatus.EXPIRED, expires_offset=-10.0)
    tx_data = make_tx_data()

    report = await certifier.certify(quote, "0.0.999-0-0", tx_data)

    assert report.passed is False
    assert report.rules[0].passed is False
