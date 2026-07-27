import { notFound } from "next/navigation";
import { ComplianceReport } from "@/components/certification/ComplianceReport";
import { API_BASE, mapAuditToLegacy } from "@/lib/api";
import type {
  CertificateSummary, ServiceAuditReport, SoulboundCertificate,
} from "@/lib/types";

async function fetchJson<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) return null;
  return (await res.json()) as T;
}

async function fetchText(path: string): Promise<string> {
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!res.ok) return "";
    return await res.text();
  } catch {
    return "";
  }
}

async function loadReport(reportId: string) {
  const report = await fetchJson<ServiceAuditReport>(
    `/api/audit/report/${encodeURIComponent(reportId)}`,
  );
  if (!report) return null;

  const skillMd = await fetchText(
    `/api/audit/report/${encodeURIComponent(reportId)}/skill.md`,
  );

  // Locate the certificate (if any) by scanning the gallery index — cheap and O(N)
  let certificate: SoulboundCertificate | null = null;
  const gallery = await fetchJson<{ certificates: CertificateSummary[] }>(
    "/api/audit/certificates?limit=200",
  );
  const row = gallery?.certificates.find((r) => r.report_id === reportId);
  if (row) {
    certificate = await fetchJson<SoulboundCertificate>(
      `/api/audit/certificate/${encodeURIComponent(row.certificate_id)}`,
    );
  }

  return { report, certificate, skillMd };
}

export async function generateMetadata({
  params,
}: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await params;
  return {
    title: `Compliance Report ${reportId.slice(0, 8)} — HACK`,
    description:
      "Hedera Agent Commerce Kit — automated compliance audit report.",
  };
}

export default async function ReportPage({
  params,
}: { params: Promise<{ reportId: string }> }) {
  const { reportId } = await params;
  const data = await loadReport(reportId);
  if (!data) notFound();
  const legacy = mapAuditToLegacy(data.report, data.certificate, data.skillMd);
  return <ComplianceReport report={legacy} />;
}
