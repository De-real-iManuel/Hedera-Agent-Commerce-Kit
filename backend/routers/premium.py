"""
Premium endpoint — Hedera Agent Kit powered
--------------------------------------------
This is the paid AI endpoint. By the time this handler runs, the x402
middleware has already validated the quote is GRANTED and advanced it to
CONSUMED (exactly once).

The "AI result" is a real response from the Hedera Agent Kit agent, which
has live access to Hedera tools (account query, HCS, HTS, HBAR transfer).

Query defaults to a Hedera-relevant prompt if none is provided via
query param: GET /api/premium-query?q=your+question
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.metering.usage import record
from backend.verification.payment_state import get_quote

router = APIRouter(tags=["premium"])


@router.get("/premium-query")
async def premium_query(request: Request, q: str = "What is my HBAR balance?"):
    s = get_settings()
    tx_id = request.headers.get("X-Payment-Token", "unknown")
    quote_id = request.headers.get("X-Quote-Id", "unknown")
    caller = request.client.host if request.client else "unknown"

    # ── Run the Hedera Agent Kit agent ────────────────────────────────────────
    agent_result: str
    agent_error: str | None = None
    try:
        from backend.agent.hedera_agent import run_agent_query
        agent_result = await run_agent_query(query=q, thread_id=tx_id)
    except Exception as exc:  # noqa: BLE001
        # Agent failure is surfaced but does not invalidate the payment —
        # the payment was already consumed and metered.
        agent_result = (
            "Hedera Agent Kit agent is not configured. "
            "Set an LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY) in .env."
        )
        agent_error = str(exc)

    # ── Meter the consumed request ────────────────────────────────────────────
    record(
        transaction_id=tx_id,
        caller=caller,
        endpoint="/api/premium-query",
        amount_hbar=s.x402_payment_amount_hbar,
    )

    quote = get_quote(quote_id)

    response = {
        "result": agent_result,
        "query": q,
        "transaction_id": tx_id,
        "quote_id": quote_id,
        "quote_status": quote.status if quote else "unknown",
        "payment_note": (
            "Response gated by Hedera x402. "
            "Payment verified on Mirror Node. "
            "Receipt published to HCS. "
            "Delivered exactly once."
        ),
        "receipt_url": f"/api/receipt/{tx_id}",
        "hashscan_url": f"https://hashscan.io/{s.hedera_network}/transaction/{tx_id}",
    }
    if agent_error:
        response["agent_error"] = agent_error

    return response
