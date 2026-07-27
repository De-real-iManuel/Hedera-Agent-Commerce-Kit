"""
demo/routers/agent.py
----------------------
Hedera Agent Kit demo endpoints — free natural-language Hedera queries.

GET  /api/agent/query?q=what+is+my+balance
POST /api/agent/query  { "query": "...", "thread_id": "..." }

Demonstrates Hedera Agent Kit without the x402 payment gate.
For production use, add "/api/agent/query" to the middleware's
protected_routes set.

Services are pulled from request.app.state.container.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/agent", tags=["Hedera Agent Kit"])


class AgentQueryRequest(BaseModel):
    query: str
    thread_id: str = "default"


@router.get(
    "/query",
    summary="Run a Hedera Agent Kit query (GET)",
)
async def agent_query_get(request: Request, q: str = "What is my HBAR balance?"):
    return await _run(q, "get-default", request)


@router.post(
    "/query",
    summary="Run a Hedera Agent Kit query (POST)",
)
async def agent_query_post(body: AgentQueryRequest, request: Request):
    return await _run(body.query, body.thread_id, request)


async def _run(query: str, thread_id: str, request: Request) -> dict:
    container = request.app.state.container
    s = container.settings

    try:
        from hack.agent.hedera_agent import build_hedera_agent, run_agent_query

        agent = build_hedera_agent(s)
        result = await run_agent_query(
            query=query, settings=s, thread_id=thread_id, agent=agent
        )
    except (RuntimeError, ImportError, ModuleNotFoundError) as exc:
        # hedera-agent-kit not available — fall back to a lightweight Mirror Node
        # query so the agent endpoint still returns real on-chain data.
        from hack.agent.fallback import run_fallback_query
        try:
            result = await run_fallback_query(query=query, settings=s)
        except Exception as inner:  # noqa: BLE001
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Hedera Agent Kit unavailable: {exc}. "
                    "Set an LLM API key in .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY)."
                ),
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "query": query,
        "result": result,
        "powered_by": "Hedera Agent Kit (hedera-agent-kit-py)",
    }
