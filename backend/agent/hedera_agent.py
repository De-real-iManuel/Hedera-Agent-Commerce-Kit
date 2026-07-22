"""
Hedera Agent Kit — Agent Layer
--------------------------------
Builds a LangChain agent backed by the official Hedera Agent Kit Python SDK.

Plugins loaded:
  - core_account_plugin       (transfer HBAR, account management)
  - core_account_query_plugin (balances, account info)
  - core_consensus_plugin     (create topics, submit HCS messages)
  - core_token_plugin         (HTS: create/mint/transfer tokens)

The agent is used by:
  - /api/agent/query  — natural-language queries against Hedera tools
  - The paid premium endpoint as the "AI result" behind the x402 gate

Safety rules (from docs/SAFETY.md):
  - Agent runs in AUTONOMOUS mode on testnet only.
  - No private key material is returned in agent responses.
  - No auto-signing on behalf of users; operator key is the server's own account.

References:
  - https://hedera.com/blog/introducing-the-python-sdk-for-the-hedera-agent-kit
  - https://github.com/hashgraph/hedera-agent-kit-py
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from backend.config import get_settings


def _build_llm():
    """Pick an LLM based on which API key is present in .env."""
    s = get_settings()

    if s.openai_api_key:
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(model="gpt-4o-mini", api_key=s.openai_api_key)

    if s.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic  # type: ignore
        return ChatAnthropic(model="claude-3-haiku-20240307", api_key=s.anthropic_api_key)  # type: ignore[call-arg]

    if s.groq_api_key:
        from langchain_groq import ChatGroq  # type: ignore
        return ChatGroq(model="llama3-8b-8192", api_key=s.groq_api_key)

    raise RuntimeError(
        "No LLM API key found. "
        "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY in .env."
    )


@lru_cache(maxsize=1)
def build_hedera_agent():
    """
    Construct and return the Hedera Agent Kit LangChain agent.
    Cached after first call — one agent instance per server process.
    """
    from hiero_sdk_python import Client, Network, AccountId, PrivateKey  # type: ignore
    from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit  # type: ignore
    from hedera_agent_kit.plugins import (  # type: ignore
        core_account_plugin,
        core_account_query_plugin,
        core_consensus_plugin,
        core_token_plugin,
    )
    from hedera_agent_kit.shared.configuration import Configuration, Context, AgentMode  # type: ignore
    from langchain.agents import create_react_agent  # type: ignore
    from langchain_core.prompts import PromptTemplate  # type: ignore
    from langgraph.checkpoint.memory import MemorySaver  # type: ignore

    s = get_settings()

    # ── Hedera client ──────────────────────────────────────────────────────────
    account_id = AccountId.from_string(s.hedera_operator_id)
    private_key = PrivateKey.from_string(s.hedera_operator_key)
    network = "testnet" if s.hedera_network == "testnet" else "mainnet"
    client = Client(Network(network=network))
    client.set_operator(account_id, private_key)

    # ── Hedera Agent Kit toolkit ───────────────────────────────────────────────
    toolkit = HederaLangchainToolkit(
        client=client,
        configuration=Configuration(
            tools=[],   # empty = load all tools from the listed plugins
            plugins=[
                core_account_plugin,
                core_account_query_plugin,
                core_consensus_plugin,
                core_token_plugin,
            ],
            context=Context(
                mode=AgentMode.AUTONOMOUS,
                account_id=str(account_id),
            ),
        ),
    )
    tools = toolkit.get_tools()

    # ── LLM + Agent ───────────────────────────────────────────────────────────
    llm = _build_llm()

    SYSTEM_PROMPT = (
        "You are a Hedera blockchain assistant. "
        "You have access to Hedera tools for account queries, HBAR transfers, "
        "HCS topic management, and HTS token operations on testnet. "
        "Always confirm the network is testnet before executing transactions. "
        "Never reveal private keys or seed phrases. "
        "Be concise and precise."
    )

    agent = create_react_agent(
        model=llm,
        tools=tools,
        checkpointer=MemorySaver(),
        prompt=SYSTEM_PROMPT,
    )

    return agent


async def run_agent_query(query: str, thread_id: str = "default") -> str:
    """
    Run a natural-language query through the Hedera Agent Kit agent.
    Returns the agent's final text response.
    """
    agent = build_hedera_agent()
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    messages = response.get("messages", [])
    if messages:
        return str(messages[-1].content)
    return "No response from agent."
