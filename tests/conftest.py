"""
tests/conftest.py
------------------
Shared pytest fixtures for the HACK toolkit test suite.

Fixtures:
  fake_settings      — Settings with safe dummy values (no real Hedera creds).
  fake_quote_store   — Fresh InMemoryQuoteStore per test.
  fake_lifecycle     — QuoteLifecycleService wired to fake_quote_store.
  fake_verifier      — AsyncMock returning a valid Mirror Node tx dict.
  fake_receipt_service — InMemoryReceiptService (no HCS calls).
  fake_container     — ServiceContainer with all fakes injected.

All async tests run with asyncio_mode = "auto" (set in pyproject.toml).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from hack.config import Settings
from hack.container import ServiceContainer
from hack.core.quote_lifecycle import QuoteLifecycleService
from hack.metering.service import InMemoryMeteringService
from hack.receipts.memory import InMemoryReceiptService
from hack.stores.memory import InMemoryQuoteStore


# ─── Settings ─────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_settings() -> Settings:
    """Return a Settings instance with dummy values safe for testing."""
    return Settings(
        hedera_operator_id="0.0.999999",
        hedera_operator_key="302e020100300506032b6570042204200000000000000000000000000000000000000000000000000000000000000001",
        hedera_network="testnet",
        x402_payment_receiver_account_id="0.0.12345",
        x402_payment_amount_hbar=0.5,
        x402_payment_memo="test-payment",
        hcs_receipt_topic_id="",  # disabled — uses InMemoryReceiptService
        mirror_node_url="",
        quote_ttl_seconds=600,
        grant_ttl_seconds=300,
        openai_api_key="",
        anthropic_api_key="",
        groq_api_key="",
    )


# ─── Stores ───────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_quote_store() -> InMemoryQuoteStore:
    """Return a fresh, empty InMemoryQuoteStore."""
    return InMemoryQuoteStore()


# ─── Lifecycle ────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_lifecycle(fake_quote_store: InMemoryQuoteStore) -> QuoteLifecycleService:
    """Return a QuoteLifecycleService wired to the fake quote store."""
    return QuoteLifecycleService(
        store=fake_quote_store,
        quote_ttl=600,
        grant_ttl=300,
    )


# ─── Verifier ─────────────────────────────────────────────────────────────────

def _valid_tx_dict(receiver: str = "0.0.12345", amount: int = 50_000_000) -> dict:
    """Return a minimal Mirror Node transaction dict for testing."""
    return {
        "transaction_id": "0.0.999999-1710000000-000000000",
        "result": "SUCCESS",
        "transfers": [
            {"account": receiver, "amount": amount},
            {"account": "0.0.3", "amount": -amount},
        ],
        "node": "0.0.3",
        "consensus_timestamp": "1710000000.000000000",
    }


@pytest.fixture
def fake_verifier() -> AsyncMock:
    """
    Return an AsyncMock that simulates a successful Mirror Node verification.
    Tests that need a different response should override .return_value or
    .side_effect on the returned mock.
    """
    mock = AsyncMock()
    mock.return_value = _valid_tx_dict()
    return mock


# ─── Receipt service ──────────────────────────────────────────────────────────

@pytest.fixture
def fake_receipt_service() -> InMemoryReceiptService:
    """Return a fresh InMemoryReceiptService."""
    return InMemoryReceiptService()


# ─── Full container ───────────────────────────────────────────────────────────

@pytest.fixture
def fake_container(
    fake_settings: Settings,
    fake_quote_store: InMemoryQuoteStore,
    fake_verifier: AsyncMock,
    fake_receipt_service: InMemoryReceiptService,
) -> ServiceContainer:
    """
    Return a ServiceContainer with all infrastructure replaced by test doubles.
    The lifecycle, compliance engine, and certifier are wired to the fakes.
    """
    container = ServiceContainer(fake_settings)

    # Inject fakes into the container's internal caches
    container._quote_store = fake_quote_store
    container._verifier = fake_verifier
    container._receipt_service = fake_receipt_service
    container._metering = InMemoryMeteringService()

    # Force lifecycle to use the fake store
    container._lifecycle = QuoteLifecycleService(
        store=fake_quote_store,
        quote_ttl=fake_settings.quote_ttl_seconds,
        grant_ttl=fake_settings.grant_ttl_seconds,
    )

    return container
