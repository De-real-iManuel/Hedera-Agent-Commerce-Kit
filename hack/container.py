"""
hack/container.py
------------------
ServiceContainer — dependency injection root for the HACK toolkit.

Lazily constructs and caches every concrete service implementation,
wiring them together according to the provided Settings.

Usage in a FastAPI app:

    container = ServiceContainer.from_settings()
    app.state.container = container
    app.add_middleware(X402Middleware, lifecycle=container.lifecycle,
                       protected_routes={"/api/premium-query"})

Each property follows the lazy-init pattern: the first access constructs
and caches the instance; subsequent accesses return the cached object.
"""

from __future__ import annotations

from .compliance.certifier import CertificationService
from .compliance.engine import ComplianceEngine
from .compliance.rules import DEFAULT_RULES
from .config import Settings, get_settings
from .core.interfaces import MeteringService, PaymentVerifier, QuoteStore, ReceiptService
from .core.quote_lifecycle import QuoteLifecycleService
from .metering.service import InMemoryMeteringService
from .receipts.hcs import HCSReceiptService
from .receipts.memory import InMemoryReceiptService
from .stores.memory import InMemoryQuoteStore
from .verifiers.mirror_node import MirrorNodeVerifier


class ServiceContainer:
    """
    Wires all concrete HACK service implementations together.

    Services are built lazily on first property access and then cached
    on the instance.  This avoids import-time side effects and allows
    tests to replace individual components after construction.

    Args:
        settings: A populated Settings instance.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

        # Internal caches (None = not yet built)
        self._quote_store: QuoteStore | None = None
        self._verifier: PaymentVerifier | None = None
        self._receipt_service: ReceiptService | None = None
        self._metering: MeteringService | None = None
        self._lifecycle: QuoteLifecycleService | None = None
        self._compliance_engine: ComplianceEngine | None = None
        self._certifier: CertificationService | None = None

    # ─── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_settings(cls) -> ServiceContainer:
        """Build a ServiceContainer from the global cached Settings."""
        return cls(get_settings())

    # ─── Properties (lazy init) ───────────────────────────────────────────────

    @property
    def quote_store(self) -> QuoteStore:
        """In-memory quote store (swap for a persistent implementation in prod)."""
        if self._quote_store is None:
            self._quote_store = InMemoryQuoteStore()
        return self._quote_store

    @property
    def verifier(self) -> PaymentVerifier:
        """Mirror Node verifier, configured with the URL from settings."""
        if self._verifier is None:
            s = self._settings
            base_url = (
                s.mirror_node_url
                if s.mirror_node_url
                else ""  # MirrorNodeVerifier auto-selects if empty
            )
            self._verifier = MirrorNodeVerifier(
                base_url=base_url or "https://testnet.mirrornode.hedera.com",
            )
        return self._verifier

    @property
    def receipt_service(self) -> ReceiptService:
        """
        HCSReceiptService when a topic ID is configured; otherwise falls back
        to InMemoryReceiptService so the app works without Hedera credentials.
        """
        if self._receipt_service is None:
            s = self._settings
            if s.hcs_receipt_topic_id:
                self._receipt_service = HCSReceiptService(
                    topic_id=s.hcs_receipt_topic_id,
                    operator_id=s.hedera_operator_id,
                    operator_key=s.hedera_operator_key,
                    network=s.hedera_network,
                )
            else:
                self._receipt_service = InMemoryReceiptService()
        return self._receipt_service

    @property
    def metering(self) -> MeteringService:
        """In-memory metering service."""
        if self._metering is None:
            self._metering = InMemoryMeteringService()
        return self._metering

    @property
    def lifecycle(self) -> QuoteLifecycleService:
        """Quote lifecycle state machine, wired to the quote store."""
        if self._lifecycle is None:
            s = self._settings
            self._lifecycle = QuoteLifecycleService(
                store=self.quote_store,
                quote_ttl=s.quote_ttl_seconds,
                grant_ttl=s.grant_ttl_seconds,
            )
        return self._lifecycle

    @property
    def compliance_engine(self) -> ComplianceEngine:
        """Compliance engine with the default built-in rule set."""
        if self._compliance_engine is None:
            self._compliance_engine = ComplianceEngine(rules=list(DEFAULT_RULES))
        return self._compliance_engine

    @property
    def certifier(self) -> CertificationService:
        """Certification service wired to the compliance engine and receipt service."""
        if self._certifier is None:
            s = self._settings
            self._certifier = CertificationService(
                engine=self.compliance_engine,
                receipt_service=self.receipt_service,
                network=s.hedera_network,
            )
        return self._certifier

    @property
    def settings(self) -> Settings:
        """Expose the settings for use in routers."""
        return self._settings
