"""
hack/config.py
---------------
Settings — Pydantic BaseSettings for the HACK toolkit.

All fields map directly to environment variables (case-insensitive).
Sensitive fields (operator key, API keys) are intentionally typed as str
and must never be logged or echoed in responses.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Hedera operator ──────────────────────────────────────────────────────
    hedera_operator_id: str = ""
    hedera_operator_key: str = ""
    hedera_network: str = "testnet"

    # ── x402 payment ─────────────────────────────────────────────────────────
    x402_payment_receiver_account_id: str = ""
    x402_payment_amount_hbar: float = 0.5
    x402_payment_memo: str = "hack-payment"

    # ── HCS ──────────────────────────────────────────────────────────────────
    hcs_receipt_topic_id: str = ""

    # ── NFT (soulbound compliance certificates) ──────────────────────────────
    # Empty = auto-create the token on first certification (id then persisted
    # to .hack_state.json in the working directory).
    hack_nft_token_id: str = ""
    hack_nft_token_name: str = "HACK Compliance Certificate"
    hack_nft_token_symbol: str = "HACKCERT"

    # ── Mirror Node ──────────────────────────────────────────────────────────
    mirror_node_url: str = ""

    # ── Quote / grant TTLs ───────────────────────────────────────────────────
    quote_ttl_seconds: int = 600
    grant_ttl_seconds: int = 300

    # ── LLM provider (OpenAI-compatible; Groq works out of the box) ──────────
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "llama3-8b-8192"
    # llm_base_url aliases openai_base_url — accepts either env var name
    llm_base_url: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # ── Compliance audit engine (developer service audits) ───────────────────
    github_token: str = ""
    compliance_probe_timeout_sec: int = 15
    compliance_store_dir: str = "./data/reports"

    # ── Server ───────────────────────────────────────────────────────────────
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Derived helpers ──────────────────────────────────────────────────────
    def resolved_llm_key(self) -> str:
        """Return the first configured LLM key (Groq > OpenAI > Anthropic)."""
        return self.groq_api_key or self.openai_api_key or self.anthropic_api_key

    def resolved_llm_base_url(self) -> str:
        """Groq uses its own OpenAI-compatible URL when the Groq key is set."""
        if self.groq_api_key:
            return "https://api.groq.com/openai/v1"
        # LLM_BASE_URL overrides OPENAI_BASE_URL when set
        return self.llm_base_url or self.openai_base_url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings singleton (reads .env on first call)."""
    return Settings()  # type: ignore[call-arg]
