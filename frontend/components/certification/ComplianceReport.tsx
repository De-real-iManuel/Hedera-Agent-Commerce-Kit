"use client";
import Link from "next/link";
import { useState } from "react";
import {
  Download, FileJson, FileText, Award,
  Check, X, AlertTriangle, Info, Copy, ExternalLink,
} from "lucide-react";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { HashScanLink, HCSTopicBadge } from "@/components/ui/HashScanLink";
import { Button, LinkButton } from "@/components/ui/Button";
import { CopyButton } from "@/components/ui/CopyButton";
import { FadeUp } from "@/components/ui/Motion";
import type { CertificationReport, RuleResult, SecurityFinding } from "@/lib/types";
import { cn, formatTxId } from "@/lib/utils";

export function ComplianceReport({ report }: { report: CertificationReport }) {
  const [jsonOpen, setJsonOpen] = useState(false);

  const score = report.score;
  const isCertified  = score >= 80;
  const isConditional = score >= 60 && score < 80;
  const verdict      = isCertified ? "CERTIFIED" : isConditional ? "CONDITIONAL" : "FAILED";
  const verdictStyle = isCertified
    ? "text-green border-green/40 bg-green/10"
    : isConditional
    ? "text-amber border-amber/40 bg-amber/10"
    : "text-red border-red/40 bg-red/10";

  const accentBar = isCertified
    ? "bg-gradient-to-r from-purple via-cyan to-green"
    : isConditional
    ? "bg-gradient-to-r from-amber to-orange-400"
    : "bg-red/40";

  return (
    <div className="min-h-screen bg-[#09090b]">
      <div className="container mx-auto px-4 sm:px-6 py-10 md:py-16 max-w-4xl">

        {/* ── Header card ─────────────────────────────────────────── */}
        <FadeUp>
          <div className="rounded-xl border border-border bg-[#0f0f12] overflow-hidden">
            <div className={cn("h-[3px] w-full", accentBar)} />
            <div className="p-5 sm:p-8">
              <div className="text-[10px] uppercase tracking-widest text-text-muted">
                Compliance Report
              </div>
              <h1 className="mt-2 text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight font-mono break-all">
                {report.service_name}
              </h1>
              <div className="mt-1.5 text-xs text-text-muted">
                {new Date(report.certified_at * 1000).toLocaleString()} · HACK v{report.framework_version} · Hedera {report.network}
              </div>

              {/* Metadata grid */}
              <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {report.transaction_id && (
                  <MetaRow label="Payment TX" value={formatTxId(report.transaction_id)}>
                    <HashScanLink txId={report.transaction_id} label="HashScan ↗" />
                  </MetaRow>
                )}
                {report.hcs_topic && (
                  <MetaRow label="HCS Receipt" value={report.hcs_topic}>
                    <HCSTopicBadge topicId={report.hcs_topic} />
                  </MetaRow>
                )}
                {report.analysis_hash && (
                  <MetaRow label="Analysis Hash" value={report.analysis_hash.slice(0, 20) + "…"}>
                    <CopyButton value={report.analysis_hash} />
                  </MetaRow>
                )}
                {report.certificate_id && (
                  <MetaRow label="Certificate" value={report.certificate_id.slice(0, 16) + "…"}>
                    <Link
                      href={`/certification/certificate/${report.certificate_id}`}
                      className="shrink-0 inline-flex items-center gap-1 text-[10px] text-purple hover:text-purple/80 font-mono"
                    >
                      View NFT <ExternalLink className="h-2.5 w-2.5" />
                    </Link>
                  </MetaRow>
                )}
              </div>
            </div>
          </div>
        </FadeUp>

        {/* ── Score + verdict ──────────────────────────────────────── */}
        <FadeUp delay={0.08} className="mt-6">
          <div className="rounded-xl border border-border bg-[#0f0f12] p-5 sm:p-8 flex flex-col sm:flex-row items-center gap-6 sm:gap-8">
            <div className="shrink-0">
              <ScoreRing score={score} size="lg" />
            </div>
            <div className="text-center sm:text-left">
              <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">
                Verdict
              </div>
              <div className={cn(
                "inline-flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-mono tracking-widest font-semibold",
                verdictStyle,
              )}>
                <Award className="h-3.5 w-3.5" />
                {verdict}
              </div>
              <p className="mt-3 text-sm text-text-secondary max-w-sm leading-relaxed">
                {isCertified
                  ? "This service fully meets HACK x402 compliance criteria. A soulbound NFT certificate has been issued and anchored on Hedera HCS."
                  : isConditional
                  ? "This service conditionally meets HACK compliance criteria. A conditional certificate has been issued. Address the findings below to reach full certification."
                  : "This service does not currently meet the certification threshold. Review the findings and re-submit after remediation."}
              </p>
              {report.certificate_id && (
                <div className="mt-4">
                  <LinkButton size="sm" href={`/certification/certificate/${report.certificate_id}`}>
                    <Award className="h-3.5 w-3.5" />
                    View Soulbound Certificate →
                  </LinkButton>
                </div>
              )}
            </div>
          </div>
        </FadeUp>

        {/* ── x402 rules ───────────────────────────────────────────── */}
        <RuleSection title="x402 Compliance" rules={report.x402_rules} delay={0.12} />

        {/* ── Hedera rules ─────────────────────────────────────────── */}
        <RuleSection title="Hedera Integration" rules={report.hedera_rules} delay={0.14} />

        {/* ── Security findings ────────────────────────────────────── */}
        {report.security_findings.length > 0 && (
          <FadeUp delay={0.16} className="mt-8">
            <SectionHeader title="Security Analysis" />
            <SecurityGrid findings={report.security_findings} />
          </FadeUp>
        )}

        {/* ── Recommendations ──────────────────────────────────────── */}
        {report.recommendations && (
          <FadeUp delay={0.18} className="mt-8">
            <SectionHeader title="Recommendations" />
            <div className="rounded-xl border border-border bg-[#0f0f12] p-5 sm:p-6">
              <MarkdownRenderer content={report.recommendations} />
            </div>
          </FadeUp>
        )}

        {/* ── AI Skill File ─────────────────────────────────────────── */}
        {report.skill_md && (
          <FadeUp delay={0.2} className="mt-8">
            <SectionHeader title="AI Skill File" />
            <CodeBlock code={report.skill_md} language="markdown" filename="SKILL.md" />
          </FadeUp>
        )}

        {/* ── Sticky export bar ────────────────────────────────────── */}
        <FadeUp delay={0.22} className="mt-8 sticky bottom-4 z-10">
          <div className="rounded-xl border border-border bg-[#0f0f12]/95 backdrop-blur-md p-3 sm:p-4 flex flex-wrap gap-2 justify-between items-center shadow-2xl">
            <div className="text-[10px] text-text-muted font-mono hidden sm:block">
              {report.report_id.slice(0, 16)}…
            </div>
            <div className="flex flex-wrap gap-2 w-full sm:w-auto">
              <Button size="sm" variant="ghost" onClick={() => window.print()} className="flex-1 sm:flex-none">
                <FileText className="h-3.5 w-3.5" /> PDF
              </Button>
              <Button
                size="sm" variant="ghost"
                onClick={() => downloadBlob(report.skill_md, `${report.service_name}.SKILL.md`, "text/markdown")}
                className="flex-1 sm:flex-none"
              >
                <Download className="h-3.5 w-3.5" /> SKILL.md
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setJsonOpen(o => !o)} className="flex-1 sm:flex-none">
                <FileJson className="h-3.5 w-3.5" /> {jsonOpen ? "Hide" : "JSON"}
              </Button>
              {report.certificate_id && (
                <LinkButton size="sm" href={`/certification/certificate/${report.certificate_id}`} className="flex-1 sm:flex-none">
                  <Award className="h-3.5 w-3.5" /> Certificate
                </LinkButton>
              )}
            </div>
          </div>
          {jsonOpen && (
            <div className="mt-3">
              <CodeBlock code={JSON.stringify(report, null, 2)} language="json" filename="report.json" />
            </div>
          )}
        </FadeUp>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ title }: { title: string }) {
  return (
    <h2 className="text-base sm:text-lg font-semibold tracking-tight mb-3">
      {title}
    </h2>
  );
}

function MetaRow({
  label, value, children,
}: { label: string; value: string; children?: React.ReactNode }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-text-muted">{label}</div>
      <div className="mt-0.5 flex items-center gap-1.5 font-mono text-text-primary text-xs min-w-0">
        <span className="truncate">{value}</span>
        {children}
      </div>
    </div>
  );
}

function RuleSection({ title, rules, delay = 0 }: {
  title: string; rules: RuleResult[]; delay?: number;
}) {
  const passed = rules.filter(r => r.passed).length;
  if (rules.length === 0) return null;
  return (
    <FadeUp delay={delay} className="mt-8">
      <div className="flex items-center justify-between mb-3">
        <SectionHeader title={title} />
        <span className={cn(
          "text-xs font-mono px-2 py-0.5 rounded-full border",
          passed === rules.length
            ? "text-green border-green/40 bg-green/10"
            : passed > 0
            ? "text-amber border-amber/40 bg-amber/10"
            : "text-red border-red/40 bg-red/10",
        )}>
          {passed}/{rules.length} ✓
        </span>
      </div>
      <div className="rounded-xl border border-border bg-[#0f0f12] divide-y divide-border/50">
        {rules.map(r => (
          <div key={r.id} className="flex items-start gap-3 px-4 sm:px-6 py-3.5">
            <div className="mt-0.5 shrink-0">
              {r.passed
                ? <Check className="h-4 w-4 text-green" />
                : <X className="h-4 w-4 text-red" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-primary">{r.name}</div>
              <div className="mt-0.5 text-xs text-text-secondary leading-relaxed">{r.detail}</div>
            </div>
            {r.severity && r.severity !== "suggestion" && !r.passed && (
              <span className={cn(
                "shrink-0 text-[9px] uppercase tracking-widest font-mono px-1.5 py-0.5 rounded border mt-0.5",
                r.severity === "critical" && "text-red border-red/40 bg-red/10",
                r.severity === "medium"   && "text-amber border-amber/40 bg-amber/10",
                r.severity === "warning"  && "text-amber border-amber/40 bg-amber/10",
              )}>
                {r.severity}
              </span>
            )}
          </div>
        ))}
      </div>
    </FadeUp>
  );
}

function SecurityGrid({ findings }: { findings: SecurityFinding[] }) {
  const counts = { critical: 0, medium: 0, warning: 0, suggestion: 0 };
  findings.forEach(f => { if (f.severity in counts) counts[f.severity as keyof typeof counts]++; });
  const total = findings.length;
  if (total === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-[#0f0f12] overflow-hidden">
      {/* Summary strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y sm:divide-y-0 divide-border/50 border-b border-border/50">
        {([
          ["Critical",    "critical",   "text-red   border-red/30   bg-red/5"],
          ["Medium",      "medium",     "text-amber border-amber/30 bg-amber/5"],
          ["Warnings",    "warning",    "text-amber border-amber/30 bg-amber/5"],
          ["Suggestions", "suggestion", "text-cyan  border-cyan/30  bg-cyan/5"],
        ] as const).map(([label, key, cls]) => (
          <div key={key} className={cn("px-4 py-3 flex items-center justify-between", cls)}>
            <span className="text-[10px] uppercase tracking-widest">{label}</span>
            <span className="text-sm font-mono font-bold">{counts[key]}</span>
          </div>
        ))}
      </div>

      {/* Findings list */}
      <ul className="divide-y divide-border/40">
        {findings.map(f => (
          <li key={f.id} className="flex items-start gap-3 px-4 sm:px-6 py-4">
            {f.severity === "critical" || f.severity === "medium"
              ? <AlertTriangle className={cn("h-4 w-4 mt-0.5 shrink-0", f.severity === "critical" ? "text-red" : "text-amber")} />
              : <Info className="h-4 w-4 mt-0.5 shrink-0 text-cyan" />}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-baseline gap-2">
                <span className={cn(
                  "text-[9px] uppercase tracking-widest font-mono",
                  f.severity === "critical"  && "text-red",
                  f.severity === "medium"    && "text-amber",
                  f.severity === "warning"   && "text-amber",
                  f.severity === "suggestion"&& "text-cyan",
                )}>
                  {f.severity}
                </span>
                <span className="text-sm font-medium text-text-primary">{f.title}</span>
              </div>
              <div className="mt-1 text-xs text-text-secondary leading-relaxed">{f.detail}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function downloadBlob(data: string, filename: string, mime: string) {
  const blob = new Blob([data], { type: mime });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  a.remove(); URL.revokeObjectURL(url);
}
