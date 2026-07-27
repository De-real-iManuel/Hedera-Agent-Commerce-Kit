// frontend/lib/types.ts
// ==================================================================
// Legacy display shapes (used by ComplianceReport, SoulboundCertificate)
// PLUS new backend shapes returned by /api/audit/*.
// api.ts contains a mapper that projects backend → legacy for display.
// ==================================================================

// ─── Payment (unchanged) ────────────────────────────────────────────
export type PaymentState = "quoted" | "verified" | "granted" | "consumed" | "expired" | "duplicate";

export interface ChallengeRequest { resource_path: string; amount_hbar?: number; }
export interface ChallengeResponse {
  quote_id: string; receiver: string; amount_hbar: number; memo: string;
  expires_at: number; network: "testnet" | "mainnet"; resource_hash: string;
}
export interface VerifyRequest { quote_id: string; transaction_id: string; }
export interface VerifyResponse {
  verified: boolean; state: PaymentState; transaction_id: string;
  grant_expires_at: number; hcs_status: "published" | "pending" | "failed";
  hashscan_url: string; receipt?: Record<string, unknown>; reason?: string;
}
export interface PremiumResponse {
  result: unknown; agent_message?: string;
  hedera_tool_calls?: Array<{ tool: string; args: Record<string, unknown> }>;
}

// ─── Legacy display types (kept for existing components) ────────────
export type RuleSeverity = "critical" | "medium" | "warning" | "suggestion";
export interface RuleResult { id: string; name: string; passed: boolean; detail: string; severity?: RuleSeverity; }
export interface SecurityFinding { id: string; severity: RuleSeverity; title: string; detail: string; }

export interface ComplianceCheckResult {
  service_name: string; score: number; passed: boolean;
  x402_rules: RuleResult[]; hedera_rules: RuleResult[];
  security_findings: SecurityFinding[]; recommendations: string;
}
export interface CertificationReport extends ComplianceCheckResult {
  report_id: string; certified_at: number; framework_version: string;
  analysis_hash: string; hcs_topic: string; hashscan_url: string;
  transaction_id: string; network: "testnet" | "mainnet";
  skill_md: string; pdf_url?: string; certificate_id?: string;
}
export interface CertificationSubmission {
  service_name: string; service_type: "mcp" | "fastapi" | "agent" | "other";
  repo_url?: string; openapi_url?: string; primary_endpoint: string;
  description?: string; source_code?: string;
}
export interface SoulboundCertificateMetadata {
  certification_id: string; service: string; score: number; passed: boolean;
  issued_at: number; framework_version: string; analysis_hash: string;
  hcs_topic: string; hashscan_url: string; network: "testnet" | "mainnet";
  transferable: false; type: "SoulboundComplianceCertificate";
}

// ─── NEW backend shapes (/api/audit/*) ──────────────────────────────
export type AuditServiceType = "x402" | "mcp" | "hybrid";
export type AuditFindingStatus = "passed" | "warning" | "failed";
export type AuditSeverity = "info" | "low" | "medium" | "high" | "critical";

export interface AuditFinding {
  finding_id: string; section: string; title: string;
  status: AuditFindingStatus; severity: AuditSeverity;
  detail: string; evidence?: string | null; remediation?: string | null;
}
export interface AuditSection {
  section_id: "payment_flow" | "security" | "architecture" | "best_practices" | "performance";
  title: string; description: string; weight: number; score: number;
  findings: AuditFinding[];
}
export interface ServiceAuditRequestBackend {
  service_name: string; service_type: AuditServiceType;
  endpoint_url: string; repo_url?: string | null;
  primary_file?: string | null; contact_email?: string | null;
  recipient_account_id?: string | null;
  source_code?: string | null;
}
export interface ServiceAuditReport {
  report_id: string;
  request: ServiceAuditRequestBackend;
  created_at: number; completed_at?: number | null;
  status: "running" | "completed" | "failed";
  overall_score: number; grade: string; passed: boolean;
  sections: AuditSection[];
  recommendations: string[];
  executive_summary: string;
  hashscan_url?: string | null;
  hcs_receipt_id?: string | null;
  error?: string | null;
}
export interface SoulboundCertificate {
  certificate_id: string; report_id: string; agent_name: string;
  service_endpoint?: string | null; service_type?: string | null;
  score: number; grade: string; version: string;
  token_id: string; serial_number: number;
  recipient_account_id: string; treasury_account_id: string;
  minted_at: number; hcs_topic_id?: string | null;
  hcs_receipt_tx?: string | null;
  payment_transaction_id?: string | null;
  mint_transaction_id: string; metadata_hash: string;
  hashscan_token_url: string; hashscan_tx_url: string;
  hashscan_payment_url?: string | null;
}
export interface CertificateSummary {
  certificate_id: string; report_id: string; agent_name: string;
  score: number; grade: string; minted_at: number;
  token_id: string; serial_number: number; hashscan_tx_url: string;
}
export interface AuditSubmitResponse {
  quote_id: string; amount: number; amount_hbar: number;
  receiver: string; memo: string; network: "testnet" | "mainnet";
  expires_at: number;
}
export interface AuditRunResponse {
  report: ServiceAuditReport;
  certificate: SoulboundCertificate | null;
}

export interface ApiError { status: number; message: string; payload?: unknown; }
