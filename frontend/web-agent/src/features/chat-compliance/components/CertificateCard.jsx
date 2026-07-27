"use client";
import { Card } from "@/components/ui/card";

export function CertificateCard({ output }) {
  const raw = output?.raw;
  if (!raw || raw.status !== "CERTIFICATE_MINTED") return null;
  const c = raw.certificate || {};
  const tokenId = c.token_id || c.tokenId;
  const serial = c.serial_number ?? c.serial;
  const txId = c.transaction_id || c.transactionId;
  const recipient = c.recipient_account_id || c.recipient;
  const reportId = c.report_id;
  const network = c.network || "testnet";

  const hashScanTx = txId
    ? `https://hashscan.io/${network}/transaction/${encodeURIComponent(txId)}`
    : null;
  const hashScanToken = tokenId
    ? `https://hashscan.io/${network}/token/${encodeURIComponent(tokenId)}`
    : null;

  return (
    <Card className="relative overflow-hidden border-purple-500/40 bg-gradient-to-br from-neutral-950 via-purple-950/20 to-neutral-950">
      <div className="absolute -right-16 -top-16 h-40 w-40 rounded-full bg-purple-500/20 blur-3xl" />
      <div className="relative p-5">
        <div className="flex items-center gap-2">
          <span className="rounded-md border border-purple-500/40 bg-purple-500/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-purple-300">
            Soulbound
          </span>
          <span className="text-[10px] uppercase tracking-wider text-neutral-500">
            Hedera · {network}
          </span>
        </div>
        <div className="mt-2 text-lg font-semibold text-neutral-50">
          HACK Compliance Certificate
        </div>
        <div className="mt-1 text-xs text-neutral-400">
          Non-transferable NFT bound to report{" "}
          <span className="font-mono text-neutral-300">{reportId || "—"}</span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 font-mono text-xs">
          <div className="text-neutral-500">Token ID</div>
          <div className="truncate text-neutral-100">{tokenId || "—"}</div>
          <div className="text-neutral-500">Serial</div>
          <div className="text-neutral-100">{serial ?? "—"}</div>
          <div className="text-neutral-500">Recipient</div>
          <div className="truncate text-neutral-100">{recipient || "—"}</div>
          <div className="text-neutral-500">TX</div>
          <div className="truncate text-neutral-100">{txId || "—"}</div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {hashScanTx && (
            <a
              className="rounded-md border border-neutral-800 bg-neutral-900 px-2.5 py-1 text-[11px] text-neutral-200 hover:border-neutral-700"
              href={hashScanTx}
              target="_blank"
              rel="noreferrer"
            >
              View TX on HashScan ↗
            </a>
          )}
          {hashScanToken && (
            <a
              className="rounded-md border border-neutral-800 bg-neutral-900 px-2.5 py-1 text-[11px] text-neutral-200 hover:border-neutral-700"
              href={hashScanToken}
              target="_blank"
              rel="noreferrer"
            >
              View token ↗
            </a>
          )}
          {reportId && (
            <a
              className="rounded-md border border-purple-500/40 bg-purple-500/10 px-2.5 py-1 text-[11px] text-purple-200 hover:bg-purple-500/20"
              href={`/certification/certificate/${encodeURIComponent(reportId)}`}
              target="_blank"
              rel="noreferrer"
            >
              Open certificate page ↗
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}

export function CertificateRow({ output }) {
  const c = output?.raw?.certificate || {};
  return <span className="text-purple-300">Cert · {c.token_id || "minted"}</span>;
}
