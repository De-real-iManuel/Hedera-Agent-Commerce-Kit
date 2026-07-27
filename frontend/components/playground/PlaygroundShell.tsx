"use client";
import { useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Play, ShieldAlert, AlertTriangle } from "lucide-react";
import { EndpointPanel } from "./EndpointPanel";
import { NetworkPanel, type NetworkEvent } from "./NetworkPanel";
import { PaymentFlowModal } from "./PaymentFlowModal";
import { ChallengeCard, VerifyCard } from "./ResponseViewer";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Button } from "@/components/ui/Button";
import { ENDPOINT_GROUPS, type EndpointDef } from "./endpoints";
import { isApiError } from "@/lib/api";
import type { ChallengeResponse, VerifyResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const ALL_ENDPOINTS = ENDPOINT_GROUPS.flatMap((g) => g.endpoints);

type ResponseState =
  | { kind: "challenge"; status?: number; data: ChallengeResponse; error?: string }
  | { kind: "verify"; status?: number; data: VerifyResponse; error?: string }
  | { kind: "raw"; status?: number; data: unknown; error?: string }
  | null;

export function PlaygroundShell() {
  const [activeId, setActiveId] = useState("challenge");
  const active = useMemo(
    () => ALL_ENDPOINTS.find((e) => e.id === activeId) || ALL_ENDPOINTS[0],
    [activeId],
  );
  const [tab,      setTab]      = useState<"body" | "headers">("body");
  const [body,     setBody]     = useState<string>(active.defaultBody || "{}");
  const [response, setResponse] = useState<ResponseState>(null);
  const [loading,   setLoading]  = useState(false);
  const [payModal,  setPayModal] = useState(false);
  const [proof,     setProof]    = useState<{ quote_id: string; transaction_id: string } | null>(null);
  const [events,    setEvents]   = useState<NetworkEvent[]>([]);

  function pushEvent(kind: NetworkEvent["kind"], message: string) {
    setEvents((prev) => [
      { id: Math.random().toString(36).slice(2), kind, message, at: Date.now() },
      ...prev,
    ]);
  }

  function onSelect(e: EndpointDef) {
    setActiveId(e.id);
    setBody(e.defaultBody || "{}");
    setResponse(null);
  }

  async function send() {
    setLoading(true);
    setResponse(null);
    pushEvent("http", `${active.method} ${active.path}`);

    const path = active.path.replace("{quote_id}", proof?.quote_id ?? "");
    const url  = `${BASE}${path}`;

    try {
      const res = await fetch(url, {
        method: active.method,
        headers: {
          "Content-Type": "application/json",
          ...(proof && active.x402
            ? { "X-Quote-Id": proof.quote_id, "X-Payment-Token": proof.transaction_id }
            : {}),
        },
        body: active.method === "POST" ? body : undefined,
      });

      const data = await res.json().catch(() => null);
      pushEvent(res.ok ? "http" : "error", `${res.status} ${active.path}`);

      if (res.status === 402 || active.id === "challenge") {
        setResponse({ kind: "challenge", status: res.status, data: data as ChallengeResponse });
      } else if (active.id === "verify") {
        if (res.ok) {
          pushEvent("mirror",   "Mirror Node confirmed transfer");
          pushEvent("transfer", "HBAR transfer verified");
          pushEvent("hcs",      "HCS receipt published");
        }
        setResponse({ kind: "verify", status: res.status, data: data as VerifyResponse });
      } else {
        setResponse({ kind: "raw", status: res.status, data });
      }
    } catch (err) {
      const msg = isApiError(err)
        ? err.message
        : "Cannot reach the HACK backend. Run ./scripts/start-backend.sh first.";
      pushEvent("error", msg);
      setResponse({ kind: "raw", status: 0, data: null, error: msg });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-56px)]">
      <EndpointPanel active={active.id} onSelect={onSelect} />

      <section className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* URL bar */}
        <div className="border-b border-border bg-surface-1 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className={cn(
              "font-mono text-[10px] px-2 py-1 rounded border",
              active.method === "GET"
                ? "text-cyan border-cyan/40 bg-cyan/10"
                : "text-purple border-purple/40 bg-purple/10",
            )}>{active.method}</span>
            <input
              readOnly
              value={`${BASE}${active.path}`}
              className="flex-1 bg-transparent font-mono text-sm text-text-primary focus:outline-none"
            />
            <Button onClick={send} size="sm" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Send
            </Button>
          </div>
          <p className="mt-2 text-xs text-text-secondary">{active.description}</p>

          {active.x402 && !proof && (
            <div className="mt-4 rounded-md border border-amber/40 bg-amber/5 px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-amber">
                <ShieldAlert className="h-4 w-4" />
                This endpoint requires x402 payment.
              </div>
              <Button size="sm" variant="ghost" onClick={() => setPayModal(true)}>
                Go through payment flow →
              </Button>
            </div>
          )}
          {active.x402 && proof && (
            <div className="mt-4 rounded-md border border-green/40 bg-green/5 px-4 py-2 flex items-center justify-between text-xs">
              <span className="text-green">
                Grant active · quote {proof.quote_id.slice(0, 8)}…
              </span>
              <button onClick={() => setProof(null)} className="text-text-muted hover:text-text-primary">
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Request body / headers */}
        {active.method === "POST" && (
          <div className="border-b border-border bg-surface-1">
            <div className="flex gap-4 px-6 border-b border-border-subtle">
              {(["body", "headers"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "py-2 text-xs uppercase tracking-widest transition-colors border-b-2 -mb-px",
                    tab === t
                      ? "border-purple text-text-primary"
                      : "border-transparent text-text-muted hover:text-text-secondary",
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="p-4">
              {tab === "body" ? (
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full min-h-[140px] rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-text-primary focus:outline-none focus:border-purple/60"
                />
              ) : (
                <pre className="rounded-md border border-border bg-background px-3 py-2 font-mono text-xs text-text-secondary">
                  {JSON.stringify({ "Content-Type": "application/json" }, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}

        {/* Response panel */}
        <div className="flex-1 p-6 space-y-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[10px] uppercase tracking-widest text-text-muted">Response</span>
            {response?.status != null && response.status > 0 && (
              <span className={cn(
                "font-mono px-2 py-0.5 rounded border",
                response.status === 402
                  ? "text-amber border-amber/40 bg-amber/10"
                  : response.status >= 400
                  ? "text-red border-red/40 bg-red/10"
                  : "text-green border-green/40 bg-green/10",
              )}>
                {response.status}
              </span>
            )}
          </div>

          <AnimatePresence mode="wait">
            {!response && (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="rounded-lg border border-dashed border-border p-8 text-sm text-text-muted"
              >
                No response yet. Hit <span className="text-text-primary">Send</span> to run this endpoint.
              </motion.div>
            )}

            {response?.error && (
              <motion.div
                key="err"
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="rounded-lg border border-red/40 bg-red/5 px-5 py-4 flex items-start gap-3"
              >
                <AlertTriangle className="h-5 w-5 text-red mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-medium text-red">Request failed</div>
                  <div className="mt-1 text-xs text-text-secondary">{response.error}</div>
                </div>
              </motion.div>
            )}

            {response?.kind === "challenge" && response.data && (
              <motion.div key="ch" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <ChallengeCard data={response.data} />
              </motion.div>
            )}

            {response?.kind === "verify" && response.data && (
              <motion.div key="v" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <VerifyCard data={response.data} />
              </motion.div>
            )}

            {response?.kind === "raw" && Boolean(response.data) && (
              <motion.div key="r" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <CodeBlock
                  code={JSON.stringify(response.data, null, 2)}
                  language="json"
                  filename={`response ${response.status ?? ""}`}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      <NetworkPanel events={events} />

      <PaymentFlowModal
        open={payModal}
        onClose={() => setPayModal(false)}
        onComplete={(p) => {
          setProof(p);
          setPayModal(false);
          pushEvent("http", "Grant window opened");
        }}
      />
    </div>
  );
}
