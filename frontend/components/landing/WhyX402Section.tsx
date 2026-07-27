import { FadeUp } from "@/components/ui/Motion";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { ENV } from "@/lib/env";

const receiver = ENV.paymentReceiver || "0.0.XXXXXX";

const HTTP_SNIPPET = `# Request
GET /api/premium-query HTTP/1.1

# Response (402)
HTTP/1.1 402 Payment Required
Content-Type: application/json
{
  "quote_id":    "3f8a1c2d-9e4b-4a7c-b820-...",
  "receiver":    "${receiver}",
  "amount_hbar": 0.5,
  "memo":        "hack-payment",
  "expires_in":  600
}

# Retry with proof (200)
GET /api/premium-query HTTP/1.1
X-Payment-Token: ${receiver}@1700000000.000000000
X-Quote-Id:      3f8a1c2d-9e4b-4a7c-b820-...`;

export function WhyX402Section() {
  return (
    <section id="why-x402" className="border-t border-border py-24">
      <div className="container mx-auto px-6">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Why x402?</h2>
          <p className="mt-2 text-text-secondary text-lg">
            HTTP already has a payment status code. We use it.
          </p>
        </FadeUp>

        <div className="mt-12 grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
          <FadeUp className="space-y-5 text-text-secondary leading-relaxed">
            <p>
              <span className="text-text-primary font-medium">
                HTTP 402 Payment Required
              </span>{" "}
              has existed since 1991. x402 is the protocol that makes it real — payment metadata
              travels in standard HTTP headers, with no new auth layer, no accounts, no
              subscriptions.
            </p>
            <p>
              An AI agent calls an endpoint. Gets a 402. Pays. Gets the result. The entire
              transaction settles in{" "}
              <span className="text-cyan font-mono">~3 seconds</span> on Hedera testnet.
            </p>
            <ul className="mt-4 space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="mt-1.5 h-1 w-1 rounded-full bg-purple" />
                <span>No new auth layer — standard HTTP semantics.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1.5 h-1 w-1 rounded-full bg-purple" />
                <span>Payment metadata in response body + reply headers.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1.5 h-1 w-1 rounded-full bg-purple" />
                <span>Machine-verifiable via public Mirror Node — no oracles.</span>
              </li>
            </ul>
          </FadeUp>

          <FadeUp delay={0.15}>
            <CodeBlock code={HTTP_SNIPPET} language="http" filename="x402-exchange.http" />
          </FadeUp>
        </div>
      </div>
    </section>
  );
}
