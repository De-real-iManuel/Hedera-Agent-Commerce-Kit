"use client";
import { Card } from "@/components/ui/card";

function ScoreRing({ score = 0 }) {
  const s = Math.max(0, Math.min(100, Math.round(score)));
  const color = s >= 85 ? "#10b981" : s >= 65 ? "#06b6d4" : s >= 40 ? "#f59e0b" : "#ef4444";
  const r = 26;
  const c = 2 * Math.PI * r;
  const off = c - (s / 100) * c;
  return (
    <svg width="72" height="72" viewBox="0 0 72 72" className="shrink-0">
      <circle cx="36" cy="36" r={r} stroke="#262626" strokeWidth="6" fill="none" />
      <circle
        cx="36"
        cy="36"
        r={r}
        stroke={color}
        strokeWidth="6"
        fill="none"
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={off}
        transform="rotate(-90 36 36)"
      />
      <text x="36" y="41" textAnchor="middle" fill="#f5f5f5" fontSize="18" fontWeight="600">
        {s}
      </text>
    </svg>
  );
}

function verdictLabel(score) {
  if (score >= 85) return { label: "Certified", tone: "text-emerald-400" };
  if (score >= 65) return { label: "Passing", tone: "text-cyan-400" };
  if (score >= 40) return { label: "Needs work", tone: "text-amber-400" };
  return { label: "Failing", tone: "text-red-400" };
}

export function ComplianceReportCard({ output }) {
  const raw = output?.raw;
  if (!raw) return null;
  const isCheck = raw.data?.check;
  const report = raw.report || raw.data?.check || raw.data;
  if (!report) return null;

  const score = report.score ?? report.overall_score ?? 0;
  const v = verdictLabel(score);
  const rules = report.rules || report.checks || report.findings || [];
  const rulesList = Array.isArray(rules) ? rules.slice(0, 8) : [];
  const reportId = report.report_id || report.id;
  const serviceName = report.service_name || raw.data?.submission?.service_name;

  return (
    <Card className="border-neutral-800 bg-neutral-950">
      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-neutral-500">
              {isCheck ? "Compliance Check" : "Certification Report"}
            </div>
            <div className="mt-1 text-lg font-semibold text-neutral-50">
              {serviceName || "Service"}
            </div>
            {reportId && (
              <div className="mt-1 font-mono text-[11px] text-neutral-500">{reportId}</div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <ScoreRing score={score} />
            <div>
              <div className={`text-sm font-medium ${v.tone}`}>{v.label}</div>
              <div className="text-xs text-neutral-500">score</div>
            </div>
          </div>
        </div>

        {rulesList.length > 0 && (
          <div className="mt-4 space-y-1.5">
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Rules
            </div>
            <ul className="divide-y divide-neutral-900 rounded-md border border-neutral-900">
              {rulesList.map((r, i) => {
                const passed = r.passed ?? r.pass ?? r.status === "pass";
                return (
                  <li
                    key={r.id || r.name || i}
                    className="flex items-start gap-3 px-3 py-2 text-xs"
                  >
                    <span
                      className={`mt-0.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                        passed ? "bg-emerald-400" : "bg-red-400"
                      }`}
                    />
                    <span className="flex-1 text-neutral-200">
                      {r.name || r.title || r.id || "Rule"}
                    </span>
                    <span className="text-neutral-500">
                      {r.severity || (passed ? "pass" : "fail")}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {report.recommendations && (
          <div className="mt-4">
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Top recommendation
            </div>
            <p className="mt-1 text-xs leading-relaxed text-neutral-300">
              {Array.isArray(report.recommendations)
                ? report.recommendations[0]
                : report.recommendations}
            </p>
          </div>
        )}

        {reportId && (
          <div className="mt-4 flex flex-wrap gap-2">
            <a
              className="rounded-md border border-neutral-800 bg-neutral-900 px-2.5 py-1 text-[11px] text-neutral-200 hover:border-neutral-700"
              href={`/certification/${encodeURIComponent(reportId)}`}
              target="_blank"
              rel="noreferrer"
            >
              Open full report ↗
            </a>
          </div>
        )}
      </div>
    </Card>
  );
}

export function ComplianceReportRow({ output }) {
  const r = output?.raw?.report || output?.raw?.data?.check || output?.raw?.data || {};
  const score = r.score ?? r.overall_score;
  return (
    <span className="text-neutral-300">
      {r.service_name || "Report"} · score {score ?? "—"}
    </span>
  );
}
