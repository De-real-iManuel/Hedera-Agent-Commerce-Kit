"""
Agent endpoint — free natural-language Hedera queries
------------------------------------------------------
GET  /api/agent/query?q=what+is+my+balance
POST /api/agent/query  { "query": "...", "thread_id": "..." }

Demonstrates the Hedera Agent Kit integration without the x402 payment gate.
For production use, protect this endpoint with the x402 middleware by adding
"/api/agent/query" to PROTECTED_ROUTES in middleware/x402.py.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agent.hedera_agent import run_agent_query

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentQueryRequest(BaseModel):
    query: str
    thread_id: str = "default"


@router.get("/query")
async def agent_query_get(q: str = "What is my HBAR balance?"):
    return await _run(q, "get-default")


@router.post("/query")
async def agent_query_post(body: AgentQueryRequest):
    return await _run(body.query, body.thread_id)


async def _run(query: str, thread_id: str) -> dict:
    try:
        result = await run_agent_query(query=query, thread_id=thread_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Hedera Agent Kit agent unavailable: {exc}. "
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
