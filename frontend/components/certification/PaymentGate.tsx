"use client";
/**
 * PaymentGate — real x402 payment flow.
 *
 * Two entry modes:
 *   • preIssuedChallenge  — SubmissionForm has already called /api/audit/submit
 *                           and passes {quote_id, receiver, amount, memo, expires_at}.
 *   • otherwise           — the gate calls /api/payment/challenge itself.
 *
 * Verification path is always the same:
 *   connect wallet if needed → sendHbar via real WalletConnect/Reown SDK
 *   → poll /api/payment/verify with Mirror Node lag retry
 *   → onComplete({quote_id, transaction_id}).
 *
 * No hardcoded accounts. No mock fallbacks.
 */

import { useState, useEffect } from "react";
import { Loader2, Check, AlertTriangle, ExternalLink, Wallet } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { CopyButton } from "@/components/ui/CopyButton";
import { useWalletConnect } from "@/hooks/useWalletConnect";
import { api, isApiError, API_BASE } from "@/lib/api";
import { formatDuration } from "@/lib/utils";

type Step = "loading" | "ready" | "sending" | "verifying" | "done" | "error";

interface Challenge {
  quote_id: string;
  receiver: string;
  amount_hbar: number;
  memo: string;
  expires_at: number;
}

interface PaymentGateProps {
  serviceName: string;
  onComplete: (proof: { quote_id: string; transaction_id: string }) => void;
  onCancel: () => void;
  /** Optional: skip /api/payment/challenge when the caller already has one. */
  preIssuedChallenge?: Challenge;
}

export function PaymentGate({
  serviceName,
  onComplete,
  onCancel,
  preIssuedChallenge,
}: PaymentGateProps) {
  const [step, setStep] = useState<Step>(preIssuedChallenge ? "ready" : "loading");
  const [challenge, setChallenge] = useState<Challenge | null>(preIssuedChallenge ?? null);
  const [txId, setTxId] = useState("");
  const [manualMode, setManualMode] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [verifyResult, setVerifyResult] = useState<{
    hcs_status: string;
    hashscan_url: string;
  } | null>(null);

  const {
    accountId,
    isConnected,
    isPending: walletPending,
    connect,
    sendHbar,
    error: walletError,
  } = useWalletConnect();

  useEffect(() => {
    if (!preIssuedChallenge) void fetchChallenge();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchChallenge() {
    setStep("loading");
    setErrorMsg("");
    try {
      const data = await api.challenge({ resource_path: "/api/premium-query" });
      setChallenge({
        quote_id: data.quote_id,
        receiver: data.receiver,
        amount_hbar: data.amount_hbar,
        memo: data.memo,
        expires_at: data.expires_at,
      });
      setStep("ready");
    } catch (err) {
      setErrorMsg(
        isApiError(err)
          ? `${err.message} (${err.status})`
          : "Could not reach the HACK backend. Start the demo server on :8000.",
      );
      setStep("error");
    }
  }

  async function handleWalletPay() {
    if (!challenge) return;
    setStep("sending");
    setErrorMsg("");
    try {
      if (!isConnected) {
        await connect();
      }

      const result = await sendHbar({
        recipientAccountId: challenge.receiver,
        amount: challenge.amount_hbar,
        memo: challenge.memo,
      });

      setTxId(result);
      await runVerify(result);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : walletError ?? "Wallet transaction failed. Try manual entry instead.";
      setErrorMsg(message);
      setStep("error");
    }
  }

  async function runVerify(id: string) {
    if (!challenge) return;
    setStep("verifying");
    const MAX_RETRIES = 5;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      if (attempt > 0) await new Promise((r) => setTimeout(r, 3000));
      try {
        const res = await fetch(`${API_BASE}/api/payment/verify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ quote_id: challenge.quote_id, transaction_id: id }),
        });
        if (res.status === 502 && attempt < MAX_RETRIES - 1) continue;
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail ?? `Verification failed (${res.status})`);
        setVerifyResult({ hcs_status: body.hcs_status, hashscan_url: body.hashscan_url });
        setStep("done");
        return;
      } catch (err) {
        if (attempt === MAX_RETRIES - 1) {
          setErrorMsg(
            err instanceof Error
              ? err.message
              : "Mirror Node verification failed after 5 attempts.",
          );
          setStep("error");
        }
      }
    }
  }

  async function handleManualVerify() {
    const id = txId.trim();
    if (!id) {
      setErrorMsg("Paste your Hedera transaction ID first.");
      return;
    }
    setErrorMsg("");
    await runVerify(id);
  }

  function handleDone() {
    if (!challenge) return;
    onComplete({ quote_id: challenge.quote_id, transaction_id: txId });
  }

  const timeLeft = challenge
    ? Math.max(0, challenge.expires_at - Math.floor(Date.now() / 1000))
    : 0;

  return (
    <div className="container mx-auto px-6 py-16 max-w-2xl">
      <div className="text-xs uppercase tracking-widest text-text-muted">Payment Required</div>
      <h2 className="mt-1 text-3xl font-bold tracking-tight">
        Authorize analysis for <span className="text-purple font-mono">{serviceName}</span>
      </h2>

      <div className="mt-8 space-y-4">
        {step === "loading" && (
          <Row><Loader2 className="h-5 w-5 animate-spin text-purple" />
            <span className="text-sm text-text-secondary">Requesting payment quote…</span></Row>
        )}

        {challenge && step !== "loading" && (
          <div className="rounded-lg border border-amber/30 bg-amber/5 p-5 space-y-4">
            <div className="flex items-start justify-between">
              <div className="text-xs uppercase tracking-widest text-amber">
                HTTP 402 — Payment Required
              </div>
              <div className="text-xs text-text-muted font-mono">{formatDuration(timeLeft)}</div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <Field label="Receiver">
                <div className="flex items-center gap-1.5">
                  <span className="font-mono truncate">{challenge.receiver}</span>
                  <CopyButton value={challenge.receiver} />
                </div>
              </Field>
              <Field label="Amount">
                <span className="font-mono font-semibold text-text-primary">
                  {challenge.amount_hbar} HBAR
                </span>
              </Field>
              <Field label="Memo"><span className="font-mono">{challenge.memo}</span></Field>
              <Field label="Network">
                <span className="font-mono">
                  {process.env.NEXT_PUBLIC_HEDERA_NETWORK ?? "testnet"}
                </span>
              </Field>
            </div>
          </div>
        )}

        {step === "ready" && (
          <div className="space-y-3">
            {!manualMode ? (
              <>
                <Button className="w-full" onClick={handleWalletPay} disabled={walletPending}>
                  {walletPending ? (
                    <><Loader2 className="h-4 w-4 animate-spin" /> Waiting for wallet…</>
                  ) : (
                    <>
                      <Wallet className="h-4 w-4" />
                      {isConnected ? `Pay with ${accountId}` : "Connect wallet & Pay"}
                    </>
                  )}
                </Button>
                <button onClick={() => setManualMode(true)}
                  className="w-full text-xs text-text-muted hover:text-text-secondary underline text-center">
                  Enter transaction ID manually instead
                </button>
              </>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-text-secondary">
                  Send <strong>{challenge?.amount_hbar} HBAR</strong> to{" "}
                  <strong className="font-mono">{challenge?.receiver}</strong> with memo{" "}
                  <strong className="font-mono">{challenge?.memo}</strong>, then paste the tx id.
                </p>
                <input value={txId} onChange={(e) => setTxId(e.target.value)}
                  placeholder="0.0.XXXXX@0000000000.000000000"
                  className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 font-mono text-xs text-text-primary focus:outline-none focus:border-purple/60" />
                {errorMsg && (
                  <div className="flex gap-2 text-xs text-red">
                    <AlertTriangle className="h-4 w-4 shrink-0" />{errorMsg}
                  </div>
                )}
                <div className="flex gap-2">
                  <Button variant="ghost" className="flex-1" onClick={() => setManualMode(false)}>
                    Back
                  </Button>
                  <Button className="flex-1" onClick={handleManualVerify}>
                    Verify Payment →
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {step === "sending" && (
          <Row><Loader2 className="h-5 w-5 animate-spin text-purple" />
            <span className="text-sm text-text-secondary">Waiting for wallet confirmation…</span></Row>
        )}

        {step === "verifying" && (
          <Row><Loader2 className="h-5 w-5 animate-spin text-cyan" />
            <div className="text-sm text-text-secondary space-y-0.5">
              <p>Verifying on Hedera Mirror Node…</p>
              <p className="text-xs text-text-muted">Mirror Node can lag ~3s. Retrying automatically.</p>
            </div></Row>
        )}

        {step === "error" && (
          <div className="rounded-lg border border-red/40 bg-red/5 p-4 space-y-3">
            <div className="flex gap-3 text-sm text-red">
              <AlertTriangle className="h-5 w-5 shrink-0" /><span>{errorMsg}</span>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={onCancel}>Cancel</Button>
              {!preIssuedChallenge && <Button onClick={fetchChallenge}>Get new quote</Button>}
              <Button onClick={() => setStep("ready")}>Try wallet again</Button>
            </div>
          </div>
        )}

        {step === "done" && verifyResult && (
          <div className="rounded-lg border border-green/40 bg-green/5 p-5 space-y-4">
            <div className="flex items-center gap-3">
              <Check className="h-5 w-5 text-green" />
              <div>
                <div className="text-sm font-semibold text-green">Payment Verified</div>
                <div className="text-xs text-text-muted mt-0.5">HCS: {verifyResult.hcs_status}</div>
              </div>
              <a href={verifyResult.hashscan_url} target="_blank" rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1 text-xs text-cyan hover:text-cyan/80">
                HashScan <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <Button className="w-full" onClick={handleDone}>Begin Analysis →</Button>
          </div>
        )}

        {step !== "error" && step !== "done" && (
          <button onClick={onCancel}
            className="text-xs text-text-muted hover:text-text-secondary underline block mx-auto">
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-surface-1 p-4">
      {children}
    </div>
  );
}
function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-text-muted">{label}</div>
      <div className="mt-0.5 text-xs text-text-secondary">{children}</div>
    </div>
  );
}
