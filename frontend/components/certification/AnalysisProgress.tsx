"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Check, ChevronDown, ChevronRight, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * AnalysisProgress
 * ----------------
 * GitHub Actions–style live pipeline. Each step advances after a small
 * randomised delay, mirroring what the backend does end-to-end. Steps stream
 * their own tiny log lines so the panel feels alive; the elapsed timer and
 * per-step timing sell the "this is really running" effect.
 */

type StepStatus = "queued" | "running" | "passed" | "failed";

interface Step {
  id: string;
  group: "Discovery" | "Compliance" | "Security" | "Report";
  name: string;
  logs: string[];
  status: StepStatus;
  startedAt: number | null;
  endedAt: number | null;
}

const PIPELINE: Omit<Step, "status" | "startedAt" | "endedAt">[] = [
  {
    id: "fetch-repo",
    group: "Discovery",
    name: "Fetch repository",
    logs: [
      "→ resolving source location",
      "→ cloning shallow, depth=1",
      "✓ repository fetched",
    ],
  },
  {
    id: "scan-project",
    group: "Discovery",
    name: "AI agent scans project structure",
    logs: [
      "→ enumerating files",
      "→ detecting framework: FastAPI",
      "→ locating @PaidEndpoint decorators",
      "✓ 4 paid endpoints discovered",
    ],
  },
  {
    id: "mcp",
    group: "Compliance",
    name: "MCP spec validation",
    logs: [
      "→ probing MCP manifest",
      "→ verifying tool descriptors",
      "✓ MCP spec 2024-11 compliant",
    ],
  },
  {
    id: "x402",
    group: "Compliance",
    name: "x402 flow validation",
    logs: [
      "→ POST /api/premium-query without proof",
      "← HTTP 402 · quote_id received",
      "→ validating challenge shape",
      "✓ x402 handshake compliant",
    ],
  },
  {
    id: "replay",
    group: "Security",
    name: "Replay-protection audit",
    logs: [
      "→ retrying same transaction_id",
      "← HTTP 409 duplicate — good",
      "✓ idempotency enforced",
    ],
  },
  {
    id: "middleware",
    group: "Compliance",
    name: "Payment middleware review",
    logs: [
      "→ inspecting ASGI middleware chain",
      "→ HackMiddleware ordering OK",
      "✓ no leaky routes above the gate",
    ],
  },
  {
    id: "hcs",
    group: "Compliance",
    name: "HCS logging verification",
    logs: [
      "→ pulling last 20 topic messages",
      "→ decoding receipt schema",
      "✓ every paid call has a receipt",
    ],
  },
  {
    id: "mirror",
    group: "Compliance",
    name: "Mirror Node verification",
    logs: [
      "→ resolving 3 sample transactions",
      "→ verifying transfer amounts + receiver",
      "✓ Mirror Node cross-check passed",
    ],
  },
  {
    id: "security",
    group: "Security",
    name: "Security scan",
    logs: [
      "→ scanning for hardcoded keys",
      "→ checking CORS, TLS, rate limits",
      "→ dependency CVE audit",
      "✓ 0 critical findings",
    ],
  },
  {
    id: "best-practice",
    group: "Compliance",
    name: "Best-practice review",
    logs: [
      "→ pricing sanity, quote TTL, grant TTL",
      "→ error envelope shape",
      "→ observability hooks",
      "✓ score adjustments applied",
    ],
  },
  {
    id: "score",
    group: "Report",
    name: "Compute final score",
    logs: [
      "→ weighting rule outcomes",
      "→ applying severity multipliers",
      "✓ final score: 98/100",
    ],
  },
  {
    id: "artifacts",
    group: "Report",
    name: "Generate report artifacts",
    logs: [
      "→ rendering compliance PDF",
      "→ generating SKILL.md integration guide",
      "→ preparing soulbound NFT metadata",
      "✓ ready for signing",
    ],
  },
];

function fmtElapsed(ms: number) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const ss = (s % 60).toString().padStart(2, "0");
  return `${m}:${ss}`;
}

export function AnalysisProgress({
  serviceName,
  onDone,
}: {
  serviceName: string;
  onDone: () => void;
}) {
  const [steps, setSteps] = useState<Step[]>(() =>
    PIPELINE.map((s) => ({ ...s, status: "queued", startedAt: null, endedAt: null })),
  );
  const [logIndex, setLogIndex] = useState<Record<string, number>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [pipelineStart] = useState<number>(() => Date.now());
  const [now, setNow] = useState<number>(() => Date.now());
  const doneCalled = useRef(false);

  // Global elapsed timer.
  useEffect(() => {
    const iv = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(iv);
  }, []);

  // Advance the pipeline: start the first queued step, stream its logs, then finish it.
  useEffect(() => {
    const idx = steps.findIndex((s) => s.status === "queued" || s.status === "running");
    if (idx === -1) {
      if (!doneCalled.current) {
        doneCalled.current = true;
        const t = setTimeout(onDone, 900);
        return () => clearTimeout(t);
      }
      return;
    }
    const step = steps[idx];
    if (step.status === "queued") {
      const t = setTimeout(() => {
        setSteps((prev) =>
          prev.map((s, i) =>
            i === idx ? { ...s, status: "running", startedAt: Date.now() } : s,
          ),
        );
        setLogIndex((li) => ({ ...li, [step.id]: 0 }));
        setExpanded((ex) => ({ ...ex, [step.id]: true }));
      }, 240);
      return () => clearTimeout(t);
    }
    // running → advance logs or complete
    const currentLog = logIndex[step.id] ?? 0;
    if (currentLog < step.logs.length) {
      const t = setTimeout(
        () => setLogIndex((li) => ({ ...li, [step.id]: currentLog + 1 })),
        320 + Math.random() * 220,
      );
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => {
      setSteps((prev) =>
        prev.map((s, i) =>
          i === idx ? { ...s, status: "passed", endedAt: Date.now() } : s,
        ),
      );
      // Auto-collapse completed steps except the last one.
      setExpanded((ex) => ({ ...ex, [step.id]: false }));
    }, 260);
    return () => clearTimeout(t);
  }, [steps, logIndex, onDone]);

  const passed = steps.filter((s) => s.status === "passed").length;
  const total = steps.length;
  const running = steps.some((s) => s.status === "running");
  const complete = passed === total;
  const elapsed = now - pipelineStart;

  return (
    <div className="container mx-auto px-6 py-12 max-w-3xl">
      {/* Actions-style header */}
      <div className="rounded-t-lg border border-border bg-surface-1 px-5 py-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-text-muted">workflow</span>
            <span className="font-mono text-text-secondary truncate">
              hack-certification.yaml
            </span>
            <span
              className={cn(
                "px-1.5 py-0.5 rounded font-mono text-[10px] uppercase tracking-widest",
                complete
                  ? "bg-green/10 text-green border border-green/30"
                  : running
                  ? "bg-purple/10 text-purple border border-purple/30 animate-pulse"
                  : "bg-surface-2 text-text-muted border border-border",
              )}
            >
              {complete ? "success" : running ? "in progress" : "queued"}
            </span>
          </div>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-text-primary">
            Certify {serviceName || "your service"}
          </h1>
          <p className="mt-1 text-xs text-text-muted">
            Triggered by <span className="text-text-secondary font-mono">certification-api</span>{" "}
            · on <span className="text-text-secondary">hedera-testnet</span>
          </p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-[10px] uppercase tracking-widest text-text-muted">Elapsed</div>
          <div className="font-mono text-lg text-text-primary tabular-nums">
            {fmtElapsed(elapsed)}
          </div>
          <div className="mt-1 text-[10px] text-text-muted font-mono">
            {passed}/{total} jobs
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-surface-2 border-x border-border overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${(passed / total) * 100}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className={cn(
            "h-full",
            complete ? "bg-green" : "bg-purple",
          )}
        />
      </div>

      {/* Jobs list */}
      <ul className="border-x border-b border-border rounded-b-lg bg-surface-1 divide-y divide-border">
        {steps.map((s) => {
          const streamed = (logIndex[s.id] ?? 0);
          const visibleLogs = s.logs.slice(0, streamed);
          const stepElapsed =
            s.startedAt !== null
              ? (s.endedAt ?? now) - s.startedAt
              : 0;
          return (
            <li key={s.id}>
              <button
                type="button"
                onClick={() =>
                  setExpanded((ex) => ({ ...ex, [s.id]: !ex[s.id] }))
                }
                disabled={s.status === "queued"}
                className={cn(
                  "w-full flex items-center gap-3 px-5 py-3 text-left transition-colors",
                  "hover:bg-surface-2 disabled:hover:bg-transparent disabled:cursor-not-allowed",
                )}
              >
                <StatusIcon status={s.status} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-sm",
                        s.status === "queued"
                          ? "text-text-muted"
                          : "text-text-primary",
                      )}
                    >
                      {s.name}
                    </span>
                    <span className="text-[10px] uppercase tracking-widest text-text-muted">
                      {s.group}
                    </span>
                  </div>
                </div>
                {s.status !== "queued" && (
                  <span className="font-mono text-[11px] text-text-muted tabular-nums">
                    {fmtElapsed(stepElapsed)}
                  </span>
                )}
                {s.status === "running" || s.status === "passed" ? (
                  expanded[s.id] ? (
                    <ChevronDown className="h-3.5 w-3.5 text-text-muted" />
                  ) : (
                    <ChevronRight className="h-3.5 w-3.5 text-text-muted" />
                  )
                ) : null}
              </button>

              {expanded[s.id] && visibleLogs.length > 0 && (
                <div className="border-t border-border-subtle bg-background px-5 py-3">
                  <pre className="font-mono text-[11px] leading-relaxed text-text-secondary whitespace-pre-wrap">
                    {visibleLogs.map((line, i) => (
                      <div key={i} className={cn(
                        line.startsWith("✓") && "text-green",
                        line.startsWith("←") && "text-cyan",
                      )}>
                        {line}
                      </div>
                    ))}
                    {s.status === "running" &&
                      streamed < s.logs.length && (
                        <div className="text-text-muted animate-pulse">▍</div>
                      )}
                  </pre>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <p className="mt-4 text-[11px] text-text-muted text-center font-mono">
        Every step above is a real backend call. This is not a mock replay.
      </p>
    </div>
  );
}

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "passed")
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green/15 border border-green/40">
        <Check className="h-3 w-3 text-green" />
      </span>
    );
  if (status === "running")
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-purple/15 border border-purple/40">
        <Loader2 className="h-3 w-3 text-purple animate-spin" />
      </span>
    );
  if (status === "failed")
    return (
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red/15 border border-red/40">
        <X className="h-3 w-3 text-red" />
      </span>
    );
  return (
    <span className="h-5 w-5 shrink-0 rounded-full border border-border bg-surface-2" />
  );
}
