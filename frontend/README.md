# frontend — Developer Portal

The Next.js 15 developer portal for Hedera Agent Commerce Kit. Provides a live demonstration of the x402 payment flow, a compliance certification interface, a certificate gallery, and integrated documentation — all connected to the `demo/` backend over a standard REST API.

---

## What This Application Does

**API Explorer**
A live walkthrough of the complete x402 payment cycle. Developers submit a request, connect a Hedera wallet via WalletConnect v2, approve an HBAR payment, and see the Mirror Node verification and HCS receipt in real time.

**Compliance Certification**
Submit any deployed service (API, MCP tool, or x402-gated endpoint) for automated compliance analysis. The interface tracks analysis progress, renders a structured report with section-by-section findings, and displays the issued soulbound certificate with its HashScan anchor link.

**Certificate Gallery**
A browsable index of all issued compliance certificates with their on-chain transaction IDs, HCS receipt references, and compliance scores.

**Documentation**
An integrated documentation viewer rendering the project's Markdown documentation inline, providing a single-origin experience for developers exploring the platform.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript 5.6 |
| Styling | Tailwind CSS |
| Animation | Framer Motion |
| Wallet integration | `@hashgraph/hedera-wallet-connect` 1.5.1 — WalletConnect v2 |
| Hedera SDK | `@hashgraph/sdk` 2.53 |
| UI primitives | Radix UI |
| Icons | Lucide React |

---

## Directory Layout

```
frontend/
│
├── app/                        Next.js App Router
│   ├── page.tsx                Landing page
│   ├── layout.tsx              Root layout — fonts, global styles
│   ├── globals.css             Tailwind base + CSS custom properties
│   ├── api-explorer/           Live x402 payment flow demonstration
│   ├── certification/          Compliance audit submission and report viewer
│   │   ├── page.tsx            Submission form
│   │   ├── [reportId]/         Report detail page
│   │   └── certificate/[id]/   Certificate detail page
│   ├── certificates/           Certificate gallery
│   └── docs/                   Integrated documentation viewer
│
├── components/
│   ├── certification/
│   │   ├── AnalysisProgress.tsx   Real-time audit progress indicator
│   │   ├── ComplianceReport.tsx   Section-by-section report renderer
│   │   ├── PaymentGate.tsx        x402 payment flow UI component
│   │   ├── RuleCheckList.tsx      Per-rule pass/fail display
│   │   └── WalletConnectModal.tsx Wallet pairing and status shell
│   └── ui/                        Shared design system primitives
│
├── hooks/
│   └── useWalletConnect.ts     Hedera WalletConnect v2 hook
│                               Manages DAppConnector lifecycle, session
│                               restoration, HBAR transfer construction,
│                               and import caching for @hashgraph/sdk.
│
├── lib/
│   ├── api.ts                  Typed REST client for the HACK backend
│   ├── types.ts                TypeScript types mirroring backend Pydantic models
│   └── utils.ts                Shared utility functions
│
└── next.config.mjs             Build configuration
```

---

## Getting Started

**Prerequisites:** Node.js 18+, the backend running on port 8000.

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local — see Configuration below

# Start the development server
npm run dev
# → http://localhost:3000
```

---

## Configuration

All runtime configuration is provided via `frontend/.env.local`. Copy `.env.local.example` and fill in the following:

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL — default `http://localhost:8000` |
| `NEXT_PUBLIC_HEDERA_NETWORK` | `testnet` or `mainnet` |
| `NEXT_PUBLIC_HASHSCAN_BASE` | HashScan base URL — `https://hashscan.io/testnet` |
| `NEXT_PUBLIC_PAYMENT_RECEIVER` | Hedera account ID receiving HBAR payments — must match backend `X402_PAYMENT_RECEIVER_ACCOUNT_ID` |
| `NEXT_PUBLIC_HCS_TOPIC_ID` | HCS topic ID for receipt links — must match backend `HCS_RECEIPT_TOPIC_ID` |
| `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` | Reown Cloud project ID — register free at [cloud.reown.com](https://cloud.reown.com) |

---

## Wallet Integration

Wallet connection is managed by `hooks/useWalletConnect.ts`. The hook wraps `DAppConnector` from `@hashgraph/hedera-wallet-connect` and exposes a stable interface across all components:

```typescript
const {
  isConnected,
  accountId,
  network,
  connect,       // Opens the WalletConnect / Reown QR modal
  disconnect,
  sendHbar,      // Builds, signs, and submits a TransferTransaction
  isPending,
  error,
} = useWalletConnect();
```

**Key implementation details:**

- The `DAppConnector` instance is a module-level singleton — one connection survives component unmounts and re-mounts
- `@hashgraph/sdk` and `@hashgraph/hedera-wallet-connect` are loaded once via a cached `loadImports()` function, then reused for all subsequent operations
- `TransactionId.generate()` is called before serialization to satisfy the SDK's requirement that a transaction ID be set before `transactionToBase64String()`
- The hook exposes `network` derived from `NEXT_PUBLIC_HEDERA_NETWORK` — all transaction routing uses this value consistently

Compatible wallets: **HashPack**, **Kabila**, and any WalletConnect v2 + Hedera-compatible wallet.

---

## API Client

`lib/api.ts` provides a fully typed REST client wrapping all backend endpoints. Every method returns a typed response corresponding to the backend's Pydantic model.

```typescript
import { api } from "@/lib/api";

// Submit a service for compliance audit
const { quote_id, amount_hbar, receiver } = await api.submitAudit(submission);

// Fetch the compliance report
const report = await api.getAuditReport(reportId);

// Download the certificate
const certificate = await api.getCertificate(certificateId);

// Map a backend audit report to the legacy display shape
const legacyReport = mapAuditToLegacy(report, certificate, skillMd);
```

The `mapAuditToLegacy()` function in `api.ts` projects `ServiceAuditReport` (backend shape) onto `CertificationReport` (display component shape), allowing report display components to remain stable as the backend evolves.

---

## Build

```bash
# Development server with hot reload
npm run dev

# Production build
npm run build

# Start production server
npm start

# Type checking
npm run typecheck

# Lint
npm run lint
```

The production build uses `node --max-old-space-size=4096` to accommodate the `@hashgraph/sdk` bundle during compilation. This is set in `package.json` and requires no manual configuration.

---

## Build Configuration Notes

`next.config.mjs` is configured as follows:

- `serverExternalPackages` — `@hashgraph/sdk`, `@hashgraph/proto`, and `@hiero-ledger/sdk` are excluded from the SSR bundle. They are only used client-side via dynamic import in `useWalletConnect.ts`.
- `transpilePackages` — WalletConnect packages are transpiled by Next.js because they ship as ESM and require transformation for the browser bundle.
- No webpack aliases override `@hashgraph/hedera-wallet-connect` — the real package is loaded at runtime for wallet pairing and transaction signing.

---

## Supported Browsers

Any modern browser supporting WebSocket connections (required for WalletConnect relay) and the Web Crypto API. Tested on Chrome 120+, Firefox 121+, and Safari 17+.
