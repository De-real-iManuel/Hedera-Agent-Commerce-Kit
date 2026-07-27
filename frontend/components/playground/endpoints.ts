import type { LucideIcon } from "lucide-react";

export interface EndpointDef {
  id: string;
  method: "GET" | "POST";
  path: string;
  label: string;
  description: string;
  category: string;
  x402?: boolean;
  defaultBody?: string;
}

export const ENDPOINT_GROUPS: Array<{
  category: string;
  endpoints: EndpointDef[];
}> = [
  {
    category: "Infrastructure",
    endpoints: [
      {
        id: "health", method: "GET", path: "/api/health",
        label: "Health", description: "Backend liveness probe.",
        category: "Infrastructure",
      },
      {
        id: "usage", method: "GET", path: "/api/usage",
        label: "Usage", description: "Per-endpoint usage metering stats.",
        category: "Infrastructure",
      },
    ],
  },
  {
    category: "Payments",
    endpoints: [
      {
        id: "challenge", method: "POST", path: "/api/payment/challenge",
        label: "Challenge", description: "Request an x402 payment quote.",
        category: "Payments",
        defaultBody: JSON.stringify(
          { resource_path: "/api/premium-query", amount_hbar: 0.5 },
          null, 2,
        ),
      },
      {
        id: "verify", method: "POST", path: "/api/payment/verify",
        label: "Verify", description: "Prove a payment against a quote.",
        category: "Payments",
        defaultBody: JSON.stringify(
          { quote_id: "<quote_id from /challenge>", transaction_id: "<0.0.XXXXX@timestamp.nanos>" },
          null, 2,
        ),
      },
      {
        id: "status", method: "GET", path: "/api/payment/status/{quote_id}",
        label: "Status", description: "Read the state machine state for a quote.",
        category: "Payments",
      },
      {
        id: "premium", method: "GET", path: "/api/premium-query",
        label: "Premium Query", description: "Hedera Agent Kit query gated behind x402.",
        category: "Payments", x402: true,
      },
    ],
  },
  {
    category: "Agent",
    endpoints: [
      {
        id: "agent-query", method: "GET", path: "/api/agent/query",
        label: "Agent Query", description: "Free Hedera Agent Kit query (balance, HCS, tokens).",
        category: "Agent",
      },
    ],
  },
  {
    category: "Compliance",
    endpoints: [
      {
        id: "compliance-check", method: "POST", path: "/api/compliance/check",
        label: "Check", description: "Run compliance rules on a verified payment.",
        category: "Compliance",
        defaultBody: JSON.stringify(
          { transaction_id: "<tx_id>", quote_id: "<quote_id>" },
          null, 2,
        ),
      },
      {
        id: "certify", method: "GET", path: "/api/compliance/certify/{quote_id}",
        label: "Certify", description: "Issue a per-transaction CertificationReport.",
        category: "Compliance",
      },
    ],
  },
  {
    category: "Audit & Certificates",
    endpoints: [
      {
        id: "audit-submit", method: "POST", path: "/api/audit/submit",
        label: "Submit Audit", description: "Request a full service compliance audit (returns payment challenge).",
        category: "Audit & Certificates",
        defaultBody: JSON.stringify(
          { service_name: "my-service", service_type: "x402", endpoint_url: "https://…", repo_url: null },
          null, 2,
        ),
      },
      {
        id: "audit-run", method: "POST", path: "/api/audit/run/{quote_id}",
        label: "Run Audit", description: "Run the audit after payment (mints NFT if passed).",
        category: "Audit & Certificates",
      },
      {
        id: "audit-report", method: "GET", path: "/api/audit/report/{report_id}",
        label: "Report", description: "Fetch a completed audit report.",
        category: "Audit & Certificates",
      },
      {
        id: "audit-certificates", method: "GET", path: "/api/audit/certificates",
        label: "Certificates", description: "List all issued soulbound certificates.",
        category: "Audit & Certificates",
      },
      {
        id: "receipt", method: "GET", path: "/api/receipt/{tx_id}",
        label: "Receipt", description: "Fetch the HCS receipt for a transaction.",
        category: "Audit & Certificates",
      },
    ],
  },
];
