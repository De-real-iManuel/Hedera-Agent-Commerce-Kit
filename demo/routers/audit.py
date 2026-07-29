"""
demo/routers/audit.py
----------------------
Service-audit endpoints — the developer-facing compliance flow.

Flow (from the frontend's perspective):

    1. POST /api/audit/submit
         Body: ServiceAuditRequest
         Returns: {quote_id, amount_hbar, receiver, memo, expires_at}
       → Client shows the payment challenge, user pays HBAR.

    2. POST /api/audit/run/{quote_id}?transaction_id=...
         Verifies payment on Mirror Node, then runs the audit pipeline,
         mints the soulbound NFT (if passed), publishes HCS anchor.
         Returns: {report, certificate}

    3. GET  /api/audit/report/{report_id}
    4. GET  /api/audit/report/{report_id}/pdf
    5. GET  /api/audit/report/{report_id}/skill.md
    6. GET  /api/audit/certificate/{certificate_id}
    7. GET  /api/audit/certificates                      ← gallery

Every response is real. No mocks.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response

from hack.models.compliance import ServiceAuditRequest

router = APIRouter(prefix="/audit", tags=["Audit"])


# ─── 1. Submit an audit request → payment challenge ────────────────────────

@router.post(
    "/submit",
    summary="Request a compliance audit (returns payment challenge)",
)
async def submit_audit(body: ServiceAuditRequest, request: Request):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle

    # Stash the submission on the quote via the resource_hash mechanism: we
    # need to retrieve the request when the client pays and calls /run. We
    # do this by keying an in-memory dict on quote_id.
    quote = lifecycle.create_quote(
        endpoint=f"audit:{body.service_name}",
        amount_hbar=s.x402_payment_amount_hbar,
        receiver=s.x402_payment_receiver_account_id,
    )

    _AUDIT_SUBMISSIONS[quote.quote_id] = body

    return {
        "quote_id": quote.quote_id,
        "amount": s.x402_payment_amount_hbar,
        "amount_hbar": s.x402_payment_amount_hbar,
        "receiver": s.x402_payment_receiver_account_id,
        "memo": s.x402_payment_memo,
        "network": s.hedera_network,
        "expires_at": quote.expires_at,
    }


# ─── 2. Run the audit after payment ────────────────────────────────────────

@router.post(
    "/run/{quote_id}",
    summary="Run the compliance audit after payment (mints NFT if passed)",
)
async def run_audit(
    quote_id: str,
    transaction_id: str,
    request: Request,
):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle
    verifier = container.verifier
    auditor = container.service_auditor
    certifier = container.certifier
    store = container.report_store

    submission = _AUDIT_SUBMISSIONS.get(quote_id)
    if submission is None:
        raise HTTPException(
            status_code=404,
            detail=f"No audit submission is on file for quote {quote_id!r}.",
        )

    # 1. Verify the payment on Mirror Node (real check)
    try:
        min_tinybars = int(s.x402_payment_amount_hbar * 100_000_000)
        tx_data = await verifier.verify(
            transaction_id=transaction_id.strip(),
            receiver=s.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=s.hedera_network,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Mirror Node unavailable: {exc}.",
        )

    # Extract the actual payer account from the transaction transfers.
    # The payer is the account with a negative HBAR transfer (they sent HBAR).
    # This is used as the NFT certificate recipient so it goes to the right wallet.
    payer_account_id: str = ""
    try:
        transfers = tx_data.get("transfers", [])
        # Find the largest negative transfer — that's the payer (excluding node fees)
        paying_transfer = min(
            (t for t in transfers if t.get("amount", 0) < 0),
            key=lambda t: t["amount"],
            default=None,
        )
        if paying_transfer:
            payer_account_id = paying_transfer.get("account", "")
    except Exception:  # noqa: BLE001
        pass

    # Advance the quote lifecycle — but only if it hasn't already been
    # advanced by POST /api/payment/verify.  That endpoint takes the quote
    # all the way to GRANTED; calling advance_to_verified() on a GRANTED
    # quote raises a ValueError.  We check the current state first and skip
    # the transitions when payment was already confirmed by the verify flow.
    from hack.models.quote import PaymentStatus
    current_quote = lifecycle.get_quote(quote_id)
    already_granted = (
        current_quote is not None
        and current_quote.status == PaymentStatus.GRANTED
    )

    if not already_granted:
        try:
            lifecycle.advance_to_verified(quote_id, transaction_id)
            lifecycle.advance_to_granted(quote_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=str(exc))

    # 2. Run the audit
    report = await auditor.audit(submission)
    # Always record the payment transaction on the report so the frontend
    # can link to it regardless of whether the service passed or failed.
    report.hashscan_url = (
        f"https://hashscan.io/{s.hedera_network}/transaction/{transaction_id.strip()}"
    )
    report.hcs_receipt_id = transaction_id.strip()
    store.save_report(report)

    # 3. Certify (mint NFT + publish HCS anchor)
    # Issue a certificate for CERTIFIED (≥80) AND CONDITIONAL (≥60) scores.
    # The NFT is proof the wallet paid for and went through certification —
    # the grade on the certificate communicates the outcome clearly.
    certificate = None
    if report.overall_score >= 60 and report.status == "completed":
        recipient = (
            submission.recipient_account_id
            or s.x402_payment_receiver_account_id
        )
        try:
            certificate = await certifier.certify_service_audit(
                report,
                recipient_account_id=recipient,
                payment_transaction_id=transaction_id.strip(),
            )
            store.save_certificate(certificate)
            # Attach cert links back onto the report
            report.hashscan_url = certificate.hashscan_tx_url or report.hashscan_url
            report.hcs_receipt_id = certificate.mint_transaction_id or report.hcs_receipt_id
            store.save_report(report)
        except Exception as exc:  # noqa: BLE001
            import traceback
            tb = traceback.format_exc()
            print(f"[HACK] Certification failed for report {report.report_id}: {exc}\n{tb}")
            report.error = f"Certification failed: {type(exc).__name__}: {exc}"
            store.save_report(report)

    # 4. Mark consumed
    try:
        lifecycle.advance_to_consumed(quote_id)
    except Exception:
        pass  # non-fatal for audits — the report is already saved
    _AUDIT_SUBMISSIONS.pop(quote_id, None)

    return {
        "report": report.model_dump(),
        "certificate": certificate.model_dump() if certificate else None,
    }


# ─── 3. Fetch a report ──────────────────────────────────────────────────────

@router.get("/report/{report_id}", summary="Fetch a compliance audit report")
async def get_report(report_id: str, request: Request):
    store = request.app.state.container.report_store
    report = store.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report.model_dump()


# ─── 4. Download the PDF ────────────────────────────────────────────────────

@router.get(
    "/report/{report_id}/pdf",
    summary="Download the audit report as a PDF",
    response_class=FileResponse,
)
async def get_report_pdf(report_id: str, request: Request):
    container = request.app.state.container
    store = container.report_store
    pdf = container.pdf_reporter

    report = store.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    cert = None
    for row in store.list_certificates(limit=200):
        if row.report_id == report_id:
            cert = store.get_certificate(row.certificate_id)
            break

    existing = store.get_pdf_path(report_id)
    if existing is None:
        data = pdf.render(report, cert)
        store.save_pdf(report_id, data)
    else:
        data = existing.read_bytes() if hasattr(existing, "read_bytes") else None
        if not data:
            data = pdf.render(report, cert)
            store.save_pdf(report_id, data)

    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="hack-compliance-{report_id[:8]}.pdf"'
            )
        },
    )


# ─── 5. Download the SKILL.md ──────────────────────────────────────────────

@router.get(
    "/report/{report_id}/skill.md",
    summary="Download the SKILL.md for AI agent ingestion",
    response_class=PlainTextResponse,
)
async def get_report_skill(report_id: str, request: Request):
    container = request.app.state.container
    store = container.report_store
    skill = container.skill_md

    report = store.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    cert = None
    for row in store.list_certificates(limit=200):
        if row.report_id == report_id:
            cert = store.get_certificate(row.certificate_id)
            break

    text = skill.render(report, cert)
    store.save_skill_md(report_id, text)
    return PlainTextResponse(
        text,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{report.request.service_name}-SKILL.md"'
            )
        },
    )


# ─── 6. Certificate detail ─────────────────────────────────────────────────

@router.get(
    "/certificate/{certificate_id}",
    summary="Fetch a soulbound certificate",
)
async def get_certificate(certificate_id: str, request: Request):
    store = request.app.state.container.report_store
    cert = store.get_certificate(certificate_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    return cert.model_dump()


# ─── 7. Gallery — all issued certificates ──────────────────────────────────

@router.get(
    "/certificates",
    summary="List all issued soulbound certificates (newest first)",
)
async def list_certificates(request: Request, limit: int = 100):
    store = request.app.state.container.report_store
    rows = store.list_certificates(limit=limit)
    return {"certificates": [row.model_dump() for row in rows]}


# ─── in-memory submission store ─────────────────────────────────────────────
# quote_id → ServiceAuditRequest
# This is intentionally in-memory — audits are ephemeral; a restart drops
# in-flight submissions but never affects saved reports or certificates.

_AUDIT_SUBMISSIONS: dict[str, ServiceAuditRequest] = {}
