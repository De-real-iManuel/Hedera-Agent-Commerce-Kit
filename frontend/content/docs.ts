export interface DocPage {
  slug: string;
  title: string;
  section: string;
  status?: "coming-soon";
  content: string; // simple markdown-ish (rendered with basic parser)
}

export const DOCS_NAV: Array<{ section: string; pages: Array<{ slug: string; title: string; status?: "coming-soon" }> }> = [
  {
    section: "Getting Started",
    pages: [
      { slug: "installation", title: "Installation" },
      { slug: "quick-start", title: "Quick Start" },
      { slug: "configuration", title: "Configuration" },
    ],
  },
  {
    section: "Toolkit Reference",
    pages: [
      { slug: "paid-endpoint", title: "@PaidEndpoint Decorator" },
      { slug: "middleware", title: "Middleware" },
      { slug: "state-machine", title: "State Machine" },
    ],
  },
  {
    section: "Compliance Engine",
    pages: [
      { slug: "certification-service", title: "Certification Service" },
      { slug: "service-audit", title: "Service Audit Pipeline" },
      { slug: "soulbound-nft", title: "Soulbound NFT Minting" },
    ],
  },
  {
    section: "Integrations",
    pages: [
      { slug: "fastapi", title: "FastAPI" },
      { slug: "agent-kit", title: "Hedera Agent Kit" },
      { slug: "mcp-integration", title: "MCP Tools" },
    ],
  },
  {
    section: "Reference",
    pages: [
      { slug: "api-reference", title: "API Reference" },
    ],
  },
];

export const DOC_PAGES: Record<string, DocPage> = {
  installation: {
    slug: "installation", section: "Getting Started", title: "Installation",
    content: `# Installation

HACK is distributed as a source repository. A published \`pip\` package is planned after the hackathon.

## Requirements

- Python **3.11+**
- A Hedera testnet account (get one at [portal.hedera.com](https://portal.hedera.com))
- \`git\` and \`curl\`
- Groq API key (for LLM-powered audit recommendations)

## From source

\`\`\`bash
git clone https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit
cd Hedera-Agent-Commerce-Kit
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
\`\`\`

The install creates a virtualenv, installs dependencies, and copies \`.env.example\` to \`.env\`. Fill in your Hedera credentials before running the server.

## Verify

\`\`\`bash
python -m demo.main
# or: uvicorn demo.main:app --host 0.0.0.0 --port 8000

# In another terminal:
curl http://localhost:8000/api/health
# { "status": "ok", "version": "0.1.0" }
\`\`\`
`,
  },
  "quick-start": {
    slug: "quick-start", section: "Getting Started", title: "Quick Start",
    content: `# Quick Start

Wrap any FastAPI route with \`@PaidEndpoint\` and it will require x402 payment.

\`\`\`python
from fastapi import FastAPI, Request
from hack.toolkit import PaidEndpoint

app = FastAPI()

@app.post("/api/premium-query")
@PaidEndpoint(price="0.5 HBAR")
async def premium_query(request: Request):
    return {"result": "paid access granted"}
\`\`\`

## What happens

1. Client calls the endpoint with no proof → HACK returns **HTTP 402** with a quote.
2. Client sends HBAR to the receiver account.
3. Client retries with \`X-Quote-Id\` and \`X-Payment-Token\` headers.
4. HACK verifies via Mirror Node, opens a grant window, and returns \`200 OK\`.

Every step is auditable via HCS receipts.
`,
  },
  configuration: {
    slug: "configuration", section: "Getting Started", title: "Configuration",
    content: `# Configuration

HACK reads its config from environment variables. Copy \`.env.example\` to \`.env\` and fill in:

\`\`\`bash
HEDERA_NETWORK=testnet
HEDERA_ACCOUNT_ID=0.0.XXXXXX
HEDERA_PRIVATE_KEY=302e0201...
HCS_TOPIC_ID=0.0.YYYYYY
MIRROR_NODE_URL=https://testnet.mirrornode.hedera.com
GROQ_API_KEY=gsk_...
\`\`\`

## Optional

- \`QUOTE_TTL_SECONDS\` — default 600
- \`GRANT_TTL_SECONDS\` — default 300
- \`STORE_BACKEND\` — \`memory\` (default) or \`redis\`
- \`HACK_NFT_TOKEN_ID\` — auto-created on first mint if not set
`,
  },
  "paid-endpoint": {
    slug: "paid-endpoint", section: "Toolkit Reference", title: "@PaidEndpoint Decorator",
    content: `# @PaidEndpoint

Wraps any async FastAPI endpoint with x402 payment logic.

\`\`\`python
@PaidEndpoint(
    price="0.5 HBAR",
    receiver="0.0.4820193",   # optional, defaults to HEDERA_ACCOUNT_ID
    ttl_seconds=600,          # optional
)
async def my_service(request: Request):
    ...
\`\`\`

The decorator:

- Intercepts requests without a valid grant → returns 402 with a signed quote
- Verifies proofs against Mirror Node before invoking your handler
- Rejects duplicate transaction IDs (idempotency)
- Publishes an HCS receipt after every successful call
`,
  },
  middleware: {
    slug: "middleware", section: "Toolkit Reference", title: "Middleware",
    content: `# Middleware

Instead of decorating individual endpoints, mount HACK as ASGI middleware to protect entire routers.

\`\`\`python
from fastapi import FastAPI
from hack.toolkit import HackMiddleware

app = FastAPI()
app.add_middleware(HackMiddleware, protected_prefixes=["/api/premium"])
\`\`\`

Middleware and decorators can be mixed. The decorator wins on a per-route basis.
`,
  },
  "state-machine": {
    slug: "state-machine", section: "Toolkit Reference", title: "State Machine",
    content: `# Payment State Machine

Every payment moves through six explicit states.

- **quoted** — Challenge issued, no proof yet
- **verified** — Mirror Node confirmed the transfer
- **granted** — Grant window opened, handler can be invoked
- **consumed** — Handler ran successfully, grant closed
- **expired** — Quote or grant TTL exceeded
- **duplicate** — Transaction ID reused across quotes

Transitions are guarded. Duplicate and expired states are terminal.
`,
  },
  "certification-service": {
    slug: "certification-service", section: "Compliance Engine", title: "Certification Service",
    content: `# Certification Service

Generates machine-readable compliance reports for MCP servers, APIs, and agents.

\`\`\`python
from hack.certification import CertificationService
from hack.models.compliance import CertificationSubmission

service = CertificationService()
report = await service.certify(
    submission=CertificationSubmission(...),
    quote_id=quote.id,
)
\`\`\`

The report includes:

- 5 x402 rule results
- 4 Hedera best-practice rule results
- Severity-grouped security findings
- LLM-generated recommendations (markdown)
- HCS receipt reference + optional soulbound NFT metadata
`,
  },
  "service-audit": {
    slug: "service-audit", section: "Compliance Engine", title: "Service Audit Pipeline",
    content: `# Service Audit Pipeline

The automated audit pipeline runs live HTTP probes, static source analysis, and LLM-powered reviews against any MCP server or API endpoint.

## Submit an audit

\`\`\`bash
POST /api/audit/submit
{
  "service_name": "my-mcp-server",
  "service_type": "mcp",
  "endpoint_url": "https://my-service.example.com/api/...",
  "repo_url": "https://github.com/..."
}
\`\`\`

Returns a payment quote. Pay 0.5 HBAR, then:

\`\`\`bash
POST /api/audit/run/{quote_id}?transaction_id=0.0.XXXX@...
\`\`\`

The backend runs 5 live probes, 6 static rules, and a Groq LLM review. The call blocks 15–30 seconds.

## Grading

- **A+** ≥ 95
- **A** ≥ 90
- **B** ≥ 80
- **C** ≥ 70
- **D** ≥ 60
- **F** < 60

Pass threshold is **70** (C or above).
`,
  },
  "soulbound-nft": {
    slug: "soulbound-nft", section: "Compliance Engine", title: "Soulbound NFT Minting",
    content: `# Soulbound NFT Minting

When a service audit passes (score ≥ 70), the compliance engine mints a non-transferable (soulbound) NFT on Hedera HTS.

## Properties

- **Freeze default = true** — tokens cannot be transferred between accounts
- **Metadata** — packed on-chain: agent name, score, grade, date, certificate ID, HCS topic, transaction ID, version, signature hash
- **SHA-256 metadata hash** — cryptographically bound to the audit report
- **HCS anchor** — mint transaction ID published to the HCS topic for verifiability

## Token ID

The NFT collection token ID is auto-created on first mint and persisted to \`.hack_state.json\`. You can also pre-create it and set \`HACK_NFT_TOKEN_ID\` in your \`.env\`.

## Viewing

Every certificate page links directly to HashScan for cross-verification.
`,
  },
  fastapi: {
    slug: "fastapi", section: "Integrations", title: "FastAPI",
    content: `# FastAPI Integration

HACK is designed FastAPI-first. See the [Quick Start](/docs/quick-start) for the minimal wiring, and [Middleware](/docs/middleware) for router-level protection.

## Router-level example

\`\`\`python
from fastapi import APIRouter
from hack.toolkit import PaidEndpoint

router = APIRouter(prefix="/api/premium")

@router.post("/query")
@PaidEndpoint(price="0.5 HBAR")
async def query(...):
    ...

@router.post("/report")
@PaidEndpoint(price="1 HBAR")
async def report(...):
    ...
\`\`\`
`,
  },
  "agent-kit": {
    slug: "agent-kit", section: "Integrations", title: "Hedera Agent Kit",
    content: `# Hedera Agent Kit

The premium endpoint in the reference implementation is backed by the official [Hedera Agent Kit](https://docs.hedera.com/hedera/open-source-solutions/ai-studio-on-hedera).

\`\`\`python
from hedera_agent_kit import HederaAgentToolkit
from langchain.agents import AgentExecutor

toolkit = HederaAgentToolkit(
    client=hedera_client,
    plugins=["core_consensus_plugin", "core_account_plugin"],
)
executor = AgentExecutor.from_agent_and_tools(...)
\`\`\`

Wrap the executor call in \`@PaidEndpoint\` and you have a fully paid, on-chain agent API.
`,
  },
  "mcp-integration": {
    slug: "mcp-integration", section: "Integrations", title: "MCP Tools",
    content: `# MCP Integration

HACK exposes an MCP server so any AI agent can discover and call paid tools via the Model Context Protocol.

## Available tools

- \`hedera_paid_query\` — submit a natural-language query; pays 0.5 HBAR automatically
- \`hedera_paid_action\` — execute a paid action (e.g., transfer, create topic)

The agent receives a 402 challenge, pays via its wallet, and retries transparently.

## Using with Claude / Cursor / Cline

Add the HACK MCP server to your agent's config:

\`\`\`json
{
  "mcpServers": {
    "hack": {
      "command": "python",
      "args": ["-m", "hack.mcp.server"]
    }
  }
}
\`\`\`
`,
  },
  "api-reference": {
    slug: "api-reference", section: "Reference", title: "API Reference",
    content: `# API Reference

The full OpenAPI specification is served by the backend at \`GET /openapi.json\`.

## Payment endpoints

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | /api/health | none | Liveness probe |
| GET | /api/demo | none | Free demo endpoint |
| POST | /api/payment/challenge | none | Issue an x402 quote |
| POST | /api/payment/verify | none | Verify a proof against a quote |
| GET | /api/payment/status/{quote_id} | none | Read state-machine state |
| POST | /api/premium-query | **x402** | Agent Kit-backed premium query |
| POST | /api/compliance/check | **x402** | Legacy compliance check |
| POST | /api/compliance/certify/{quote_id} | **x402** | Legacy full report |
| GET | /api/compliance/report/{report_id} | none | Legacy report fetch |
| GET | /api/receipt/{tx_id} | none | Read the HCS receipt |

## Audit endpoints (new)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| POST | /api/audit/submit | none | Submit a service for audit (returns payment quote) |
| POST | /api/audit/run/{quote_id} | paid | Run live probes + static analysis + LLM review |
| GET | /api/audit/report/{report_id} | none | Fetch audit report JSON |
| GET | /api/audit/report/{report_id}/pdf | none | Download PDF report |
| GET | /api/audit/report/{report_id}/skill.md | none | AI-agent SKILL.md |
| GET | /api/audit/certificate/{certificate_id} | none | Fetch soulbound certificate |
| GET | /api/audit/certificates | none | List all certificates (newest first) |
`,
  },
};
