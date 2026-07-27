import { FadeUp } from "@/components/ui/Motion";
import { LinkButton } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { HCSTopicBadge } from "@/components/ui/HashScanLink";
import { Check } from "lucide-react";
import { ENV } from "@/lib/env";

export function DemoShowcaseSection() {
  return (
    <section className="border-t border-border py-24 bg-surface-1">
      <div className="container mx-auto px-6">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">See it run</h2>
          <p className="mt-2 text-text-secondary text-lg">
            The Playground is a live, three-panel console over the entire backend.
          </p>
        </FadeUp>

        <div className="mt-12 grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-10 items-center">
          <FadeUp>
            {/* Playground mockup */}
            <div className="rounded-lg border border-border bg-background overflow-hidden shadow-2xl">
              <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-4 py-2.5">
                <span className="h-3 w-3 rounded-full bg-red" />
                <span className="h-3 w-3 rounded-full bg-amber" />
                <span className="h-3 w-3 rounded-full bg-green" />
                <span className="ml-2 text-xs text-text-muted font-mono">/playground</span>
              </div>
              <div className="grid grid-cols-[180px_1fr_200px] h-[340px] text-xs">
                <div className="border-r border-border bg-surface-2 p-3 space-y-3">
                  <div className="text-[10px] uppercase tracking-widest text-text-muted">Payment</div>
                  <div className="pl-2 py-1 border-l-2 border-purple bg-purple/10 font-mono text-text-primary">
                    POST /challenge
                  </div>
                  <div className="pl-2 py-1 font-mono text-text-secondary">POST /verify</div>
                  <div className="text-[10px] uppercase tracking-widest text-text-muted mt-3">Premium</div>
                  <div className="pl-2 py-1 font-mono text-amber">/premium-query 402</div>
                </div>
                <div className="p-4 space-y-3">
                  <div className="text-text-secondary font-mono text-[11px]">POST /api/payment/challenge</div>
                  <div className="rounded-md border border-border bg-surface-1 p-3 space-y-2">
                    <div className="flex justify-between">
                      <span className="text-text-muted">quote_id</span>
                      <span className="font-mono text-text-primary">3f8a…7c11</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">amount</span>
                      <span className="font-mono text-purple">0.5 HBAR</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">state</span>
                      <StatusBadge status="quoted" />
                    </div>
                  </div>
                </div>
                <div className="border-l border-border bg-surface-2 p-3 space-y-2">
                  <div className="text-[10px] uppercase tracking-widest text-text-muted">Network</div>
                  <div className="flex items-center gap-1.5 text-cyan">
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan animate-pulse" />
                    Mirror Node 12ms
                  </div>
                  <div className="flex items-center gap-1.5 text-green">
                    <span className="h-1.5 w-1.5 rounded-full bg-green" />
                    Transfer confirmed
                  </div>
                  <div className="flex items-center gap-1.5 text-purple">
                    <span className="h-1.5 w-1.5 rounded-full bg-purple" />
                    HCS published
                  </div>
                  <div className="pt-2 border-t border-border-subtle mt-3">
                    {ENV.hcsTopicId && <HCSTopicBadge topicId={ENV.hcsTopicId} />}
                  </div>
                </div>
              </div>
            </div>
          </FadeUp>

          <FadeUp delay={0.15}>
            <ul className="space-y-4 text-sm">
              {[
                "Every backend endpoint, live",
                "Real Mirror Node verification",
                "Real HCS receipt on Hedera testnet",
                "Every response rendered as structured cards",
                "Step-by-step x402 payment modal",
              ].map((s) => (
                <li key={s} className="flex items-start gap-3">
                  <Check className="h-5 w-5 text-green mt-0.5 shrink-0" />
                  <span className="text-text-secondary">{s}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8">
              <LinkButton href="/playground" size="lg">
                Open the x402 Playground →
              </LinkButton>
            </div>
          </FadeUp>
        </div>
      </div>
    </section>
  );
}
