import { Zap, DollarSign, Search, FileCheck, Bot, Link as LinkIcon } from "lucide-react";
import { FadeUp, Stagger, StaggerItem } from "@/components/ui/Motion";
import { Card, CardTitle, CardBody } from "@/components/ui/Card";

const FEATURES = [
  { icon: Zap, color: "text-cyan", title: "3-Second Finality", stat: "~3s",
    body: "Payment verified before your UI updates" },
  { icon: DollarSign, color: "text-green", title: "Fixed Fees", stat: "$0.001",
    body: "Agents calculate cost before calling. No gas surprises." },
  { icon: Search, color: "text-cyan", title: "Mirror Node API", stat: "Free",
    body: "Public payment verification. No oracle. No middleware." },
  { icon: FileCheck, color: "text-purple", title: "HCS Receipts", stat: "Immutable",
    body: "Tamper-proof, timestamped on-chain audit trail for every payment" },
  { icon: Bot, color: "text-purple", title: "Hedera Agent Kit", stat: "Official SDK",
    body: "AI agents as first-class citizens in the Hedera ecosystem" },
  { icon: LinkIcon, color: "text-text-secondary", title: "x402 Protocol", stat: "HTTP-native",
    body: "Zero new auth layer. Payment in standard HTTP headers." },
];

export function WhyHederaSection() {
  return (
    <section className="border-t border-border py-24">
      <div className="container mx-auto px-6">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">Why Hedera?</h2>
          <p className="mt-2 text-text-secondary text-lg">
            Deterministic fees. Public verifiability. On-chain audit trails.
          </p>
        </FadeUp>

        <Stagger className="mt-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <StaggerItem key={f.title}>
                <Card className="h-full">
                  <div className="flex items-start justify-between">
                    <Icon className={`h-5 w-5 ${f.color}`} />
                    <span className="font-mono text-xs text-text-muted">{f.stat}</span>
                  </div>
                  <CardTitle className="mt-4">{f.title}</CardTitle>
                  <CardBody>{f.body}</CardBody>
                </Card>
              </StaggerItem>
            );
          })}
        </Stagger>
      </div>
    </section>
  );
}
