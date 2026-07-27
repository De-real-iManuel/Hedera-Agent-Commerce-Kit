"""
hack/audit/static_rules.py
---------------------------
Static analysis of a single fetched source file — regex-based checks
producing AuditFindings.

Rules are intentionally coarse (regex, not AST) so we can run them against
Python, JavaScript, Go, or Rust sources with minimal per-language logic.
Each rule returns exactly one AuditFinding.
"""

from __future__ import annotations

import re

from ..models.compliance import AuditFinding


# ─── Individual static rules ────────────────────────────────────────────────


_X402_HINTS = re.compile(
    r"(X402Middleware|PaidEndpoint|x402_paid|require_payment|@paid_endpoint|"
    r"paidEndpoint|X-Payment-Token|X-Quote-Id|"
    # MCP / programmatic x402 patterns
    r"payment_required|create_quote|advance_to_verified|advance_to_granted|"
    r"advance_to_consumed|QuoteLifecycleService|lifecycle\.create_quote|"
    r"status.*402|[\"']402[\"']|type.*payment_required)",
    re.IGNORECASE,
)
_HCS_HINTS = re.compile(
    r"(TopicMessageSubmitTransaction|HCSReceiptService|hcs_receipt|"
    r"publish_receipt|topic_id)",
    re.IGNORECASE,
)
_MIRROR_HINTS = re.compile(
    r"(mirrornode|MirrorNodeVerifier|mirror_node|verify_transaction)",
    re.IGNORECASE,
)
_REPLAY_HINTS = re.compile(
    r"(nonce|already_consumed|quote_lifecycle|mark_consumed|"
    r"idempotency|used_quotes|consumed_quotes|"
    # MCP / HACK lifecycle patterns
    r"advance_to_consumed|AlreadyConsumedError|CONSUMED|"
    r"advance_to_verified|advance_to_granted|PaymentStatus)",
    re.IGNORECASE,
)
_ERROR_HINTS = re.compile(r"(try:|except\s|catch\s*\(|Result<|\.ok_or)", re.MULTILINE)
_SECRET_HINTS = re.compile(
    r"(private_key\s*=\s*[\"'][0-9a-fA-F]{32,}"
    r"|OPERATOR_KEY\s*=\s*[\"'][0-9a-fA-F]{32,}"
    r"|sk_live_[A-Za-z0-9]{20,})"
)


def check_x402_middleware(content: str, source_path: str) -> AuditFinding:
    if _X402_HINTS.search(content):
        return AuditFinding(
            finding_id="static-x402-middleware",
            section="architecture",
            title="Source references x402 payment middleware",
            status="passed",
            severity="info",
            detail=f"Found x402 references in {source_path}.",
        )
    return AuditFinding(
        finding_id="static-x402-middleware",
        section="architecture",
        title="Source references x402 payment middleware",
        status="failed",
        severity="high",
        detail=f"No x402 middleware or decorator references found in {source_path}.",
        remediation="Import `hack.middleware.X402Middleware` or the `@x402_paid` decorator.",
    )


def check_hcs_receipts(content: str, source_path: str) -> AuditFinding:
    if _HCS_HINTS.search(content):
        return AuditFinding(
            finding_id="static-hcs-receipts",
            section="architecture",
            title="Source publishes HCS receipts",
            status="passed",
            severity="info",
            detail=f"Found HCS receipt publishing references in {source_path}.",
        )
    return AuditFinding(
        finding_id="static-hcs-receipts",
        section="architecture",
        title="Source publishes HCS receipts",
        status="warning",
        severity="medium",
        detail="No HCS receipt publishing detected — payments will not be anchored on-chain.",
        remediation="Configure `HCS_RECEIPT_TOPIC_ID` and wire `HCSReceiptService` into the container.",
    )


def check_mirror_verification(content: str, source_path: str) -> AuditFinding:
    if _MIRROR_HINTS.search(content):
        return AuditFinding(
            finding_id="static-mirror-verify",
            section="security",
            title="Source verifies transactions via Mirror Node",
            status="passed",
            severity="info",
            detail="Mirror Node verification is present.",
        )
    return AuditFinding(
        finding_id="static-mirror-verify",
        section="security",
        title="Source verifies transactions via Mirror Node",
        status="failed",
        severity="critical",
        detail="No Mirror Node verification found — payments cannot be trusted.",
        remediation="Verify every payment through `hack.verifiers.MirrorNodeVerifier`.",
    )


def check_replay_protection(content: str, source_path: str) -> AuditFinding:
    if _REPLAY_HINTS.search(content):
        return AuditFinding(
            finding_id="static-replay-protection",
            section="security",
            title="Quote/token replay protection is implemented",
            status="passed",
            severity="info",
            detail="Nonce or single-use quote logic detected.",
        )
    return AuditFinding(
        finding_id="static-replay-protection",
        section="security",
        title="Quote/token replay protection is implemented",
        status="warning",
        severity="high",
        detail="No obvious replay protection detected — the same payment might be reused.",
        remediation="Track consumed quote IDs via `QuoteLifecycleService.mark_consumed`.",
    )


def check_error_handling(content: str, source_path: str) -> AuditFinding:
    if _ERROR_HINTS.search(content):
        return AuditFinding(
            finding_id="static-error-handling",
            section="best_practices",
            title="Handlers wrap external calls in error handling",
            status="passed",
            severity="info",
            detail="try/except (or equivalent) blocks are present.",
        )
    return AuditFinding(
        finding_id="static-error-handling",
        section="best_practices",
        title="Handlers wrap external calls in error handling",
        status="warning",
        severity="low",
        detail="No try/except blocks detected — external failures may crash the service.",
        remediation="Wrap Mirror Node and HCS calls in try/except and return graceful errors.",
    )


def check_no_secrets(content: str, source_path: str) -> AuditFinding:
    match = _SECRET_HINTS.search(content)
    if match:
        return AuditFinding(
            finding_id="static-no-secrets",
            section="security",
            title="Source does not contain hardcoded private keys",
            status="failed",
            severity="critical",
            detail="Hardcoded private key or API secret detected in source.",
            evidence=match.group(0)[:80] + "…",
            remediation="Move secrets to environment variables. Rotate any leaked keys immediately.",
        )
    return AuditFinding(
        finding_id="static-no-secrets",
        section="security",
        title="Source does not contain hardcoded private keys",
        status="passed",
        severity="info",
        detail="No obvious hardcoded secrets detected.",
    )


DEFAULT_STATIC_RULES = [
    check_x402_middleware,
    check_hcs_receipts,
    check_mirror_verification,
    check_replay_protection,
    check_error_handling,
    check_no_secrets,
]


def run_static_rules(content: str, source_path: str) -> list[AuditFinding]:
    """Run every default static rule against *content*; return findings."""
    findings: list[AuditFinding] = []
    for rule in DEFAULT_STATIC_RULES:
        try:
            findings.append(rule(content, source_path))
        except Exception as exc:  # noqa: BLE001
            findings.append(
                AuditFinding(
                    finding_id=f"static-error-{rule.__name__}",
                    section="best_practices",
                    title=f"Static rule {rule.__name__} failed to run",
                    status="warning",
                    severity="low",
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
    return findings
