"""
hack/config.py
---------------
Settings — Pydantic BaseSettings for the HACK toolkit.

All fields map directly to environment variables (case-insensitive).
Sensitive fields (operator key, API keys) are intentionally typed as str
and must never be logged or echoed in responses.

New fields vs original backend/config.py:
  - hcs_receipt_topic_id: default "" (HCS publishing is optional for dev)
  - quote_ttl_seconds:    int = 600  (quote validity window)
  - grant_ttl_seconds:    int = 300  (access grant window after verification)
  - mirror_node_url:      str = ""   (empty = auto-select from hedera_network)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Hedera operator ──────────────────────────────────────────────────────
    # Used by the Hedera SDK to sign transactions.
    # NEVER log or echo these values.
    hedera_operator_id: str = ""
    hedera_operator_key: str = ""
    hedera_network: str = "testnet"

    # ── x402 payment ─────────────────────────────────────────────────────────
    x402_payment_receiver_account_id: str = ""
    x402_payment_amount_hbar: float = 0.5
    x402_payment_memo: str = "hack-payment"

    # ── HCS ──────────────────────────────────────────────────────────────────
    # Empty string means HCS publishing is disabled; falls back to in-memory.
    hcs_receipt_topic_id: str = ""

    # ── Mirror Node ──────────────────────────────────────────────────────────
    # Empty string = auto-select URL from hedera_network.
    mirror_node_url: str = ""

    # ── Quote / grant TTLs ───────────────────────────────────────────────────
    quote_ttl_seconds: int = 600   # 10 minutes
    grant_ttl_seconds: int = 300   # 5 minutes

    # ── LLM provider ─────────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # ── Server ───────────────────────────────────────────────────────────────
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (reads .env on first call)."""
    return Settings()  # type: ignore[call-arg]
