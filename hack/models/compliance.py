"""
hack/models/compliance.py
--------------------------
Pydantic v2 models for compliance checking, service audits, and
certification reports.

Two flows coexist here:

  1. **Payment compliance** — did a specific tx satisfy the quote?
     Models: ComplianceRule, ComplianceCheckResult, CertificationReport.

  2. **Service audit** — is a developer's x402 / MCP service correctly
     implemented? Runs live probes + repo static checks + LLM review.
     Models: ServiceAuditRequest, AuditFinding, AuditSection,
     ServiceAuditReport, SoulboundCertificate, CertificateSummary.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ══════════════════════════════════════════════════════════════════════════════
#  Payment compliance (per-transaction)
# ══════════════════════════════════════════════════════════════════════════════


class ComplianceRule(BaseModel):
    """Result of running a single compliance rule against a transaction."""

    model_config = ConfigDict(frozen=False)

    rule_id: str
    name: str
    passed: bool
    detail: str


class ComplianceCheckResult(BaseModel):
    """Aggregated result of running all payment-compliance rules."""

    model_config = ConfigDict(frozen=False)

    quote_id: str
    transaction_id: str
    passed: bool
    rules: list[ComplianceRule] = Field(default_factory=list)
    checked_at: int  # unix ts


class CertificationReport(BaseModel):
    """Legacy: per-tx certification (kept for backwards compatibility)."""

    model_config = ConfigDict(frozen=False)

    report_id: str
    quote_id: str
    transaction_id: str
    issued_at: int
    passed: bool
    rules: list[ComplianceRule] = Field(default_factory=list)
    hashscan_url: str
    hcs_receipt_id: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
#  Service audit (per-developer-service)
# ══════════════════════════════════════════════════════════════════════════════


Severity = Literal["info", "low", "medium", "high", "critical"]
FindingStatus = Literal["passed", "warning", "failed"]
ServiceType = Literal["x402", "mcp", "hybrid"]


class ServiceAuditRequest(BaseModel):
    """Developer submission for a compliance audit."""

    service_name: str
    service_type: ServiceType
    endpoint_url: str  # e.g. https://myapi.example.com/api/premium-query
    repo_url: Optional[str] = None  # e.g. https://github.com/user/repo
    primary_file: Optional[str] = "main.py"  # path within the repo to inspect
    contact_email: Optional[str] = None
    recipient_account_id: Optional[str] = None  # who receives the NFT
    source_code: Optional[str] = None  # pasted source — used when repo_url is absent


class AuditFinding(BaseModel):
    """A single finding produced by a probe, static check, or LLM analyst."""

    finding_id: str
    section: str  # section_id it belongs to
    title: str
    status: FindingStatus
    severity: Severity
    detail: str
    evidence: Optional[str] = None  # HTTP response snippet, code excerpt, etc.
    remediation: Optional[str] = None


class AuditSection(BaseModel):
    """A named group of findings — maps to a card in the report UI."""

    section_id: str
    title: str
    description: str
    weight: float = 1.0  # relative contribution to the overall score
    findings: list[AuditFinding] = Field(default_factory=list)
    score: float = 0.0  # 0.0 – 1.0, populated after all findings are in


class ServiceAuditReport(BaseModel):
    """Full audit report — the single source of truth for the frontend."""

    report_id: str
    request: ServiceAuditRequest
    created_at: int
    completed_at: Optional[int] = None
    status: Literal["running", "completed", "failed"] = "running"
    overall_score: float = 0.0  # 0 – 100
    grade: str = ""  # "A+", "A", "B", …
    passed: bool = False
    sections: list[AuditSection] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    executive_summary: str = ""
    hashscan_url: Optional[str] = None
    hcs_receipt_id: Optional[str] = None
    error: Optional[str] = None


class SoulboundCertificate(BaseModel):
    """On-chain soulbound NFT certificate metadata (mirrors HTS mint)."""

    certificate_id: str
    report_id: str
    agent_name: str
    service_endpoint: Optional[str] = None        # the audited service URL
    service_type: Optional[str] = None            # x402 / mcp / hybrid
    score: float
    grade: str
    version: str = "1.0.0"
    token_id: str
    serial_number: int
    recipient_account_id: str                      # owner wallet
    treasury_account_id: str
    minted_at: int
    hcs_topic_id: Optional[str] = None            # topic where receipt is anchored
    hcs_receipt_tx: Optional[str] = None          # HCS submit tx for the anchor
    payment_transaction_id: Optional[str] = None  # the original HBAR payment tx
    mint_transaction_id: str
    metadata_hash: str                             # sha256 of full metadata JSON
    hashscan_token_url: str
    hashscan_tx_url: str
    hashscan_payment_url: Optional[str] = None    # direct link to payment tx


class CertificateSummary(BaseModel):
    """Row in the /certificates gallery."""

    certificate_id: str
    report_id: str
    agent_name: str
    score: float
    grade: str
    minted_at: int
    token_id: str
    serial_number: int
    hashscan_tx_url: str
