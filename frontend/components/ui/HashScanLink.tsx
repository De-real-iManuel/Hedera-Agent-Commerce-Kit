import { ExternalLink } from "lucide-react";
import { hashScanTxUrl, hashScanTopicUrl, formatTxId } from "@/lib/utils";
import { cn } from "@/lib/utils";

export function HashScanLink({
  txId,
  className,
  label,
}: {
  txId: string;
  className?: string;
  label?: string;
}) {
  return (
    <a
      href={hashScanTxUrl(txId)}
      target="_blank"
      rel="noreferrer"
      className={cn(
        "inline-flex items-center gap-1 text-cyan hover:text-cyan/80 transition-colors",
        className,
      )}
    >
      {label || `View on HashScan`}
      <ExternalLink className="h-3 w-3" />
      {!label && <span className="font-mono text-xs text-text-muted">({formatTxId(txId)})</span>}
    </a>
  );
}

export function HCSTopicBadge({ topicId, className }: { topicId: string; className?: string }) {
  return (
    <a
      href={hashScanTopicUrl(topicId)}
      target="_blank"
      rel="noreferrer"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-cyan/40 bg-cyan/10 px-2.5 py-0.5 font-mono text-[11px] text-cyan hover:bg-cyan/15 transition-colors",
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-cyan animate-pulse" />
      HCS · {topicId}
      <ExternalLink className="h-3 w-3" />
    </a>
  );
}
