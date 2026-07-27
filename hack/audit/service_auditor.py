"""
hack/audit/service_auditor.py
------------------------------
ServiceAuditor — orchestrates the full audit of a developer's submitted
x402/MCP service and returns a ServiceAuditReport.

Pipeline
--------
1. Live HTTP probes against the endpoint (payment_flow, security, performance).
2. GitHub raw fetch of the primary source file → static rule pass
   (architecture, security, best_practices).
3. Aggregate findings into weighted sections; compute overall score & grade.
4. LLM-generated Executive Summary + Recommendations.
5. Return a completed ServiceAuditReport.

The auditor NEVER raises — probe failures and network errors are captured
as findings so the demo always produces a report.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from ..models.compliance import (
    AuditFinding,
    AuditSection,
    ServiceAuditReport,
    ServiceAuditRequest,
)
from .github import GithubFileFetcher
from .llm import LlmAnalyst
from .probes import EndpointProber
from .static_rules import run_static_rules


# Section catalogue (title + description + weight)
SECTION_CATALOG: list[tuple[str, str, str, float]] = [
    (
        "payment_flow",
        "Payment Flow",
        "Verifies that the endpoint correctly implements the x402 challenge/response protocol.",
        1.5,
    ),
    (
        "security",
        "Security & Verification",
        "Checks Mirror Node verification, replay protection, and secret handling.",
        2.0,
    ),
    (
        "architecture",
        "Architecture",
        "Confirms the service uses the HACK middleware and HCS receipts.",
        1.0,
    ),
    (
        "best_practices",
        "Best Practices",
        "Style, error handling, and general implementation hygiene.",
        0.7,
    ),
    (
        "performance",
        "Performance",
        "Latency and reliability of the payment-challenge response.",
        0.5,
    ),
]


def _grade(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _finding_score(f: AuditFinding) -> float:
    if f.status == "passed":
        return 1.0
    if f.status == "warning":
        return 0.5
    return 0.0


class ServiceAuditor:
    """Runs the full audit pipeline end-to-end."""

    def __init__(
        self,
        probe_timeout: int = 15,
        github_token: str = "",
        llm_api_key: str = "",
        llm_base_url: str = "https://api.openai.com/v1",
        llm_model: str = "gpt-4o-mini",
    ) -> None:
        self._prober = EndpointProber(timeout=float(probe_timeout))
        self._github = GithubFileFetcher(token=github_token, timeout=15.0)
        self._llm = LlmAnalyst(
            api_key=llm_api_key, base_url=llm_base_url, model=llm_model
        )

    async def audit(self, request: ServiceAuditRequest) -> ServiceAuditReport:
        """Run the audit pipeline. Never raises."""
        report_id = str(uuid.uuid4())
        created_at = int(time.time())
        report = ServiceAuditReport(
            report_id=report_id,
            request=request,
            created_at=created_at,
            status="running",
            sections=self._empty_sections(),
        )

        try:
            # 1. Live probes
            probe_findings = await self._prober.run_all(request.endpoint_url)

            # 2. Static analysis
            # Priority: repo_url (GitHub fetch) > source_code (pasted) > skip
            static_findings: list[AuditFinding] = []
            source_path = request.primary_file or "main.py"
            if request.repo_url:
                fetched = await self._github.fetch(request.repo_url, source_path)
                if fetched is not None:
                    static_findings = run_static_rules(fetched.content, fetched.path)
                else:
                    static_findings = [self._repo_unreachable_finding(request.repo_url)]
            elif request.source_code and request.source_code.strip():
                static_findings = run_static_rules(
                    request.source_code, source_path
                )

            # 3. Distribute findings into sections
            all_findings = probe_findings + static_findings
            self._distribute(all_findings, report.sections)

            # 4. Compute scores
            report.overall_score = self._compute_overall(report.sections)
            report.grade = _grade(report.overall_score)
            report.passed = report.overall_score >= 70

            # 5. LLM summary + recommendations
            summary, recs = await self._llm.analyse(
                request.service_name, report.overall_score, report.sections
            )
            report.executive_summary = summary
            report.recommendations = recs

            report.completed_at = int(time.time())
            report.status = "completed"
        except Exception as exc:  # noqa: BLE001
            report.status = "failed"
            report.completed_at = int(time.time())
            report.error = f"{type(exc).__name__}: {exc}"

        return report

    # ─── Internals ──────────────────────────────────────────────────────────

    @staticmethod
    def _empty_sections() -> list[AuditSection]:
        return [
            AuditSection(
                section_id=sid, title=title, description=desc, weight=weight,
            )
            for sid, title, desc, weight in SECTION_CATALOG
        ]

    @staticmethod
    def _distribute(
        findings: list[AuditFinding], sections: list[AuditSection]
    ) -> None:
        by_id = {s.section_id: s for s in sections}
        for f in findings:
            target = by_id.get(f.section) or by_id.get("best_practices")
            if target is not None:
                target.findings.append(f)
        for s in sections:
            if not s.findings:
                s.score = 1.0  # no findings → treat as pass
                continue
            s.score = sum(_finding_score(f) for f in s.findings) / len(s.findings)

    @staticmethod
    def _compute_overall(sections: list[AuditSection]) -> float:
        total_weight = sum(s.weight for s in sections) or 1.0
        weighted = sum(s.score * s.weight for s in sections)
        return round(weighted / total_weight * 100, 1)

    @staticmethod
    def _repo_unreachable_finding(repo_url: str) -> AuditFinding:
        return AuditFinding(
            finding_id="static-repo-unreachable",
            section="architecture",
            title="Repository source is reachable via GitHub raw",
            status="warning",
            severity="low",
            detail=f"Could not fetch the primary source file from {repo_url}.",
            remediation="Ensure the repo is public and the primary file path is correct.",
        )
