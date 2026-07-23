"""
demo/routers/premium.py
------------------------
Premium paid endpoint — powered by the Hedera Agent Kit.

GET /api/premium-query?q=your+question

By the time this handler executes, the X402Middleware has already validated
the quote (GRANTED) and advanced it to CONSUMED (exactly once).

The handler runs the user's query through the Hedera Agent Kit agent and
returns the result along with receipt and HashScan links.

Services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["Premium (Paid)"])


@router.get(
    "/premium-query",
    summary="Paid AI query via Hedera Agent Kit",
    description=(
        "Requires a valid x402 payment.  "
        "The X402Middleware validates the payment and consumes the quote before "
        "this handler runs.  The result is delivered exactly once per payment."
    ),
)
async def premium_query(request: Request, q: str = "What is my HBAR balance?"):
    container = request.app.state.container
    s = container.settings

    tx_id = request.headers.get("X-Payment-Token", "unknown")
    quote_id = request.headers.get("X-Quote-Id", "unknown")
    caller = request.client.host if request.client else "unknown"

    # Run the Hedera Agent Kit agent
    agent_result: str
    agent_error: str | None = None
    try:
        from hack.agent.hedera_agent import build_hedera_agent, run_agent_query

        agent = build_hedera_agent(s)
        agent_result = await run_agent_query(
            query=q, settings=s, thread_id=tx_id, agent=agent
        )
    except Exception as exc:  # noqa: BLE001
        agent_result = (
            "Hedera Agent Kit is not configured. "
            "Set an LLM API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY) in .env."
        )
        agent_error = str(exc)

    # Record usage metering for this consumed request
    from hack.models.quote import UsageRecord
    import time

    container.metering.record(
        UsageRecord(
            transaction_id=tx_id,
            caller=caller,
            endpoint="/api/premium-query",
            amount_hbar=s.x402_payment_amount_hbar,
            timestamp=int(time.time()),
        )
    )

    quote = container.lifecycle.get_quote(quote_id)

    response: dict = {
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
