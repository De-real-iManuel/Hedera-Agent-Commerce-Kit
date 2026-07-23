"""
demo/routers/compliance.py
---------------------------
Compliance and certification endpoints.

POST /api/compliance/check
    Body: {transaction_id: str, quote_id: str}
    Verifies the transaction on Mirror Node, runs the compliance engine
    against the quote, and returns a ComplianceCheckResult.

GET /api/compliance/certify/{quote_id}?transaction_id=...
    Fetches the quote, re-verifies on Mirror Node, runs the compliance
    engine via the certifier, and returns a CertificationReport.

All services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/compliance", tags=["Compliance"])


class ComplianceCheckRequest(BaseModel):
    transaction_id: str
    quote_id: str


# ─── POST /api/compliance/check ──────────────────────────────────────────────

@router.post(
    "/check",
    summary="Run compliance rules on a verified payment",
    description=(
        "Fetches the on-chain transaction from the Mirror Node, retrieves "
        "the corresponding quote, and evaluates all compliance rules. "
        "Returns a ComplianceCheckResult with per-rule pass/fail detail."
    ),
)
async def compliance_check(body: ComplianceCheckRequest, request: Request):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle
    verifier = container.verifier
    engine = container.compliance_engine

    quote_id = body.quote_id.strip()
    tx_id = body.transaction_id.strip()

    # Resolve the quote
    quote = lifecycle.get_quote(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"Quote {quote_id!r} not found.")

    # Fetch transaction data from Mirror Node for rule evaluation
    try:
        min_tinybars = int(s.x402_payment_amount_hbar * 100_000_000)
        tx_data = await verifier.verify(
            transaction_id=tx_id,
            receiver=s.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=s.hedera_network,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Mirror Node unavailable: {exc}.",
        )

    result = await engine.check(quote, tx_id, tx_data)
    return result.model_dump()


# ─── GET /api/compliance/certify/{quote_id} ──────────────────────────────────

@router.get(
    "/certify/{quote_id}",
    summary="Issue a certification report for a payment",
    description=(
        "Runs the full compliance suite and issues a CertificationReport. "
        "If the check passes, the report is optionally anchored to HCS."
    ),
)
async def compliance_certify(
    quote_id: str,
    transaction_id: str,
    request: Request,
):
    container = request.app.state.container
    s = container.settings
    lifecycle = container.lifecycle
    verifier = container.verifier
    certifier = container.certifier

    tx_id = transaction_id.strip()
    quote_id = quote_id.strip()

    # Resolve the quote
    quote = lifecycle.get_quote(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"Quote {quote_id!r} not found.")

    # Fetch transaction data
    try:
        min_tinybars = int(s.x402_payment_amount_hbar * 100_000_000)
        tx_data = await verifier.verify(
            transaction_id=tx_id,
            receiver=s.x402_payment_receiver_account_id,
            min_tinybars=min_tinybars,
            network=s.hedera_network,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Mirror Node unavailable: {exc}.",
        )

    report = await certifier.certify(quote, tx_id, tx_data)
    return report.model_dump()
