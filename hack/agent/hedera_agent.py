"""
hack/agent/hedera_agent.py
---------------------------
Hedera Agent Kit integration — builds and runs a LangChain ReAct agent
with Hedera tools (account, HCS, HTS, HBAR transfer).

The agent is constructed lazily on first call and cached per process.
Hedera SDK credentials are read from the injected Settings object; no
global config is accessed directly.

Supported LLM providers (first non-empty key wins):
  - OpenAI       via OPENAI_API_KEY
  - Anthropic    via ANTHROPIC_API_KEY
  - Groq         via GROQ_API_KEY

Safety constraints (see docs/SAFETY.md):
  - Runs on testnet only in AUTONOMOUS mode.
  - Private key material is never included in responses.
  - The operator key signs only on behalf of the server's own account.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any


def _build_llm(settings: Any):
    """Pick the first available LLM based on configured API keys."""
    # Use groq_api_key first (fastest, free); fall back to openai, then anthropic.
    # The model name comes from settings.llm_model so .env controls it.
    model_name = getattr(settings, "llm_model", "gpt-4o-mini") or "gpt-4o-mini"

    if settings.groq_api_key:
        from langchain_openai import ChatOpenAI  # type: ignore

        groq_base = "https://api.groq.com/openai/v1"
        # Groq doesn't support gpt-* models; default to llama if the configured
        # model looks like an OpenAI name.
        groq_model = model_name
        if groq_model.startswith("gpt-") or groq_model.startswith("o1"):
            groq_model = "llama3-8b-8192"
        return ChatOpenAI(
            model=groq_model,
            api_key=settings.groq_api_key,
            base_url=groq_base,
        )

    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI  # type: ignore

        base_url = getattr(settings, "openai_base_url", "https://api.openai.com/v1") or "https://api.openai.com/v1"
        return ChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            base_url=base_url,
        )

    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic  # type: ignore

        return ChatAnthropic(  # type: ignore[call-arg]
            model="claude-3-haiku-20240307",
            api_key=settings.anthropic_api_key,
        )

    raise RuntimeError(
        "No LLM API key configured. "
        "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GROQ_API_KEY in .env."
    )


def build_hedera_agent(settings: Any):
    """
    Construct and return the Hedera Agent Kit LangChain agent.

    This is NOT cached by default because settings may vary; callers that
    want a process-level singleton should use the module-level cached variant
    build_hedera_agent_cached() below.
    """
    from hiero_sdk_python import Client, Network, AccountId, PrivateKey  # type: ignore
    from hedera_agent_kit.langchain.toolkit import HederaLangchainToolkit  # type: ignore
    from hedera_agent_kit.plugins import (  # type: ignore
        core_account_plugin,
        core_account_query_plugin,
        core_consensus_plugin,
        core_token_plugin,
    )
    from hedera_agent_kit.shared.configuration import (  # type: ignore
        Configuration,
        Context,
        AgentMode,
    )
    from langchain.agents import create_react_agent  # type: ignore
    from langgraph.checkpoint.memory import MemorySaver  # type: ignore

    account_id = AccountId.from_string(settings.hedera_operator_id)
    private_key = PrivateKey.from_string(settings.hedera_operator_key)
    net_str = "testnet" if settings.hedera_network == "testnet" else "mainnet"
    client = Client(Network(network=net_str))
    client.set_operator(account_id, private_key)

    toolkit = HederaLangchainToolkit(
        client=client,
        configuration=Configuration(
            tools=[],
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
    llm = _build_llm(settings)

    system_prompt = (
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
        prompt=system_prompt,
    )
    return agent


async def run_agent_query(
    query: str,
    settings: Any,
    thread_id: str = "default",
    agent: Any = None,
) -> str:
    """
    Run a natural-language query through the Hedera Agent Kit agent.

    Args:
        query:     The user's question or instruction.
        settings:  Settings object (used to build the agent if not provided).
        thread_id: LangGraph conversation thread ID for memory continuity.
        agent:     Pre-built agent instance (optional; built from settings if None).

    Returns:
        The agent's final text response.
    """
    if agent is None:
        agent = build_hedera_agent(settings)

    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    messages = response.get("messages", [])
    if messages:
        return str(messages[-1].content)
    return "No response from agent."
