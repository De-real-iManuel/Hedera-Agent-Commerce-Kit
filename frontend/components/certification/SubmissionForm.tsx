"use client";
/**
 * SubmissionForm — real service-audit flow.
 *
 * Order of operations:
 *   1. user fills form → click Analyze
 *   2. api.submitAudit(...)             → { quote_id, receiver, amount, memo, expires_at }
 *   3. WalletConnect modal opens
 *   4. PaymentGate opens with the pre-issued challenge, user pays HBAR
 *   5. PaymentGate returns { quote_id, transaction_id }
 *   6. AnalysisProgress mounts; in parallel we call api.runAudit(quote_id, tx_id)
 *      (backend blocks ~15-30 s while probes + LLM run)
 *   7. On success → router.push(`/certification/{report_id}`)
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Check, ShieldCheck, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { FadeUp } from "@/components/ui/Motion";
import { AnalysisProgress } from "./AnalysisProgress";
import { api, isApiError } from "@/lib/api";
import type { CertificationSubmission, AuditSubmitResponse } from "@/lib/types";

// Wallet-dependent components use the Hedera SDK (Node.js-only packages).
// Dynamic import with ssr:false keeps them out of the webpack client bundle
// entirely — they are loaded in the browser only when actually needed.
const PaymentGate = dynamic(
  () => import("./PaymentGate").then((m) => m.PaymentGate),
  { ssr: false },
);
const WalletConnectModal = dynamic(
  () => import("./WalletConnectModal").then((m) => m.WalletConnectModal),
  { ssr: false },
);

const CHECKS = [
  {
    title: "Payment Flow",
    items: [
      "HTTP 402 challenge",
      "Challenge shape",
      "x-402 protocol headers",
      "Replay rejection",
      "Latency",
    ],
  },
  {
    title: "Security & Verification",
    items: ["Mirror Node verification", "Replay protection", "Hardcoded secrets"],
  },
  {
    title: "Architecture",
    items: ["x402 middleware", "HCS receipts", "Repo source scan"],
  },
];

export function SubmissionForm() {
  const router = useRouter();
  const [form, setForm] = useState<CertificationSubmission>({
    service_name: "",
    service_type: "mcp",
    repo_url: "",
    openapi_url: "",
    primary_endpoint: "",
    description: "",
    source_code: "",
  });
  const [challenge, setChallenge] = useState<AuditSubmitResponse | null>(null);
  const [walletOpen, setWalletOpen] = useState(false);
  const [gateOpen, setGateOpen] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [proof, setProof] = useState<{ quote_id: string; transaction_id: string } | null>(null);

  function update<K extends keyof CertificationSubmission>(
    k: K, v: CertificationSubmission[K],
  ) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const canSubmit =
    form.service_name.trim().length > 1 &&
    form.primary_endpoint.trim().length > 4;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitError(null);
    try {
      const c = await api.submitAudit(form);
      setChallenge(c);
      setWalletOpen(true);
    } catch (err) {
      setSubmitError(
        isApiError(err)
          ? `Backend rejected the submission: ${err.message} (${err.status}).`
          : "Could not reach the HACK backend. Run the demo server on :8000.",
      );
    }
  }

  function onWalletConnected(_accountId: string) {
    setWalletOpen(false);
    setGateOpen(true);
  }

  function onPaymentComplete(p: { quote_id: string; transaction_id: string }) {
    setProof(p);
    setGateOpen(false);
    setAnalyzing(true);
    // Fire the real audit; the AnalysisProgress UI plays visuals in parallel.
    void runAudit(p);
  }

  async function runAudit(p: { quote_id: string; transaction_id: string }) {
    try {
      const res = await api.runAudit(p.quote_id, p.transaction_id);
      // wait a beat so the AnalysisProgress animation reaches its final state
      setTimeout(() => {
        router.push(`/certification/${res.report.report_id}`);
      }, 600);
    } catch (err) {
      setSubmitError(
        isApiError(err)
          ? `Audit failed: ${err.message} (${err.status}).`
          : "The audit could not complete. Check the backend logs.",
      );
      setAnalyzing(false);
    }
  }

  if (analyzing) {
    return (
      <AnalysisProgress
        serviceName={form.service_name}
        onDone={() => {/* navigation is triggered by runAudit's success handler */}}
      />
    );
  }

  if (gateOpen && challenge) {
    return (
      <PaymentGate
        serviceName={form.service_name}
        onComplete={onPaymentComplete}
        onCancel={() => setGateOpen(false)}
        preIssuedChallenge={{
          quote_id: challenge.quote_id,
          receiver: challenge.receiver,
          amount_hbar: challenge.amount_hbar,
          memo: challenge.memo,
          expires_at: challenge.expires_at,
        }}
      />
    );
  }

  return (
    <div className="container mx-auto px-6 py-16">
      <FadeUp className="max-w-3xl">
        <div className="text-xs uppercase tracking-widest text-purple">Flagship Demo</div>
        <h1 className="mt-2 text-4xl md:text-5xl font-bold tracking-tight">
          AI Agent Compliance Certification
        </h1>
        <p className="mt-4 text-lg text-text-secondary max-w-2xl">
          Submit your MCP server, API, or agent for automated x402 compliance
          analysis. Every certification is paid via HACK and anchored on Hedera —
          the passing report mints a soulbound NFT.
        </p>
      </FadeUp>

      {submitError && (
        <div className="mt-6 max-w-3xl rounded-md border border-red/40 bg-red/5 px-4 py-3 flex items-start gap-3 text-sm text-red">
          <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
          {submitError}
        </div>
      )}

      <form onSubmit={onSubmit} className="mt-12 grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-10">
        <FadeUp delay={0.1} className="space-y-4">
          <Field label="Service Name" required>
            <input value={form.service_name}
              onChange={(e) => update("service_name", e.target.value)}
              placeholder="my-mcp-server" className={inputCls} />
          </Field>
          <Field label="Service Type">
            <select value={form.service_type}
              onChange={(e) => update("service_type", e.target.value as CertificationSubmission["service_type"])}
              className={inputCls}>
              <option value="mcp">MCP Server</option>
              <option value="fastapi">FastAPI API</option>
              <option value="agent">Agent</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="GitHub Repository URL" hint="optional — enables static repo scan">
            <input value={form.repo_url}
              onChange={(e) => update("repo_url", e.target.value)}
              placeholder="https://github.com/…" className={inputCls} />
          </Field>
          <Field
            label="Paste Source Code"
            hint={form.repo_url?.trim() ? "repo URL takes priority" : "optional — paste your main file instead of a GitHub URL"}
          >
            <textarea
              value={form.source_code ?? ""}
              onChange={(e) => update("source_code", e.target.value)}
              rows={6}
              placeholder={"# Paste your main.py, index.js, server.ts…\n# Static analysis runs on this when no GitHub URL is provided."}
              className={`${inputCls} font-mono text-xs resize-y`}
              disabled={!!form.repo_url?.trim()}
            />
          </Field>
          <Field label="Primary Endpoint URL" required
            hint={form.service_type === "mcp" ? "use SSE transport: python server.py --transport sse --port 9000 → http://localhost:9000" : "the URL your service is deployed at"}>
            <input value={form.primary_endpoint}
              onChange={(e) => update("primary_endpoint", e.target.value)}
              placeholder={form.service_type === "mcp" ? "http://localhost:9000" : "https://my-service.example.com/api/…"}
              className={inputCls} />
          </Field>
          <Field label="Description" hint="optional">
            <textarea value={form.description}
              onChange={(e) => update("description", e.target.value)}
              rows={3} placeholder="What does this service do?" className={inputCls} />
          </Field>
          <div className="pt-2">
            <Button type="submit" size="lg" className="w-full" disabled={!canSubmit}>
              <ShieldCheck className="h-4 w-4" />
              Analyze Service →
            </Button>
            <div className="mt-3 rounded-md border border-border bg-surface-1 px-4 py-3 text-xs text-text-secondary flex flex-wrap items-center justify-between gap-2">
              <span><span className="text-text-primary font-mono">0.5 HBAR</span> per analysis</span>
              <span>· Verified on Hedera testnet</span>
              <span>· Soulbound NFT on pass</span>
            </div>
          </div>
        </FadeUp>

        <FadeUp delay={0.2}>
          <div className="rounded-lg border border-border bg-surface-1 p-6">
            <div className="text-xs uppercase tracking-widest text-text-muted">What gets checked</div>
            <div className="mt-4 space-y-6">
              {CHECKS.map((c) => (
                <div key={c.title}>
                  <div className="text-sm font-semibold text-text-primary">{c.title}</div>
                  <ul className="mt-2 space-y-1">
                    {c.items.map((it) => (
                      <li key={it} className="flex items-center gap-2 text-sm text-text-secondary">
                        <Check className="h-4 w-4 text-green" />{it}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </FadeUp>
      </form>

      <WalletConnectModal open={walletOpen}
        onClose={() => setWalletOpen(false)} onConnected={onWalletConnected} />
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-border bg-surface-1 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-purple/60 transition-colors";

function Field({ label, hint, required, children }: {
  label: string; hint?: string; required?: boolean; children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-xs uppercase tracking-widest text-text-muted">
          {label} {required && <span className="text-purple">*</span>}
        </span>
        {hint && <span className="text-[10px] text-text-muted">{hint}</span>}
      </div>
      {children}
    </label>
  );
}
