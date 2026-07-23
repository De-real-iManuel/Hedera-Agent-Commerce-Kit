"""
hack/__init__.py
-----------------
Hedera Agent Commerce Kit (HACK) — public API surface.

Top-level imports provide the complete developer-facing API so consumers
can use the toolkit without knowing the internal module layout:

    from hack import PaidEndpoint, ServiceContainer, Settings
    from hack import X402Middleware, QuoteLifecycleService
    from hack import ComplianceEngine, CertificationService
"""

from __future__ import annotations

from .compliance.certifier import CertificationService
from .compliance.engine import ComplianceEngine
from .config import Settings, get_settings
from .container import ServiceContainer
from .core.exceptions import (
    AlreadyConsumedError,
    HACKError,
    InsufficientPaymentError,
    PaymentExpiredError,
    QuoteNotFoundError,
    ReplayError,
    VerifierUnavailableError,
)
from .core.quote_lifecycle import QuoteLifecycleService
from .decorator import PaidEndpoint
from .middleware.x402 import X402Middleware
from .models.compliance import CertificationReport, ComplianceCheckResult, ComplianceRule
from .models.quote import (
    ChallengeResponse,
    PaymentStatus,
    Quote,
    ReceiptModel,
    UsageRecord,
    UsageSummary,
    VerifyResponse,
)

__all__ = [
    # Primary developer API
    "PaidEndpoint",
    "ServiceContainer",
    "Settings",
    "get_settings",
    "X402Middleware",
    # Core business logic
    "QuoteLifecycleService",
    "ComplianceEngine",
    "CertificationService",
    # Models
    "PaymentStatus",
    "Quote",
    "ChallengeResponse",
    "VerifyResponse",
    "ReceiptModel",
    "UsageRecord",
    "UsageSummary",
    "ComplianceRule",
    "ComplianceCheckResult",
    "CertificationReport",
    # Exceptions
    "HACKError",
    "PaymentExpiredError",
    "ReplayError",
    "InsufficientPaymentError",
    "VerifierUnavailableError",
    "AlreadyConsumedError",
    "QuoteNotFoundError",
]
