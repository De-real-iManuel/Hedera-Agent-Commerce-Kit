"use client";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { HashScanLink, HCSTopicBadge } from "@/components/ui/HashScanLink";
import { CopyButton } from "@/components/ui/CopyButton";
import { formatHBAR, formatDuration } from "@/lib/utils";
import type { ChallengeResponse, VerifyResponse } from "@/lib/types";
import { useEffect, useState } from "react";

export function ChallengeCard({ data }: { data: ChallengeResponse }) {
  const [now, setNow] = useState(Math.floor(Date.now() / 1000));
  useEffect(() => {
    const i = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => clearInterval(i);
  }, []);
  const remaining = data.expires_at - now;
  return (
    <div className="rounded-lg border border-amber/30 bg-amber/5 p-5">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-amber">Payment Challenge · 402</h4>
        <StatusBadge status="quoted" />
      </div>
      <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <Row label="Quote ID" value={data.quote_id} copy />
        <Row label="Receiver" value={data.receiver} copy />
        <Row label="Amount" value={formatHBAR(data.amount_hbar)} />
        <Row label="Expires" value={formatDuration(remaining)} accent={remaining < 60 ? "amber" : "muted"} />
        <Row label="Memo" value={data.memo} />
        <Row label="Network" value={data.network} />
      </dl>
    </div>
  );
}

export function VerifyCard({ data }: { data: VerifyResponse }) {
  const [now, setNow] = useState(Math.floor(Date.now() / 1000));
  useEffect(() => {
    const i = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 1000);
    return () => clearInterval(i);
  }, []);
  const remaining = data.grant_expires_at - now;
  return (
    <div className="rounded-lg border border-green/30 bg-green/5 p-5">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-green">Payment Verified</h4>
        <StatusBadge status={data.state} />
      </div>
      <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <Row label="Transaction" value={data.transaction_id} copy />
        <Row label="Grant window" value={formatDuration(remaining)} />
        <div className="col-span-full flex items-center gap-3 text-xs">
          <HCSTopicBadge topicId={
            (data.receipt as any)?.hcs_topic_id ??
            (data.receipt as any)?.topic_id ?? ""
          } />
          <HashScanLink txId={data.transaction_id} label="View on HashScan" />
        </div>
      </dl>
      {data.receipt && (
        <details className="mt-4">
          <summary className="text-xs text-text-muted cursor-pointer hover:text-text-primary">
            Show receipt payload
          </summary>
          <div className="mt-2">
            <CodeBlock
              code={JSON.stringify(data.receipt, null, 2)}
              language="json"
            />
          </div>
        </details>
      )}
    </div>
  );
}

function Row({
  label, value, copy, accent,
}: { label: string; value: string; copy?: boolean; accent?: "amber" | "muted" }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-widest text-text-muted">{label}</dt>
      <dd className="mt-0.5 flex items-center gap-2">
        <span
          className={
            accent === "amber"
              ? "font-mono text-sm text-amber"
              : accent === "muted"
              ? "font-mono text-sm text-text-muted"
              : "font-mono text-sm text-text-primary break-all"
          }
        >
          {value}
        </span>
        {copy && <CopyButton value={value} className="shrink-0" />}
      </dd>
    </div>
  );
}
