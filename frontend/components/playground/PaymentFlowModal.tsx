"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Check, X, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { StepIndicator } from "@/components/ui/StepIndicator";
import { ChallengeCard, VerifyCard } from "./ResponseViewer";
import { api, isApiError } from "@/lib/api";
import type { ChallengeResponse, VerifyResponse } from "@/lib/types";

const STEPS = [
  { id: "challenge", title: "Challenge",     description: "Request an x402 quote from the backend." },
  { id: "pay",       title: "Send HBAR",     description: "Transfer to the receiver, paste your transaction ID." },
  { id: "verify",    title: "Verify",        description: "Backend verifies via Mirror Node." },
  { id: "access",    title: "Access granted",description: "Retry the endpoint with your payment proof." },
];

interface PaymentFlowModalProps {
  open: boolean;
  onClose: () => void;
  onComplete: (proof: { quote_id: string; transaction_id: string }) => void;
}

export function PaymentFlowModal({ open, onClose, onComplete }: PaymentFlowModalProps) {
  const [step,      setStep]      = useState(0);
  const [challenge, setChallenge] = useState<ChallengeResponse | null>(null);
  const [verify,    setVerify]    = useState<VerifyResponse | null>(null);
  const [txId,      setTxId]      = useState("");
  const [busy,      setBusy]      = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  if (!open) return null;

  async function startChallenge() {
    setBusy(true);
    setError(null);
    try {
      const body = await api.challenge({ resource_path: "/api/premium-query" });
      setChallenge(body);
      setStep(1);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Backend unreachable. Start the HACK backend first.");
    } finally {
      setBusy(false);
    }
  }

  async function submitVerify() {
    if (!challenge) return;
    if (!txId.trim()) { setError("Paste your Hedera transaction ID first."); return; }
    setBusy(true);
    setError(null);
    setStep(2);
    try {
      const body = await api.verify({ quote_id: challenge.quote_id, transaction_id: txId.trim() });
      setVerify(body);
      setStep(3);
    } catch (err) {
      setError(isApiError(err) ? err.message : "Verification failed. Check the transaction ID and retry.");
      setStep(1);
    } finally {
      setBusy(false);
    }
  }

  function finish() {
    if (!challenge || !verify) return;
    onComplete({ quote_id: challenge.quote_id, transaction_id: verify.transaction_id });
    reset();
  }

  function reset() {
    setStep(0); setChallenge(null); setVerify(null);
    setTxId(""); setError(null); onClose();
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={reset}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }} transition={{ duration: 0.25 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-3xl rounded-lg border border-border bg-surface-1 shadow-2xl overflow-hidden"
        >
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <h3 className="text-sm font-semibold">x402 Payment Flow</h3>
            <button onClick={reset} className="text-text-muted hover:text-text-primary">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-[220px_1fr] gap-6 p-6">
            <StepIndicator steps={STEPS} currentStep={step} />

            <div className="min-h-[280px] space-y-4">
              {error && (
                <div className="flex items-start gap-2 rounded-md border border-red/40 bg-red/5 px-4 py-3 text-xs text-red">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              {step === 0 && (
                <div>
                  <p className="text-sm text-text-secondary">
                    Click below to request an x402 payment quote from the backend.
                  </p>
                  <Button className="mt-4" onClick={startChallenge} disabled={busy}>
                    {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                    Request quote
                  </Button>
                </div>
              )}

              {step === 1 && challenge && (
                <div className="space-y-4">
                  <ChallengeCard data={challenge} />
                  <div>
                    <label className="block text-xs uppercase tracking-widest text-text-muted mb-1.5">
                      Transaction ID
                    </label>
                    <input
                      value={txId}
                      onChange={(e) => setTxId(e.target.value)}
                      placeholder="0.0.XXXXX@1700000000.000000000"
                      className="w-full rounded-md border border-border bg-surface-2 px-3 py-2 font-mono text-xs text-text-primary focus:outline-none focus:border-purple/60"
                    />
                  </div>
                  <div className="flex justify-between">
                    <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                    <Button onClick={submitVerify} disabled={busy}>
                      {busy && <Loader2 className="h-4 w-4 animate-spin" />}
                      I&apos;ve sent the HBAR
                    </Button>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="flex items-center gap-3 text-sm text-text-secondary">
                  <Loader2 className="h-5 w-5 animate-spin text-purple" />
                  Verifying against Mirror Node…
                </div>
              )}

              {step === 3 && verify && (
                <div className="space-y-4">
                  <VerifyCard data={verify} />
                  <div className="flex justify-between">
                    <div className="flex items-center gap-2 text-sm text-green">
                      <Check className="h-4 w-4" /> Grant issued
                    </div>
                    <Button onClick={finish}>Continue →</Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
