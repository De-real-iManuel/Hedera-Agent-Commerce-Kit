"""
hack/audit/store.py
--------------------
ReportStore — a tiny JSON-file-backed store for ServiceAuditReports and
SoulboundCertificates. Enough for a hackathon demo; swap for Postgres in
production.

Directory layout:

    {base_dir}/
        reports/{report_id}.json
        certificates/{certificate_id}.json
        certificates/_index.json     (ordered list for the gallery)
        pdfs/{report_id}.pdf         (generated on demand)
        skills/{report_id}.md        (generated on demand)
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from ..models.compliance import (
    CertificateSummary,
    ServiceAuditReport,
    SoulboundCertificate,
)


class ReportStore:
    """File-backed persistence for reports and certificates."""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)
        self._reports = self._base / "reports"
        self._certs = self._base / "certificates"
        self._pdfs = self._base / "pdfs"
        self._skills = self._base / "skills"
        for p in (self._reports, self._certs, self._pdfs, self._skills):
            p.mkdir(parents=True, exist_ok=True)
        self._index_path = self._certs / "_index.json"
        self._lock = threading.Lock()

    # ─── Reports ────────────────────────────────────────────────────────────

    def save_report(self, report: ServiceAuditReport) -> None:
        path = self._reports / f"{report.report_id}.json"
        with self._lock:
            path.write_text(report.model_dump_json(indent=2), "utf-8")

    def get_report(self, report_id: str) -> Optional[ServiceAuditReport]:
        path = self._reports / f"{report_id}.json"
        if not path.exists():
            return None
        try:
            return ServiceAuditReport.model_validate_json(path.read_text("utf-8"))
        except Exception:
            return None

    # ─── Certificates ───────────────────────────────────────────────────────

    def save_certificate(self, cert: SoulboundCertificate) -> None:
        path = self._certs / f"{cert.certificate_id}.json"
        with self._lock:
            path.write_text(cert.model_dump_json(indent=2), "utf-8")
            self._append_index(cert)

    def get_certificate(self, cert_id: str) -> Optional[SoulboundCertificate]:
        path = self._certs / f"{cert_id}.json"
        if not path.exists():
            return None
        try:
            return SoulboundCertificate.model_validate_json(path.read_text("utf-8"))
        except Exception:
            return None

    def list_certificates(self, limit: int = 100) -> list[CertificateSummary]:
        index = self._read_index()
        rows = [CertificateSummary(**row) for row in index[:limit]]
        return rows

    # ─── PDF / SKILL.md artefacts ──────────────────────────────────────────

    def save_pdf(self, report_id: str, data: bytes) -> Path:
        path = self._pdfs / f"{report_id}.pdf"
        with self._lock:
            path.write_bytes(data)
        return path

    def get_pdf_path(self, report_id: str) -> Optional[Path]:
        path = self._pdfs / f"{report_id}.pdf"
        return path if path.exists() else None

    def save_skill_md(self, report_id: str, text: str) -> Path:
        path = self._skills / f"{report_id}.md"
        with self._lock:
            path.write_text(text, "utf-8")
        return path

    def get_skill_path(self, report_id: str) -> Optional[Path]:
        path = self._skills / f"{report_id}.md"
        return path if path.exists() else None

    # ─── Index helpers ──────────────────────────────────────────────────────

    def _read_index(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        try:
            return json.loads(self._index_path.read_text("utf-8"))
        except Exception:
            return []

    def _append_index(self, cert: SoulboundCertificate) -> None:
        row = {
            "certificate_id": cert.certificate_id,
            "report_id": cert.report_id,
            "agent_name": cert.agent_name,
            "score": cert.score,
            "grade": cert.grade,
            "minted_at": cert.minted_at,
            "token_id": cert.token_id,
            "serial_number": cert.serial_number,
            "hashscan_tx_url": cert.hashscan_tx_url,
            "recipient_account_id": cert.recipient_account_id,
            "service_endpoint": cert.service_endpoint,
        }
        index = self._read_index()
        # Newest first, deduplicate by certificate_id
        index = [r for r in index if r.get("certificate_id") != cert.certificate_id]
        index.insert(0, row)
        self._index_path.write_text(json.dumps(index, indent=2), "utf-8")
