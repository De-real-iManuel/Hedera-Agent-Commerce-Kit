# Hedera Agent Kit Integration

## What it is

The [Hedera Agent Kit Python SDK](https://github.com/hashgraph/hedera-agent-kit-py) is an official open-source framework for building AI agents that interact with the Hedera network. It provides a plugin architecture where each plugin bundles related Hedera tools for use by a LangChain agent.

## Plugins used in HACK

| Plugin | Tools provided |
|---|---|
| `core_account_plugin` | Transfer HBAR, create/update/delete accounts, approve allowances |
| `core_account_query_plugin` | Get account info, HBAR balances, transaction records |
| `core_consensus_plugin` | Create/update/delete HCS topics, **submit messages to topics** |
| `core_token_plugin` | Create fungible/NFT tokens, mint, associate, transfer (HTS) |

## How it connects to the x402 payment flow

```
User pays HBAR
  ↓
Mirror Node verifies
  ↓
Payment state → GRANTED
  ↓
/api/premium-query handler runs
  ↓
Hedera Agent Kit agent receives the query
  ↓
Agent uses Hedera tools (account query, HCS, HTS)
  ↓
Result returned to caller
  ↓
Usage metered + HCS receipt published via core_consensus_plugin
```

## HCS receipt publishing

The `core_consensus_plugin` includes `TopicMessageSubmitTransaction`. HACK uses this directly (via `hiero_sdk_python`) in `backend/receipts/hcs.py` to publish a JSON receipt after every verified payment.

## Agent modes

| Mode | Behavior |
|---|---|
| `AgentMode.AUTONOMOUS` | Agent executes transactions using the configured operator account |
| `ReturnBytes` (future) | Agent returns unsigned transaction bytes for user review/signing |

HACK uses `AUTONOMOUS` mode on testnet. The operator account is the server's own Hedera account — it does not act on behalf of users.

## LLM flexibility

The agent works with any of these providers (set one key in `.env`):

| Provider | Key | Notes |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` default |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-3-haiku` |
| Groq | `GROQ_API_KEY` | Free tier; `llama3-8b-8192` |
| Ollama | *(none)* | Local; no API key needed (not yet wired) |

## Installation

```bash
pip install hedera-agent-kit hiero-sdk-python langchain langchain-openai langgraph
```

## Key files

| File | Role |
|---|---|
| `backend/agent/hedera_agent.py` | Builds and caches the agent; `run_agent_query()` entry point |
| `backend/routers/agent.py` | Free `/api/agent/query` endpoint |
| `backend/routers/premium.py` | Paid `/api/premium-query` — runs agent after x402 verification |
| `backend/receipts/hcs.py` | HCS receipt publishing via `hiero_sdk_python` |

## Safety boundary

The Hedera Agent Kit agent operates the **server's own operator account** on testnet.
It does NOT:
- connect or sign for user wallets
- move user funds
- handle private keys other than the operator key in `.env`

User payments are made externally by the user's wallet. The server only observes the transfer via Mirror Node.
