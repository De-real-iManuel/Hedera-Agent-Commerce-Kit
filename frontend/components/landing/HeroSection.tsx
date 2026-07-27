"use client";
import { Terminal } from "@/components/ui/Terminal";
import { LinkButton } from "@/components/ui/Button";
import { motion } from "framer-motion";
import { ENV } from "@/lib/env";

const receiver = ENV.paymentReceiver || "0.0.XXXXXX";
const topic    = ENV.hcsTopicId     || "0.0.YYYYYY";

const TERMINAL_LINES = [
  `$ curl -X POST ${ENV.apiBase}/api/premium-query \\`,
  "    -H 'Content-Type: application/json' \\",
  "    -d '{\"query\": \"What is my HBAR balance?\"}'",
  "",
  "HTTP/1.1 402 Payment Required",
  "content-type: application/json",
  "{",
  "  \"quote_id\": \"3f8a1c2d-9e4b-4a7c-b820-...\",",
  `  "receiver": "${receiver}",`,
  "  \"amount_hbar\": 0.5,",
  "  \"memo\": \"hack-payment\",",
  "  \"expires_in\": 600",
  "}",
  "",
  "# → send HBAR to receiver, then retry with proof",
  `$ curl -X POST ${ENV.apiBase}/api/payment/verify \\`,
  "    -d '{\"quote_id\":\"3f8a1c2d...\",\"transaction_id\":\"0.0.XXXXX@170000...\"}'",
  "",
  "> Mirror Node verified · amount OK · receiver OK",
  `> HCS receipt published on topic ${topic}`,
  "",
  "HTTP/1.1 200 OK",
  "{ \"balance\": \"1,204.7183 ℏ\", \"agent\": \"hedera-agent-kit\" }",
  "✓ Grant window: 5m 00s",
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-30 pointer-events-none" />
      <div className="absolute -top-32 left-1/3 h-[500px] w-[500px] bg-radial-purple blur-3xl opacity-40 pointer-events-none" />

      <div className="container mx-auto px-6 pt-20 pb-24 grid grid-cols-1 lg:grid-cols-[55%_45%] gap-12 items-center min-h-[calc(100vh-56px)]">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="max-w-2xl"
        >
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-purple">
            Hedera Agent Commerce Kit
          </div>

          <h1 className="mt-4 text-5xl md:text-6xl font-bold tracking-tight leading-[1.05]">
            The infrastructure for
            <br />
            <span className="text-purple">x402-paid</span> AI services.
          </h1>

          <p className="mt-6 text-xl text-text-secondary max-w-xl leading-relaxed">
            Build AI services that can{" "}
            <span className="text-text-primary font-medium">charge other AI agents per request</span>{" "}
            using x402 on Hedera.
          </p>

          <p className="mt-4 text-base text-text-muted max-w-md leading-relaxed">
            One decorator. Mirror Node verification. HCS receipts. Compliance certification.
            Production-ready architecture.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <LinkButton href="/docs" size="lg">Read the Docs →</LinkButton>
            <LinkButton href="/api-explorer" variant="ghost" size="lg">
              Open API Explorer
            </LinkButton>
            <LinkButton
              href="https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit"
              variant="link"
              size="lg"
              target="_blank"
              rel="noreferrer"
            >
              GitHub ↗
            </LinkButton>
          </div>

          <div className="mt-10 flex flex-wrap items-center gap-6 text-xs text-text-muted">
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-green animate-pulse" />
              Hedera Testnet
            </span>
            <span>Python · FastAPI · HCS · Mirror Node</span>
            <span className="rounded-full border border-border px-2 py-0.5 font-mono">MIT</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.15 }}
          className="relative"
        >
          <div className="absolute -inset-8 bg-radial-purple blur-3xl opacity-20 pointer-events-none" />
          <Terminal lines={TERMINAL_LINES} typingSpeed={12} loop />
        </motion.div>
      </div>
    </section>
  );
}
