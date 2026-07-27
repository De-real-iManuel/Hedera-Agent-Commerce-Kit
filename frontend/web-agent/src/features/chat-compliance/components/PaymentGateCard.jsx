"use client";
import { Card } from "@/components/ui/card";

const fmtHbar = (n) => {
  if (n === undefined || n === null) return "—";
  const v = typeof n === "number" ? n : parseFloat(n);
  if (Number.isNaN(v)) return String(n);
  return v.toFixed(6).replace(/0+$/, "").replace(/\.$/, "") + " HBAR";
};

const short = (s, n = 10) => (s && s.length > n * 2 ? `${s.slice(0, n)}…${s.slice(-n)}` : s || "—");

export function PaymentGateCard({ output, state }) {
  const raw = output?.raw;
  if (!raw || raw.status !== "PAYMENT_REQUIRED") return null;
  const c = raw.challenge || {};
  const quoteId = c.quote_id || c.id;
  const amount = c.amount_hbar ?? c.amount;
  const receiver = c.receiver || c.pay_to;
  const memo = c.memo || c.payment_memo;
  const expires = c.expires_at || c.valid_until;

  return (
    <Card className="border-amber-500/40 bg-amber-500/5">
      <div className="flex items-start gap-3 p-4">
        <div className="mt-0.5 h-2 w-2 shrink-0 animate-pulse rounded-full bg-amber-400" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-amber-400">
              402 · Payment Required
            </span>
            <span className="text-xs text-neutral-500">via x402</span>
          </div>
          <div className="mt-1 text-sm font-medium text-neutral-100">
            {raw.toolName === "run_compliance_check"
              ? "Pay to run compliance check"
              : raw.toolName === "certify_service"
              ? "Pay to finalise certification"
              : "Payment required"}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 font-mono text-xs">
            <div className="text-neutral-500">Amount</div>
            <div className="text-neutral-100">{fmtHbar(amount)}</div>
            <div className="text-neutral-500">Receiver</div>
            <div className="truncate text-neutral-100">{receiver || "—"}</div>
            <div className="text-neutral-500">Memo</div>
            <div className="truncate text-neutral-100">{memo || "—"}</div>
            <div className="text-neutral-500">Quote ID</div>
            <div className="truncate text-neutral-100">{short(quoteId, 8)}</div>
            {expires && (
              <>
                <div className="text-neutral-500">Expires</div>
                <div className="text-neutral-100">{new Date(expires).toLocaleTimeString()}</div>
              </>
            )}
            <div className="text-neutral-500">Resource</div>
            <div className="truncate text-neutral-100">
              {raw.method} {raw.resource}
            </div>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-neutral-400">
            Authorize this HBAR transfer in your connected wallet. Once the transaction is confirmed, tell the agent and provide the transaction ID — it will re-invoke the tool with proof of payment and continue.
          </p>
          <div className="mt-3 text-[10px] uppercase tracking-wide text-neutral-500">
            state: {state || "output-available"}
          </div>
        </div>
      </div>
    </Card>
  );
}

export function PaymentGateRow({ output }) {
  const c = output?.raw?.challenge || {};
  return (
    <span className="text-amber-400">
      402 · {fmtHbar(c.amount_hbar ?? c.amount)} to {short(c.receiver, 6)}
    </span>
  );
}
