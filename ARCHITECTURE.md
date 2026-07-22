# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        A["AI Agent / curl / Frontend"]
    end

    subgraph HACK["HACK Backend (FastAPI)"]
        B["x402 Middleware"]
        C["Payment Router\n/api/payment/challenge\n/api/payment/verify"]
        D["State Machine\nQUOTED → CONSUMED"]
        E["Premium Handler\n/api/premium-query"]
        F["Hedera Agent Kit\nLangChain + Plugins"]
        G["Usage Metering"]
    end

    subgraph Hedera["Hedera Network"]
        H["Mirror Node\nREST API"]
        I["HCS Topic\nImmutable Receipts"]
        J["HashScan\nExplorer"]
    end

    A -->|"GET /api/premium-query"| B
    B -->|"No token → HTTP 402"| A
    A -->|"POST /api/payment/challenge"| C
    C -->|"quote_id + payment details"| A
    A -->|"Sends 0.5 HBAR"| Hedera
    A -->|"POST /api/payment/verify"| C
    C -->|"Verify tx"| H
    H -->|"amount ✓ receiver ✓"| C
    C --> D
    D -->|"GRANTED"| C
    C -->|"Publish receipt"| I
    C -->|"verified + grant"| A
    A -->|"Retry + X-Payment-Token + X-Quote-Id"| B
    B -->|"GRANTED → CONSUMED"| E
    E --> F
    E --> G
    F -->|"AI result"| A
    I -.->|"hashscan_url"| J
```

---

## Payment Flow (Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant C as Client / Agent
    participant MW as x402 Middleware
    participant PS as Payment State Machine
    participant MN as Hedera Mirror Node
    participant HCS as HCS Topic
    participant AK as Hedera Agent Kit

    C->>MW: GET /api/premium-query
    MW->>C: 402 Payment Required<br/>{next: POST /api/payment/challenge}

    C->>PS: POST /api/payment/challenge<br/>{endpoint}
    PS->>C: {quote_id, resource_hash,<br/>receiver, amount_hbar, expires_at}

    Note over C: Sends 0.5 HBAR to receiver<br/>via Hedera wallet

    C->>PS: POST /api/payment/verify<br/>{transaction_id, quote_id}
    PS->>MN: GET /api/v1/transactions/{txId}
    MN-->>PS: {transfers: [{account, amount}]}
    PS->>PS: amount ✓  receiver ✓  expiry ✓
    PS->>PS: State: QUOTED → VERIFIED → GRANTED
    PS->>HCS: TopicMessageSubmitTransaction<br/>{txId, caller, amount, hashscan_url}
    HCS-->>PS: receipt published
    PS->>C: {verified: true, grant_expires_at, receipt}

    C->>MW: GET /api/premium-query<br/>X-Payment-Token + X-Quote-Id
    MW->>PS: advance GRANTED → CONSUMED
    MW->>AK: run_agent_query(q)
    AK-->>MW: AI result
    MW->>C: 200 OK {result, receipt_url, hashscan_url}
```

---

## Payment State Machine

```mermaid
stateDiagram-v2
    direction LR

    [*] --> QUOTED : POST /payment/challenge

    QUOTED --> VERIFIED : Mirror Node confirms\namount + receiver
    QUOTED --> EXPIRED : TTL elapsed (10 min)

    VERIFIED --> GRANTED : access window opened\n(5 min TTL)

    GRANTED --> CONSUMED : request delivered\n(exactly once)
    GRANTED --> EXPIRED : grant TTL elapsed

    CONSUMED --> [*] : done

    EXPIRED --> [*] : request new quote

    QUOTED --> DUPLICATE : same tx_id\non different quote

    note right of CONSUMED
        Replay attempt → 402 CONSUMED
        Each payment = one request
    end note
```

---

## Component Map

```mermaid
flowchart LR
    subgraph API["Developer API"]
        DEC["@PaidEndpoint\nbackend/hack.py"]
    end

    subgraph Core["Core Backend"]
        MW["x402 Middleware\nmiddleware/x402.py"]
        SM["Payment State Machine\nverification/payment_state.py"]
        MNV["Mirror Node Verifier\nverification/mirror_node.py"]
        HCS["HCS Receipt Logger\nreceipts/hcs.py"]
        MTR["Usage Metering\nmetering/usage.py"]
    end

    subgraph AgentKit["Hedera Agent Kit"]
        AG["LangChain Agent\nagent/hedera_agent.py"]
        P1["core_account_plugin"]
        P2["core_account_query_plugin"]
        P3["core_consensus_plugin"]
        P4["core_token_plugin"]
    end

    subgraph Routers["FastAPI Routers"]
        R1["/api/payment/*"]
        R2["/api/premium-query"]
        R3["/api/receipt/{txId}"]
        R4["/api/agent/query"]
        R5["/api/usage"]
        R6["/api/hashscan/{txId}"]
    end

    DEC --> MW
    MW --> SM
    SM --> MNV
    SM --> HCS
    HCS --> P3
    R2 --> AG
    AG --> P1 & P2 & P3 & P4
    R1 --> SM
    R2 --> MTR
    R3 --> HCS
```

---

## Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| `@PaidEndpoint` | `backend/hack.py` | One-line decorator for monetizing any route |
| x402 Middleware | `backend/middleware/x402.py` | Global gate — enforces GRANTED state before handler |
| Payment State Machine | `backend/verification/payment_state.py` | QUOTED→CONSUMED with replay protection + TTLs |
| Mirror Node Verifier | `backend/verification/mirror_node.py` | Stateless on-chain payment confirmation |
| HCS Receipt Logger | `backend/receipts/hcs.py` | Publishes immutable receipts via `core_consensus_plugin` |
| Usage Metering | `backend/metering/usage.py` | In-memory per-request tracking |
| Hedera Agent | `backend/agent/hedera_agent.py` | LangChain agent backed by Hedera Kit plugins |
| FastAPI App | `backend/main.py` | Wires all components together |
| Demo UI | `frontend/src/app/page.tsx` | Next.js interactive demo |
| MCP Tool Example | `examples/mcp/paid_tool.py` | Paid MCP tool pattern |

---

## Security Notes

- The operator private key is used **only** for HCS topic publishing — it is loaded from `.env` and never echoed in API responses.
- Payment proofs are bound to a `quote_id` + `resource_hash`. Cross-quote replay is rejected with 409.
- Each verified payment is consumed **exactly once** (CONSUMED state). Retrying with the same headers returns 402.
- All transactions are on Hedera **testnet** for the MVP. Mainnet requires explicit operator opt-in.
