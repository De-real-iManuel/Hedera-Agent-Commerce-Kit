import Link from "next/link";

const groups = [
  {
    title: "Product",
    links: [
      { href: "/playground", label: "x402 Playground" },
      { href: "/docs", label: "Documentation" },
      { href: "/certification", label: "Compliance Certification" },
      { href: "/#architecture", label: "Architecture" },
    ],
  },
  {
    title: "Repo",
    links: [
      { href: "https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit", label: "GitHub" },
      { href: "https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit/issues", label: "Issues" },
      { href: "https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit/blob/main/ROADMAP.md", label: "Roadmap" },
    ],
  },
  {
    title: "Hedera",
    links: [
      { href: "https://portal.hedera.com", label: "Portal" },
      { href: "https://hashscan.io/testnet", label: "HashScan" },
      { href: "https://mirrornode.hedera.com", label: "Mirror Node" },
      { href: "https://docs.hedera.com/hedera/open-source-solutions/ai-studio-on-hedera", label: "Agent Kit" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border bg-surface-1 mt-24">
      <div className="container mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold tracking-tight text-purple">HACK</span>
            <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 font-mono text-[10px] text-text-muted">
              MIT
            </span>
          </div>
          <p className="mt-3 text-sm text-text-secondary max-w-xs">
            Infrastructure for building x402-paid AI services on Hedera.
          </p>
        </div>

        {groups.map((g) => (
          <div key={g.title}>
            <h4 className="text-xs font-semibold uppercase tracking-widest text-text-muted">
              {g.title}
            </h4>
            <ul className="mt-4 space-y-2">
              {g.links.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    target={l.href.startsWith("http") ? "_blank" : undefined}
                    className="text-sm text-text-secondary hover:text-text-primary"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-border">
        <div className="container mx-auto px-6 py-6 text-xs text-text-muted flex flex-col md:flex-row items-center justify-between gap-2">
          <div>© 2026 Hedera Agent Commerce Kit · MIT License</div>
          <div>Built on Hedera Testnet · Not financial advice</div>
        </div>
      </div>
    </footer>
  );
}
