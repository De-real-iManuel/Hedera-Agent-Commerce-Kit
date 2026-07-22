from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Hedera operator ──────────────────────────────────────────────────────
    # Used by Hedera Agent Kit to set the network operator.
    # NEVER log or echo these values.
    hedera_operator_id: str
    hedera_operator_key: str
    hedera_network: str = "testnet"

    # ── x402 payment ─────────────────────────────────────────────────────────
    x402_payment_receiver_account_id: str
    x402_payment_amount_hbar: float = 0.5
    x402_payment_memo: str = "hack-payment"

    # ── HCS ──────────────────────────────────────────────────────────────────
    hcs_receipt_topic_id: str

    # ── LLM provider (for Hedera Agent Kit agent) ─────────────────────────────
    # Set exactly one. The agent router picks the first non-empty value.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""

    # ── Server ───────────────────────────────────────────────────────────────
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
