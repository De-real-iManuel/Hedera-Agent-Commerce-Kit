import { FadeUp } from "@/components/ui/Motion";
import { ArrowRight } from "lucide-react";

const NODES: Array<{
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  variant: "agent" | "hack" | "hedera";
}> = [
  { id: "agent", label: "AI Agent / Client", x: 40, y: 40, w: 180, h: 60, variant: "agent" },
  { id: "middleware", label: "HACK Middleware\n@PaidEndpoint", x: 320, y: 40, w: 220, h: 60, variant: "hack" },
  { id: "state", label: "Payment State Machine\nquoted → verified → granted", x: 320, y: 140, w: 220, h: 60, variant: "hack" },
  { id: "verifier", label: "Mirror Node Verifier", x: 320, y: 240, w: 220, h: 60, variant: "hack" },
  { id: "receipt", label: "HCS Receipt Service", x: 320, y: 340, w: 220, h: 60, variant: "hack" },
  { id: "agentkit", label: "Hedera Agent Kit\n(LangChain)", x: 620, y: 40, w: 200, h: 60, variant: "hedera" },
  { id: "mirror", label: "Mirror Node API", x: 620, y: 240, w: 200, h: 60, variant: "hedera" },
  { id: "hcs", label: "HCS Topic", x: 620, y: 340, w: 200, h: 60, variant: "hedera" },
];

const EDGES: Array<[string, string]> = [
  ["agent", "middleware"],
  ["middleware", "state"],
  ["state", "verifier"],
  ["state", "receipt"],
  ["middleware", "agentkit"],
  ["verifier", "mirror"],
  ["receipt", "hcs"],
];

function nodeStyle(v: "agent" | "hack" | "hedera") {
  if (v === "agent") return { fill: "#18181b", stroke: "#7c3aed" };
  if (v === "hedera") return { fill: "#111113", stroke: "#06b6d4" };
  return { fill: "#1c1c21", stroke: "#fafafa" };
}

export function ArchitectureSection() {
  return (
    <section id="architecture" className="border-t border-border py-24">
      <div className="container mx-auto px-6">
        <FadeUp>
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">How it fits together</h2>
          <p className="mt-2 text-text-secondary text-lg max-w-2xl">
            A thin middleware wraps your endpoint, a state machine guards every payment, and Hedera
            provides the settlement and audit trail.
          </p>
        </FadeUp>

        <FadeUp delay={0.15} className="mt-10">
          <div className="rounded-lg border border-border bg-surface-1 overflow-x-auto">
            <svg viewBox="0 0 860 420" className="w-full h-auto min-w-[720px]">
              <defs>
                <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5"
                  markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M0,0 L10,5 L0,10 z" fill="#52525b" />
                </marker>
              </defs>
              {EDGES.map(([a, b], i) => {
                const na = NODES.find((n) => n.id === a)!;
                const nb = NODES.find((n) => n.id === b)!;
                const x1 = na.x + na.w;
                const y1 = na.y + na.h / 2;
                const x2 = nb.x;
                const y2 = nb.y + nb.h / 2;
                return (
                  <line key={i} x1={x1} y1={y1} x2={x2 - 4} y2={y2}
                    stroke="#52525b" strokeWidth="1.5" markerEnd="url(#arr)" />
                );
              })}
              {NODES.map((n) => {
                const s = nodeStyle(n.variant);
                const lines = n.label.split("\n");
                return (
                  <g key={n.id}>
                    <rect x={n.x} y={n.y} width={n.w} height={n.h}
                      rx="8" ry="8" fill={s.fill} stroke={s.stroke} strokeWidth="1.5" />
                    {lines.map((l, i) => (
                      <text key={i} x={n.x + n.w / 2}
                        y={n.y + n.h / 2 + (i - (lines.length - 1) / 2) * 16 + 4}
                        fill="#fafafa" fontSize="12" fontFamily="Inter, sans-serif"
                        textAnchor="middle">{l}</text>
                    ))}
                  </g>
                );
              })}
              <g fontFamily="Inter, sans-serif" fontSize="10" fill="#52525b">
                <text x="40" y="20">CLIENT</text>
                <text x="320" y="20">HACK BACKEND</text>
                <text x="620" y="20">HEDERA NETWORK</text>
              </g>
            </svg>
          </div>
        </FadeUp>

        <FadeUp delay={0.25} className="mt-10">
          <div className="rounded-lg border border-border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2 text-text-muted text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-3">Component</th>
                  <th className="text-left px-4 py-3">Description</th>
                  <th className="text-left px-4 py-3">Source</th>
                </tr>
              </thead>
              <tbody className="text-text-secondary">
                {[
                  ["hack/toolkit/decorators.py", "@PaidEndpoint decorator + middleware"],
                  ["hack/toolkit/state_machine.py", "6-state payment lifecycle"],
                  ["hack/verifier/mirror.py", "Mirror Node verification client"],
                  ["hack/receipt/hcs.py", "HCS topic receipt publisher"],
                  ["hack/compliance/rules/", "5 built-in compliance rules"],
                  ["hack/certification/service.py", "Report + soulbound certificate"],
                ].map(([p, d]) => (
                  <tr key={p} className="border-t border-border-subtle">
                    <td className="px-4 py-3 font-mono text-xs text-text-primary">{p}</td>
                    <td className="px-4 py-3">{d}</td>
                    <td className="px-4 py-3">
                      <a
                        href={`https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit/blob/main/${p}`}
                        target="_blank" rel="noreferrer"
                        className="inline-flex items-center gap-1 text-purple hover:text-purple/80"
                      >
                        Source <ArrowRight className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </FadeUp>
      </div>
    </section>
  );
}
