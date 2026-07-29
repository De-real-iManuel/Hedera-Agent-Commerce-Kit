"use client";
/**
 * SoulboundCertificateCard
 * -------------------------
 * Premium certificate display. The NFT is proof the wallet paid for and
 * passed (or conditionally passed) the HACK compliance certification.
 *
 * Displays every piece of on-chain metadata:
 *   service name · owner wallet · score · grade · HCS topic · HCS receipt
 *   analysis hash · issue date · framework version · payment tx · mint tx
 */

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Share2, Download, FileJson, ExternalLink,
  ShieldCheck, Award, Copy, Check,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { cn } from "@/lib/utils";
import type { SoulboundCertificate } from "@/lib/types";

interface Props {
  cert: SoulboundCertificate;
  reportUrl?: string;
}

const NETWORK = process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet";
const HASHSCAN = process.env.NEXT_PUBLIC_HASHSCAN_BASE ?? `https://hashscan.io/${NETWORK}`;

export function SoulboundCertificateCard({ cert, reportUrl }: Props) {
  const [jsonOpen, setJsonOpen] = useState(false);

  const score = Math.round(cert.score);
  const grade = cert.grade || (score >= 90 ? "A+" : score >= 80 ? "A" : score >= 70 ? "B" : score >= 60 ? "C" : "F");
  const isCertified = score >= 80;
  const isConditional = score >= 60 && score < 80;
  const verdict = isCertified ? "CERTIFIED" : isConditional ? "CONDITIONAL" : "FAILED";

  const accentGradient = isCertified
    ? "from-purple via-cyan to-green"
    : isConditional
    ? "from-amber via-orange-400 to-amber"
    : "from-red/60 via-red/40 to-red/20";

  const verdictStyle = isCertified
    ? "text-green border-green/50 bg-green/10"
    : isConditional
    ? "text-amber border-amber/50 bg-amber/10"
    : "text-red border-red/40 bg-red/10";

  const glowStyle = isCertified
    ? "shadow-[0_0_80px_-10px_rgba(124,58,237,0.3)]"
    : isConditional
    ? "shadow-[0_0_80px_-10px_rgba(251,191,36,0.2)]"
    : "shadow-[0_0_40px_-10px_rgba(239,68,68,0.15)]";

  function handleShare() {
    const url = window.location.href;
    if (navigator.share) {
      void navigator.share({ title: `HACK Certificate — ${cert.agent_name}`, url });
    } else {
      void navigator.clipboard.writeText(url);
    }
  }

  const issueDate = new Date(cert.minted_at * 1000).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div className="min-h-screen bg-[#09090b] px-4 py-10 md:py-16">
      <div className="mx-auto max-w-xl">

        {/* Certificate card */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={cn(
            "rounded-2xl border border-border bg-[#0f0f12] overflow-hidden",
            glowStyle,
          )}
        >
          {/* Gradient accent bar */}
          <div className={cn("h-[3px] w-full bg-gradient-to-r", accentGradient)} />

          {/* Issuer header */}
          <div className="px-6 pt-7 pb-5 text-center border-b border-border/60">
            <div className="flex items-center justify-center gap-2 mb-3">
              <ShieldCheck className="h-5 w-5 text-purple" />
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-purple">
                Hedera Agent Commerce Kit
              </span>
            </div>
            <div className="text-[11px] uppercase tracking-widest text-text-muted">
              Certificate of Compliance
            </div>
            <h1 className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-text-primary font-mono break-all">
              {cert.agent_name}
            </h1>
            {cert.service_endpoint && (
              <div className="mt-1 text-xs text-text-muted font-mono truncate">
                {cert.service_endpoint}
              </div>
            )}
          </div>

          {/* Score + verdict */}
          <div className="px-6 py-7 flex flex-col sm:flex-row items-center gap-6 border-b border-border/60">
            <div className="shrink-0">
              <ScoreRing score={score} size="lg" />
            </div>
            <div className="text-center sm:text-left">
              <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">
                Compliance Verdict
              </div>
              <div className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-mono tracking-widest font-semibold",
                verdictStyle,
              )}>
                <Award className="h-3.5 w-3.5" />
                {verdict} · {grade}
              </div>
              <p className="mt-3 text-xs text-text-secondary leading-relaxed max-w-xs">
                {isCertified
                  ? "This service fully meets HACK x402 compliance requirements. This certificate is permanently anchored on Hedera."
                  : isConditional
                  ? "This service conditionally meets HACK compliance requirements. The certificate is on-chain proof of the audit and payment."
                  : "This service did not meet the certification threshold. The audit record is still anchored on-chain as proof of assessment."}
              </p>
            </div>
          </div>

          {/* NFT proof story */}
          <div className="px-6 py-4 bg-purple/5 border-b border-border/60">
            <div className="text-[10px] uppercase tracking-widest text-purple mb-2">
              On-Chain Proof
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">
              Wallet <span className="font-mono text-text-primary">{cert.recipient_account_id}</span> paid
              for this certification and received this soulbound NFT (Token{" "}
              <a
                href={`${HASHSCAN}/token/${cert.token_id}`}
                target="_blank" rel="noopener noreferrer"
                className="text-cyan hover:underline font-mono"
              >
                {cert.token_id}
              </a>
              , Serial #{cert.serial_number}) as immutable proof of compliance assessment.
            </p>
          </div>

          {/* Metadata grid */}
          <div className="px-6 py-6 grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-5 border-b border-border/60">
            <MetaField label="Service Name"       value={cert.agent_name} mono />
            <MetaField label="Owner Wallet"       value={cert.recipient_account_id} mono copyable />
            <MetaField label="Certification Score" value={`${score}/100 (${grade})`} mono />
            <MetaField label="Certification Level" value={verdict} mono />
            <MetaField label="Issue Date"         value={issueDate} />
            <MetaField label="Framework Version"  value={`HACK v${cert.version}`} />
            <MetaField label="Service Type"       value={(cert.service_type ?? "—").toUpperCase()} mono />
            <MetaField label="NFT Serial"         value={`#${cert.serial_number}`} mono />

            {cert.hcs_topic_id && (
              <MetaField label="HCS Topic" value={cert.hcs_topic_id} mono copyable>
                <a
                  href={`${HASHSCAN}/topic/${cert.hcs_topic_id}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-cyan hover:text-cyan/80 shrink-0"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </MetaField>
            )}

            {cert.hcs_receipt_tx && (
              <MetaField
                label={cert.hcs_sequence_number ? `HCS Message #${cert.hcs_sequence_number}` : "HCS Receipt TX"}
                value={cert.hcs_receipt_tx.slice(0, 20) + "…"}
                mono copyable full={cert.hcs_receipt_tx}
              >
                <a
                  href={
                    // Prefer the direct message link (topic + sequenceNumber) —
                    // this jumps to the exact HCS message that anchors this cert.
                    // Falls back to the submit transaction page.
                    cert.hashscan_hcs_message_url ??
                    (cert.hcs_topic_id && cert.hcs_sequence_number
                      ? `${HASHSCAN}/topic/${cert.hcs_topic_id}?sequenceNumber=${cert.hcs_sequence_number}`
                      : `${HASHSCAN}/transaction/${cert.hcs_receipt_tx}`)
                  }
                  target="_blank" rel="noopener noreferrer"
                  className="text-cyan hover:text-cyan/80 shrink-0"
                  title={cert.hcs_sequence_number ? `View HCS message #${cert.hcs_sequence_number} on HashScan` : "View HCS submit transaction"}
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </MetaField>
            )}

            <MetaField
              label="Analysis Hash"
              value={cert.metadata_hash.slice(0, 20) + "…"}
              mono copyable full={cert.metadata_hash}
            />

            {cert.payment_transaction_id && (
              <MetaField label="Payment TX" value={cert.payment_transaction_id.slice(0, 20) + "…"} mono copyable full={cert.payment_transaction_id}>
                <a
                  href={cert.hashscan_payment_url ?? `${HASHSCAN}/transaction/${cert.payment_transaction_id}`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-cyan hover:text-cyan/80 shrink-0"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </MetaField>
            )}

            {cert.mint_transaction_id && (
              <MetaField label="Mint TX" value={cert.mint_transaction_id.slice(0, 20) + "…"} mono copyable full={cert.mint_transaction_id}>
                <a
                  href={cert.hashscan_tx_url}
                  target="_blank" rel="noopener noreferrer"
                  className="text-cyan hover:text-cyan/80 shrink-0"
                >
                  <ExternalLink className="h-3 w-3" />
                </a>
              </MetaField>
            )}

            <MetaField label="Transferable" value="No — Soulbound" />
            <MetaField label="Network"      value={`Hedera ${NETWORK}`} />
          </div>

          {/* HashScan CTA */}
          {cert.hashscan_tx_url && (
            <div className="px-6 py-4 flex items-center justify-between border-b border-border/60">
              <span className="text-xs text-text-muted">Verify on Hedera HashScan</span>
              <a
                href={cert.hashscan_tx_url}
                target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-cyan hover:text-cyan/80 font-mono"
              >
                View NFT Mint <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}

          {/* Footer */}
          <div className="px-6 py-4 bg-surface-2/30 text-center">
            <p className="text-[10px] text-text-muted leading-relaxed">
              This soulbound certificate is a permanent on-chain record of compliance analysis
              conducted through the Hedera Agent Commerce Kit. It is non-transferable and
              not a financial instrument. Issued on Hedera {NETWORK}.
            </p>
          </div>
        </motion.div>

        {/* Action row */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.4 }}
          className="mt-5 flex flex-wrap gap-2 justify-center"
        >
          <Button variant="ghost" size="sm" onClick={handleShare}>
            <Share2 className="h-3.5 w-3.5" /> Share
          </Button>
          <Button variant="ghost" size="sm" onClick={() => window.print()}>
            <Download className="h-3.5 w-3.5" /> Save PDF
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setJsonOpen(o => !o)}>
            <FileJson className="h-3.5 w-3.5" /> {jsonOpen ? "Hide" : "View"} JSON
          </Button>
          {reportUrl && (
            <a
              href={reportUrl}
              className="inline-flex items-center gap-1.5 h-8 px-3 text-xs rounded-md border border-border text-text-secondary hover:text-text-primary hover:border-purple/50 transition-colors"
            >
              ← Full Report
            </a>
          )}
        </motion.div>

        {/* JSON drawer */}
        {jsonOpen && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4"
          >
            <CodeBlock
              code={JSON.stringify(cert, null, 2)}
              language="json"
              filename="certificate.json"
            />
          </motion.div>
        )}
      </div>
    </div>
  );
}

// ── Keep old export alias so any existing imports don't break ─────────────────
export { SoulboundCertificateCard as SoulboundCertificate };

// ─── MetaField ────────────────────────────────────────────────────────────────

function CopyInline({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  function handle() {
    void navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return (
    <button
      onClick={handle}
      className="shrink-0 text-text-muted hover:text-text-primary transition-colors"
      aria-label="Copy"
    >
      {copied
        ? <Check className="h-3 w-3 text-green" />
        : <Copy className="h-3 w-3" />}
    </button>
  );
}

function MetaField({
  label, value, mono, copyable, full, children,
}: {
  label: string;
  value: string;
  mono?: boolean;
  copyable?: boolean;
  full?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="min-w-0">
      <div className="text-[10px] uppercase tracking-widest text-text-muted mb-0.5">
        {label}
      </div>
      <div className={cn(
        "flex items-center gap-1.5 text-xs text-text-primary break-all",
        mono && "font-mono",
      )}>
        <span className="truncate">{value}</span>
        {copyable && <CopyInline value={full ?? value} />}
        {children}
      </div>
    </div>
  );
}
