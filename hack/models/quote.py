"""
hack/models/quote.py
---------------------
Pydantic v2 data models for the x402 payment lifecycle.

Covers every stage from quote issuance through payment verification,
access grant, consumption, and optional refund, plus receipt and
metering records used across the rest of the toolkit.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PaymentStatus(str, Enum):
    """All valid states a Quote can occupy during its lifecycle."""

    QUOTED = "quoted"
    VERIFIED = "verified"
    GRANTED = "granted"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    DUPLICATE = "duplicate"
    REFUNDED = "refunded"


class Quote(BaseModel):
    """
    A single payment quote issued in response to a protected-resource request.

    Progresses through the state machine:
      QUOTED → VERIFIED → GRANTED → CONSUMED
    with EXPIRED and DUPLICATE as terminal failure states.
    """

    model_config = ConfigDict(frozen=False)

    quote_id: str
    endpoint: str
    amount_hbar: float
    receiver: str
    resource_hash: str  # SHA-256 of endpoint + quote_id
    issued_at: float
    expires_at: float
    status: PaymentStatus = PaymentStatus.QUOTED
    transaction_id: Optional[str] = None
    granted_at: Optional[float] = None
    grant_expires_at: Optional[float] = None
    consumed_at: Optional[float] = None
    error: Optional[str] = None


class ChallengeResponse(BaseModel):
    """
    HTTP 402 challenge payload returned by POST /api/payment/challenge.
    Tells the caller how much to pay and where to send it.
    """

    model_config = ConfigDict(frozen=False)

    status: int = 402
    quote_id: str
    resource_hash: str
    network: str
    receiver: str
    amount_hbar: float
    memo: str
    issued_at: int
    expires_at: int
    retry_instructions: str


class VerifyResponse(BaseModel):
    """
    Payload returned by POST /api/payment/verify on success.
    Contains the grant window and receipt details.
    """

    model_config = ConfigDict(frozen=False)

    verified: bool
    quote_id: str
    transaction_id: str
    grant_expires_at: int
    next_step: str


class ReceiptModel(BaseModel):
    """
    Immutable record of a verified payment, published to HCS.
    Stored in the ReceiptService for retrieval by transaction ID.
    """

    model_config = ConfigDict(frozen=False)

    transaction_id: str
    caller: str
    endpoint: str
    amount_hbar: float
    timestamp: int
    hashscan_url: str
    hcs_status: str = "pending"
    hcs_error: Optional[str] = None
    hcs_sequence_number: Optional[int] = None  # HCS topic sequence number of the submitted message


class UsageRecord(BaseModel):
    """Single metering event recorded after a successful consumed request."""

    model_config = ConfigDict(frozen=False)

    transaction_id: str
    caller: str
    endpoint: str
    amount_hbar: float
    timestamp: int


class UsageSummary(BaseModel):
    """Aggregate usage statistics across all metered requests."""

    model_config = ConfigDict(frozen=False)

    total_requests: int
    total_revenue_hbar: float
    records: list[UsageRecord] = Field(default_factory=list)
