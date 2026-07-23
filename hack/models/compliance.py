"""
hack/models/compliance.py
--------------------------
Pydantic v2 models for compliance checking and certification reports.

Used by ComplianceEngine to communicate rule-by-rule results and by
CertificationService to issue signed, auditable CertificationReports.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ComplianceRule(BaseModel):
    """
    Result of running a single compliance rule against a transaction.
    Each rule has a stable rule_id for programmatic filtering.
    """

    model_config = ConfigDict(frozen=False)

    rule_id: str
    name: str
    passed: bool
    detail: str


class ComplianceCheckResult(BaseModel):
    """
    Aggregated result of running all compliance rules against a quote/transaction
    pair. `passed` is True only if every individual rule passed.
    """

    model_config = ConfigDict(frozen=False)

    quote_id: str
    transaction_id: str
    passed: bool
    rules: list[ComplianceRule] = Field(default_factory=list)
    checked_at: int  # Unix timestamp


class CertificationReport(BaseModel):
    """
    Auditable certification report issued by CertificationService.
    If the compliance check passed, it is optionally published to HCS and
    includes the resulting hcs_receipt_id.
    """

    model_config = ConfigDict(frozen=False)

    report_id: str  # UUID
    quote_id: str
    transaction_id: str
    issued_at: int  # Unix timestamp
    passed: bool
    rules: list[ComplianceRule] = Field(default_factory=list)
    hashscan_url: str
    hcs_receipt_id: Optional[str] = None
