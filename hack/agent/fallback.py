"""
hack/agent/fallback.py
-----------------------
Lightweight Hedera agent fallback when hedera-agent-kit is not installed.

Uses:
  1. Hedera Mirror Node REST API for real on-chain data (account info,
     transactions, HCS topics, token info).
  2. An OpenAI-compatible LLM (Groq / OpenAI) to reason over the results
     and produce a natural-language answer.

Supports common query patterns without requiring any Hedera SDK:
  - "What is my HBAR balance?"
  - "Show recent transactions for 0.0.XXXX"
  - "What is the HCS topic 0.0.XXXX?"
  - "What tokens are associated with 0.0.XXXX?"
  - General blockchain questions answered from LLM knowledge

Falls back to a pure LLM answer if Mirror Node is unavailable or the
query doesn't match a recognisable pattern.
"""

from __future__ import annotations

import re
from typing import Any

import httpx


_MIRROR_BASE = {
    "testnet": "https://testnet.mirrornode.hedera.com/api/v1",
    "mainnet": "https://mainnet-public.mirrornode.hedera.com/api/v1",
}


async def _mirror_get(url: str, timeout: float = 10.0) -> dict | None:
    """Return JSON from a Mirror Node URL, or None on failure."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def _extract_account_id(text: str) -> str | None:
    """Extract the first 0.0.XXXXX pattern from text."""
    m = re.search(r"\b(0\.\d+\.\d+)\b", text)
    return m.group(1) if m else None


async def _gather_context(query: str, settings: Any) -> str:
    """Fetch relevant Mirror Node data and return it as a string."""
    network = getattr(settings, "hedera_network", "testnet")
    base = _MIRROR_BASE.get(network, _MIRROR_BASE["testnet"])
    operator_id = getattr(settings, "hedera_operator_id", "")

    q = query.lower()
    account_id = _extract_account_id(query) or operator_id

    chunks: list[str] = []

    # --- Account balance / info ---
    if account_id and any(
        kw in q for kw in ("balance", "hbar", "account", "info", "my account")
    ):
        data = await _mirror_get(f"{base}/accounts/{account_id}")
        if data:
            balance_hbar = data.get("balance", {}).get("balance", 0) / 1e8
            alias = data.get("alias") or "none"
            evm = data.get("evm_address") or "none"
            memo = data.get("memo") or ""
            created = data.get("created_timestamp") or "unknown"
            chunks.append(
                f"Account {account_id}:\n"
                f"  HBAR balance: {balance_hbar:.8f} HBAR\n"
                f"  EVM address:  {evm}\n"
                f"  Alias:        {alias}\n"
                f"  Memo:         {memo}\n"
                f"  Created at:   {created}"
            )

    # --- Recent transactions ---
    if account_id and any(kw in q for kw in ("transaction", "transfer", "recent", "history")):
        data = await _mirror_get(
            f"{base}/transactions?account.id={account_id}&limit=5&order=desc"
        )
        if data:
            txs = data.get("transactions", [])
            if txs:
                lines = [f"Recent transactions for {account_id}:"]
                for tx in txs[:5]:
                    tid = tx.get("transaction_id", "?")
                    ts = tx.get("consensus_timestamp", "?")
                    ttype = tx.get("name", "?")
                    result = tx.get("result", "?")
                    lines.append(f"  [{ts}] {tid} | {ttype} | {result}")
                chunks.append("\n".join(lines))

    # --- HCS topic ---
    if any(kw in q for kw in ("hcs", "topic", "consensus", "receipt")):
        hcs_topic = _extract_account_id(query)
        if not hcs_topic:
            hcs_topic = getattr(settings, "hcs_receipt_topic_id", "")
        if hcs_topic:
            data = await _mirror_get(f"{base}/topics/{hcs_topic}")
            if data:
                memo = data.get("memo") or "none"
                chunks.append(
                    f"HCS Topic {hcs_topic}:\n"
                    f"  Memo:            {memo}\n"
                    f"  Admin key:       {data.get('admin_key', 'none')}\n"
                    f"  Submit key:      {data.get('submit_key', 'none')}"
                )
            msgs = await _mirror_get(f"{base}/topics/{hcs_topic}/messages?limit=3&order=desc")
            if msgs:
                messages = msgs.get("messages", [])
                if messages:
                    lines = [f"Last {len(messages)} HCS messages:"]
                    for m in messages:
                        seq = m.get("sequence_number", "?")
                        ts = m.get("consensus_timestamp", "?")
                        lines.append(f"  [#{seq} at {ts}]")
                    chunks.append("\n".join(lines))

    # --- Token info ---
    if account_id and any(kw in q for kw in ("token", "nft", "associate", "soulbound")):
        data = await _mirror_get(f"{base}/accounts/{account_id}/tokens?limit=10")
        if data:
            tokens = data.get("tokens", [])
            if tokens:
                lines = [f"Tokens associated with {account_id}:"]
                for t in tokens[:10]:
                    lines.append(
                        f"  {t.get('token_id', '?')} — "
                        f"balance: {t.get('balance', 0)}, "
                        f"freeze: {t.get('freeze_status', 'NOT_APPLICABLE')}"
                    )
                chunks.append("\n".join(lines))

    return "\n\n".join(chunks) if chunks else ""


async def _ask_llm(query: str, context: str, settings: Any) -> str:
    """Send the query + Mirror Node context to the LLM and return the answer."""
    api_key = (
        getattr(settings, "groq_api_key", "")
        or getattr(settings, "openai_api_key", "")
    ).strip()
    if not api_key:
        return (
            "No LLM API key configured. "
            "Set GROQ_API_KEY or OPENAI_API_KEY in .env for AI-powered responses.\n\n"
            + (f"Raw Hedera data:\n{context}" if context else "No on-chain data retrieved.")
        )

    base_url = getattr(settings, "resolved_llm_base_url", lambda: "https://api.openai.com/v1")()
    model = getattr(settings, "llm_model", "llama3-8b-8192") or "llama3-8b-8192"

    system = (
        "You are a Hedera blockchain assistant. "
        "Answer the user's question based on the provided real-time Hedera Mirror Node data. "
        "Be concise, precise, and never invent data."
    )
    messages = [{"role": "system", "content": system}]
    if context:
        messages.append(
            {"role": "user", "content": f"Hedera Mirror Node data:\n{context}\n\nQuestion: {query}"}
        )
    else:
        messages.append({"role": "user", "content": query})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.1},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        if context:
            return f"LLM unavailable ({exc}).\n\nRaw Hedera data:\n{context}"
        return f"LLM unavailable: {exc}"


async def run_fallback_query(query: str, settings: Any) -> str:
    """
    Run a Hedera query using Mirror Node + LLM, without hedera-agent-kit.
    Returns a natural-language answer.
    """
    context = await _gather_context(query, settings)
    return await _ask_llm(query, context, settings)
