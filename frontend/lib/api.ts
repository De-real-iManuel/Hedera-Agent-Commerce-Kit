// frontend/lib/api.ts
// ==================================================================
// Real backend client. No mock fallbacks anywhere.
//
// Two flows exposed:
//   1. Payment (legacy)   — challenge / verify / premium
//   2. Service audit      — submitAudit / runAudit / getAuditReport / ...
//
// mapAuditToLegacy() projects the backend's ServiceAuditReport onto the
// legacy CertificationReport shape so existing display components keep
// working unchanged.
// ==================================================================

import type {
  ChallengeRequest, ChallengeResponse, VerifyRequest, VerifyResponse,
  PremiumResponse, ApiError,
  ServiceAuditRequestBackend, ServiceAuditReport, SoulboundCertificate,
  CertificateSummary, AuditSubmitResponse, AuditRunResponse,
  CertificationReport, CertificationSubmission,
  RuleResult, RuleSeverity, SecurityFinding,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

interface FetchOptions extends RequestInit { timeoutMs?: number; }

async function request<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { timeoutMs = 60000, headers, ...rest } = opts;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(headers || {}),
      },
    });
    const text = await res.text();
    const body = text ? JSON.parse(text) : null;
    if (!res.ok) {
      const err: ApiError = {
        status: res.status,
        message: (body && (body.message || body.detail)) || res.statusText,
        payload: body,
      };
      throw err;
    }
    return body as T;
  } finally { clearTimeout(timer); }
}

async function fetchText(path: string, timeoutMs = 30000): Promise<string> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, { signal: controller.signal });
    if (!res.ok) throw { status: res.status, message: res.statusText } as ApiError;
    return await res.text();
  } finally { clearTimeout(timer); }
}

// ─── Frontend submission → backend request mapper ───────────────────
export function toBackendSubmission(
  s: CertificationSubmission,
): ServiceAuditRequestBackend {
  const svc: ServiceAuditRequestBackend["service_type"] =
    s.service_type === "mcp" ? "mcp" : "x402";
  return {
    service_name: s.service_name.trim(),
    service_type: svc,
    endpoint_url: s.primary_endpoint.trim(),
    repo_url: s.repo_url?.trim() || null,
    // If source code is pasted and no repo URL, label the file after the service
    // so findings reference the correct filename instead of the generic "main.py".
    primary_file: s.repo_url?.trim()
      ? "main.py"
      : s.source_code?.trim()
      ? `${s.service_name.trim().replace(/\s+/g, "_").toLowerCase()}.py`
      : "main.py",
    contact_email: null,
    recipient_account_id: null,
    source_code: s.source_code?.trim() || null,
  };
}

// ─── Backend ServiceAuditReport → legacy CertificationReport ────────
function severityToLegacy(s: string, status: string): RuleSeverity {
  if (status === "failed" && (s === "critical" || s === "high")) return "critical";
  if (s === "critical" || s === "high") return "critical";
  if (s === "medium") return "medium";
  if (s === "low") return "warning";
  return "suggestion";
}

export function mapAuditToLegacy(
  report: ServiceAuditReport,
  certificate: SoulboundCertificate | null,
  skillMd = "",
): CertificationReport {
  const asRule = (f: {
    finding_id: string; title: string; status: string; severity: string; detail: string;
  }): RuleResult => ({
    id: f.finding_id,
    name: f.title,
    passed: f.status === "passed",
    detail: f.detail,
    severity: severityToLegacy(f.severity, f.status),
  });

  const payment = report.sections.find((s) => s.section_id === "payment_flow");
  const perf = report.sections.find((s) => s.section_id === "performance");
  const security = report.sections.find((s) => s.section_id === "security");
  const architecture = report.sections.find((s) => s.section_id === "architecture");
  const best = report.sections.find((s) => s.section_id === "best_practices");

  const x402_rules: RuleResult[] = [
    ...(payment?.findings ?? []),
    ...(perf?.findings ?? []),
  ].map(asRule);

  const hedera_rules: RuleResult[] = [
    ...(architecture?.findings ?? []),
    ...(security?.findings ?? []),
    ...(best?.findings ?? []),
  ].map(asRule);

  const security_findings: SecurityFinding[] = report.sections
    .flatMap((s) => s.findings)
    .filter((f) => f.status !== "passed")
    .map((f) => ({
      id: f.finding_id,
      severity: severityToLegacy(f.severity, f.status),
      title: f.title,
      detail: f.remediation ? `${f.detail}  •  ${f.remediation}` : f.detail,
    }));

  const recommendationsMd = [
    report.executive_summary?.trim(),
    "",
    ...report.recommendations.map((r) => `- ${r}`),
  ]
    .filter(Boolean)
    .join("\n");

  const network: "testnet" | "mainnet" =
    (process.env.NEXT_PUBLIC_HEDERA_NETWORK as "testnet" | "mainnet") || "testnet";

  // transaction_id: prefer the NFT mint tx (cert exists) otherwise fall back
  // to the payment transaction stored on the report (hcs_receipt_id holds it
  // for non-certified reports — see audit.py run_audit).
  const txId =
    certificate?.mint_transaction_id ||
    report.hcs_receipt_id ||
    "";

  // hashscan_url: prefer the cert's url, then the report's stored url,
  // then construct one from whatever tx id we have.
  const hashscanBase =
    process.env.NEXT_PUBLIC_HASHSCAN_BASE ||
    `https://hashscan.io/${network}`;
  const hashscanUrl =
    certificate?.hashscan_tx_url ||
    report.hashscan_url ||
    (txId ? `${hashscanBase}/transaction/${txId}` : "");

  // hcs_topic: the static receipt topic configured for this deployment.
  // certificate.hcs_topic_id is the authoritative source; fall back to
  // the env var which is always set.
  const hcsTopic =
    certificate?.hcs_topic_id ||
    process.env.NEXT_PUBLIC_HCS_TOPIC_ID ||
    "";

  // analysis_hash: from the cert metadata_hash (sha256 of report JSON);
  // fall back to a placeholder so the UI always renders something.
  const analysisHash = certificate?.metadata_hash || report.report_id;

  return {
    service_name: report.request.service_name,
    score: Math.round(report.overall_score),
    passed: report.passed,
    x402_rules,
    hedera_rules,
    security_findings,
    recommendations: recommendationsMd,
    report_id: report.report_id,
    certified_at: report.completed_at ?? report.created_at,
    framework_version: certificate?.version ?? "1.0.0",
    analysis_hash: analysisHash,
    hcs_topic: hcsTopic,
    hashscan_url: hashscanUrl,
    transaction_id: txId,
    network,
    skill_md: skillMd,
    pdf_url: `${API_BASE}/api/audit/report/${encodeURIComponent(report.report_id)}/pdf`,
    certificate_id: certificate?.certificate_id,
  };
}

// ─── Public API ─────────────────────────────────────────────────────
export const api = {
  health: () => request<{ status: string; version: string }>("/api/health"),

  // Payment (legacy — used by API Explorer / PaymentGate)
  challenge: (body: ChallengeRequest) =>
    request<ChallengeResponse>("/api/payment/challenge", {
      method: "POST", body: JSON.stringify(body),
    }),
  verify: (body: VerifyRequest) =>
    request<VerifyResponse>("/api/payment/verify", {
      method: "POST", body: JSON.stringify(body),
    }),
  status: (quoteId: string) =>
    request<{ state: string; expires_at: number }>(
      `/api/payment/status/${encodeURIComponent(quoteId)}`,
    ),
  premium: (quoteId: string, txId: string, query: string) =>
    request<PremiumResponse>("/api/premium-query", {
      method: "POST",
      headers: { "X-Quote-Id": quoteId, "X-Payment-Token": txId },
      body: JSON.stringify({ query }),
    }),
  receipt: (txId: string) =>
    request<{ topic: string; sequence: number; consensus_ts: number }>(
      `/api/receipt/${encodeURIComponent(txId)}`,
    ),

  // Service audit (new — used by /certification flow)
  submitAudit: (submission: CertificationSubmission) =>
    request<AuditSubmitResponse>("/api/audit/submit", {
      method: "POST",
      body: JSON.stringify(toBackendSubmission(submission)),
    }),
  runAudit: (quoteId: string, transactionId: string) =>
    request<AuditRunResponse>(
      `/api/audit/run/${encodeURIComponent(quoteId)}?transaction_id=${encodeURIComponent(transactionId)}`,
      { method: "POST", timeoutMs: 120000 }, // audits can take up to 60s
    ),
  getAuditReport: (reportId: string) =>
    request<ServiceAuditReport>(
      `/api/audit/report/${encodeURIComponent(reportId)}`,
    ),
  getSkillMd: (reportId: string) =>
    fetchText(`/api/audit/report/${encodeURIComponent(reportId)}/skill.md`),
  getCertificate: (id: string) =>
    request<SoulboundCertificate>(
      `/api/audit/certificate/${encodeURIComponent(id)}`,
    ),
  listCertificates: (limit = 100) =>
    request<{ certificates: CertificateSummary[] }>(
      `/api/audit/certificates?limit=${limit}`,
    ),
  pdfUrl: (reportId: string) =>
    `${API_BASE}/api/audit/report/${encodeURIComponent(reportId)}/pdf`,
  skillMdUrl: (reportId: string) =>
    `${API_BASE}/api/audit/report/${encodeURIComponent(reportId)}/skill.md`,
};

export function isApiError(e: unknown): e is ApiError {
  return typeof e === "object" && e !== null && "status" in e && "message" in e;
}
export function is402(e: unknown): e is ApiError {
  return isApiError(e) && e.status === 402;
}
