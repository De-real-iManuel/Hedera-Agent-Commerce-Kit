import { KeyRound, CreditCard, Bot } from "lucide-react";
import { FadeUp, Stagger, StaggerItem } from "@/components/ui/Motion";
import { Card, CardTitle, CardBody } from "@/components/ui/Card";
import { CodeBlock } from "@/components/ui/CodeBlock";

const CARDS = [
  {
    icon: KeyRound,
    color: "text-red",
    title: "API Keys Break",
    body: "Your agent calls a premium API. The key expired. The subscription lapsed. The billing system was built for humans, not software.",
  },
  {
    icon: CreditCard,
    color: "text-amber",
    title: "Charging Is Too Hard",
    body: "You built an MCP tool worth charging for. You're using Stripe, manual invoicing, or giving it away because billing takes weeks to integrate.",
  },
  {
    icon: Bot,
    color: "text-text-muted",
    title: "Agents Can't Trade",
    body: "Autonomous agents need to exchange value with each other. No payment primitive exists at the HTTP layer. Every agent is blocked by human auth.",
  },
];

const SNIPPET = `@PaidEndpoint(price="0.5 HBAR")
async def my_service(request: Request):
    return {"result": "paid access granted"}`;

export function ProblemSection() {
  return (
    <section className="border-t border-border py-24">
      <div className="container mx-auto px-6">
        <Stagger className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {CARDS.map((c) => {
            const Icon = c.icon;
            return (
              <StaggerItem key={c.title}>
                <Card className="h-full">
                  <Icon className={`h-6 w-6 ${c.color}`} />
                  <CardTitle className="mt-4">{c.title}</CardTitle>
                  <CardBody>{c.body}</CardBody>
                </Card>
              </StaggerItem>
            );
          })}
        </Stagger>

        <FadeUp delay={0.2} className="mt-16 text-center">
          <p className="text-text-secondary text-lg">
            HACK replaces all of this with three lines of Python.
          </p>
          <div className="mt-6 max-w-2xl mx-auto">
            <CodeBlock code={SNIPPET} language="python" filename="app.py" />
          </div>
        </FadeUp>
      </div>
    </section>
  );
}
