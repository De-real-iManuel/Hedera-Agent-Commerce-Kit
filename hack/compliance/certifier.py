"""
hack/compliance/certifier.py
-----------------------------
CertificationService — issues auditable certifications.

Two flows:

  1. **Per-transaction certification (legacy)**
     ``certify(quote, transaction_id, tx_data) -> CertificationReport``
     Runs the payment-compliance engine against a paid transaction and
     optionally publishes an HCS receipt.

  2. **Service-audit certification (new)**
     ``certify_service_audit(report, recipient) -> SoulboundCertificate``
     Mints a soulbound NFT bound to the audit report + publishes an HCS
     receipt anchoring the mint on-chain.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from typing import Optional

from ..core.interfaces import ReceiptService
from ..models.compliance import (
    CertificationReport,
    ServiceAuditReport,
    SoulboundCertificate,
)
from ..models.quote import Quote, ReceiptModel
from ..nft.service import NftMintingService
from .engine import ComplianceEngine


class CertificationService:
    """
    Issues auditable certifications.

    Args:
        engine:          ComplianceEngine for per-tx checks.
        receipt_service: Optional ReceiptService (HCS or in-memory).
        nft_service:     Optional NftMintingService for soulbound certificates.
        network:         Hedera network ("testnet" or "mainnet").
        hcs_topic_id:    Optional HCS topic id (for certificate provenance).
    """

    def __init__(
        self,
        engine: ComplianceEngine,
        receipt_service: Optional[ReceiptService] = None,
        nft_service: Optional[NftMintingService] = None,
        network: str = "testnet",
        hcs_topic_id: str = "",
    ) -> None:
        self._engine = engine
        self._receipt_service = receipt_service
        self._nft_service = nft_service
        self._network = network
        self._hcs_topic_id = hcs_topic_id

    # ══════════════════════════════════════════════════════════════════════
    #  Per-transaction certification (legacy)
    # ══════════════════════════════════════════════════════════════════════

    async def certify(
        self,
        quote: Quote,
        transaction_id: str,
        tx_data: dict,
    ) -> CertificationReport:
        """Run per-tx compliance rules; publish HCS receipt if passing."""
        check_result = await self._engine.check(quote, transaction_id, tx_data)

        report_id = str(uuid.uuid4())
        hashscan_url = (
            f"https://hashscan.io/{self._network}/transaction/{transaction_id}"
        )
        hcs_receipt_id: Optional[str] = None

        if check_result.passed and self._receipt_service is not None:
            receipt = ReceiptModel(
                transaction_id=transaction_id,
                caller="certification-service",
                endpoint=quote.endpoint,
                amount_hbar=quote.amount_hbar,
                timestamp=int(time.time()),
                hashscan_url=hashscan_url,
            )
            published = await self._receipt_service.publish_receipt(receipt)
            if published.hcs_status == "published":
                hcs_receipt_id = published.transaction_id

        return CertificationReport(
            report_id=report_id,
            quote_id=quote.quote_id,
            transaction_id=transaction_id,
            issued_at=check_result.checked_at,
            passed=check_result.passed,
            rules=check_result.rules,
            hashscan_url=hashscan_url,
            hcs_receipt_id=hcs_receipt_id,
        )

    # ══════════════════════════════════════════════════════════════════════
    #  Service-audit certification (soulbound NFT)
    # ══════════════════════════════════════════════════════════════════════

    async def certify_service_audit(
        self,
        report: ServiceAuditReport,
        recipient_account_id: str,
        payment_transaction_id: str = "",
    ) -> SoulboundCertificate:
        """
        Mint a soulbound NFT certificate for a completed ServiceAuditReport,
        and publish an HCS receipt anchoring it on-chain.

        Args:
            report:                   A completed ServiceAuditReport.
            recipient_account_id:     Hedera account that paid — receives the NFT.
            payment_transaction_id:   The original HBAR payment transaction ID.

        Returns:
            A SoulboundCertificate. If minting failed, fields like
            ``mint_transaction_id`` and ``hashscan_tx_url`` will be empty
            but the certificate record is still returned and saved.
        """
        if self._nft_service is None:
            raise RuntimeError(
                "certify_service_audit requires an NftMintingService — "
                "check container wiring."
            )

        # 1. Build full metadata payload — this is what goes into the NFT
        #    and is hashed for the analysis_hash field.
        issued_at = int(time.time())
        report_hash = self.hash_report(report)
        metadata = {
            "version": "1.0.0",
            "report_id": report.report_id,
            "agent_name": report.request.service_name,
            "service_type": report.request.service_type,
            "endpoint": report.request.endpoint_url,
            "score": round(report.overall_score, 1),
            "grade": report.grade,
            "passed": report.passed,
            "issued_at": issued_at,
            "recipient": recipient_account_id,
            "owner_wallet": recipient_account_id,
            "network": self._network,
            "hcs_topic": self._hcs_topic_id or "",
            "payment_tx": payment_transaction_id,
            "report_hash": report_hash,
            "framework": "HACK v1.0.0",
        }

        # 2. Mint the NFT off the event loop (blocking SDK call)
        mint = await asyncio.to_thread(
            self._nft_service.mint, metadata, recipient_account_id,
        )

        # Surface mint errors clearly rather than silently storing empty fields
        if mint.error:
            import logging
            logging.getLogger("hack.certifier").error(
                "NFT mint failed for report %s: %s", report.report_id, mint.error
            )

        certificate_id = str(uuid.uuid4())
        network = self._network
        cert = SoulboundCertificate(
            certificate_id=certificate_id,
            report_id=report.report_id,
            agent_name=report.request.service_name,
            service_endpoint=report.request.endpoint_url,
            service_type=report.request.service_type,
            score=report.overall_score,
            grade=report.grade,
            version="1.0.0",
            token_id=mint.token_id,
            serial_number=mint.serial_number,
            recipient_account_id=recipient_account_id,
            treasury_account_id=mint.treasury_account_id,
            minted_at=mint.minted_at,
            hcs_topic_id=self._hcs_topic_id or None,
            payment_transaction_id=payment_transaction_id or None,
            mint_transaction_id=mint.transaction_id,
            metadata_hash=mint.metadata_hash or report_hash,
            hashscan_token_url=mint.hashscan_token_url,
            hashscan_tx_url=mint.hashscan_tx_url,
            hashscan_payment_url=(
                f"https://hashscan.io/{network}/transaction/{payment_transaction_id}"
                if payment_transaction_id else None
            ),
        )

        # 3. Anchor the certificate on HCS (best-effort, non-fatal)
        if self._receipt_service is not None and mint.transaction_id:
            try:
                anchor = ReceiptModel(
                    transaction_id=mint.transaction_id,
                    caller="hack-certifier",
                    endpoint=f"cert:{certificate_id}",
                    amount_hbar=0.0,
                    timestamp=cert.minted_at,
                    hashscan_url=cert.hashscan_tx_url,
                )
                published = await self._receipt_service.publish_receipt(anchor)
                cert.hcs_receipt_tx = published.transaction_id
                if published.hcs_status == "published":
                    report.hcs_receipt_id = published.transaction_id
                    # Build a direct link to the specific HCS message.
                    # HashScan supports ?sequenceNumber= to jump to the exact message.
                    if published.hcs_sequence_number and self._hcs_topic_id:
                        cert.hcs_sequence_number = published.hcs_sequence_number
                        cert.hashscan_hcs_message_url = (
                            f"https://hashscan.io/{network}/topic/{self._hcs_topic_id}"
                            f"?sequenceNumber={published.hcs_sequence_number}"
                        )
            except Exception:  # noqa: BLE001
                pass

        return cert

    # ── Convenience helpers ────────────────────────────────────────────────

    @staticmethod
    def hash_report(report: ServiceAuditReport) -> str:
        """SHA-256 of the report's canonical JSON — pin to on-chain metadata."""
        canonical = report.model_dump_json()
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
