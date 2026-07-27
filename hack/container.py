"""
hack/container.py
------------------
ServiceContainer — dependency injection root for the HACK toolkit.

Every concrete service is built lazily on first property access and cached.
Callers get a ServiceContainer instance via ``ServiceContainer.from_settings()``.
"""

from __future__ import annotations

from .audit.service_auditor import ServiceAuditor
from .audit.store import ReportStore
from .compliance.certifier import CertificationService
from .compliance.engine import ComplianceEngine
from .compliance.rules import DEFAULT_RULES
from .config import Settings, get_settings
from .core.interfaces import MeteringService, PaymentVerifier, QuoteStore, ReceiptService
from .core.quote_lifecycle import QuoteLifecycleService
from .metering.service import InMemoryMeteringService
from .nft.service import NftMintingService
from .receipts.hcs import HCSReceiptService
from .receipts.memory import InMemoryReceiptService
from .reporting.pdf import PdfReporter
from .reporting.skill_md import SkillMdGenerator
from .stores.memory import InMemoryQuoteStore
from .verifiers.mirror_node import MirrorNodeVerifier


class ServiceContainer:
    """Wires all concrete HACK service implementations together (lazy)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._quote_store: QuoteStore | None = None
        self._verifier: PaymentVerifier | None = None
        self._receipt_service: ReceiptService | None = None
        self._metering: MeteringService | None = None
        self._lifecycle: QuoteLifecycleService | None = None
        self._compliance_engine: ComplianceEngine | None = None
        self._certifier: CertificationService | None = None
        self._nft_service: NftMintingService | None = None
        self._service_auditor: ServiceAuditor | None = None
        self._report_store: ReportStore | None = None
        self._pdf: PdfReporter | None = None
        self._skill_md: SkillMdGenerator | None = None

    @classmethod
    def from_settings(cls) -> ServiceContainer:
        return cls(get_settings())

    # ─── Payment-side services ──────────────────────────────────────────────

    @property
    def quote_store(self) -> QuoteStore:
        if self._quote_store is None:
            self._quote_store = InMemoryQuoteStore()
        return self._quote_store

    @property
    def verifier(self) -> PaymentVerifier:
        if self._verifier is None:
            s = self._settings
            # Resolve the mirror node URL based on the network if not explicitly set
            if s.mirror_node_url:
                mirror_url = s.mirror_node_url
            elif s.hedera_network == "mainnet":
                mirror_url = "https://mainnet-public.mirrornode.hedera.com"
            else:
                mirror_url = "https://testnet.mirrornode.hedera.com"
            self._verifier = MirrorNodeVerifier(base_url=mirror_url)
        return self._verifier

    @property
    def receipt_service(self) -> ReceiptService:
        if self._receipt_service is None:
            s = self._settings
            if s.hcs_receipt_topic_id and s.hedera_operator_id and s.hedera_operator_key:
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
        if self._metering is None:
            self._metering = InMemoryMeteringService()
        return self._metering

    @property
    def lifecycle(self) -> QuoteLifecycleService:
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
        if self._compliance_engine is None:
            self._compliance_engine = ComplianceEngine(rules=list(DEFAULT_RULES))
        return self._compliance_engine

    @property
    def certifier(self) -> CertificationService:
        if self._certifier is None:
            s = self._settings
            self._certifier = CertificationService(
                engine=self.compliance_engine,
                receipt_service=self.receipt_service,
                nft_service=self.nft_service,
                network=s.hedera_network,
                hcs_topic_id=s.hcs_receipt_topic_id,
            )
        return self._certifier

    # ─── Audit-side services (NEW) ──────────────────────────────────────────

    @property
    def nft_service(self) -> NftMintingService:
        if self._nft_service is None:
            s = self._settings
            self._nft_service = NftMintingService(
                operator_id=s.hedera_operator_id,
                operator_key=s.hedera_operator_key,
                network=s.hedera_network,
                token_name=s.hack_nft_token_name,
                token_symbol=s.hack_nft_token_symbol,
                token_id=s.hack_nft_token_id,
            )
        return self._nft_service

    @property
    def report_store(self) -> ReportStore:
        if self._report_store is None:
            self._report_store = ReportStore(base_dir=self._settings.compliance_store_dir)
        return self._report_store

    @property
    def pdf_reporter(self) -> PdfReporter:
        if self._pdf is None:
            self._pdf = PdfReporter()
        return self._pdf

    @property
    def skill_md(self) -> SkillMdGenerator:
        if self._skill_md is None:
            self._skill_md = SkillMdGenerator()
        return self._skill_md

    @property
    def service_auditor(self) -> ServiceAuditor:
        if self._service_auditor is None:
            s = self._settings
            self._service_auditor = ServiceAuditor(
                probe_timeout=s.compliance_probe_timeout_sec,
                github_token=s.github_token,
                llm_api_key=s.resolved_llm_key(),
                llm_base_url=s.resolved_llm_base_url(),
                llm_model=s.llm_model,
            )
        return self._service_auditor

    @property
    def settings(self) -> Settings:
        return self._settings
