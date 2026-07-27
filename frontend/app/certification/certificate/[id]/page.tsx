import { notFound } from "next/navigation";
import { SoulboundCertificateCard } from "@/components/certification/SoulboundCertificate";
import { API_BASE } from "@/lib/api";
import type { SoulboundCertificate as BackendCert } from "@/lib/types";

async function fetchCert(id: string): Promise<BackendCert | null> {
  const res = await fetch(
    `${API_BASE}/api/audit/certificate/${encodeURIComponent(id)}`,
    { cache: "no-store" },
  );
  if (!res.ok) return null;
  return (await res.json()) as BackendCert;
}

export async function generateMetadata({
  params,
}: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return {
    title: `Certificate ${id.slice(0, 8)} — HACK`,
    description: "Soulbound compliance certificate issued by the Hedera Agent Commerce Kit.",
  };
}

export default async function CertificatePage({
  params,
}: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cert = await fetchCert(id);
  if (!cert) notFound();
  const reportUrl = `/certification/${encodeURIComponent(cert.report_id)}`;
  return <SoulboundCertificateCard cert={cert} reportUrl={reportUrl} />;
}
