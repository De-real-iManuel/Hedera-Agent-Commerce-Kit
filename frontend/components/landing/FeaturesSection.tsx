import { FadeUp } from "@/components/ui/Motion";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Check, AlertTriangle } from "lucide-react";
import { ENV } from "@/lib/env";
import type { PaymentState } from "@/lib/types";

const STATES: PaymentState[] = ["quoted", "verified", "granted", "consumed", "expired", "duplicate"];

const REPORT_JSON = `{
  "service_name": "my-mcp-server",
  "score": 92,
  "passed": true,
  "x402_rules": [
    { "id": "replay_protection", "passed": true },
    { "id": "payment_expiry",    "passed": true },
    { "id": "idempotency",       "passed": true },
    { "id": "settlement",        "passed": true },
    { "id": "quote_lifecycle",   "passed": true }
  ],
  "certified_at": 1753228800,
  "hcs_topic": "${ENV.hcsTopicId || "0.0.YYYYYY"}"
}`;

const CONTAINER = `# service_container.py
class ServiceContainer:
    lifecycle:  PaymentLifecycle
    verifier:   MirrorNodeVerifier
    certifier:  CertificationService
    quotes:     QuoteStore
    receipts:   HCSReceiptService

# Swap any implementation:
container.verifier = InMemoryVerifier()   # for tests
container.receipts = NoOpReceiptService() # for local dev`;

const AGENT_DEMO = `> "What is my HBAR balance?"

[tool] hedera.mirror.account_info()
[tool] hedera.hcs.topic_info(id="${ENV.hcsTopicId || "0.0.9702133"}")

agent: "Your account currently holds 1,204.7183 ℏ.
        The associated HCS topic has 42 receipts."`;


export function FeaturesSection() {
  return (
    <section className="border-t border-border py-24">
      <div className="container mx-auto px-6">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Built for production from day one
          </h2>
        </FadeUp>

        {/* Block 1 */}
        <div className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <FadeUp>
            <h3 className="text-xs uppercase tracking-widest text-purple">Payment State Machine</h3>
            <p className="mt-3 text-2xl font-semibold text-text-primary">
              Six explicit states. Zero replay attacks.
            </p>
            <p className="mt-3 text-text-secondary leading-relaxed">
              Every payment moves through 6 explicit states. Replay attacks are rejected at the
              state level. Grant windows expire. Duplicate transaction IDs are detected and
              flagged. Nothing leaks.
            </p>
          </FadeUp>
          <FadeUp delay={0.15}>
            <div className="rounded-lg border border-border bg-surface-1 p-6 flex flex-wrap gap-2 justify-center">
              {STATES.map((s, i) => (
                <div key={s} className="flex items-center gap-2">
                  <StatusBadge status={s} />
                  {i < STATES.length - 1 && <span className="text-text-muted">→</span>}
                </div>
              ))}
            </div>
          </FadeUp>
        </div>

        {/* Block 2 */}
        <div className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <FadeUp className="lg:order-2">
            <h3 className="text-xs uppercase tracking-widest text-purple">Compliance Engine</h3>
            <p className="mt-3 text-2xl font-semibold text-text-primary">
              Rules you can trust, certificates you can verify.
            </p>
            <p className="mt-3 text-text-secondary leading-relaxed">
              5 built-in compliance rules. Pluggable architecture. Every payment can be certified
              on-chain via HCS. Compliance reports are machine-readable and exportable.
            </p>
            <ul className="mt-4 text-sm text-text-secondary space-y-1">
              {[
                "Replay protection", "Payment expiry", "Idempotency", "Settlement validation",
                "Quote lifecycle",
              ].map((r) => (
                <li key={r} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green" /> {r}
                </li>
              ))}
            </ul>
          </FadeUp>
          <FadeUp delay={0.15} className="lg:order-1">
            <CodeBlock code={REPORT_JSON} language="json" filename="certification.report.json" />
          </FadeUp>
        </div>

        {/* Block 3 */}
        <div className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <FadeUp>
            <h3 className="text-xs uppercase tracking-widest text-purple">Dependency Injection</h3>
            <p className="mt-3 text-2xl font-semibold text-text-primary">
              Swap any layer without touching business logic.
            </p>
            <p className="mt-3 text-text-secondary leading-relaxed">
              Every service is injectable. Swap the QuoteStore, the verifier, or the receipt
              service without touching business logic. Tested with real unit tests —{" "}
              <span className="text-green font-mono">31 passing</span>.
            </p>
            <p className="mt-3 flex items-center gap-2 text-sm text-amber">
              <AlertTriangle className="h-4 w-4" />
              Tests run on every commit via GitHub Actions.
            </p>
          </FadeUp>
          <FadeUp delay={0.15}>
            <CodeBlock code={CONTAINER} language="python" filename="hack/di/container.py" />
          </FadeUp>
        </div>

        {/* Block 4 */}
        <div className="mt-20 grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <FadeUp className="lg:order-2">
            <h3 className="text-xs uppercase tracking-widest text-purple">Hedera Agent Kit</h3>
            <p className="mt-3 text-2xl font-semibold text-text-primary">
              LangChain agent, on-chain, behind an x402 gate.
            </p>
            <p className="mt-3 text-text-secondary leading-relaxed">
              The premium endpoint is backed by a real Hedera Agent Kit agent. Account queries,
              HCS topics, HTS tokens — all accessible via natural language through the paid API.
            </p>
          </FadeUp>
          <FadeUp delay={0.15} className="lg:order-1">
            <CodeBlock code={AGENT_DEMO} language="text" filename="agent.log" />
          </FadeUp>
        </div>
      </div>
    </section>
  );
}
