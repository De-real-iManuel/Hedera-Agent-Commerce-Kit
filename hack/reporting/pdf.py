"""
hack/reporting/pdf.py
----------------------
PdfReporter — renders a ServiceAuditReport into an enterprise-styled PDF.

Sections
--------
1. Cover page (service name, score badge, grade, HashScan link)
2. Executive Summary
3. Risk Score Breakdown (per-section scores)
4. Findings — one subsection per report section
5. Recommendations
6. On-chain audit trail (NFT + HCS + Mirror Node URLs)

Uses reportlab (pure-Python, no system deps). If reportlab is missing at
runtime a minimal text-only fallback is produced so the API never breaks.
"""

from __future__ import annotations

import io
import time
from datetime import datetime, timezone

from ..models.compliance import ServiceAuditReport, SoulboundCertificate


class PdfReporter:
    """Render ServiceAuditReport → PDF bytes."""

    def render(
        self,
        report: ServiceAuditReport,
        certificate: SoulboundCertificate | None = None,
    ) -> bytes:
        try:
            return self._render_reportlab(report, certificate)
        except Exception:
            return self._render_fallback(report, certificate)

    # ─── reportlab path (rich layout) ───────────────────────────────────────

    def _render_reportlab(
        self,
        report: ServiceAuditReport,
        certificate: SoulboundCertificate | None,
    ) -> bytes:
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (  # type: ignore
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            leftMargin=0.9 * inch,
            rightMargin=0.9 * inch,
            topMargin=0.9 * inch,
            bottomMargin=0.9 * inch,
        )

        styles = getSampleStyleSheet()
        title = ParagraphStyle(
            "Title", parent=styles["Title"], fontSize=22, spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        )
        subtitle = ParagraphStyle(
            "Subtitle", parent=styles["Normal"], fontSize=11,
            textColor=colors.HexColor("#6b7280"), spaceAfter=18,
        )
        h2 = ParagraphStyle(
            "H2", parent=styles["Heading2"], fontSize=14,
            textColor=colors.HexColor("#111827"), spaceAfter=8, spaceBefore=12,
        )
        body = ParagraphStyle(
            "Body", parent=styles["BodyText"], fontSize=10, leading=14,
            alignment=TA_LEFT,
        )
        mono = ParagraphStyle(
            "Mono", parent=styles["BodyText"], fontSize=8, leading=11,
            fontName="Courier", textColor=colors.HexColor("#374151"),
        )

        story = []
        req = report.request

        # ─── Cover ─────────────────────────────────────────────────────────
        story.append(Paragraph("HACK Compliance Certification", title))
        story.append(Paragraph("Hedera Agent Commerce Kit", subtitle))

        cover_data = [
            ["Service", req.service_name],
            ["Type", req.service_type.upper()],
            ["Endpoint", req.endpoint_url],
            ["Repository", req.repo_url or "—"],
            ["Report ID", report.report_id],
            [
                "Issued",
                datetime.fromtimestamp(
                    report.completed_at or report.created_at, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M UTC"),
            ],
            ["Score", f"{report.overall_score:.1f} / 100  ({report.grade})"],
            ["Status", "PASSED" if report.passed else "NEEDS ATTENTION"],
        ]
        tbl = Table(cover_data, colWidths=[1.5 * inch, 4.4 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
                    ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#111827")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    (
                        "LINEBELOW", (0, 0), (-1, -2),
                        0.25, colors.HexColor("#e5e7eb"),
                    ),
                    (
                        "TEXTCOLOR", (1, 6), (1, 6),
                        colors.HexColor("#7c3aed"),
                    ),
                    ("FONTNAME", (1, 6), (1, 7), "Helvetica-Bold"),
                    (
                        "TEXTCOLOR", (1, 7), (1, 7),
                        colors.HexColor("#10b981")
                        if report.passed
                        else colors.HexColor("#ef4444"),
                    ),
                ]
            )
        )
        story.append(tbl)

        # ─── Executive Summary ─────────────────────────────────────────────
        story.append(Paragraph("Executive Summary", h2))
        story.append(
            Paragraph(
                report.executive_summary
                or "Automated audit completed; see per-section findings below.",
                body,
            )
        )

        # ─── Risk Score Breakdown ──────────────────────────────────────────
        story.append(Paragraph("Risk Score Breakdown", h2))
        risk_rows = [["Section", "Score", "Weight"]]
        for s in report.sections:
            risk_rows.append(
                [s.title, f"{s.score * 100:.0f} / 100", f"{s.weight:.1f}"]
            )
        risk = Table(risk_rows, colWidths=[3.2 * inch, 1.4 * inch, 1.2 * inch])
        risk.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "BACKGROUND", (0, 0), (-1, 0),
                        colors.HexColor("#f3f4f6"),
                    ),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    (
                        "LINEBELOW", (0, 0), (-1, -1),
                        0.25, colors.HexColor("#e5e7eb"),
                    ),
                ]
            )
        )
        story.append(risk)

        # ─── Findings per section ──────────────────────────────────────────
        story.append(PageBreak())
        story.append(Paragraph("Findings", h2))
        for s in report.sections:
            story.append(
                Paragraph(
                    f"<b>{s.title}</b> "
                    f"<font color='#6b7280'>({s.score * 100:.0f}/100)</font>",
                    body,
                )
            )
            if not s.findings:
                story.append(Paragraph("No findings.", body))
                story.append(Spacer(1, 8))
                continue
            for f in s.findings:
                icon = {"passed": "✓", "warning": "!", "failed": "✗"}[f.status]
                color = {
                    "passed": "#10b981",
                    "warning": "#f59e0b",
                    "failed": "#ef4444",
                }[f.status]
                story.append(
                    Paragraph(
                        f"<font color='{color}'><b>{icon}</b></font> "
                        f"<b>{f.title}</b> "
                        f"<font color='#6b7280'>[{f.severity}]</font>",
                        body,
                    )
                )
                story.append(Paragraph(f.detail, body))
                if f.remediation:
                    story.append(
                        Paragraph(
                            f"<i>Remediation:</i> {f.remediation}", body
                        )
                    )
                story.append(Spacer(1, 6))
            story.append(Spacer(1, 6))

        # ─── Recommendations ───────────────────────────────────────────────
        story.append(Paragraph("Recommendations", h2))
        if report.recommendations:
            for i, r in enumerate(report.recommendations, 1):
                story.append(Paragraph(f"{i}. {r}", body))
        else:
            story.append(Paragraph("No recommendations at this time.", body))

        # ─── On-chain audit trail ──────────────────────────────────────────
        story.append(Paragraph("On-chain Audit Trail", h2))
        trail = []
        if certificate:
            trail.extend(
                [
                    ("NFT Token", certificate.token_id),
                    ("Serial", str(certificate.serial_number)),
                    ("Mint Tx", certificate.hashscan_tx_url),
                    ("Metadata SHA-256", certificate.metadata_hash),
                    ("Recipient", certificate.recipient_account_id),
                ]
            )
        if report.hcs_receipt_id:
            trail.append(("HCS Receipt", report.hcs_receipt_id))
        if not trail:
            story.append(
                Paragraph(
                    "No on-chain artefacts issued (audit did not pass, or minting disabled).",
                    body,
                )
            )
        else:
            for label, value in trail:
                story.append(
                    Paragraph(f"<b>{label}:</b> <font face='Courier'>{value}</font>", mono)
                )

        doc.build(story)
        return buffer.getvalue()

    # ─── Fallback path (plain text wrapped as PDF-shaped bytes) ────────────

    def _render_fallback(
        self,
        report: ServiceAuditReport,
        certificate: SoulboundCertificate | None,
    ) -> bytes:
        lines = [
            "HACK Compliance Certification",
            "=" * 60,
            f"Service:  {report.request.service_name}",
            f"Type:     {report.request.service_type}",
            f"Endpoint: {report.request.endpoint_url}",
            f"Score:    {report.overall_score:.1f} / 100  ({report.grade})",
            f"Status:   {'PASSED' if report.passed else 'NEEDS ATTENTION'}",
            f"Issued:   {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(report.completed_at or report.created_at))}",
            "",
            "Executive Summary",
            "-" * 60,
            report.executive_summary or "(no summary)",
            "",
        ]
        for s in report.sections:
            lines.append(f"{s.title} — {s.score * 100:.0f}/100")
            for f in s.findings:
                lines.append(f"  [{f.status.upper():7}] {f.title} — {f.detail}")
            lines.append("")
        lines.append("Recommendations")
        lines.append("-" * 60)
        for i, r in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {r}")
        if certificate:
            lines.extend(
                [
                    "",
                    "On-chain Audit Trail",
                    "-" * 60,
                    f"NFT Token: {certificate.token_id}",
                    f"Serial:    {certificate.serial_number}",
                    f"Tx:        {certificate.hashscan_tx_url}",
                ]
            )
        return "\n".join(lines).encode("utf-8")
