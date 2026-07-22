"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Step = "idle" | "calling" | "402" | "verifying" | "success" | "error";

interface Challenge {
  quote_id: string;
  resource_hash: string;
  payment_details: {
    receiver: string;
    amount_hbar: number;
    network: string;
    memo: string;
    expires_at: number;
  };
  retry_instructions: string;
}

export default function Home() {
  const [step, setStep] = useState<Step>("idle");
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [txId, setTxId] = useState("");
  const [quoteId, setQuoteId] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  // ── Step 1: Call premium endpoint ────────────────────────────────────────
  async function callPremium(token?: string, qid?: string) {
    setStep("calling");
    setError(null);
    const headers: HeadersInit = {};
    if (token) headers["X-Payment-Token"] = token;
    if (qid)   headers["X-Quote-Id"] = qid;

    const res = await fetch(`${API}/api/premium-query`, { headers });

    if (res.status === 402) {
      // Get a proper challenge with quote_id
      await requestChallenge();
      return;
    }
    if (!res.ok) {
      setError(`Error ${res.status}: ${await res.text()}`);
      setStep("error");
      return;
    }
    setResult(await res.json());
    setStep("success");
  }

  // ── Step 2: Request a payment challenge ───────────────────────────────────
  async function requestChallenge() {
    const res = await fetch(`${API}/api/payment/challenge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint: "/api/premium-query" }),
    });
    const data: Challenge = await res.json();
    setChallenge(data);
    setQuoteId(data.quote_id);
    setStep("402");
  }

  // ── Step 3: Verify payment ────────────────────────────────────────────────
  async function verifyPayment() {
    setStep("verifying");
    setError(null);
    const res = await fetch(`${API}/api/payment/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transaction_id: txId, quote_id: quoteId }),
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data.detail ?? "Verification failed.");
      setStep("402");
      return;
    }
    // Verified — retry the premium endpoint
    await callPremium(txId, quoteId);
  }

  function reset() {
    setStep("idle");
    setTxId("");
    setQuoteId("");
    setChallenge(null);
    setResult(null);
    setError(null);
  }

  return (
    <main className="max-w-2xl mx-auto px-4 py-16 space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-purple-400">Hedera Agent Commerce Kit</h1>
        <p className="mt-1 text-gray-400 text-sm">
          Pay-per-request infrastructure · Hedera x402 · HBAR · HCS · Mirror Node
        </p>
      </div>

      {/* Idle */}
      {step === "idle" && (
        <div className="space-y-4">
          <p className="text-gray-300 text-sm">
            Click to call the premium endpoint. A payment challenge will be issued automatically.
          </p>
          <button
            onClick={() => callPremium()}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 rounded-lg font-semibold transition"
          >
            Call /api/premium-query
          </button>
        </div>
      )}

      {/* Calling / Verifying */}
      {(step === "calling" || step === "verifying") && (
        <p className="text-yellow-400 animate-pulse text-sm">
          {step === "calling" ? "Calling premium endpoint…" : "Verifying payment on Mirror Node…"}
        </p>
      )}

      {/* 402 Payment Required */}
      {step === "402" && challenge && (
        <div className="border border-yellow-500 rounded-lg p-5 space-y-4">
          <h2 className="text-yellow-400 font-bold">⚡ HTTP 402 — Payment Required</h2>

          <div className="text-sm space-y-1 text-gray-300">
            <p><span className="text-gray-500">Quote ID:</span> <span className="text-xs font-mono">{challenge.quote_id}</span></p>
            <p><span className="text-gray-500">Network:</span> {challenge.payment_details.network}</p>
            <p><span className="text-gray-500">Receiver:</span> <span className="font-mono">{challenge.payment_details.receiver}</span></p>
            <p><span className="text-gray-500">Amount:</span> {challenge.payment_details.amount_hbar} HBAR</p>
            <p><span className="text-gray-500">Memo:</span> <span className="font-mono">{challenge.payment_details.memo}</span></p>
            <p>
              <span className="text-gray-500">Expires:</span>{" "}
              {new Date(challenge.payment_details.expires_at * 1000).toLocaleTimeString()}
            </p>
          </div>

          {error && (
            <p className="text-red-400 text-sm bg-red-950 border border-red-700 rounded px-3 py-2">{error}</p>
          )}

          <div className="space-y-2">
            <label className="block text-sm text-gray-400">
              Paste your Transaction ID after sending HBAR:
            </label>
            <input
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm font-mono focus:outline-none focus:border-purple-500"
              placeholder="0.0.12345@1234567890.123456789"
              value={txId}
              onChange={(e) => setTxId(e.target.value)}
            />
            <button
              onClick={verifyPayment}
              disabled={!txId.trim()}
              className="px-5 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-40 rounded font-semibold transition"
            >
              Verify &amp; Unlock
            </button>
          </div>
        </div>
      )}

      {/* Success */}
      {step === "success" && result && (
        <div className="border border-green-500 rounded-lg p-5 space-y-4">
          <h2 className="text-green-400 font-bold">✅ 200 OK — Access Granted</h2>
          <pre className="text-xs text-gray-300 overflow-auto bg-gray-900 p-3 rounded leading-relaxed">
            {JSON.stringify(result, null, 2)}
          </pre>
          <div className="flex gap-4 text-xs">
            <a
              href={`${API}/api/receipt/${txId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-400 underline"
            >
              HCS Receipt
            </a>
            <a
              href={`${API}/api/hashscan/${txId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 underline"
            >
              HashScan →
            </a>
            <a
              href={`${API}/api/usage`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 underline"
            >
              Usage Metering
            </a>
          </div>
          <button
            onClick={reset}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition"
          >
            Reset
          </button>
        </div>
      )}

      {/* Error */}
      {step === "error" && (
        <div className="border border-red-500 rounded-lg p-5 space-y-3">
          <h2 className="text-red-400 font-bold">Error</h2>
          <p className="text-sm text-gray-300">{error}</p>
          <button onClick={reset} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm transition">
            Reset
          </button>
        </div>
      )}

    </main>
  );
}
