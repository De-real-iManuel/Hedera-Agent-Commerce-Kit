"""
hack/compliance/certifier.py
-----------------------------
CertificationService — issues a CertificationReport after running the
compliance engine against a Quote + transaction.

If compliance passes and a ReceiptService is configured, the certification
is optionally published to HCS via the receipt service, giving auditors an
immutable on-chain record.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from .engine import ComplianceEngine
from ..core.interfaces import ReceiptService
from ..models.compliance import CertificationReport
from ..models.quote import Quote, ReceiptModel


class CertificationService:
    """
    Issues auditable CertificationReports for verified payment transactions.

    Args:
        engine:          ComplianceEngine with the desired rule set.
        receipt_service: Optional ReceiptService.  If provided and the
                         compliance check passes, a receipt is published.
        network:         Hedera network name for Hashscan URL construction.
    """

    def __init__(
        self,
        engine: ComplianceEngine,
        receipt_service: Optional[ReceiptService] = None,
        network: str = "testnet",
    ) -> None:
        self._engine = engine
        self._receipt_service = receipt_service
        self._network = network

    async def certify(
        self,
        quote: Quote,
        transaction_id: str,
        tx_data: dict,
    ) -> CertificationReport:
        """
        Run all compliance rules and issue a CertificationReport.

        If compliance passes and a receipt service is present, publish a
        receipt to HCS and record the resulting hcs_receipt_id.

        Args:
            quote:          The Quote being certified.
            transaction_id: The on-chain transaction ID.
            tx_data:        Raw Mirror Node transaction dict.

        Returns:
            A fully populated CertificationReport.
        """
        check_result = await self._engine.check(quote, transaction_id, tx_data)

        report_id = str(uuid.uuid4())
        hashscan_url = (
            f"https://hashscan.io/{self._network}/transaction/{transaction_id}"
        )

        hcs_receipt_id: Optional[str] = None

        # Optionally publish to HCS when the check passes
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
