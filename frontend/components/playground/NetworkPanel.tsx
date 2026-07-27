"use client";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { ENV } from "@/lib/env";

export interface NetworkEvent {
  id: string;
  kind: "mirror" | "transfer" | "hcs" | "http" | "error";
  message: string;
  at: number; // ms timestamp
}

const KIND_STYLES: Record<NetworkEvent["kind"], { dot: string; label: string }> = {
  mirror:   { dot: "bg-cyan",   label: "Mirror"   },
  transfer: { dot: "bg-green",  label: "Transfer" },
  hcs:      { dot: "bg-purple", label: "HCS"      },
  http:     { dot: "bg-green",  label: "HTTP"     },
  error:    { dot: "bg-red",    label: "Error"    },
};

const NETWORK     = process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet";
const MIRROR_HOST = NETWORK === "mainnet"
  ? "mainnet-public.mirrornode.hedera.com"
  : "testnet.mirrornode.hedera.com";
const HASHSCAN_BASE = process.env.NEXT_PUBLIC_HASHSCAN_BASE ?? `https://hashscan.io/${NETWORK}`;

export function NetworkPanel({ events }: { events: NetworkEvent[] }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const i = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(i);
  }, []);

  return (
    <aside className="w-[340px] shrink-0 border-l border-border bg-surface-1 overflow-y-auto">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="text-[10px] uppercase tracking-widest text-text-muted">
          Network activity
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-green">
          <span className="h-1.5 w-1.5 rounded-full bg-green animate-pulse" /> live
        </div>
      </div>

      {/* Events feed */}
      <ol className="p-3 space-y-2">
        {events.length === 0 && (
          <li className="rounded-md border border-dashed border-border p-4 text-xs text-text-muted">
            No traffic yet. Fire a request from the center panel.
          </li>
        )}
        {events.map((e) => {
          const s   = KIND_STYLES[e.kind];
          const ago = Math.max(0, Math.floor((now - e.at) / 1000));
          return (
            <li
              key={e.id}
              className="rounded-md border border-border-subtle bg-surface-2 px-3 py-2 text-xs flex items-center gap-2"
            >
              <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", s.dot)} />
              <span className="text-text-muted font-mono w-[54px] shrink-0">{s.label}</span>
              <span className="text-text-primary flex-1 truncate">{e.message}</span>
              <span className="text-text-muted shrink-0">{ago}s ago</span>
            </li>
          );
        })}
      </ol>

      {/* Hedera info — all values from env, no hardcoded IDs */}
      <div className="p-4 mt-2 border-t border-border">
        <div className="text-[10px] uppercase tracking-widest text-text-muted">Hedera</div>
        <dl className="mt-3 space-y-2 text-xs">
          <div className="flex justify-between">
            <dt className="text-text-muted">Network</dt>
            <dd className="font-mono text-text-primary">{ENV.network}</dd>
          </div>
          {ENV.paymentReceiver && (
            <div className="flex justify-between gap-2">
              <dt className="text-text-muted">Receiver</dt>
              <dd className="font-mono text-purple truncate">{ENV.paymentReceiver}</dd>
            </div>
          )}
          {ENV.hcsTopicId && (
            <div className="flex justify-between gap-2">
              <dt className="text-text-muted">HCS Topic</dt>
              <dd className="font-mono text-cyan truncate">
                <a
                  href={`${ENV.hashscanBase}/topic/${ENV.hcsTopicId}`}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-cyan/80"
                >
                  {ENV.hcsTopicId} ↗
                </a>
              </dd>
            </div>
          )}
          <div className="flex justify-between gap-2">
            <dt className="text-text-muted">Mirror Node</dt>
            <dd className="font-mono text-text-secondary truncate">{ENV.mirrorNodeHost}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-muted">Backend</dt>
            <dd className="font-mono text-text-secondary truncate">{ENV.apiBase}</dd>
          </div>
        </dl>
        <a
          href={ENV.hashscanBase}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-flex text-xs text-purple hover:text-purple/80"
        >
          Open HashScan ↗
        </a>
      </div>
    </aside>
  );
}
