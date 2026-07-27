"use client";
import { useEffect, useState } from "react";
import { FadeUp } from "@/components/ui/Motion";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Star, GitFork, AlertCircle, GitCommit } from "lucide-react";

interface RepoStats {
  stars: number;
  forks: number;
  issues: number;
  updatedAt: string;
}

export function OpenSourceSection() {
  const [stats, setStats] = useState<RepoStats | null>(null);

  useEffect(() => {
    fetch("https://api.github.com/repos/De-real-iManuel/Hedera-Agent-Commerce-Kit", {
      headers: { Accept: "application/vnd.github+json" },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setStats({
          stars: d.stargazers_count,
          forks: d.forks_count,
          issues: d.open_issues_count,
          updatedAt: d.pushed_at,
        });
      })
      .catch(() => {});
  }, []);

  return (
    <section className="border-t border-border py-24">
      <div className="container mx-auto px-6 max-w-4xl">
        <FadeUp className="text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Open source infrastructure
          </h2>
          <p className="mt-4 text-text-secondary text-lg leading-relaxed">
            HACK is MIT licensed. The toolkit, the compliance engine, the state machine, and the
            Hedera integrations are all importable into your own project.
          </p>
        </FadeUp>

        <FadeUp delay={0.15} className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-4">
          <CodeBlock
            code={`# Coming soon\npip install hack-hedera`}
            language="bash"
            filename="pip"
          />
          <CodeBlock
            code={`git clone https://github.com/De-real-iManuel/Hedera-Agent-Commerce-Kit\n./scripts/install.sh`}
            language="bash"
            filename="from source"
          />
        </FadeUp>

        <FadeUp delay={0.25} className="mt-10 grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat icon={Star} color="text-amber" label="Stars" value={stats?.stars} />
          <Stat icon={GitFork} color="text-cyan" label="Forks" value={stats?.forks} />
          <Stat icon={AlertCircle} color="text-red" label="Issues" value={stats?.issues} />
          <Stat
            icon={GitCommit}
            color="text-green"
            label="Last commit"
            value={stats ? new Date(stats.updatedAt).toLocaleDateString() : undefined}
          />
        </FadeUp>
      </div>
    </section>
  );
}

function Stat({
  icon: Icon,
  color,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  label: string;
  value: number | string | undefined;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-1 p-4">
      <div className="flex items-center gap-2 text-xs text-text-muted">
        <Icon className={`h-3.5 w-3.5 ${color}`} />
        <span className="uppercase tracking-widest">{label}</span>
      </div>
      <div className="mt-2 text-xl font-mono text-text-primary">
        {value ?? "—"}
      </div>
    </div>
  );
}
