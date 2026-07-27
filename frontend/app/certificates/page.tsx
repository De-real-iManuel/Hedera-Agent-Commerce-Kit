import Link from "next/link";
import { Award, ExternalLink, Shield } from "lucide-react";
import { API_BASE } from "@/lib/api";
import type { CertificateSummary } from "@/lib/types";

export const metadata = {
  title: "Certificates Gallery — HACK",
  description:
    "Every soulbound compliance certificate minted by the Hedera Agent Commerce Kit.",
};

async function loadCertificates(): Promise<CertificateSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/api/audit/certificates?limit=200`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    const body = (await res.json()) as { certificates: CertificateSummary[] };
    return body.certificates ?? [];
  } catch {
    return [];
  }
}

function grade(score: number): string {
  if (score >= 95) return "A+";
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

function gradeColor(g: string): string {
  if (g.startsWith("A")) return "text-green border-green/40 bg-green/10";
  if (g === "B") return "text-cyan border-cyan/40 bg-cyan/10";
  if (g === "C") return "text-amber border-amber/40 bg-amber/10";
  return "text-red border-red/40 bg-red/10";
}

export default async function CertificatesPage() {
  const certs = await loadCertificates();

  return (
    <div className="container mx-auto px-6 py-16 max-w-6xl">
      <div className="text-xs uppercase tracking-widest text-purple">Gallery</div>
      <h1 className="mt-2 text-4xl md:text-5xl font-bold tracking-tight">
        Soulbound Compliance Certificates
      </h1>
      <p className="mt-4 text-lg text-text-secondary max-w-2xl">
        Every audited service that passes the HACK compliance suite mints a
        non-transferable NFT on Hedera. Each row below is a verifiable on-chain
        certification you can cross-check on HashScan.
      </p>

      <div className="mt-10">
        {certs.length === 0 ? (
          <div className="rounded-lg border border-border bg-surface-1 p-10 text-center">
            <Shield className="h-8 w-8 text-text-muted mx-auto" />
            <div className="mt-3 text-sm text-text-secondary">
              No certificates minted yet. Submit a service for audit to be first.
            </div>
            <Link
              href="/certification"
              className="mt-4 inline-flex items-center gap-2 text-sm text-purple hover:text-purple/80"
            >
              Get certified <span aria-hidden>→</span>
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-surface-1">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-text-muted text-xs uppercase tracking-widest">
                <tr>
                  <th className="text-left px-4 py-3">#</th>
                  <th className="text-left px-4 py-3">Agent</th>
                  <th className="text-left px-4 py-3">Score</th>
                  <th className="text-left px-4 py-3">Grade</th>
                  <th className="text-left px-4 py-3">Token · Serial</th>
                  <th className="text-left px-4 py-3">Minted</th>
                  <th className="text-right px-4 py-3">On-chain</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {certs.map((c, idx) => {
                  const g = c.grade || grade(c.score);
                  return (
                    <tr key={c.certificate_id} className="hover:bg-surface-2/50 transition-colors">
                      <td className="px-4 py-3 text-text-muted font-mono text-xs">
                        {String(certs.length - idx).padStart(3, "0")}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/certification/certificate/${c.certificate_id}`}
                          className="text-text-primary font-medium hover:text-purple transition-colors flex items-center gap-2"
                        >
                          <Award className="h-4 w-4 text-purple" />
                          {c.agent_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 font-mono text-text-primary">
                        {Math.round(c.score)}
                        <span className="text-text-muted">/100</span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-xs ${gradeColor(g)}`}
                        >
                          {g}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                        {c.token_id}
                        <span className="text-text-muted"> · #{c.serial_number}</span>
                      </td>
                      <td className="px-4 py-3 text-xs text-text-muted">
                        {new Date(c.minted_at * 1000).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <a
                          href={c.hashscan_tx_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-cyan hover:text-cyan/80"
                        >
                          HashScan <ExternalLink className="h-3 w-3" />
                        </a>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="mt-6 text-xs text-text-muted">
        Certificates are anchored on Hedera testnet. Each mint is signed by the
        HACK operator account and cryptographically bound to its audit report
        via a SHA-256 metadata hash.
      </p>
    </div>
  );
}
